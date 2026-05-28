# FastAPI inference server for University Recommendation System.
from fastapi import FastAPI
from pydantic import BaseModel
import joblib, json, pandas as pd, numpy as np
from pathlib import Path

app = FastAPI(title="University Recommender API", version="1.0")

# Load artifacts
pipeline = joblib.load("model_artifacts/model_pipeline.joblib")
le = joblib.load("model_artifacts/label_encoder.joblib")
with open("model_artifacts/model_metadata.json") as f:
    meta = json.load(f)

class ProgramFeatures(BaseModel):
    qs_world_ranking: int = 100
    qs_overall_score: float = 50.0
    tuition_international: int = 20000
    country: str = "United Kingdom"
    degree_level: str = "Masters"
    program_category: str = "Computer Science"
    gpa_requirement_min: float = 3.0
    ielts_min: float = 6.0
    toefl_min: int = 80
    duration_years: float = 1.5
    cost_of_living: int = 12000

@app.post("/score")
def score_program(program: ProgramFeatures):
    row = pd.DataFrame([program.model_dump()])
    proba = pipeline.predict_proba(row)[0]
    classes = list(le.classes_)
    top_i = classes.index('top') if 'top' in classes else 0
    good_i = classes.index('good') if 'good' in classes else 1
    std_i = classes.index('standard') if 'standard' in classes else 2
    return {
        "predicted_tier": classes[proba.argmax()],
        "match_score": round(float(proba[top_i]+0.5*proba[good_i]+0.1*proba[std_i]),4),
    }

@app.get("/health")
def health():
    return {"status": "ok", "model": meta["model_backend"]}