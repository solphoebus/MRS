from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ModelResult:
    model_name: str
    disease_scores: Dict[str, float]


class BaseInferenceModel:
    model_name = "base"

    def predict(self, symptoms: List[str], diseases: List[str]) -> ModelResult:
        raise NotImplementedError


class KeywordOverlapModel(BaseInferenceModel):
    model_name = "keyword-overlap"

    def predict(self, symptoms: List[str], diseases: List[str]) -> ModelResult:
        normalized = [s.lower().strip() for s in symptoms if s.strip()]
        scores: Dict[str, float] = {}
        for disease in diseases:
            disease_l = disease.lower()
            overlap = sum(
                1
                for symptom in normalized
                if symptom in disease_l or disease_l in symptom
            )
            scores[disease] = overlap / max(len(normalized), 1)
        return ModelResult(model_name=self.model_name, disease_scores=scores)


class EnsembleInferencePipeline:
    """Production-oriented interface with placeholder model registry.

    The implementation is intentionally lightweight for this repository, but the
    contract supports future RandomForest/XGBoost/LightGBM/CatBoost/NN adapters.
    """

    def __init__(self) -> None:
        self.models = [KeywordOverlapModel()]

    def predict(self, symptoms: List[str], diseases: List[str]) -> Dict[str, float]:
        if not diseases:
            return {}
        aggregate = {disease: 0.0 for disease in diseases}
        for model in self.models:
            result = model.predict(symptoms, diseases)
            for disease, score in result.disease_scores.items():
                aggregate[disease] += score
        divisor = max(len(self.models), 1)
        return {
            disease: round(score / divisor, 4) for disease, score in aggregate.items()
        }
