import json
import os

nb = json.load(
    open("university_recommendation_system_executed.ipynb", encoding="utf-8")
)
size_kb = os.path.getsize("university_recommendation_system_executed.ipynb") / 1024
print(f"Executed notebook: {size_kb:.0f} KB")
print(f"Cells: {len(nb['cells'])}")

errors = []
for i, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        for out in cell.get("outputs", []):
            if out.get("output_type") == "error":
                ename = out.get("ename", "")
                evalue = out.get("evalue", "")[:100]
                errors.append(f"  Cell {i}: {ename} — {evalue}")

if errors:
    print(f"\nERRORS ({len(errors)}):")
    for e in errors:
        print(e)
else:
    print("\n✅ NO ERRORS in any cell!")

# Check key text outputs
for i, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        for out in cell.get("outputs", []):
            if out.get("output_type") == "stream":
                text = "".join(out.get("text", []))
                # Look for key success markers
                for marker in [
                    "Training complete",
                    "MODEL EVALUATION",
                    "Accuracy:",
                    "Pipeline complete",
                    "Model pipeline saved",
                    "Scored programs saved",
                ]:
                    if marker in text:
                        # Extract the line
                        for line in text.split("\n"):
                            if marker in line:
                                print(f"  Cell {i}: {line.strip()}")
                                break

# Check artifacts
print("\n--- Model Artifacts ---")
artifacts = [
    "model_artifacts/model_pipeline.joblib",
    "model_artifacts/label_encoder.joblib",
    "model_artifacts/model_metadata.json",
    "model_artifacts/scored_programs.csv",
    "model_artifacts/serve.py",
    "model_artifacts/requirements.txt",
]
for f in artifacts:
    if os.path.exists(f):
        sz = os.path.getsize(f)
        print(f"  OK  {f} ({sz/1024:.0f} KB)")
    else:
        print(f"  MISSING  {f}")
