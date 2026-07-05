from __future__ import annotations

from app.db.sqlite_store import SQLiteStore
from app.engine.recommendation_engine import RecommendationEngine
from app.models.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    SymptomAnalysisResponse,
)
from app.repositories.in_memory import InMemoryRepository


class RecommendationService:
    def __init__(self, repository: InMemoryRepository) -> None:
        self.repository = repository
        self.engine = RecommendationEngine(repository)

    def get_recommendations(
        self, request: RecommendationRequest, store: SQLiteStore | None = None
    ) -> RecommendationResponse:
        response = self.engine.recommend(request)
        self.repository.log_history(
            {
                "type": "recommendation",
                "request": request.model_dump(),
                "response": response.model_dump(),
            }
        )
        if store is not None:
            store.log_history(
                "recommendation",
                {"request": request.model_dump(), "response": response.model_dump()},
            )
        return response

    def analyze_symptoms(
        self, symptoms: list[str], store: SQLiteStore | None = None
    ) -> SymptomAnalysisResponse:
        request = RecommendationRequest(symptoms=symptoms, age=30)
        response = self.engine.recommend(request)
        if store is not None:
            store.log_history(
                "symptom-analysis",
                {"symptoms": symptoms, "response": response.model_dump()},
            )
        return SymptomAnalysisResponse(
            normalized_symptoms=[
                symptom.strip().lower() for symptom in symptoms if symptom.strip()
            ],
            likely_diseases=response.matched_disease_candidates,
            confidence_score=response.confidence_score,
        )
