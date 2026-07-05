from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.dependencies import get_repository
from app.db.session import get_store, init_db

configure_logging()
settings = get_settings()
init_db()

_repository = get_repository()
get_store().sync_medicines(
    [
        {
            "medicine_id": item.medicine_id,
            "generic_name": item.generic_name,
            "brand_names": item.brand_names,
            "disease": item.disease,
            "otc": item.otc,
            "prescription": item.prescription,
            "estimated_price": _repository.price_for(item),
        }
        for item in _repository.list_medicines()
    ]
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Generic AI-powered medicine recommendation platform for educational purposes "
        "and clinical decision support only. Not a substitute for professional medical advice."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_frontend() -> FileResponse:
    return FileResponse(static_dir / "index.html")
