from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Medicine Recommendation Platform")
    app_version: str = Field(default="1.0.0")
    environment: str = Field(default="development")
    debug: bool = Field(default=True)
    database_url: str = Field(default="sqlite:///./medicine_recommendation.db")
    allow_mock_llm_explanations: bool = Field(default=True)
    medical_disclaimer: str = Field(
        default=(
            "For educational purposes and clinical decision support only. "
            "This system is not a substitute for professional medical advice, diagnosis, or treatment. "
            "Medication suggestions are non-definitive and must be reviewed by a licensed clinician."
        )
    )

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MRS_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
