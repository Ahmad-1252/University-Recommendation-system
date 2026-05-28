"""
Ranking-aware evaluation metrics for recommendation systems.

Classification metrics (accuracy, F1) answer the wrong question for recommendations.
They measure "did we label the tier correctly?" when the real question is
"did we rank the best programs highest?"

These metrics answer the right question.

Usage:
    from evaluation.ranking_metrics import evaluate_recommendations

    report = evaluate_recommendations(predictions_df, ground_truth_df, k_values=[5, 10, 20])
    print(report)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ── Core Ranking Metrics ─────────────────────────────────────────────────────

def ndcg_at_k(
    recommended: List[str],
    relevant: Set[str],
    k: int,
    relevance_scores: Optional[Dict[str, float]] = None,
) -> float:
    """
    Normalized Discounted Cumulative Gain at k.

    Measures ranking quality — items near the top of the list are weighted
    more heavily. A perfect NDCG@k means the top-k items are the most
    relevant items in the ideal order.

    Args:
        recommended: Ordered list of recommended item IDs.
        relevant: Set of truly relevant item IDs.
        k: Number of top items to evaluate.
        relevance_scores: Optional dict mapping item_id → graded relevance
            (e.g., 3=top, 2=good, 1=standard). If None, binary relevance.

    Returns:
        NDCG@k score in [0.0, 1.0]. Higher is better.
    """
    if not recommended or not relevant:
        return 0.0

    top_k = recommended[:k]

    # Compute DCG
    dcg = 0.0
    for i, item in enumerate(top_k):
        if item in relevant:
            rel = relevance_scores.get(item, 1.0) if relevance_scores else 1.0
            dcg += rel / np.log2(i + 2)  # +2 because log2(1)=0

    # Compute ideal DCG
    if relevance_scores:
        ideal_rels = sorted(
            [relevance_scores.get(item, 0.0) for item in relevant],
            reverse=True,
        )[:k]
    else:
        ideal_rels = [1.0] * min(k, len(relevant))

    idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_rels))

    if idcg == 0:
        return 0.0

    return dcg / idcg


def map_at_k(
    recommended: List[str],
    relevant: Set[str],
    k: int,
) -> float:
    """
    Mean Average Precision at k.

    Measures both precision and ordering. A high MAP@k means we found
    many relevant items AND found them early in the list.

    Args:
        recommended: Ordered list of recommended item IDs.
        relevant: Set of truly relevant item IDs.
        k: Number of top items to evaluate.

    Returns:
        AP@k score in [0.0, 1.0]. Higher is better.
    """
    if not recommended or not relevant:
        return 0.0

    top_k = recommended[:k]
    score = 0.0
    hits = 0

    for i, item in enumerate(top_k):
        if item in relevant:
            hits += 1
            precision_at_i = hits / (i + 1)
            score += precision_at_i

    if not relevant:
        return 0.0

    return score / min(len(relevant), k)


def precision_at_k(
    recommended: List[str],
    relevant: Set[str],
    k: int,
) -> float:
    """
    Precision at k — fraction of top-k recommendations that are relevant.

    Args:
        recommended: Ordered list of recommended item IDs.
        relevant: Set of truly relevant item IDs.
        k: Number of top items to evaluate.

    Returns:
        Precision@k in [0.0, 1.0]. Higher is better.
    """
    if not recommended or k == 0:
        return 0.0

    top_k = recommended[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / k


def recall_at_k(
    recommended: List[str],
    relevant: Set[str],
    k: int,
) -> float:
    """
    Recall at k — fraction of relevant items found in top-k.

    Args:
        recommended: Ordered list of recommended item IDs.
        relevant: Set of truly relevant item IDs.
        k: Number of top items to evaluate.

    Returns:
        Recall@k in [0.0, 1.0]. Higher is better.
    """
    if not relevant:
        return 0.0

    top_k = recommended[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / len(relevant)


def hit_rate_at_k(
    recommended: List[str],
    relevant: Set[str],
    k: int,
) -> float:
    """
    Hit Rate at k — binary indicator: is at least one relevant item in top-k?

    Args:
        recommended: Ordered list of recommended item IDs.
        relevant: Set of truly relevant item IDs.
        k: Number of top items to evaluate.

    Returns:
        1.0 if any relevant item in top-k, else 0.0.
    """
    if not recommended or not relevant:
        return 0.0

    top_k = set(recommended[:k])
    return 1.0 if top_k.intersection(relevant) else 0.0


def mrr(
    recommended: List[str],
    relevant: Set[str],
) -> float:
    """
    Mean Reciprocal Rank — 1/position of the first relevant item.

    Args:
        recommended: Ordered list of recommended item IDs.
        relevant: Set of truly relevant item IDs.

    Returns:
        MRR score in [0.0, 1.0]. Higher is better.
    """
    for i, item in enumerate(recommended):
        if item in relevant:
            return 1.0 / (i + 1)
    return 0.0


# ── Evaluation Report ────────────────────────────────────────────────────────

@dataclass
class RankingEvalReport:
    """Aggregated ranking evaluation results across all queries."""
    k_values: List[int] = field(default_factory=lambda: [5, 10, 20])
    n_queries: int = 0
    metrics: Dict[str, Dict[int, float]] = field(default_factory=dict)
    mean_mrr: float = 0.0

    def summary(self) -> str:
        lines = [f"Ranking Evaluation Report ({self.n_queries} queries)"]
        lines.append("-" * 55)
        lines.append(f"{'Metric':<20} " + " ".join(f"@{k:<4}" for k in self.k_values))
        lines.append("-" * 55)
        for metric_name, k_scores in self.metrics.items():
            values = " ".join(f"{k_scores.get(k, 0.0):.4f}" for k in self.k_values)
            lines.append(f"{metric_name:<20} {values}")
        lines.append(f"{'MRR':<20} {self.mean_mrr:.4f}")
        return "\n".join(lines)


def evaluate_recommendations(
    predictions_df: pd.DataFrame,
    ground_truth_df: pd.DataFrame,
    k_values: List[int] = None,
    item_col: str = "program_name",
    score_col: str = "match_score",
    query_col: str = "query_id",
    relevance_col: str = "relevant",
) -> RankingEvalReport:
    """
    Evaluate recommendation quality using ranking metrics.

    For synthetic datasets where no real user interactions exist, this function
    can be used with proxy ground truth:
    - Hold out a random 20% of programs per "tier" as ground truth
    - Define "relevant" as programs that match the user's filters
      AND are in the held-out set
    - Run the recommendation engine as normal on the remaining 80%
    - Measure how well the model ranks programs that would actually
      be relevant to the student

    Args:
        predictions_df: DataFrame with columns [query_col, item_col, score_col].
            Must be sorted by score (descending) within each query group.
        ground_truth_df: DataFrame with columns [query_col, item_col, relevance_col].
            relevance_col is 1 for relevant items, 0 otherwise.
        k_values: List of k values to evaluate (default [5, 10, 20]).
        item_col: Column name for item identifiers.
        score_col: Column name for predicted scores.
        query_col: Column name for query/user identifiers.
        relevance_col: Column name for binary relevance labels.

    Returns:
        RankingEvalReport with aggregated metrics.
    """
    if k_values is None:
        k_values = [5, 10, 20]

    report = RankingEvalReport(k_values=k_values)

    # Group by query
    all_ndcg = {k: [] for k in k_values}
    all_map = {k: [] for k in k_values}
    all_prec = {k: [] for k in k_values}
    all_recall = {k: [] for k in k_values}
    all_hit = {k: [] for k in k_values}
    all_mrr = []

    query_ids = predictions_df[query_col].unique()

    for qid in query_ids:
        # Get predicted ranking
        pred_mask = predictions_df[query_col] == qid
        pred_items = predictions_df.loc[pred_mask].sort_values(
            score_col, ascending=False
        )[item_col].tolist()

        # Get relevant items
        gt_mask = (ground_truth_df[query_col] == qid) & (ground_truth_df[relevance_col] == 1)
        relevant_items = set(ground_truth_df.loc[gt_mask, item_col].tolist())

        if not relevant_items:
            continue

        for k in k_values:
            all_ndcg[k].append(ndcg_at_k(pred_items, relevant_items, k))
            all_map[k].append(map_at_k(pred_items, relevant_items, k))
            all_prec[k].append(precision_at_k(pred_items, relevant_items, k))
            all_recall[k].append(recall_at_k(pred_items, relevant_items, k))
            all_hit[k].append(hit_rate_at_k(pred_items, relevant_items, k))

        all_mrr.append(mrr(pred_items, relevant_items))

    report.n_queries = len(query_ids)
    report.mean_mrr = float(np.mean(all_mrr)) if all_mrr else 0.0

    report.metrics = {
        "NDCG": {k: float(np.mean(v)) for k, v in all_ndcg.items() if v},
        "MAP": {k: float(np.mean(v)) for k, v in all_map.items() if v},
        "Precision": {k: float(np.mean(v)) for k, v in all_prec.items() if v},
        "Recall": {k: float(np.mean(v)) for k, v in all_recall.items() if v},
        "HitRate": {k: float(np.mean(v)) for k, v in all_hit.items() if v},
    }

    return report


# ── Synthetic Data Evaluation Setup ──────────────────────────────────────────

def create_synthetic_ground_truth(
    programs_df: pd.DataFrame,
    n_queries: int = 50,
    holdout_fraction: float = 0.2,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Create proxy ground truth for offline evaluation with synthetic data.

    Since no real user interaction data exists, we simulate evaluation by:
    1. Creating synthetic "student queries" with random profiles
    2. Defining relevance as: program matches filters AND is in top tier

    This is NOT a substitute for A/B testing with real users.
    It is a minimum viable evaluation to catch model regressions.

    Args:
        programs_df: DataFrame with all program data.
        n_queries: Number of synthetic queries to generate.
        holdout_fraction: Fraction of programs to hold out as candidates.
        random_state: Random seed.

    Returns:
        Tuple of (queries_df, ground_truth_df).
    """
    rng = np.random.RandomState(random_state)

    countries = programs_df["country"].unique() if "country" in programs_df.columns else ["Unknown"]
    categories = programs_df["program_category"].unique() if "program_category" in programs_df.columns else ["Unknown"]

    queries = []
    ground_truth_rows = []

    for qid in range(n_queries):
        # Random student profile
        country = rng.choice(countries)
        category = rng.choice(categories)
        budget = rng.choice([20000, 30000, 40000, 50000])
        gpa = round(rng.uniform(2.5, 4.0), 1)

        queries.append({
            "query_id": qid,
            "preferred_country": country,
            "program_category": category,
            "budget": budget,
            "gpa": gpa,
        })

        # Define relevant programs for this query
        mask = pd.Series(True, index=programs_df.index)
        if "country" in programs_df.columns:
            mask &= programs_df["country"] == country
        if "program_category" in programs_df.columns:
            mask &= programs_df["program_category"] == category
        if "tuition_international" in programs_df.columns:
            mask &= programs_df["tuition_international"] <= budget
        if "gpa_requirement_min" in programs_df.columns:
            mask &= programs_df["gpa_requirement_min"] <= gpa

        relevant_programs = programs_df[mask]
        if len(relevant_programs) == 0:
            continue

        # Hold out some as "ground truth relevant"
        n_holdout = max(1, int(len(relevant_programs) * holdout_fraction))
        holdout_idx = rng.choice(len(relevant_programs), size=n_holdout, replace=False)
        holdout = relevant_programs.iloc[holdout_idx]

        for _, prog in holdout.iterrows():
            prog_id = f"{prog.get('university_name', 'UNK')}_{prog.get('program_name', 'UNK')}"
            ground_truth_rows.append({
                "query_id": qid,
                "program_name": prog_id,
                "relevant": 1,
            })

    queries_df = pd.DataFrame(queries)
    ground_truth_df = pd.DataFrame(ground_truth_rows)

    logger.info(
        f"Created {len(queries_df)} synthetic queries with "
        f"{len(ground_truth_df)} relevant items"
    )

    return queries_df, ground_truth_df
