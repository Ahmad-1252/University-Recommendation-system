"""Verify structured admission/fee fields in output."""
import json

path = "output/test_structured.json"
data = json.load(open(path, encoding="utf-8"))
print(f"Total programs: {len(data)}\n")

# Show new structured fields
FIELDS = [
    "gre_score",
    "bachelor_gpa",
    "toefl_score",
    "ielts_score",
    "pte_score",
    "cambridge_cae_score",
    "duolingo_score",
    "sat_score",
    "gmat_score",
    "fee_domestic",
    "fee_international",
    "fee_currency",
]

for p in data[:5]:
    print(f"=== {p.get('program_name', '?')} @ {p.get('university_name', '?')} ===")
    for f in FIELDS:
        val = p.get(f)
        if val is not None:
            print(f"  {f:25s} = {val}")
        else:
            print(f"  {f:25s} = (not available)")
    print()

# Summary stats
filled_counts = {f: sum(1 for p in data if p.get(f)) for f in FIELDS}
print("=== FIELD COVERAGE ===")
for f, cnt in filled_counts.items():
    pct = cnt / len(data) * 100
    print(f"  {f:25s}: {cnt}/{len(data)} ({pct:.0f}%)")
