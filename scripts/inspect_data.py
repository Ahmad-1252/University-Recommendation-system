"""Quick inspection of scraped data fields."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..",
    "output",
    "programs.json",
)
if not os.path.exists(path):
    path = "output/programs.json"

data = json.load(open(path, encoding="utf-8"))
print(f"Total programs: {len(data)}\n")

# Show admission_requirements samples
with_admit = [x for x in data if x.get("admission_requirements")]
print(f"=== ADMISSION REQUIREMENTS ({len(with_admit)}/{len(data)} have data) ===")
for p in with_admit[:3]:
    print(f"\n--- {p.get('program_name')} ---")
    print(p.get("admission_requirements", "")[:800])

# Show tuition_fee_detail samples
with_fee = [x for x in data if x.get("tuition_fee_detail")]
print(f"\n\n=== TUITION FEE DETAIL ({len(with_fee)}/{len(data)} have data) ===")
for p in with_fee[:3]:
    print(f"\n--- {p.get('program_name')} ---")
    print(p.get("tuition_fee_detail", "")[:800])

# Show tuition_fee_summary samples
with_summary = [x for x in data if x.get("tuition_fee_summary")]
print(f"\n\n=== TUITION FEE SUMMARY ({len(with_summary)}/{len(data)} have data) ===")
for p in with_summary[:5]:
    print(f"  {p.get('program_name')}: {p.get('tuition_fee_summary')}")
