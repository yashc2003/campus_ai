from __future__ import annotations

import re
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import BinaryIO

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from utils.config import PROJECT_ROOT

XLSX_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
           "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
CATEGORY_ALIASES = {
    "result": "Results",
    "academic procedure": "Academic Procedures",
}
CANONICAL_COLUMNS = ["query", "intent", "language", "course", "semester", "timestamp", "source"]


def _column_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _find_column(columns, candidates: tuple[str, ...]) -> str | None:
    by_normalized = {_column_name(column): str(column) for column in columns}
    for candidate in candidates:
        if _column_name(candidate) in by_normalized:
            return by_normalized[_column_name(candidate)]
    return None


def _read_xlsx_fallback(stream: BinaryIO) -> pd.DataFrame:
    """Read simple text-based workbook sheets without an Excel engine."""
    stream.seek(0)
    with zipfile.ZipFile(stream) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(text.text or "" for text in item.findall(".//m:t", XLSX_NS))
                      for item in strings.findall("m:si", XLSX_NS)]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        sheet = next((item for item in workbook.findall(".//m:sheet", XLSX_NS)
                      if item.attrib.get("name") == "Responses"), None)
        if sheet is None:
            sheet = workbook.find(".//m:sheet", XLSX_NS)
        if sheet is None:
            raise ValueError("Workbook has no readable worksheet.")
        target = rel_map[sheet.attrib[f"{{{XLSX_NS['r']}}}id"]].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        root = ET.fromstring(archive.read(target))
        rows: list[dict[str, str]] = []
        for row in root.findall(".//m:sheetData/m:row", XLSX_NS):
            values: dict[str, str] = {}
            for cell in row.findall("m:c", XLSX_NS):
                column = re.match(r"[A-Z]+", cell.attrib["r"]).group(0)
                value = cell.find("m:v", XLSX_NS)
                text = value.text if value is not None else "".join(
                    part.text or "" for part in cell.findall(".//m:t", XLSX_NS))
                if cell.attrib.get("t") == "s" and text:
                    text = shared[int(text)]
                values[column] = text
            rows.append(values)
    if not rows:
        return pd.DataFrame()
    headers = rows[0]
    return pd.DataFrame([{headers.get(column, ""): value for column, value in row.items()}
                         for row in rows[1:]])


def read_dataset(upload, filename: str) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    upload.seek(0)
    if suffix == ".csv":
        try:
            return pd.read_csv(upload)
        except UnicodeDecodeError:
            upload.seek(0)
            return pd.read_csv(upload, encoding="latin-1")
    if suffix in {".xlsx", ".xlsm"}:
        try:
            upload.seek(0)
            return pd.read_excel(upload, sheet_name="Responses")
        except (ImportError, ValueError, KeyError):
            upload.seek(0)
            return _read_xlsx_fallback(upload)
    raise ValueError("Choose a CSV or Excel .xlsx file.")


def standardize_dataset(raw: pd.DataFrame, categories: list[str] | None = None) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)
    query_column = _find_column(raw.columns, ("query", "text", "question", "Q4_Academic_Question"))
    intent_column = _find_column(raw.columns, ("intent", "label", "category", "Q3_Category"))
    if not query_column or not intent_column:
        raise ValueError("Could not find query and intent columns. Use `query,intent` or the provided survey workbook columns.")

    def mapped_frame(text_col: str, label_col: str) -> pd.DataFrame:
        return pd.DataFrame({
            "query": raw[text_col], "intent": raw[label_col],
            "language": raw[_find_column(raw.columns, ("language", "lang"))] if _find_column(raw.columns, ("language", "lang")) else "",
            "course": raw[_find_column(raw.columns, ("course", "field_course", "Q2_Field_Course"))] if _find_column(raw.columns, ("course", "field_course", "Q2_Field_Course")) else "",
            "semester": raw[_find_column(raw.columns, ("semester", "term"))] if _find_column(raw.columns, ("semester", "term")) else "",
            "timestamp": raw[_find_column(raw.columns, ("timestamp", "created_at", "date"))] if _find_column(raw.columns, ("timestamp", "created_at", "date")) else "",
            "source": raw[_find_column(raw.columns, ("source", "provenance"))] if _find_column(raw.columns, ("source", "provenance")) else "Imported",
        })

    frames = [mapped_frame(query_column, intent_column)]
    secondary_query = _find_column(raw.columns, ("Q8_Additional_Question", "additional_question"))
    secondary_intent = _find_column(raw.columns, ("Q8_Category", "additional_category"))
    if secondary_query and secondary_intent:
        frames.append(mapped_frame(secondary_query, secondary_intent))
    standardized = pd.concat(frames, ignore_index=True)
    for column in CANONICAL_COLUMNS:
        standardized[column] = standardized[column].fillna("").astype(str).str.strip()
    standardized["query"] = standardized["query"].str.replace(r"\s+", " ", regex=True)
    standardized["intent"] = standardized["intent"].str.replace(r"\s+", " ", regex=True)
    standardized["source"] = standardized["source"].replace("", "Imported")
    canonical_names = categories or [
        item["name"] for item in json.loads(
            (PROJECT_ROOT / "data" / "intent_categories.json").read_text(encoding="utf-8"))]
    canonical_by_key = {name.casefold(): name for name in canonical_names}
    standardized["intent"] = standardized["intent"].map(
        lambda label: CATEGORY_ALIASES.get(label.casefold(), canonical_by_key.get(label.casefold(), label)))
    return standardized[CANONICAL_COLUMNS]


def clean_dataset(standardized: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    total = len(standardized)
    missing_query = int(standardized["query"].eq("").sum())
    missing_intent = int(standardized["intent"].eq("").sum())
    valid = standardized[(standardized["query"] != "") & (standardized["intent"] != "")].copy()
    normalized_queries = valid["query"].str.casefold().str.replace(r"\s+", " ", regex=True).str.strip()
    valid["_query_key"] = normalized_queries
    conflict_keys = valid.groupby("_query_key")["intent"].nunique()
    conflict_keys = set(conflict_keys[conflict_keys > 1].index)
    conflict_rows = int(valid["_query_key"].isin(conflict_keys).sum())
    valid = valid[~valid["_query_key"].isin(conflict_keys)].copy()
    before_duplicates = len(valid)
    valid = valid.drop_duplicates(subset=["_query_key", "intent"], keep="first")
    duplicates_removed = before_duplicates - len(valid)
    valid = valid.drop(columns=["_query_key"]).reset_index(drop=True)
    report = {
        "rows_before_cleaning": total,
        "missing_query_rows": missing_query,
        "missing_intent_rows": missing_intent,
        "conflicting_label_rows_excluded": conflict_rows,
        "duplicate_rows_removed": duplicates_removed,
        "rows_after_cleaning": len(valid),
        "classes": int(valid["intent"].nunique()),
    }
    return valid, report


def encode_and_split(data: pd.DataFrame, test_size: float = 0.2, random_seed: int = 42) -> tuple[pd.DataFrame, dict]:
    if data.empty:
        raise ValueError("There are no clean labeled rows to encode.")
    labels = data["intent"].astype(str)
    encoder = LabelEncoder()
    label_ids = encoder.fit_transform(labels)
    class_counts = labels.value_counts()
    stratify = labels if class_counts.min() >= 2 and int(len(data) * test_size) >= len(class_counts) else None
    indices = list(range(len(data)))
    train_ids, test_ids = train_test_split(indices, test_size=test_size, random_state=random_seed,
                                            stratify=stratify)
    encoded = data.copy()
    encoded["label_id"] = label_ids
    encoded["split"] = "train"
    encoded.loc[test_ids, "split"] = "test"
    info = {
        "label_mapping": {str(name): int(index) for index, name in enumerate(encoder.classes_)},
        "train_rows": len(train_ids),
        "test_rows": len(test_ids),
        "stratified": stratify is not None,
        "random_seed": random_seed,
        "test_fraction": test_size,
    }
    return encoded, info


def load_default_dataset() -> pd.DataFrame:
    path = PROJECT_ROOT / "data" / "raw" / "student_query_dataset.xlsx"
    if not path.exists():
        return pd.DataFrame()
    with path.open("rb") as stream:
        return read_dataset(stream, path.name)
