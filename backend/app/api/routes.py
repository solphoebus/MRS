from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.core.config import get_settings
from app.db.dependencies import (
    get_persistent_store,
    get_recommendation_service,
    get_repository,
)
from app.db.sqlite_store import SQLiteStore
from app.models.schemas import (
    DiseaseInfoResponse,
    HealthCheckResponse,
    InteractionResponse,
    MedicineInfoResponse,
    PatientCreateRequest,
    PatientResponse,
    PrescriptionScanRequest,
    PrescriptionScanResponse,
    RecommendationRequest,
    RecommendationResponse,
    SafetyIssue,
    ScannedPrescriptionItem,
    SymptomAnalysisRequest,
    SymptomAnalysisResponse,
)
from app.repositories.in_memory import InMemoryRepository
from app.services.recommendation_service import RecommendationService
from app.utils.ocr import extract_text_from_uploaded_prescription
from app.utils.prescription_parser import extract_medicine_candidates

router = APIRouter()


def _build_scan_response(
    text: str, repository: InMemoryRepository
) -> PrescriptionScanResponse:
    candidates = extract_medicine_candidates(text)
    items: list[ScannedPrescriptionItem] = []
    for candidate in candidates:
        matches = repository.match_medicines_by_tokens(candidate)
        if not matches:
            items.append(
                ScannedPrescriptionItem(
                    original_text=candidate,
                    review_note="No confident match found. Manual pharmacist review recommended.",
                )
            )
            continue
        match = matches[0]
        cheapest = repository.cheapest_alternative(match)
        current_price = repository.price_for(match)
        alt_price = repository.price_for(cheapest) if cheapest else None
        items.append(
            ScannedPrescriptionItem(
                original_text=candidate,
                matched_medicine_id=match.medicine_id,
                matched_generic_name=match.generic_name,
                estimated_price=current_price,
                cheapest_alternative_id=cheapest.medicine_id if cheapest else None,
                cheapest_alternative_name=cheapest.generic_name if cheapest else None,
                cheapest_alternative_price=alt_price,
                estimated_savings=round(current_price - alt_price, 2)
                if alt_price is not None
                else None,
                review_note=(
                    "Estimated lower-cost alternative identified from same disease bucket. "
                    "Substitution requires clinician/pharmacist verification for formulation, strength, and appropriateness."
                ),
            )
        )
    return PrescriptionScanResponse(
        disclaimer=get_settings().medical_disclaimer,
        extracted_candidates=candidates,
        items=items,
        summary="Prescription scan completed with heuristic medicine extraction and price comparison. Always verify substitutions professionally.",
    )


@router.get("/health-check", response_model=HealthCheckResponse)
def health_check() -> HealthCheckResponse:
    settings = get_settings()
    return HealthCheckResponse(
        status="ok",
        version=settings.app_version,
        disclaimer=settings.medical_disclaimer,
    )


@router.post("/patient", response_model=PatientResponse)
def create_patient(
    payload: PatientCreateRequest,
    repository: InMemoryRepository = Depends(get_repository),
    store: SQLiteStore = Depends(get_persistent_store),
) -> PatientResponse:
    repository.save_patient(payload.model_dump())
    store.save_patient(payload.model_dump())
    return PatientResponse(
        patient_id=payload.patient_id,
        message="Patient profile stored for educational clinical decision support workflows.",
    )


@router.post("/recommend", response_model=RecommendationResponse)
def recommend(
    payload: RecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service),
    store: SQLiteStore = Depends(get_persistent_store),
) -> RecommendationResponse:
    return service.get_recommendations(payload, store=store)


@router.post("/symptom-analysis", response_model=SymptomAnalysisResponse)
def symptom_analysis(
    payload: SymptomAnalysisRequest,
    service: RecommendationService = Depends(get_recommendation_service),
    store: SQLiteStore = Depends(get_persistent_store),
) -> SymptomAnalysisResponse:
    return service.analyze_symptoms(payload.symptoms, store=store)


@router.post("/scan-prescription", response_model=PrescriptionScanResponse)
def scan_prescription(
    payload: PrescriptionScanRequest,
    repository: InMemoryRepository = Depends(get_repository),
    store: SQLiteStore = Depends(get_persistent_store),
) -> PrescriptionScanResponse:
    response = _build_scan_response(payload.prescription_text, repository)
    store.log_history("scan-prescription", response.model_dump())
    return response


@router.post("/scan-prescription-image", response_model=PrescriptionScanResponse)
async def scan_prescription_image(
    file: UploadFile = File(...),
    repository: InMemoryRepository = Depends(get_repository),
    store: SQLiteStore = Depends(get_persistent_store),
) -> PrescriptionScanResponse:
    uploads_dir = Path(__file__).resolve().parents[1] / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    destination = uploads_dir / file.filename
    destination.write_bytes(await file.read())
    extracted_text = extract_text_from_uploaded_prescription(destination)
    response = _build_scan_response(extracted_text, repository)
    store.log_history(
        "scan-prescription-image",
        {"filename": file.filename, "response": response.model_dump()},
    )
    return response


@router.get("/medicine/{medicine_id}", response_model=MedicineInfoResponse)
def get_medicine(
    medicine_id: str, repository: InMemoryRepository = Depends(get_repository)
) -> MedicineInfoResponse:
    medicine = repository.get_medicine(medicine_id)
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    return MedicineInfoResponse(
        medicine_id=medicine.medicine_id,
        generic_name=medicine.generic_name,
        brand_names=medicine.brand_names,
        indications=medicine.indications,
        otc=medicine.otc,
        prescription=medicine.prescription,
        contraindications=medicine.contraindications,
        common_side_effects=medicine.common_side_effects,
        serious_side_effects=medicine.serious_side_effects,
    )


@router.get("/disease/{disease_id}", response_model=DiseaseInfoResponse)
def get_disease(
    disease_id: str, repository: InMemoryRepository = Depends(get_repository)
) -> DiseaseInfoResponse:
    return DiseaseInfoResponse(**repository.get_disease_info(disease_id))


@router.get("/interaction", response_model=InteractionResponse)
def get_interaction(
    subject: str = Query(...), target: str = Query(...)
) -> InteractionResponse:
    interaction = None
    if subject.lower() == target.lower():
        interaction = SafetyIssue(
            category="drug-drug",
            severity="high",
            message="Duplicate or same medicine detected; review therapeutic duplication risk.",
        )
    elif any(
        token in {subject.lower(), target.lower()}
        for token in {"alcohol", "warfarin", "ibuprofen"}
    ):
        interaction = SafetyIssue(
            category="drug-drug",
            severity="medium",
            message="Potential interaction found in heuristic rules; clinician/pharmacist review recommended.",
        )
    return InteractionResponse(subject=subject, target=target, interaction=interaction)


@router.get("/alternatives")
def get_alternatives(
    query: str, repository: InMemoryRepository = Depends(get_repository)
) -> dict:
    matches = repository.search_medicines(query)[:10]
    return {
        "disclaimer": get_settings().medical_disclaimer,
        "query": query,
        "results": [
            {
                "medicine_id": item.medicine_id,
                "generic_name": item.generic_name,
                "brand_names": item.brand_names,
                "disease": item.disease,
                "estimated_price": repository.price_for(item),
            }
            for item in matches
        ],
    }


@router.get("/drug-info")
def get_drug_info(
    query: str, repository: InMemoryRepository = Depends(get_repository)
) -> dict:
    matches = repository.search_medicines(query)[:5]
    return {
        "disclaimer": get_settings().medical_disclaimer,
        "query": query,
        "results": [
            {
                "medicine_id": item.medicine_id,
                "generic_name": item.generic_name,
                "brand_names": item.brand_names,
                "indications": item.indications,
                "contraindications": item.contraindications,
                "food_interactions": item.food_interactions,
                "estimated_price": repository.price_for(item),
            }
            for item in matches
        ],
    }


@router.get("/debug/patients")
def debug_patients(store: SQLiteStore = Depends(get_persistent_store)) -> dict:
    return {
        "count": len(store.list_patients(limit=200)),
        "patients": store.list_patients(limit=50),
    }


@router.get("/debug/history")
def debug_history(store: SQLiteStore = Depends(get_persistent_store)) -> dict:
    return {
        "count": len(store.list_history(limit=500)),
        "events": store.list_history(limit=100),
    }


@router.get("/debug/medicines")
def debug_medicines(
    repository: InMemoryRepository = Depends(get_repository),
    store: SQLiteStore = Depends(get_persistent_store),
) -> dict:
    medicines = repository.list_medicines()
    return {
        "count": len(medicines),
        "db_persisted_count": store.count_medicines(),
        "sample": [
            {
                "medicine_id": item.medicine_id,
                "generic_name": item.generic_name,
                "disease": item.disease,
            }
            for item in medicines[:20]
        ],
    }
