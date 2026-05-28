"""
🎓 University Recommendation System — Interactive Demo
Powered by LightGBM + Cosine Similarity | Built with Streamlit
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity

# ─── Page Config ─────────────────────────────────────────────
st.set_page_config(
    page_title="UniRecommender — AI University Finder",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main-header {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .main-header h1 {
        font-size: 2.4rem;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .main-header p {
        color: #a0a0c0;
        font-size: 1.05rem;
        margin-top: 0.5rem;
    }

    .metric-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #2a2a4a;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
        color: white;
    }
    .metric-card h3 { color: #667eea; font-size: 2rem; margin: 0; }
    .metric-card p { color: #8888aa; font-size: 0.85rem; margin: 0.3rem 0 0; }

    .program-card {
        background: #0e1117;
        border: 1px solid #262640;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.8rem;
        transition: border-color 0.2s;
    }
    .program-card:hover { border-color: #667eea; }
    .program-card h4 { margin: 0 0 0.3rem; color: #e0e0e0; font-size: 1rem; }
    .program-card .meta { color: #8888aa; font-size: 0.85rem; }
    .program-card .score {
        display: inline-block;
        background: linear-gradient(90deg, #667eea, #764ba2);
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .tier-badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .tier-top { background: #2ecc7133; color: #2ecc71; }
    .tier-good { background: #3498db33; color: #3498db; }
    .tier-standard { background: #95a5a633; color: #95a5a6; }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29, #1a1a2e);
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] label {
        color: #c0c0d0 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ─── Load Artifacts ──────────────────────────────────────────
@st.cache_resource
def load_model():
    pipeline = joblib.load("model_artifacts/model_pipeline.joblib")
    le = joblib.load("model_artifacts/label_encoder.joblib")
    with open("model_artifacts/model_metadata.json") as f:
        meta = json.load(f)
    return pipeline, le, meta


@st.cache_data
def load_data():
    paths = [
        "data/exports/training_dataset_latest.csv",
        "data/universities.csv",
        "model_artifacts/scored_programs.csv",
    ]
    for p in paths:
        if Path(p).exists():
            return pd.read_csv(p)
    return None


pipeline, le, meta = load_model()
df = load_data()

if df is None:
    st.error("❌ No dataset found. Please place your CSV in one of the expected paths.")
    st.stop()

# Detect column names
TARGET = meta.get("target_column", "university_tier")
ID_FEATURES = meta.get("id_features", [])
class_names = meta.get("class_names", ["good", "standard", "top"])


# ─── Helper Functions ────────────────────────────────────────
def get_tier_badge(tier: str) -> str:
    tier_lower = str(tier).lower()
    cls = (
        f"tier-{tier_lower}"
        if tier_lower in ("top", "good", "standard")
        else "tier-standard"
    )
    return f'<span class="tier-badge {cls}">{tier}</span>'


def recommend_programs(profile: dict, top_n: int = 10) -> pd.DataFrame:
    """Content-based recommendation."""
    candidates = df.copy()

    # Hard filters
    if profile.get("gpa") and "gpa_requirement_min" in candidates.columns:
        candidates = candidates[candidates["gpa_requirement_min"] <= profile["gpa"]]
    if profile.get("ielts") and "ielts_min" in candidates.columns:
        candidates = candidates[candidates["ielts_min"] <= profile["ielts"]]
    if profile.get("toefl") and "toefl_min" in candidates.columns:
        candidates = candidates[candidates["toefl_min"] <= profile["toefl"]]
    if profile.get("budget") and "tuition_international" in candidates.columns:
        candidates = candidates[
            candidates["tuition_international"] <= profile["budget"]
        ]
    if (
        profile.get("country")
        and profile["country"] != "Any"
        and "country" in candidates.columns
    ):
        candidates = candidates[candidates["country"] == profile["country"]]
    if (
        profile.get("degree_level")
        and profile["degree_level"] != "Any"
        and "degree_level" in candidates.columns
    ):
        candidates = candidates[candidates["degree_level"] == profile["degree_level"]]
    if (
        profile.get("program_category")
        and profile["program_category"] != "Any"
        and "program_category" in candidates.columns
    ):
        candidates = candidates[
            candidates["program_category"] == profile["program_category"]
        ]

    if len(candidates) == 0:
        return pd.DataFrame()

    # Predict probabilities
    X_cand = candidates.drop(columns=[TARGET] + ID_FEATURES, errors="ignore")
    try:
        proba = pipeline.predict_proba(X_cand)
        classes = list(le.classes_)
        top_i = classes.index("top") if "top" in classes else 0
        good_i = classes.index("good") if "good" in classes else 1
        std_i = classes.index("standard") if "standard" in classes else 2

        candidates = candidates.copy()
        candidates["match_score"] = (
            proba[:, top_i] * 1.0 + proba[:, good_i] * 0.5 + proba[:, std_i] * 0.1
        )
        candidates["predicted_tier"] = le.inverse_transform(proba.argmax(axis=1))
    except Exception:
        candidates["match_score"] = 0.5
        candidates["predicted_tier"] = "unknown"

    result = candidates.sort_values("match_score", ascending=False).head(top_n)
    return result.reset_index(drop=True)


def find_similar(program_idx: int, top_n: int = 10) -> pd.DataFrame:
    """Item-to-item similarity."""
    sample = df.head(5000).copy()
    X_sim = sample.drop(columns=[TARGET] + ID_FEATURES, errors="ignore")
    try:
        X_transformed = pipeline.named_steps["preprocessor"].transform(X_sim)
        if hasattr(X_transformed, "toarray"):
            X_transformed = X_transformed.toarray()
        similarities = cosine_similarity(
            X_transformed[program_idx : program_idx + 1], X_transformed
        )[0]
        top_indices = np.argsort(similarities)[::-1][1 : top_n + 1]
        result = sample.iloc[top_indices].copy()
        result["similarity"] = similarities[top_indices]
        return result.reset_index(drop=True)
    except Exception as e:
        st.error(f"Similarity computation failed: {e}")
        return pd.DataFrame()


# ─── Header ──────────────────────────────────────────────────
st.markdown(
    """
<div class="main-header">
    <h1>🎓 UniRecommender</h1>
    <p>AI-powered university program recommendations — Find your perfect match from 13,800+ programs</p>
</div>
""",
    unsafe_allow_html=True,
)

# ─── Metrics Row ─────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f"""<div class="metric-card"><h3>{len(df):,}</h3><p>Programs</p></div>""",
        unsafe_allow_html=True,
    )
with c2:
    n_unis = df["university_name"].nunique() if "university_name" in df.columns else "—"
    st.markdown(
        f"""<div class="metric-card"><h3>{n_unis}</h3><p>Universities</p></div>""",
        unsafe_allow_html=True,
    )
with c3:
    n_countries = df["country"].nunique() if "country" in df.columns else "—"
    st.markdown(
        f"""<div class="metric-card"><h3>{n_countries}</h3><p>Countries</p></div>""",
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        f"""<div class="metric-card"><h3>{meta["model_backend"].upper()}</h3><p>ML Engine</p></div>""",
        unsafe_allow_html=True,
    )

st.markdown("")

# ─── Tabs ────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(
    ["🔍 Find Programs", "🔗 Similar Programs", "📊 Dataset Explorer"]
)

# ═══════════════════════════════════════════════════════════
# TAB 1 — Content-Based Recommendations
# ═══════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Your Profile")
    st.caption(
        "Fill in your academic profile to get personalized program recommendations"
    )

    col_left, col_right = st.columns([1, 2])

    with col_left:
        with st.form("profile_form"):
            st.markdown("**Academic Scores**")
            gpa = st.slider("GPA (out of 4.0)", 2.0, 4.0, 3.3, 0.1)
            ielts = st.selectbox("IELTS Score", [5.5, 6.0, 6.5, 7.0, 7.5, 8.0], index=2)
            toefl = st.selectbox(
                "TOEFL Score", [70, 75, 80, 85, 90, 95, 100, 105, 110], index=4
            )

            st.markdown("**Preferences**")
            budget = st.number_input("Max Tuition (USD/year)", 0, 80000, 30000, 5000)

            countries = (
                ["Any"] + sorted(df["country"].dropna().unique().tolist())
                if "country" in df.columns
                else ["Any"]
            )
            country = st.selectbox("Country", countries)

            levels = (
                ["Any"] + sorted(df["degree_level"].dropna().unique().tolist())
                if "degree_level" in df.columns
                else ["Any"]
            )
            degree = st.selectbox("Degree Level", levels)

            categories = (
                ["Any"] + sorted(df["program_category"].dropna().unique().tolist())
                if "program_category" in df.columns
                else ["Any"]
            )
            category = st.selectbox("Field of Study", categories)

            n_results = st.slider("Results to show", 5, 30, 10)
            submitted = st.form_submit_button(
                "🔍 Find Programs", use_container_width=True
            )

    with col_right:
        if submitted:
            profile = {
                "gpa": gpa,
                "ielts": ielts,
                "toefl": toefl,
                "budget": budget,
                "country": country,
                "degree_level": degree,
                "program_category": category,
            }

            with st.spinner("Running AI model..."):
                results = recommend_programs(profile, top_n=n_results)

            if len(results) == 0:
                st.warning(
                    "No programs match your criteria. Try relaxing some filters."
                )
            else:
                st.success(f"Found **{len(results)}** recommended programs")

                for _, row in results.iterrows():
                    uni = row.get("university_name", "—")
                    prog = row.get("program_name", "—")
                    ctry = row.get("country", "—")
                    rank = row.get("qs_world_ranking", "—")
                    tuition = row.get("tuition_international", "—")
                    score = row.get("match_score", 0)
                    tier = row.get("predicted_tier", "standard")
                    deg = row.get("degree_level", "—")

                    tuition_str = (
                        f"${tuition:,.0f}"
                        if isinstance(tuition, (int, float))
                        else str(tuition)
                    )
                    rank_str = (
                        f"#{int(rank)}" if isinstance(rank, (int, float)) else str(rank)
                    )

                    st.markdown(
                        f"""
                    <div class="program-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <h4>{uni}</h4>
                                <div class="meta">{prog} · {deg} · {ctry} · QS Rank {rank_str} · {tuition_str}/yr</div>
                            </div>
                            <div style="text-align:right;">
                                <span class="score">{score:.0%} match</span><br/>
                                {get_tier_badge(tier)}
                            </div>
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
        else:
            st.info(
                "👈 Fill in your profile and click **Find Programs** to get personalized recommendations."
            )


# ═══════════════════════════════════════════════════════════
# TAB 2 — Similar Programs
# ═══════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Find Similar Programs")
    st.caption(
        "Select a program to find similar ones using cosine similarity on feature vectors"
    )

    max_idx = min(len(df) - 1, 4999)
    if "university_name" in df.columns and "program_name" in df.columns:
        options = [
            f"{i}: {row.get('university_name','?')} — {row.get('program_name','?')}"
            for i, row in df.head(max_idx + 1).iterrows()
        ]
        selected = st.selectbox("Select a program", options[:200], index=0)
        idx = int(selected.split(":")[0])
    else:
        idx = st.number_input("Program index", 0, max_idx, 0)

    n_similar = st.slider("Number of similar programs", 5, 20, 10, key="sim_n")

    if st.button("🔗 Find Similar", use_container_width=False):
        with st.spinner("Computing similarity..."):
            similar = find_similar(idx, top_n=n_similar)

        if len(similar) > 0:
            st.success(f"Found **{len(similar)}** similar programs")

            display_cols = [
                c
                for c in [
                    "university_name",
                    "program_name",
                    "degree_level",
                    "country",
                    "qs_world_ranking",
                    "tuition_international",
                    "similarity",
                ]
                if c in similar.columns
            ]

            styled = similar[display_cols].copy()
            if "similarity" in styled.columns:
                styled["similarity"] = styled["similarity"].apply(lambda x: f"{x:.3f}")
            if "tuition_international" in styled.columns:
                styled["tuition_international"] = styled["tuition_international"].apply(
                    lambda x: f"${x:,.0f}" if pd.notnull(x) else "—"
                )
            st.dataframe(styled, use_container_width=True, hide_index=True)
        else:
            st.warning("No similar programs found.")


# ═══════════════════════════════════════════════════════════
# TAB 3 — Dataset Explorer
# ═══════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Dataset Explorer")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Tier Distribution**")
        if TARGET in df.columns:
            tier_counts = df[TARGET].value_counts()
            st.bar_chart(tier_counts)

    with col_b:
        st.markdown("**Top 15 Countries**")
        if "country" in df.columns:
            country_counts = df["country"].value_counts().head(15)
            st.bar_chart(country_counts)

    st.markdown("---")
    st.markdown("**Browse Programs**")

    # Filters
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        filter_country = st.selectbox(
            "Filter by Country",
            ["All"] + sorted(df["country"].dropna().unique().tolist())
            if "country" in df.columns
            else ["All"],
            key="ex_country",
        )
    with fc2:
        filter_level = st.selectbox(
            "Filter by Level",
            ["All"] + sorted(df["degree_level"].dropna().unique().tolist())
            if "degree_level" in df.columns
            else ["All"],
            key="ex_level",
        )
    with fc3:
        filter_cat = st.selectbox(
            "Filter by Category",
            ["All"] + sorted(df["program_category"].dropna().unique().tolist())
            if "program_category" in df.columns
            else ["All"],
            key="ex_cat",
        )

    filtered = df.copy()
    if filter_country != "All" and "country" in filtered.columns:
        filtered = filtered[filtered["country"] == filter_country]
    if filter_level != "All" and "degree_level" in filtered.columns:
        filtered = filtered[filtered["degree_level"] == filter_level]
    if filter_cat != "All" and "program_category" in filtered.columns:
        filtered = filtered[filtered["program_category"] == filter_cat]

    browse_cols = [
        c
        for c in [
            "university_name",
            "program_name",
            "degree_level",
            "program_category",
            "country",
            "qs_world_ranking",
            "tuition_international",
            TARGET,
        ]
        if c in filtered.columns
    ]

    st.dataframe(
        filtered[browse_cols].head(100), use_container_width=True, hide_index=True
    )
    st.caption(f"Showing top 100 of {len(filtered):,} filtered programs")


# ─── Footer ──────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
<div style="text-align:center; color: #666; font-size: 0.85rem; padding: 1rem 0;">
    <strong>UniRecommender</strong> — AI-Powered University Recommendation System<br/>
    Built with LightGBM, scikit-learn, and Streamlit · 13,800+ programs · 1,500+ universities · 106 countries<br/>
    <a href="https://github.com" style="color:#667eea;">GitHub</a>
</div>
""",
    unsafe_allow_html=True,
)
