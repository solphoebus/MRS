from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"
    undisclosed = "undisclosed"


class SafetyIssue(BaseModel):
    category: str
    severity: str
    message: str


class SideEffectProfile(BaseModel):
    common: List[str] = Field(default_factory=list)
    serious: List[str] = Field(default_factory=list)
    black_box_warnings: List[str] = Field(default_factory=list)
    stop_medication_when: List[str] = Field(default_factory=list)
    emergency_warning_signs: List[str] = Field(default_factory=list)


class DosingInstruction(BaseModel):
    dose: str
    frequency: str
    duration: str
    route: str
    administration_instructions: List[str] = Field(default_factory=list)


class AlternativeRecommendation(BaseModel):
    type: str
    name: str
    rationale: str


class MedicineRecommendation(BaseModel):
    medicine_id: str
    generic_name: str
    brand_names: List[str] = Field(default_factory=list)
    category: str
    recommendation_type: str
    confidence_score: float
    rationale: List[str] = Field(default_factory=list)
    why_selected: List[str] = Field(default_factory=list)
    why_alternatives_rejected: List[str] = Field(default_factory=list)
    risk_factors_considered: List[str] = Field(default_factory=list)
    supporting_symptoms: List[str] = Field(default_factory=list)
    contraindications_considered: List[str] = Field(default_factory=list)
    expected_effectiveness: str
    estimated_price: float | None = None
    dosage: DosingInstruction
    safety_issues: List[SafetyIssue] = Field(default_factory=list)
    side_effects: SideEffectProfile


class RecommendationRequest(BaseModel):
    symptoms: List[str] = Field(default_factory=list)
    diagnosed_disease: Optional[str] = None
    age: int = Field(ge=0, le=120)
    weight_kg: Optional[float] = Field(default=None, gt=0)
    gender: Gender = Gender.undisclosed
    pregnancy_status: Optional[bool] = None
    breastfeeding: Optional[bool] = None
    existing_medical_conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    current_medications: List[str] = Field(default_factory=list)
    severity: Severity = Severity.mild
    country_region: Optional[str] = None


class RecommendationResponse(BaseModel):
    disclaimer: str
    patient_friendly_explanation: str
    confidence_score: float
    matched_disease_candidates: List[str] = Field(default_factory=list)
    recommendations: List[MedicineRecommendation] = Field(default_factory=list)
    alternatives: List[AlternativeRecommendation] = Field(default_factory=list)
    dangerous_combinations: List[SafetyIssue] = Field(default_factory=list)


class PatientCreateRequest(BaseModel):
    patient_id: str
    age: int = Field(ge=0, le=120)
    weight_kg: Optional[float] = Field(default=None, gt=0)
    gender: Gender = Gender.undisclosed
    pregnancy_status: Optional[bool] = None
    breastfeeding: Optional[bool] = None
    conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    country_region: Optional[str] = None


class PatientResponse(BaseModel):
    patient_id: str
    message: str


class MedicineInfoResponse(BaseModel):
    medicine_id: str
    generic_name: str
    brand_names: List[str]
    indications: List[str]
    otc: bool
    prescription: bool
    contraindications: List[str]
    common_side_effects: List[str]
    serious_side_effects: List[str]


class DiseaseInfoResponse(BaseModel):
    disease_id: str
    name: str
    symptoms: List[str]
    precautions: List[str]


class InteractionResponse(BaseModel):
    subject: str
    target: str
    interaction: Optional[SafetyIssue] = None


class SymptomAnalysisRequest(BaseModel):
    symptoms: List[str]


class SymptomAnalysisResponse(BaseModel):
    normalized_symptoms: List[str]
    likely_diseases: List[str]
    confidence_score: float


class PrescriptionScanRequest(BaseModel):
    prescription_text: str


class ScannedPrescriptionItem(BaseModel):
    original_text: str
    matched_medicine_id: str | None = None
    matched_generic_name: str | None = None
    estimated_price: float | None = None
    cheapest_alternative_id: str | None = None
    cheapest_alternative_name: str | None = None
    cheapest_alternative_price: float | None = None
    estimated_savings: float | None = None
    review_note: str


class PrescriptionScanResponse(BaseModel):
    disclaimer: str
    extracted_candidates: List[str] = Field(default_factory=list)
    items: List[ScannedPrescriptionItem] = Field(default_factory=list)
    summary: str


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    disclaimer: str
