"""
FAISS-based Approximate Nearest Neighbor similarity index.

Replaces the O(n²) in-memory cosine similarity matrix with a
scalable ANN index that handles 100k+ programs efficiently.

Supports:
  - FAISS Flat (exact, small datasets)
  - FAISS IVF (approximate, large datasets)
  - Automatic fallback to sklearn if FAISS not installed

Usage:
    from inference.similarity_index import SimilarityIndex

    index = SimilarityIndex()
    index.build(feature_matrix, program_ids)
    similar = index.query(program_idx=42, top_n=10)
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Try FAISS import
try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    logger.info("faiss-cpu not installed — using sklearn NearestNeighbors fallback")


class SimilarityIndex:
    """
    Scalable similarity search using FAISS or sklearn fallback.

    Builds an index from pre-computed feature vectors and supports
    fast k-nearest-neighbor queries for finding similar programs.
    """

    def __init__(
        self,
        n_clusters: int = 100,
        n_probe: int = 10,
        metric: str = "cosine",
    ):
        """
        Args:
            n_clusters: Number of IVF clusters for FAISS (used when > 10k items).
            n_probe: Number of clusters to probe at query time.
            metric: Similarity metric ("cosine" or "l2").
        """
        self.n_clusters = n_clusters
        self.n_probe = n_probe
        self.metric = metric
        self._index = None
        self._program_ids: List[str] = []
        self._n_items = 0
        self._d = 0  # feature dimension
        self._backend = "none"

    def build(
        self,
        feature_matrix: np.ndarray,
        program_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Build the similarity index from feature vectors.

        Args:
            feature_matrix: (n_items, n_features) array of feature vectors.
            program_ids: Optional list of program identifiers.
                If None, uses integer indices.
        """
        self._n_items, self._d = feature_matrix.shape
        self._program_ids = program_ids or [str(i) for i in range(self._n_items)]

        # Ensure float32 for FAISS
        vectors = feature_matrix.astype(np.float32)

        # Normalize for cosine similarity
        if self.metric == "cosine":
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms = np.clip(norms, 1e-8, None)
            vectors = vectors / norms

        if HAS_FAISS:
            self._build_faiss(vectors)
        else:
            self._build_sklearn(vectors)

        logger.info(
            f"Similarity index built: {self._n_items} items, "
            f"dim={self._d}, backend={self._backend}"
        )

    def _build_faiss(self, vectors: np.ndarray) -> None:
        """Build FAISS index (exact or IVF based on size)."""
        if self._n_items < 5000:
            # Small dataset: exact search
            if self.metric == "cosine":
                self._index = faiss.IndexFlatIP(self._d)  # Inner product = cosine for normalized
            else:
                self._index = faiss.IndexFlatL2(self._d)
            self._backend = "faiss_flat"
        else:
            # Large dataset: IVF approximate search
            n_clusters = min(self.n_clusters, self._n_items // 10)
            quantizer = faiss.IndexFlatIP(self._d) if self.metric == "cosine" else faiss.IndexFlatL2(self._d)
            self._index = faiss.IndexIVFFlat(quantizer, self._d, n_clusters)
            self._index.train(vectors)
            self._index.nprobe = self.n_probe
            self._backend = "faiss_ivf"

        self._index.add(vectors)
        self._vectors = vectors  # Keep for re-query

    def _build_sklearn(self, vectors: np.ndarray) -> None:
        """Fallback: sklearn NearestNeighbors."""
        from sklearn.neighbors import NearestNeighbors

        metric = "cosine" if self.metric == "cosine" else "euclidean"
        self._index = NearestNeighbors(
            n_neighbors=min(50, self._n_items),
            metric=metric,
            algorithm="auto",
        )
        self._index.fit(vectors)
        self._vectors = vectors
        self._backend = "sklearn"

    def query(
        self,
        program_idx: int,
        top_n: int = 10,
    ) -> List[Dict]:
        """
        Find the most similar programs to a given program.

        Args:
            program_idx: Index of the query program.
            top_n: Number of similar programs to return.

        Returns:
            List of dicts with 'program_id', 'similarity', 'rank'.
        """
        if self._index is None:
            raise RuntimeError("Index not built — call build() first")

        if program_idx < 0 or program_idx >= self._n_items:
            raise ValueError(f"Invalid program_idx {program_idx} (range: 0-{self._n_items-1})")

        query_vector = self._vectors[program_idx:program_idx+1]

        if self._backend.startswith("faiss"):
            # FAISS query (returns distances and indices)
            scores, indices = self._index.search(query_vector, top_n + 1)
            scores = scores[0]
            indices = indices[0]
        else:
            # sklearn query
            distances, indices = self._index.kneighbors(query_vector, n_neighbors=top_n + 1)
            # Convert distance to similarity
            if self.metric == "cosine":
                scores = 1 - distances[0]
            else:
                scores = 1 / (1 + distances[0])
            indices = indices[0]

        results = []
        rank = 1
        for idx, score in zip(indices, scores):
            if idx == program_idx:
                continue  # Skip self
            if idx < 0:
                continue  # FAISS may return -1 for empty results

            results.append({
                "program_id": self._program_ids[int(idx)],
                "program_idx": int(idx),
                "similarity": round(float(score), 4),
                "rank": rank,
            })
            rank += 1

            if rank > top_n:
                break

        return results

    def query_by_vector(
        self,
        query_vector: np.ndarray,
        top_n: int = 10,
    ) -> List[Dict]:
        """
        Find the most similar programs to an arbitrary feature vector.

        Useful for finding programs similar to a student's ideal profile.

        Args:
            query_vector: Feature vector (1D array, same dim as index).
            top_n: Number of results to return.

        Returns:
            List of dicts with 'program_id', 'similarity', 'rank'.
        """
        if self._index is None:
            raise RuntimeError("Index not built — call build() first")

        qv = query_vector.astype(np.float32).reshape(1, -1)

        # Normalize for cosine
        if self.metric == "cosine":
            norm = np.linalg.norm(qv)
            if norm > 0:
                qv = qv / norm

        if self._backend.startswith("faiss"):
            scores, indices = self._index.search(qv, top_n)
            scores = scores[0]
            indices = indices[0]
        else:
            distances, indices = self._index.kneighbors(qv, n_neighbors=top_n)
            scores = 1 - distances[0] if self.metric == "cosine" else 1 / (1 + distances[0])
            indices = indices[0]

        results = []
        for rank, (idx, score) in enumerate(zip(indices, scores), 1):
            if idx < 0:
                continue
            results.append({
                "program_id": self._program_ids[int(idx)],
                "program_idx": int(idx),
                "similarity": round(float(score), 4),
                "rank": rank,
            })

        return results

    # ── Persistence ──────────────────────────────────────────────────────────

    def save(self, path: str = "model_artifacts/similarity_index") -> None:
        """Save the index to disk."""
        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)

        # Save vectors and IDs
        np.save(save_dir / "vectors.npy", self._vectors)
        import json
        with open(save_dir / "program_ids.json", "w") as f:
            json.dump(self._program_ids, f)

        # Save FAISS index if available
        if HAS_FAISS and self._backend.startswith("faiss"):
            faiss.write_index(self._index, str(save_dir / "faiss.index"))

        logger.info(f"Similarity index saved: {save_dir}")

    def load(self, path: str = "model_artifacts/similarity_index") -> None:
        """Load the index from disk."""
        load_dir = Path(path)

        self._vectors = np.load(load_dir / "vectors.npy")
        self._n_items, self._d = self._vectors.shape

        import json
        with open(load_dir / "program_ids.json") as f:
            self._program_ids = json.load(f)

        faiss_path = load_dir / "faiss.index"
        if HAS_FAISS and faiss_path.exists():
            self._index = faiss.read_index(str(faiss_path))
            self._backend = "faiss_loaded"
        else:
            self._build_sklearn(self._vectors)

        logger.info(f"Similarity index loaded: {self._n_items} items")

    @property
    def stats(self) -> Dict:
        """Return index statistics."""
        return {
            "n_items": self._n_items,
            "dimensions": self._d,
            "backend": self._backend,
            "memory_mb": round(self._vectors.nbytes / (1024 * 1024), 2) if self._vectors is not None else 0,
        }
