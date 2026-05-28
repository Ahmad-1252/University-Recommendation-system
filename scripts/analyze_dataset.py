#!/usr/bin/env python3
"""Analyze the training dataset for ML model selection."""
import csv
import math
from collections import Counter

CSV_PATH = "data/exports/training_dataset_latest.csv"


def load():
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def stats(vals):
    n = len(vals)
    if n == 0:
        return {}
    avg = sum(vals) / n
    vals_sorted = sorted(vals)
    median = vals_sorted[n // 2]
    mn, mx = min(vals), max(vals)
    variance = sum((v - avg) ** 2 for v in vals) / n
    std = math.sqrt(variance)
    zeros = sum(1 for v in vals if v == 0)
    uniq = len(set(vals))
    return {
        "mean": avg,
        "median": median,
        "min": mn,
        "max": mx,
        "std": std,
        "unique": uniq,
        "zeros": zeros,
        "n": n,
    }


def main():
    rows = load()
    print(f"={'='*60}")
    print(f"DATASET ANALYSIS — {len(rows)} Records")
    print(f"={'='*60}")

    # Basic
    unis = set(r["university_name"] for r in rows)
    countries = set(r["country"] for r in rows)
    print(f"\nUniversities: {len(unis)}")
    print(f"Countries: {len(countries)}")
    print(f"Features: {len(rows[0])}")

    # Numerical features
    num_cols = [
        "gpa_requirement_min",
        "ielts_min",
        "toefl_min",
        "duration_years",
        "tuition_domestic",
        "tuition_international",
        "cost_of_living",
        "application_fee",
        "qs_world_ranking",
        "qs_overall_score",
        "qs_academic_reputation",
        "qs_employer_reputation",
        "qs_faculty_student_ratio",
        "qs_citations",
        "qs_intl_students",
        "qs_employment_outcomes",
        "qs_sustainability",
    ]

    print(f"\n{'='*60}")
    print("NUMERICAL FEATURES")
    print(f"{'='*60}")
    print(
        f"{'Feature':<30} {'Mean':>8} {'Std':>8} {'Min':>8} {'Max':>8} {'Unique':>7} {'Zeros%':>7}"
    )
    print("-" * 78)

    for col in num_cols:
        vals = []
        for r in rows:
            try:
                vals.append(float(r[col]))
            except (ValueError, TypeError):
                pass
        s = stats(vals)
        if s:
            z_pct = s["zeros"] / s["n"] * 100
            print(
                f"{col:<30} {s['mean']:>8.1f} {s['std']:>8.1f} {s['min']:>8.1f} {s['max']:>8.1f} {s['unique']:>7} {z_pct:>6.0f}%"
            )

    # Categorical features
    cat_cols = [
        "degree_type",
        "degree_level",
        "program_category",
        "country",
        "university_tier",
        "university_size",
        "university_focus",
        "university_research",
        "university_status",
        "rolling_admission",
        "tuition_currency",
    ]

    print(f"\n{'='*60}")
    print("CATEGORICAL FEATURES")
    print(f"{'='*60}")

    for col in cat_cols:
        vals = [r[col] for r in rows if r[col]]
        uniq = len(set(vals))
        top5 = Counter(vals).most_common(5)
        top_str = "  |  ".join(f"{k}: {v}" for k, v in top5)
        print(f"\n  {col} ({uniq} unique)")
        print(f"    Top: {top_str}")

    # Text/List features
    print(f"\n{'='*60}")
    print("TEXT/LIST FEATURES")
    print(f"{'='*60}")

    text_cols = ["specializations", "career_outcomes"]
    for col in text_cols:
        non_empty = sum(1 for r in rows if r[col] and r[col].strip())
        avg_len = sum(len(r[col].split("; ")) for r in rows if r[col]) / max(
            1, non_empty
        )
        print(f"  {col}: {non_empty}/{len(rows)} filled, avg {avg_len:.1f} items")

    # Sparsity
    print(f"\n{'='*60}")
    print("SPARSITY ANALYSIS (>5% empty/zero)")
    print(f"{'='*60}")

    for col in rows[0].keys():
        empty = sum(1 for r in rows if not r[col] or r[col] in ("", "0", "0.0", "None"))
        pct = empty / len(rows) * 100
        if pct > 5:
            print(f"  {col}: {pct:.0f}% empty/zero")

    # Correlation proxy: How varied are features?
    print(f"\n{'='*60}")
    print("FEATURE VARIANCE (for ML usefulness)")
    print(f"{'='*60}")

    for col in num_cols:
        vals = []
        for r in rows:
            try:
                vals.append(float(r[col]))
            except (ValueError, TypeError):
                pass
        s = stats(vals)
        if s and s["mean"] != 0:
            cv = s["std"] / abs(s["mean"]) * 100  # coefficient of variation
            usefulness = "HIGH" if cv > 50 else "MEDIUM" if cv > 20 else "LOW"
            print(f"  {col:<30} CV={cv:>6.1f}%  [{usefulness}]")

    # Class balance for recommendation
    print(f"\n{'='*60}")
    print("CLASS BALANCE (for recommendation targets)")
    print(f"{'='*60}")

    # Tier distribution
    tier = Counter(r["university_tier"] for r in rows)
    print("\n  University Tier:")
    for t, c in tier.most_common():
        pct = c / len(rows) * 100
        bar = "█" * int(pct / 2)
        print(f"    {t:<10} {c:>6} ({pct:>5.1f}%) {bar}")

    # Ranking buckets
    print("\n  QS Ranking Buckets:")
    buckets = {
        "1-50": 0,
        "51-100": 0,
        "101-200": 0,
        "201-500": 0,
        "501-1000": 0,
        "1001+": 0,
    }
    for r in rows:
        try:
            rank = int(float(r["qs_world_ranking"]))
            if rank <= 50:
                buckets["1-50"] += 1
            elif rank <= 100:
                buckets["51-100"] += 1
            elif rank <= 200:
                buckets["101-200"] += 1
            elif rank <= 500:
                buckets["201-500"] += 1
            elif rank <= 1000:
                buckets["501-1000"] += 1
            else:
                buckets["1001+"] += 1
        except (ValueError, TypeError):
            pass
    for b, c in buckets.items():
        pct = c / len(rows) * 100
        bar = "█" * int(pct / 2)
        print(f"    {b:<10} {c:>6} ({pct:>5.1f}%) {bar}")

    print(f"\n{'='*60}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
