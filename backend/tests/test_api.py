import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import get_store
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health-check")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "educational purposes" in body["disclaimer"].lower()


def test_root_serves_frontend() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Medisense" in response.text


def test_symptom_analysis() -> None:
    response = client.post("/symptom-analysis", json={"symptoms": ["fever", "pain"]})
    assert response.status_code == 200
    body = response.json()
    assert "fever" in body["normalized_symptoms"]
    assert isinstance(body["likely_diseases"], list)


def test_recommendation_endpoint() -> None:
    response = client.post(
        "/recommend",
        json={
            "symptoms": ["fever", "pain"],
            "diagnosed_disease": "Pain",
            "age": 34,
            "weight_kg": 70,
            "gender": "male",
            "pregnancy_status": False,
            "breastfeeding": False,
            "existing_medical_conditions": ["hypertension"],
            "allergies": ["penicillin"],
            "current_medications": ["ibuprofen"],
            "severity": "moderate",
            "country_region": "IN",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendations"]
    assert body["confidence_score"] > 0
    assert body["recommendations"][0]["estimated_price"] is not None
    assert "not a substitute" in body["disclaimer"].lower()


def test_prescription_scan() -> None:
    response = client.post(
        "/scan-prescription",
        json={
            "prescription_text": "Tab Aceclo Plus 10'S\nCap Paracetamol 500mg\nIbuprofen SOS"
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    assert "verify substitutions" in body["summary"].lower()


def test_prescription_scan_matches_known_drug() -> None:
    response = client.post(
        "/scan-prescription",
        json={"prescription_text": "Tab Aceclo Plus 10'S"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    assert any(item["matched_generic_name"] for item in body["items"])


def test_debug_medicines_endpoint() -> None:
    response = client.get("/debug/medicines")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] > 0
    assert body["db_persisted_count"] > 0
    assert body["sample"]


def test_prescription_image_upload() -> None:
    response = client.post(
        "/scan-prescription-image",
        files={
            "file": ("prescription.txt", b"Paracetamol 500mg\nIbuprofen", "text/plain")
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["items"]


def test_patient_write_and_debug_endpoints() -> None:
    patient_id = "test-patient-debug"
    response = client.post(
        "/patient",
        json={
            "patient_id": patient_id,
            "age": 28,
            "weight_kg": 65,
            "gender": "female",
            "pregnancy_status": False,
            "breastfeeding": False,
            "conditions": ["asthma"],
            "allergies": ["pollen"],
            "medications": ["cetirizine"],
            "country_region": "IN",
        },
    )
    assert response.status_code == 200
    patients_response = client.get("/debug/patients")
    history_response = client.get("/debug/history")
    assert patients_response.status_code == 200
    assert history_response.status_code == 200
    patients_body = patients_response.json()
    history_body = history_response.json()
    assert any(
        patient["patient_id"] == patient_id for patient in patients_body["patients"]
    )
    store = get_store()
    conn = sqlite3.connect(store.path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM patient_profiles WHERE patient_id = ?", (patient_id,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert count >= 1


def test_medicine_lookup_not_found() -> None:
    response = client.get("/medicine/does-not-exist")
    assert response.status_code == 404
