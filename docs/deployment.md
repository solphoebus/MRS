# Deployment Guide

## Local API

```bash
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

## Run tests

```bash
pytest backend/tests -q
```

## Docker

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000` and docs at `http://localhost:8000/docs`.

## Deploying to Render (recommended)

This app is a stateful FastAPI service (SQLite database, prescription-upload handling), which
fits Render's always-on web service model better than a serverless/edge platform like Vercel.

1. Push this repository to GitHub.
2. In the Render dashboard, choose **New > Blueprint** and point it at this repo. Render will
   read `render.yaml` from the repo root and provision the service automatically, including:
   - build command: `pip install -r backend/requirements.txt`
   - start command: `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`
   - a 1 GB persistent disk mounted at `/var/data` for the SQLite database
   - `MRS_DATABASE_URL` pointed at that persistent disk so patient/history data survives deploys
3. Once deployed, visit the Render-provided URL for the UI, and `/docs` for the API reference.

If you'd rather configure it manually instead of using the blueprint: create a **Web Service**,
set the same build/start commands above, add a persistent disk mounted at `/var/data`, and set
the environment variable `MRS_DATABASE_URL=sqlite:////var/data/medicine_recommendation.db`.

## Why not Vercel

Vercel's Python support targets stateless serverless functions. This app relies on:

- a local SQLite database for patient profiles and recommendation history
- a writable uploads folder for prescription image scanning

Both need a persistent, writable filesystem, which Vercel's serverless runtime does not provide
(storage is ephemeral and reset between invocations). To deploy on Vercel, first swap the SQLite
layer (`backend/app/db/sqlite_store.py`) for a hosted database (e.g. Postgres via Neon/Supabase)
and route uploads through object storage instead of the local disk.

## Important note

This application is for educational purposes and clinical decision support only. It must not be used as an autonomous prescribing or treatment system.
