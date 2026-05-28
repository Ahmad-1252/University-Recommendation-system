# 🚀 Deployment Guide

## Prerequisites

- GitHub account
- MongoDB Atlas free cluster ([create here](https://cloud.mongodb.com))

---

## Option A: Render.com (Free — Recommended)

### 1. Push to GitHub

```bash
git add .
git commit -m "feat: deployment config"
git push origin main
```

### 2. Deploy

1. Go to [render.com](https://render.com) → **Sign up with GitHub**
2. Click **New → Blueprint** → select your repo
3. Render detects `render.yaml` automatically → click **Apply**
4. Set `MONGO_CONNECTION_STRING` in **Environment Variables**:
   ```
   mongodb+srv://user:pass@cluster.mongodb.net/university_db
   ```
5. Click **Deploy** → Live in ~3 minutes

### 3. Verify

```bash
curl https://YOUR-APP.onrender.com/health
curl https://YOUR-APP.onrender.com/api/model/info
curl https://YOUR-APP.onrender.com/api/docs   # Swagger UI
```

---

## Option B: Docker (Any Cloud)

```bash
docker build -t university-recommender .
docker run -p 8000:8000 \
  -e MONGO_CONNECTION_STRING="mongodb+srv://..." \
  -e DATABASE_NAME="university_db" \
  university-recommender
```

Deploy the image to Railway, Fly.io, or any Docker host.

---

## Option C: Streamlit Demo (Portfolio)

1. Go to [share.streamlit.io](https://share.streamlit.io) → Sign in with GitHub
2. Click **New app** → select repo → set main file: `streamlit_app.py`
3. Click **Deploy** → Live in ~2 minutes

---

## MongoDB Atlas Setup (Free)

1. Go to [cloud.mongodb.com](https://cloud.mongodb.com) → Create free M0 cluster
2. Create database user → Note the password
3. Whitelist `0.0.0.0/0` in Network Access
4. Get connection string → Replace `<password>` → Use in `MONGO_CONNECTION_STRING`

---

## Environment Variables

| Variable                  | Required | Default                     | Description               |
| :------------------------ | :------: | :-------------------------- | :------------------------ |
| `MONGO_CONNECTION_STRING` |    ✅    | `mongodb://localhost:27017` | MongoDB URI               |
| `DATABASE_NAME`           |    ❌    | `university_db`             | Database name             |
| `API_KEY`                 |    ❌    | auto-generated              | Admin endpoint auth       |
| `LOG_LEVEL`               |    ❌    | `INFO`                      | Logging level             |
| `ENVIRONMENT`             |    ❌    | `development`               | `production` hides errors |

---

## Project Structure for Deployment

```
├── Procfile                    # Render start command
├── render.yaml                 # Render blueprint
├── runtime.txt                 # Python version
├── Dockerfile                  # Docker deployment
├── .dockerignore               # Docker build exclusions
├── requirements-deploy.txt     # Deployment dependencies
├── model_artifacts/            # ML model (tracked in git)
│   ├── model_pipeline.joblib
│   ├── label_encoder.joblib
│   └── model_metadata.json
├── src/api/main.py             # FastAPI app
└── data/exports/               # Training data
```
