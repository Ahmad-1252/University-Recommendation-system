"""Test the recommendation service end-to-end."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from services.recommendation_service import RecommendationService

rs = RecommendationService()
assert rs.load(), "Model failed to load"
n = rs.load_programs_dataframe()
print(f"Programs loaded: {n}")

# Test recommend
print("\n--- Recommend Test ---")
result = rs.recommend({"gpa": 3.5, "ielts": 6.5, "budget": 30000}, top_n=5)
print(f"Candidates: {result['total_candidates']}")
print(f"Recommendations: {len(result['recommendations'])}")
for i, rec in enumerate(result["recommendations"]):
    print(
        f"  {i+1}. {rec['university_name'][:40]} | "
        f"Score: {rec['match_score']:.4f} | Tier: {rec['predicted_tier']}"
    )

# Test similar
print("\n--- Similar Test ---")
similar = rs.find_similar(0, top_n=5)
print(f"Query: {similar['query_program'].get('university_name', '?')}")
for i, s in enumerate(similar["similar_programs"]):
    print(
        f"  {i+1}. {s.get('university_name', '?')[:40]} | Sim: {s.get('similarity_score', 0):.4f}"
    )

# Test model info
print("\n--- Model Info ---")
info = rs.get_model_info()
print(f"Backend: {info['model_backend']}")
print(f"Accuracy: {info['metrics'].get('accuracy', 'N/A')}")
print(f"Classes: {info['class_names']}")

print("\n✅ All tests passed!")
