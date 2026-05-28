"""
Retrain script — rebuilds model artifacts with leakage-free pipeline.

Usage:
    python scripts/retrain_model.py                    # full pipeline
    python scripts/retrain_model.py --skip-leakage     # skip leakage checks (dev only)
    python scripts/retrain_model.py --data path/to.csv # custom dataset

Changes from original:
  - L1: qs_world_ranking removed from training features (used only for tier labels, then dropped)
  - L2: qs_overall_score removed from training features
  - L3: All 8 QS sub-scores removed from training features
  - L4: GroupShuffleSplit on university_name replaces flat stratified split
  - L5: Leakage checks run automatically — pipeline refuses to produce artifacts
        if any check fails
  - T1: RandomizedSearchCV actually runs (was imported but unused)
  - T2: 3-fold GroupKFold cross-validation
  - T3: Versioned artifact naming with timestamp
  - E1: Refuses accuracy >= 1.0
  - E5: DummyClassifier baseline comparison
"""

import argparse
import hashlib
import json
import logging
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.leakage_checks import (
    check_baseline_gap,
    check_group_leakage,
    check_high_accuracy_warning,
    check_perfect_metrics,
    check_target_correlation,
)

warnings.filterwarnings("ignore", category=FutureWarning)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

np.random.seed(42)

# ─── KNOWN LEAKY FEATURES ────────────────────────────────────────────────────
# These are components OF the QS ranking or directly derived from it.
# Including them as training features when the target is tier=f(qs_ranking)
# guarantees perfect accuracy via trivial memorization — not real learning.

QS_LEAKY_FEATURES = {
    "qs_world_ranking",
    "qs_overall_score",
    "qs_academic_reputation",
    "qs_employer_reputation",
    "qs_faculty_student_ratio",
    "qs_citations",
    "qs_intl_students",
    "qs_intl_faculty",
    "qs_employment_outcomes",
    "qs_sustainability",
}


def compute_data_hash(df: pd.DataFrame) -> str:
    """SHA-256 hash of DataFrame contents for reproducibility tracking."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser(description="Retrain ML pipeline (leakage-free)")
    parser.add_argument("--data", type=str, default=None, help="Path to training CSV")
    parser.add_argument(
        "--skip-leakage", action="store_true", help="Skip leakage checks (dev only)"
    )
    parser.add_argument(
        "--output-dir", type=str, default="model_artifacts", help="Output directory"
    )
    args = parser.parse_args()

    # ── Load data ────────────────────────────────────────────────────────────
    DATA_PATHS = [
        Path("data/exports/training_dataset_latest.csv"),
        Path("data/universities.csv"),
    ]
    if args.data:
        DATA_PATHS.insert(0, Path(args.data))

    df = None
    for p in DATA_PATHS:
        if p.exists():
            df = pd.read_csv(p)
            logger.info(f"Loaded {len(df)} rows from {p}")
            break

    if df is None:
        logger.error("ERROR: No data found at any of: %s", DATA_PATHS)
        sys.exit(1)

    data_hash = compute_data_hash(df)
    logger.info(f"Data hash: {data_hash}")

    # ── Auto-detect target ───────────────────────────────────────────────────
    TARGET = None
    for col in ["university_tier", "tier", "label", "target"]:
        if col in df.columns:
            TARGET = col
            break

    if TARGET is None:
        if "qs_world_ranking" in df.columns:
            df["university_tier"] = pd.cut(
                df["qs_world_ranking"].fillna(9999),
                bins=[0, 100, 500, float("inf")],
                labels=["top", "good", "standard"],
            )
            TARGET = "university_tier"
        else:
            logger.error(
                "ERROR: No target column and no qs_world_ranking to derive one"
            )
            sys.exit(1)

    # Drop rows where target is NaN
    df = df.dropna(subset=[TARGET])
    logger.info(f"Target: {TARGET} | Classes: {df[TARGET].value_counts().to_dict()}")

    # ── Feature groups ───────────────────────────────────────────────────────
    # ID columns (never used as features)
    ID_COLS = [
        c
        for c in df.columns
        if c.endswith("_id")
        or c in ["university_name", "city", "confidence_score", "data_completeness"]
    ]

    # L1-L3 FIX: Explicitly remove all QS ranking-derived features
    # These are used to CREATE the target, so they MUST NOT be training features
    leaky_present = QS_LEAKY_FEATURES.intersection(set(df.columns))
    if leaky_present:
        logger.info(
            f"LEAKAGE FIX: Removing {len(leaky_present)} QS-derived features: {sorted(leaky_present)}"
        )

    NUMERIC = [
        c
        for c in df.select_dtypes(include=[np.number]).columns
        if c != TARGET and c not in ID_COLS and c not in QS_LEAKY_FEATURES
    ]

    CATEGORICAL = [
        c
        for c in df.select_dtypes(include=["object", "category"]).columns
        if c != TARGET
        and c not in ID_COLS
        and c not in QS_LEAKY_FEATURES
        and df[c].nunique() < 200
        and df[c].nunique() > 1
    ]

    TEXT = [c for c in df.columns if c in ("specializations", "career_outcomes")]
    CATEGORICAL = [c for c in CATEGORICAL if c not in TEXT]

    logger.info(
        f"Features: {len(NUMERIC)} numeric, {len(CATEGORICAL)} categorical, {len(TEXT)} text"
    )
    logger.info(f"  Numeric: {NUMERIC}")
    logger.info(f"  Categorical: {CATEGORICAL}")

    # ── Pipeline ─────────────────────────────────────────────────────────────
    from sklearn.compose import ColumnTransformer
    from sklearn.dummy import DummyClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
    )
    from sklearn.model_selection import (
        GroupShuffleSplit,
        RandomizedSearchCV,
    )
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import LabelEncoder, OneHotEncoder, RobustScaler

    transformers = [
        (
            "num",
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", RobustScaler()),
                ]
            ),
            NUMERIC,
        ),
        (
            "cat",
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    (
                        "encoder",
                        OneHotEncoder(
                            handle_unknown="infrequent_if_exist",
                            sparse_output=True,
                            min_frequency=5,
                            max_categories=50,
                        ),
                    ),
                ]
            ),
            CATEGORICAL,
        ),
    ]
    for t in TEXT:
        transformers.append(
            (f"text_{t}", TfidfVectorizer(max_features=200, stop_words="english"), t)
        )

    preprocessor = ColumnTransformer(transformers, remainder="drop")

    # ── Label encode target ──────────────────────────────────────────────────
    le = LabelEncoder()
    y = le.fit_transform(df[TARGET].astype(str))

    DROP_COLS = [TARGET] + ID_COLS + [c for c in QS_LEAKY_FEATURES if c in df.columns]
    X = df.drop(columns=[c for c in DROP_COLS if c in df.columns])

    # ── L4 FIX: GroupShuffleSplit on university_name ──────────────────────────
    # Programs from the same university MUST NOT appear in both train and test.
    # This prevents the model from memorizing university-specific patterns.
    group_col = "university_name"
    if group_col in df.columns:
        groups = df[group_col]
        gss = GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=42)
        train_idx, test_idx = next(gss.split(X, y, groups=groups))
        logger.info(
            f"GroupShuffleSplit: {len(train_idx)} train, {len(test_idx)} test "
            f"(grouped by {group_col})"
        )
    else:
        from sklearn.model_selection import train_test_split

        logger.warning(
            f"Column '{group_col}' not found — falling back to stratified split"
        )
        indices = np.arange(len(X))
        train_idx, test_idx = train_test_split(
            indices, test_size=0.15, random_state=42, stratify=y
        )

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
    logger.info(f"Train: {len(X_train)} | Test: {len(X_test)}")

    # ── LEAKAGE CHECKS ──────────────────────────────────────────────────────
    if not args.skip_leakage:
        logger.info("Running leakage checks...")

        # Check 1: No leaky features in training data
        check_target_correlation(
            X_train,
            y_train,
            threshold=0.95,
            known_leaky_features=QS_LEAKY_FEATURES,
        )

        # Check 2: No group leakage
        check_group_leakage(df, group_col, train_idx, test_idx)

        logger.info("All leakage checks PASSED")
    else:
        logger.warning("LEAKAGE CHECKS SKIPPED (--skip-leakage flag)")

    # ── Model ────────────────────────────────────────────────────────────────
    try:
        from lightgbm import LGBMClassifier

        model = LGBMClassifier(
            n_estimators=1000,
            learning_rate=0.05,
            num_leaves=31,
            random_state=42,
            class_weight="balanced",
            verbose=-1,
            n_jobs=-1,
        )
        backend = "lightgbm"
    except ImportError:
        from sklearn.ensemble import HistGradientBoostingClassifier

        model = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.05, random_state=42
        )
        backend = "sklearn_hgb"

    pipe = Pipeline([("preprocessor", preprocessor), ("model", model)])

    # ── T1 FIX: Hyperparameter tuning with RandomizedSearchCV ────────────────
    if backend == "lightgbm":
        # REGULARIZATION: Capped to prevent overfitting on synthetic data.
        # num_leaves max 63 (was 127), max_depth max 15 (was 20).
        param_dist = {
            "model__n_estimators": [100, 200, 300, 500],
            "model__learning_rate": [0.01, 0.05, 0.1],
            "model__num_leaves": [15, 31, 63],
            "model__max_depth": [5, 10, 15],
            "model__min_child_samples": [10, 20, 30],
            "model__subsample": [0.7, 0.8, 0.9],
            "model__colsample_bytree": [0.7, 0.8, 0.9],
            "model__reg_alpha": [0.0, 0.1, 1.0],
            "model__reg_lambda": [0.0, 0.1, 1.0],
        }
    else:
        param_dist = {
            "model__max_iter": [100, 200, 300, 500],
            "model__learning_rate": [0.01, 0.05, 0.1],
            "model__max_depth": [5, 10, 20, None],
            "model__min_samples_leaf": [5, 10, 20],
        }

    # FIX: Use GroupKFold for inner CV to prevent group leakage during tuning.
    # StratifiedKFold allows the same university in both inner train/validation —
    # GroupKFold prevents this by splitting on the same group column.
    from sklearn.model_selection import GroupKFold

    cv = GroupKFold(n_splits=3)

    search = RandomizedSearchCV(
        pipe,
        param_distributions=param_dist,
        n_iter=20,
        cv=cv,
        scoring="f1_macro",
        random_state=42,
        n_jobs=-1,
        verbose=0,
    )

    # Extract group labels for inner CV (must match X_train rows)
    groups_train = (
        df.iloc[train_idx][group_col].values if group_col in df.columns else None
    )

    logger.info("Starting hyperparameter search (20 iterations, 3-fold GroupKFold)...")
    t0 = time.time()
    search.fit(X_train, y_train, groups=groups_train)
    train_time = time.time() - t0
    logger.info(f"Training: {train_time:.1f}s ({backend})")
    logger.info(f"Best params: {search.best_params_}")
    logger.info(f"Best CV F1-macro: {search.best_score_:.4f}")

    best_pipe = search.best_estimator_

    # ── Evaluate ─────────────────────────────────────────────────────────────
    y_pred = best_pipe.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average="macro")
    f1_weighted = f1_score(y_test, y_pred, average="weighted")

    logger.info(
        f"Test Accuracy: {acc:.4f} | F1-macro: {f1_macro:.4f} | F1-weighted: {f1_weighted:.4f}"
    )

    # Classification report
    class_report = classification_report(y_test, y_pred, target_names=list(le.classes_))
    logger.info(f"\nClassification Report:\n{class_report}")

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    logger.info(f"Confusion Matrix:\n{cm}")

    # ── QUALITY GATES ────────────────────────────────────────────────────────
    metrics = {"accuracy": acc, "f1_macro": f1_macro, "f1_weighted": f1_weighted}

    if not args.skip_leakage:
        # E1 FIX: Refuse perfect metrics
        check_perfect_metrics(metrics)

        # High accuracy warning
        check_high_accuracy_warning(acc, threshold=0.98)

    # E5 FIX: Multiple baselines for complexity justification
    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier

    baselines = {
        "most_frequent": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": LogisticRegression(
            max_iter=500, class_weight="balanced", random_state=42
        ),
        "decision_tree_d5": DecisionTreeClassifier(
            max_depth=5, class_weight="balanced", random_state=42
        ),
    }

    baseline_results = {}
    for bl_name, bl_model in baselines.items():
        try:
            bl_pipe = Pipeline([("preprocessor", preprocessor), ("model", bl_model)])
            bl_pipe.fit(X_train, y_train)
            bl_pred = bl_pipe.predict(X_test)
            bl_acc = accuracy_score(y_test, bl_pred)
            bl_f1 = f1_score(y_test, bl_pred, average="macro", zero_division=0)
            baseline_results[bl_name] = {"accuracy": bl_acc, "f1_macro": bl_f1}
            logger.info(
                f"Baseline {bl_name}: accuracy={bl_acc:.4f}, f1_macro={bl_f1:.4f}"
            )
        except Exception as e:
            logger.warning(f"Baseline {bl_name} failed: {e}")

    baseline_acc = baseline_results.get("most_frequent", {}).get("accuracy", 0.0)
    baseline_f1 = baseline_results.get("most_frequent", {}).get("f1_macro", 0.0)

    if not args.skip_leakage:
        baseline_gap = check_baseline_gap(
            acc, baseline_acc, min_gap=0.05, metric_name="accuracy"
        )
    else:
        baseline_gap = acc - baseline_acc

    # ── Feature Importance ───────────────────────────────────────────────────
    try:
        if backend == "lightgbm":
            importances = best_pipe.named_steps["model"].feature_importances_
            # Get feature names from preprocessor
            feature_names = best_pipe.named_steps[
                "preprocessor"
            ].get_feature_names_out()
            # Sort by importance
            importance_pairs = sorted(
                zip(feature_names, importances), key=lambda x: x[1], reverse=True
            )
            logger.info("\nTop 15 Feature Importances:")
            for name, imp in importance_pairs[:15]:
                logger.info(f"  {name}: {imp}")

            # Save feature importance to file
            OUT = Path(args.output_dir)
            OUT.mkdir(exist_ok=True)
            importance_df = pd.DataFrame(
                importance_pairs, columns=["feature", "importance"]
            )
            importance_df.to_csv(OUT / "feature_importance.csv", index=False)
    except Exception as e:
        logger.warning(f"Could not extract feature importance: {e}")

    # ── Save artifacts ───────────────────────────────────────────────────────
    OUT = Path(args.output_dir)
    OUT.mkdir(exist_ok=True)

    # T3 FIX: Versioned naming
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pipeline_path = OUT / "model_pipeline.joblib"
    le_path = OUT / "label_encoder.joblib"
    versioned_pipeline = OUT / f"model_pipeline_{timestamp}.joblib"

    joblib.dump(best_pipe, pipeline_path)
    joblib.dump(best_pipe, versioned_pipeline)  # versioned backup
    joblib.dump(le, le_path)
    logger.info(f"Saved pipeline: {pipeline_path.stat().st_size / 1024:.0f} KB")
    logger.info(f"Versioned copy: {versioned_pipeline}")

    # Save classification report
    with open(OUT / "classification_report.txt", "w") as f:
        f.write(f"Training Date: {datetime.now().isoformat()}\n")
        f.write(f"Data Hash: {data_hash}\n")
        f.write(f"Backend: {backend}\n\n")
        f.write(class_report)
        f.write(f"\nConfusion Matrix:\n{cm}\n")

    # ── Metadata ─────────────────────────────────────────────────────────────
    metadata = {
        "model_backend": backend,
        "target_column": TARGET,
        "class_names": list(le.classes_),
        "numeric_features": NUMERIC,
        "categorical_features": CATEGORICAL,
        "text_features": TEXT,
        "id_features": ID_COLS,
        "leaky_features_removed": sorted(leaky_present),
        "best_params": search.best_params_,
        "best_cv_score": round(search.best_score_, 4),
        "metrics": {
            "accuracy": round(acc, 4),
            "f1_macro": round(f1_macro, 4),
            "f1_weighted": round(f1_weighted, 4),
        },
        "baseline_metrics": {
            "accuracy": round(baseline_acc, 4),
            "f1_macro": round(baseline_f1, 4),
            "strategy": "most_frequent",
        },
        "accuracy_gap_over_baseline": round(baseline_gap, 4),
        "leakage_check_passed": not args.skip_leakage,
        "dataset_shape": list(df.shape),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "group_split_column": group_col,
        "n_groups_train": int(df.iloc[train_idx][group_col].nunique())
        if group_col in df.columns
        else None,
        "n_groups_test": int(df.iloc[test_idx][group_col].nunique())
        if group_col in df.columns
        else None,
        "training_time_seconds": round(train_time, 1),
        "data_hash": data_hash,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "sklearn_version": __import__("sklearn").__version__,
        "created_at": datetime.now().isoformat(),
    }

    with open(OUT / "model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # ── Score all programs for CSV export ─────────────────────────────────────
    try:
        from pipeline.scoring import (
            compute_confidence_bands_batch,
            compute_match_scores_batch,
        )

        all_X = df.drop(columns=[c for c in DROP_COLS if c in df.columns])
        all_pred = best_pipe.predict(all_X)
        all_proba = best_pipe.predict_proba(all_X)

        df_scored = df.copy()
        df_scored["predicted_tier"] = le.inverse_transform(all_pred)

        classes = list(le.classes_)
        # BUG FIX: Use canonical scoring (was 1.0/0.5/0.1, now 1.0/0.6/0.2)
        df_scored["match_score"] = compute_match_scores_batch(all_proba, classes)
        df_scored["confidence_band"] = compute_confidence_bands_batch(all_proba)

        df_scored.to_csv(OUT / "scored_programs.csv", index=False)
        logger.info(f"Scored {len(df_scored)} programs → {OUT / 'scored_programs.csv'}")
    except Exception as e:
        logger.warning(f"Could not score all programs: {e}")

    # ── Summary ──────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(f"✅ Model retrained — {backend}")
    logger.info(
        f"   Python {metadata['python_version']} / sklearn {metadata['sklearn_version']}"
    )
    logger.info(
        f"   Accuracy: {acc:.4f} (baseline: {baseline_acc:.4f}, gap: {baseline_gap:.4f})"
    )
    logger.info(f"   F1-macro: {f1_macro:.4f}")
    logger.info(f"   Best CV score: {search.best_score_:.4f}")
    logger.info(f"   Leaky features removed: {len(leaky_present)}")
    logger.info(f"   Data hash: {data_hash}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
