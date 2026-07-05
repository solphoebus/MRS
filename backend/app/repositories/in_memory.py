from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from app.data.seed_loader import MedicineRecord, load_seed_data

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_DOSAGE_TOKEN_RE = re.compile(r"^\d+(mg|ml|mcg|g|iu|s)$")


def _significant_tokens(text: str) -> List[str]:
    tokens: List[str] = []
    for token in _TOKEN_RE.findall(text.lower()):
        if token.isdigit() or len(token) < 2 or _DOSAGE_TOKEN_RE.match(token):
            continue
        tokens.append(token)
    return tokens


def _combined_text(item: MedicineRecord) -> str:
    return " ".join(
        [item.generic_name, " ".join(item.brand_names), item.disease]
    ).lower()


class InMemoryRepository:
    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[3]
        csv_path = root / "medicine.csv"
        self.medicines: List[MedicineRecord] = load_seed_data(csv_path)
        self.medicine_by_id: Dict[str, MedicineRecord] = {
            item.medicine_id: item for item in self.medicines
        }
        self.patient_store: Dict[str, dict] = {}
        self.history: List[dict] = []

    def list_medicines(self) -> List[MedicineRecord]:
        return self.medicines

    def get_medicine(self, medicine_id: str) -> Optional[MedicineRecord]:
        return self.medicine_by_id.get(medicine_id)

    def find_by_disease(self, disease: str) -> List[MedicineRecord]:
        disease_l = disease.lower()
        return [
            item
            for item in self.medicines
            if disease_l in item.disease.lower()
            or any(disease_l in indication.lower() for indication in item.indications)
        ]

    def search_medicines(self, query: str) -> List[MedicineRecord]:
        query_l = query.lower()
        return [
            item
            for item in self.medicines
            if query_l in item.generic_name.lower()
            or any(query_l in brand.lower() for brand in item.brand_names)
            or query_l in item.disease.lower()
        ]

    def match_medicines_by_tokens(self, query: str) -> List[MedicineRecord]:
        """Token-based matching used for prescription scanning.

        The seed CSV concatenates dosage-form words (Tablet, Syrup, etc.) and
        pack-size suffixes directly into drug names in inconsistent ways, while
        scanned prescription text has those same words stripped out. A strict
        whole-phrase substring match therefore misses real, present drugs.
        Matching on significant tokens (ignoring dosage/pack-size noise) and
        ranking by how many tokens matched is far more robust.
        """
        tokens = _significant_tokens(query)
        if not tokens:
            return []
        scored: List[tuple[int, MedicineRecord]] = []
        for item in self.medicines:
            combined = _combined_text(item)
            matched = sum(1 for token in tokens if token in combined)
            if matched:
                scored.append((matched, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored]

    def price_for(self, medicine: MedicineRecord) -> float:
        base = 35 + (sum(ord(ch) for ch in medicine.generic_name[:12]) % 250)
        if medicine.prescription:
            base += 45
        return round(float(base), 2)

    def cheapest_alternative(
        self, medicine: MedicineRecord
    ) -> Optional[MedicineRecord]:
        peers = [
            item
            for item in self.find_by_disease(medicine.disease)
            if item.medicine_id != medicine.medicine_id
        ]
        if not peers:
            return None
        return sorted(peers, key=self.price_for)[0]

    def save_patient(self, payload: dict) -> None:
        self.patient_store[payload["patient_id"]] = payload

    def get_disease_info(self, disease_id: str) -> dict:
        name = disease_id.replace("-", " ").title()
        examples = self.find_by_disease(name)[:8]
        symptoms = []
        for item in examples:
            for indication in item.indications:
                symptoms.extend(
                    [token.strip() for token in indication.split(",") if token.strip()]
                )
        return {
            "disease_id": disease_id,
            "name": name,
            "symptoms": list(dict.fromkeys(symptoms))[:10],
            "precautions": [
                "Seek professional medical evaluation for persistent or severe symptoms",
                "Review medicine safety against allergies, pregnancy, kidney, and liver status",
            ],
        }

    def log_history(self, payload: dict) -> None:
        self.history.append(payload)
