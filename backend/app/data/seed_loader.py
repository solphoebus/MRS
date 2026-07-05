from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class MedicineRecord:
    medicine_id: str
    generic_name: str
    brand_names: List[str]
    disease: str
    indications: List[str]
    otc: bool
    prescription: bool
    contraindications: List[str]
    allergies: List[str]
    pregnancy_avoid: bool
    breastfeeding_caution: bool
    kidney_caution: bool
    liver_caution: bool
    pediatric_caution: bool
    geriatric_caution: bool
    common_side_effects: List[str]
    serious_side_effects: List[str]
    black_box_warnings: List[str]
    food_interactions: List[str]
    dosage: Dict[str, str]


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return cleaned.strip("-") or "unknown"


def _split_brands(value: str) -> List[str]:
    parts = re.findall(
        r"[A-Z0-9][A-Za-z0-9%()+'/.-]*(?:\s+[A-Za-z0-9%()+'/.-]+)*", value
    )
    normalized = [part.strip() for part in parts if len(part.strip()) > 2]
    return normalized[:5] or [value[:80].strip()]


def _infer_generic_name(brands: List[str]) -> str:
    first = brands[0]
    return re.sub(r"\s+\d.*$", "", first).strip()


def _infer_side_effects(disease: str) -> List[str]:
    defaults = {
        "pain": ["nausea", "dizziness", "stomach upset"],
        "fever": ["nausea", "rash", "heartburn"],
        "cold": ["dry mouth", "drowsiness", "nausea"],
        "general": ["nausea", "headache", "dizziness"],
    }
    return defaults.get(disease.lower(), ["nausea", "headache", "dizziness"])


def load_seed_data(csv_path: Path) -> List[MedicineRecord]:
    records: List[MedicineRecord] = []
    with csv_path.open("r", encoding="utf-8", errors="ignore") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            disease = (row.get("Reason") or row.get("Category") or "General").strip()
            description = (
                row.get("Description") or "General symptomatic treatment"
            ).strip()
            raw_name = (row.get("Drug_Name") or "Unknown Medicine").strip()
            brands = _split_brands(raw_name)
            generic_name = _infer_generic_name(brands)
            medicine_id = _slugify(generic_name)
            lower_description = description.lower()
            lower_disease = disease.lower()
            is_otc = any(
                keyword in lower_disease or keyword in lower_description
                for keyword in ["cold", "fever", "pain", "cough"]
            )
            serious_effects = ["severe allergic reaction", "difficulty breathing"]
            if any(keyword in lower_description for keyword in ["renal", "kidney"]):
                serious_effects.append("worsening kidney function")
            records.append(
                MedicineRecord(
                    medicine_id=medicine_id,
                    generic_name=generic_name,
                    brand_names=brands,
                    disease=disease,
                    indications=[description],
                    otc=is_otc,
                    prescription=not is_otc,
                    contraindications=[
                        "known hypersensitivity",
                        "clinician review required before use",
                    ],
                    allergies=[generic_name.lower()],
                    pregnancy_avoid=any(
                        keyword in lower_description
                        for keyword in ["hormone", "steroid"]
                    ),
                    breastfeeding_caution=True,
                    kidney_caution=any(
                        keyword in lower_description for keyword in ["renal", "kidney"]
                    ),
                    liver_caution=any(
                        keyword in lower_description for keyword in ["liver", "hepatic"]
                    ),
                    pediatric_caution=not is_otc,
                    geriatric_caution=True,
                    common_side_effects=_infer_side_effects(lower_disease),
                    serious_side_effects=serious_effects,
                    black_box_warnings=[
                        "Use only with licensed clinician oversight when risk factors are present"
                    ],
                    food_interactions=["alcohol may increase side effects"],
                    dosage={
                        "dose": "Use standard labelled dose or clinician-directed dosing",
                        "frequency": "1-2 times daily depending on formulation",
                        "duration": "Shortest duration necessary",
                        "route": "oral",
                    },
                )
            )
    deduped: Dict[str, MedicineRecord] = {}
    for record in records:
        deduped.setdefault(record.medicine_id, record)
    return list(deduped.values())
