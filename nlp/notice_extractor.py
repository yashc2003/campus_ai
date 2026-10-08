from __future__ import annotations

import re


DATE_PATTERN = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})\b", re.I)


def extract_notice_facts(text: str) -> dict:
    lines = [re.sub(r"\s+", " ", line).strip(" •-\t") for line in text.splitlines()]
    lines = [line for line in lines if line]
    title = next((line for line in lines if len(line) > 5), "Untitled notice")[:180]
    dates = []
    for line in lines:
        for match in DATE_PATTERN.finditer(line):
            dates.append({"date_text": match.group(0), "context": line[:360]})
    actions = [line[:360] for line in lines if re.search(r"\b(submit|register|apply|pay|attend|complete|contact|deadline|last date|eligible|eligibility|required documents)\b", line, re.I)]
    summary = " ".join(lines[:3])[:850]
    return {"title": title, "summary": summary, "important_dates": dates,
            "eligibility": [line[:360] for line in lines if re.search(r"eligible|eligibility|who can|semester|students of", line, re.I)],
            "required_documents": [line[:360] for line in lines if re.search(r"required documents|attach|enclose|documents required", line, re.I)],
            "actions": actions}
