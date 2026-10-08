from __future__ import annotations

import re


def detect_language(text: str) -> tuple[str, str]:
    """Identify common Devanagari queries without claiming model-level accuracy."""
    devanagari = len(re.findall(r"[\u0900-\u097f]", text))
    if devanagari:
        lower = text.casefold()
        marathi_markers = ("ची", "चा", "चे", "भरण्याची", "शेवटची", "आहे", "मला", "कधी", "यासाठी")
        hindi_markers = ("क्या", "है", "कब", "कैसे", "की तारीख", "करना", "में", "कृपया")
        marathi_score = sum(marker in lower for marker in marathi_markers)
        hindi_score = sum(marker in lower for marker in hindi_markers)
        if marathi_score > hindi_score: return "mr", "Marathi (script and phrase hints)"
        if hindi_score > marathi_score: return "hi", "Hindi (script and phrase hints)"
        return "und", "Devanagari (Hindi/Marathi not confidently distinguished)"
    return "en", "English / Latin script"
