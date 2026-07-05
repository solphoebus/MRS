# Medisense AI

A modernized, production-oriented foundation for a **generic AI-powered medicine recommendation and prescription analysis platform**.

> **Medical disclaimer**
> This project is **for educational purposes and clinical decision support only**. It is **not** a substitute for professional medical advice, diagnosis, treatment, or prescribing. Any medication recommendation, substitution, or pricing output is **non-definitive** and must be reviewed by a licensed clinician or pharmacist.

## Highlights

- Apple-inspired glassmorphism frontend
- single-service FastAPI app that serves both API and UI
- symptom-driven recommendation engine with confidence scores
- safety-aware recommendation filtering
- prescription text scanning workflow
- upload-based prescription scan endpoint
- heuristic lowest-cost alternative suggestions
- SQLite-backed persistence for patient profiles and recommendation history
- explainable outputs with risk factors, side effects, and warnings
- modular inference layer for future ML/LLM upgrades
- Dockerized local deployment
- automated API tests

## New integrated capabilities

### 1. One-command app
The frontend is now served directly by FastAPI from `/`, so the app can run from one backend process instead of separate static hosting.

### 2. Prescription upload scanning
A new `POST /scan-prescription-image` endpoint accepts uploaded files and routes them through an OCR-ready extraction pipeline. In this repository, text files are parsed directly and image OCR is implemented as a placeholder extraction layer designed for swapping in a real OCR engine.

### 3. Persistent storage
The platform now initializes a SQLite database and stores:

- patient profiles
- recommendation history
- symptom analysis history
- prescription scan history

### 4. Cheapest alternative engine
The platform estimates medicine pricing heuristically and surfaces lower-cost peers from the same disease bucket. These are clearly labeled as **review-required** substitutions, never definitive replacements.

## API endpoints

- `GET /`
- `POST /recommend`
- `POST /patient`
- `GET /medicine/{id}`
- `GET /disease/{id}`
- `GET /interaction`
- `POST /symptom-analysis`
- `GET /alternatives`
- `GET /drug-info`
- `POST /scan-prescription`
- `POST /scan-prescription-image`
- `GET /health-check`

## Run locally

```bash
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

Then open:

- UI: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`

## Tests

```bash
python -m pytest backend/tests -q
```

## Docker

```bash
docker compose up --build
```

## Important caution

- Do **not** use this system as an autonomous diagnosis or prescribing tool.
- Do **not** substitute medicines solely based on app output.
- Always verify drug identity, formulation, route, dose, strength, interactions, allergies, pregnancy safety, renal/hepatic considerations, and regional availability.

## Production roadmap

To turn this into a true clinical-grade platform, the next high-value steps are:

1. Replace heuristic matching with curated RxNorm/OpenFDA/SNOMED/ICD-linked knowledge ingestion
2. Replace OCR placeholder logic with a real prescription OCR/VLM pipeline
3. Expand built-in SQLite persistence into PostgreSQL plus migrations
4. Add semantic retrieval embeddings and calibrated model ensembles
5. Add authentication, audit trails, clinician review queues, and observability
6. Add real pharmacy pricing integrations where legally and operationally appropriate
