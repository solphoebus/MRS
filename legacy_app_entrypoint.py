"""Legacy entrypoint retained for compatibility.

The original Streamlit demo has been superseded by the FastAPI backend in
`backend/app/main.py` and the static dashboard in `frontend/`.
"""

print(
    "This repository has been refactored into a FastAPI-based platform. "
    "Run: uvicorn app.main:app --app-dir backend --reload"
)
