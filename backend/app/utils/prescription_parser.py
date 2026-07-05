from __future__ import annotations

import re
from typing import List

COMMON_MED_TOKENS = {
    "tablet",
    "tab",
    "capsule",
    "cap",
    "syrup",
    "inj",
    "injection",
    "cream",
    "gel",
    "drop",
    "drops",
    "mg",
    "ml",
    "od",
    "bd",
    "tid",
    "sos",
}


def extract_medicine_candidates(text: str) -> List[str]:
    candidates: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        cleaned = re.sub(r"[^A-Za-z0-9%()'+/ .-]", " ", line)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            continue
        words = cleaned.split()
        meaningful = [w for w in words if w.lower() not in COMMON_MED_TOKENS]
        if not meaningful:
            continue
        candidate = " ".join(meaningful[:4]).strip()
        if len(candidate) > 2 and candidate.lower() not in {
            c.lower() for c in candidates
        }:
            candidates.append(candidate)
    return candidates[:10]
