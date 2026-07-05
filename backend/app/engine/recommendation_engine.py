from __future__ import annotations

from collections import defaultdict
from typing import List

from app.core.config import get_settings
from app.inference.pipeline import EnsembleInferencePipeline
from app.models.schemas import (
    AlternativeRecommendation,
    DosingInstruction,
    MedicineRecommendation,
    RecommendationRequest,
    RecommendationResponse,
    SafetyIssue,
    SideEffectProfile,
)
from app.repositories.in_memory import InMemoryRepository


class RecommendationEngine:
    def __init__(self, repository: InMemoryRepository) -> None:
        self.repository = repository
        self.inference = EnsembleInferencePipeline()
        self.settings = get_settings()

    def _normalize_symptoms(self, symptoms: List[str]) -> List[str]:
        return list(
            dict.fromkeys(
                symptom.strip().lower() for symptom in symptoms if symptom.strip()
            )
        )

    def _match_diseases(self, request: RecommendationRequest) -> List[str]:
        candidates = defaultdict(int)
        for symptom in self._normalize_symptoms(request.symptoms):
            for medicine in self.repository.list_medicines():
                text = " ".join(medicine.indications + [medicine.disease]).lower()
                if symptom in text:
                    candidates[medicine.disease] += 1
        if request.diagnosed_disease:
            candidates[request.diagnosed_disease] += 5
        ranked = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
        return [name for name, _ in ranked[:5]]

    def _safety_checks(
        self, request: RecommendationRequest, medicine
    ) -> List[SafetyIssue]:
        issues: List[SafetyIssue] = []
        current_meds = [m.lower() for m in request.current_medications]
        allergies = [a.lower() for a in request.allergies]
        conditions = [c.lower() for c in request.existing_medical_conditions]

        if any(allergy in medicine.generic_name.lower() for allergy in allergies):
            issues.append(
                SafetyIssue(
                    category="allergy",
                    severity="high",
                    message="Potential allergy conflict with medicine name or known hypersensitivity.",
                )
            )
        if request.pregnancy_status and medicine.pregnancy_avoid:
            issues.append(
                SafetyIssue(
                    category="pregnancy",
                    severity="high",
                    message="Avoid or review carefully in pregnancy.",
                )
            )
        if request.breastfeeding and medicine.breastfeeding_caution:
            issues.append(
                SafetyIssue(
                    category="breastfeeding",
                    severity="medium",
                    message="Breastfeeding safety needs clinician review.",
                )
            )
        if (
            any(
                "kidney" in condition or "renal" in condition
                for condition in conditions
            )
            and medicine.kidney_caution
        ):
            issues.append(
                SafetyIssue(
                    category="kidney",
                    severity="high",
                    message="Kidney impairment caution.",
                )
            )
        if (
            any(
                "liver" in condition or "hepatic" in condition
                for condition in conditions
            )
            and medicine.liver_caution
        ):
            issues.append(
                SafetyIssue(
                    category="liver",
                    severity="high",
                    message="Liver impairment caution.",
                )
            )
        if request.age < 12 and medicine.pediatric_caution:
            issues.append(
                SafetyIssue(
                    category="pediatric",
                    severity="high",
                    message="Pediatric dosing/safety requires clinician confirmation.",
                )
            )
        if request.age >= 65 and medicine.geriatric_caution:
            issues.append(
                SafetyIssue(
                    category="geriatric",
                    severity="medium",
                    message="Geriatric patient may need conservative dosing and closer monitoring.",
                )
            )
        if any(token in medicine.generic_name.lower() for token in current_meds):
            issues.append(
                SafetyIssue(
                    category="drug-drug",
                    severity="high",
                    message="Possible duplication with current medication list.",
                )
            )
        if medicine.food_interactions:
            issues.append(
                SafetyIssue(
                    category="drug-food",
                    severity="low",
                    message=medicine.food_interactions[0],
                )
            )
        return issues

    def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        matched_diseases = self._match_diseases(request)
        if not matched_diseases:
            matched_diseases = (
                [request.diagnosed_disease]
                if request.diagnosed_disease
                else ["General"]
            )

        disease_scores = self.inference.predict(request.symptoms, matched_diseases)
        candidate_medicines = []
        for disease in matched_diseases:
            candidate_medicines.extend(self.repository.find_by_disease(disease)[:10])

        seen = set()
        unique_candidates = []
        for medicine in candidate_medicines:
            if medicine.medicine_id not in seen:
                unique_candidates.append(medicine)
                seen.add(medicine.medicine_id)

        recommendations = []
        dangerous_combinations = []
        normalized_symptoms = self._normalize_symptoms(request.symptoms)
        for idx, medicine in enumerate(unique_candidates[:5]):
            safety_issues = self._safety_checks(request, medicine)
            dangerous_combinations.extend(
                [issue for issue in safety_issues if issue.severity == "high"]
            )
            disease_score = disease_scores.get(medicine.disease, 0.35)
            severity_bonus = {"mild": 0.0, "moderate": 0.05, "severe": 0.1}[
                request.severity.value
            ]
            confidence = min(
                round(
                    0.35
                    + disease_score
                    + severity_bonus
                    - (0.1 * len([i for i in safety_issues if i.severity == "high"])),
                    3,
                ),
                0.99,
            )
            category = "otc" if medicine.otc else "prescription"
            recommendation_type = (
                "first-line"
                if idx == 0
                else ("alternative" if idx < 3 else "supportive")
            )
            recommendations.append(
                MedicineRecommendation(
                    medicine_id=medicine.medicine_id,
                    generic_name=medicine.generic_name,
                    brand_names=medicine.brand_names,
                    category=category,
                    recommendation_type=recommendation_type,
                    confidence_score=max(confidence, 0.05),
                    rationale=[
                        f"Matched disease context: {medicine.disease}",
                        f"Indication overlap with symptoms: {', '.join(normalized_symptoms[:4]) or 'limited'}",
                        "Recommendation generated from educational seed data and rule-based safety filters",
                    ],
                    why_selected=[
                        "Candidate indication aligned with symptom/disease context",
                        "Included in top-ranked disease match set",
                    ],
                    why_alternatives_rejected=[
                        "Some alternatives ranked lower due to weaker disease match or higher safety burden",
                    ],
                    risk_factors_considered=[
                        "age",
                        "pregnancy status",
                        "breastfeeding",
                        "allergies",
                        "current medications",
                        "kidney/liver conditions",
                    ],
                    supporting_symptoms=normalized_symptoms[:5],
                    contraindications_considered=medicine.contraindications,
                    expected_effectiveness="Potentially helpful for symptom relief or disease-directed support; clinician review required.",
                    estimated_price=self.repository.price_for(medicine),
                    dosage=DosingInstruction(
                        dose=medicine.dosage["dose"],
                        frequency=medicine.dosage["frequency"],
                        duration=medicine.dosage["duration"],
                        route=medicine.dosage["route"],
                        administration_instructions=[
                            "Follow product labeling and clinician advice",
                            "Stop and seek medical advice if symptoms worsen or serious side effects appear",
                        ],
                    ),
                    safety_issues=safety_issues,
                    side_effects=SideEffectProfile(
                        common=medicine.common_side_effects,
                        serious=medicine.serious_side_effects,
                        black_box_warnings=medicine.black_box_warnings,
                        stop_medication_when=[
                            "signs of allergy",
                            "severe rash",
                            "worsening symptoms",
                        ],
                        emergency_warning_signs=[
                            "difficulty breathing",
                            "facial swelling",
                            "chest pain",
                        ],
                    ),
                )
            )

        overall_confidence = round(
            sum(item.confidence_score for item in recommendations)
            / max(len(recommendations), 1),
            3,
        )
        alternatives = [
            AlternativeRecommendation(
                type="natural-remedy",
                name="Warm fluids / hydration",
                rationale="Supports symptomatic recovery for many mild conditions.",
            ),
            AlternativeRecommendation(
                type="lifestyle",
                name="Adequate rest",
                rationale="Reduces physiologic stress and may improve recovery.",
            ),
            AlternativeRecommendation(
                type="diet",
                name="Light balanced meals",
                rationale="Can reduce GI strain and support hydration/nutrition.",
            ),
            AlternativeRecommendation(
                type="home-care",
                name="Monitor warning signs",
                rationale="Escalate promptly if severe or persistent symptoms develop.",
            ),
        ]

        explanation = (
            "These non-definitive options were ranked using symptom/disease matching, "
            "rule-based safety checks, educational seed data, and estimated price signals. "
            "A licensed clinician should confirm suitability, dosing, and interaction safety before use."
        )

        return RecommendationResponse(
            disclaimer=self.settings.medical_disclaimer,
            patient_friendly_explanation=explanation,
            confidence_score=overall_confidence,
            matched_disease_candidates=matched_diseases,
            recommendations=recommendations,
            alternatives=alternatives,
            dangerous_combinations=dangerous_combinations,
        )
