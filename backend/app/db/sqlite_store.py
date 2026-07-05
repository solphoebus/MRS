from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class SQLiteStore:
    def __init__(self, database_url: str) -> None:
        if database_url.startswith("sqlite:///"):
            db_path = database_url.replace("sqlite:///", "", 1)
        else:
            db_path = database_url
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS patient_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT UNIQUE NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recommendation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS medicines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    medicine_id TEXT UNIQUE NOT NULL,
                    generic_name TEXT NOT NULL,
                    brand_names_json TEXT NOT NULL,
                    disease TEXT NOT NULL,
                    otc INTEGER NOT NULL,
                    prescription INTEGER NOT NULL,
                    estimated_price REAL NOT NULL
                )
                """
            )
            conn.commit()

    def save_patient(self, payload: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO patient_profiles (patient_id, payload_json)
                VALUES (?, ?)
                ON CONFLICT(patient_id) DO UPDATE SET payload_json=excluded.payload_json
                """,
                (payload["patient_id"], json.dumps(payload)),
            )
            conn.commit()

    def log_history(self, event_type: str, payload: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO recommendation_history (event_type, payload_json) VALUES (?, ?)",
                (event_type, json.dumps(payload)),
            )
            conn.commit()

    def list_patients(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT patient_id, payload_json, created_at FROM patient_profiles ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "patient_id": row[0],
                "payload": json.loads(row[1]),
                "created_at": row[2],
            }
            for row in rows
        ]

    def list_history(self, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event_type, payload_json, created_at FROM recommendation_history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "event_type": row[0],
                "payload": json.loads(row[1]),
                "created_at": row[2],
            }
            for row in rows
        ]

    def sync_medicines(self, medicines: list[dict]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO medicines (medicine_id, generic_name, brand_names_json, disease, otc, prescription, estimated_price)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(medicine_id) DO UPDATE SET
                    generic_name=excluded.generic_name,
                    brand_names_json=excluded.brand_names_json,
                    disease=excluded.disease,
                    otc=excluded.otc,
                    prescription=excluded.prescription,
                    estimated_price=excluded.estimated_price
                """,
                [
                    (
                        m["medicine_id"],
                        m["generic_name"],
                        json.dumps(m["brand_names"]),
                        m["disease"],
                        int(m["otc"]),
                        int(m["prescription"]),
                        m["estimated_price"],
                    )
                    for m in medicines
                ],
            )
            conn.commit()

    def count_medicines(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM medicines").fetchone()[0]
