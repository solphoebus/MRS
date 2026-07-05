from functools import lru_cache

from app.db.session import get_store
from app.repositories.in_memory import InMemoryRepository
from app.services.recommendation_service import RecommendationService


@lru_cache
def get_repository() -> InMemoryRepository:
    return InMemoryRepository()


def get_persistent_store():
    return get_store()


def get_recommendation_service() -> RecommendationService:
    return RecommendationService(get_repository())
