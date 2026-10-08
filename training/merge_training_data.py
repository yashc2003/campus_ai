from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from nlp.preprocessing import clean_dataset, read_dataset, standardize_dataset
from utils.config import PROJECT_ROOT

def load(path: Path) -> pd.DataFrame:
    with path.open("rb") as stream:
        return standardize_dataset(read_dataset(stream, path.name))

def merge(base: Path, corrections: Path, output: Path) -> dict:
    base_frame = load(base)
    correction_frame = load(corrections)
    correction_keys = set(correction_frame["query"].str.casefold().str.replace(r"\s+", " ", regex=True).str.strip())
    base_keys = base_frame["query"].str.casefold().str.replace(r"\s+", " ", regex=True).str.strip()
    # A staff correction supersedes the old label for that same normalized query.
    base_frame = base_frame[~base_keys.isin(correction_keys)]
    combined = pd.concat([base_frame, correction_frame], ignore_index=True)
    clean, report = clean_dataset(combined)
    if clean.empty: raise ValueError("No labeled rows remain after cleaning.")
    output.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(output, index=False, encoding="utf-8")
    return {**report, "output": str(output)}

def main():
    parser = argparse.ArgumentParser(description="Merge reviewed feedback with a labeled base dataset.")
    parser.add_argument("--base", type=Path, default=PROJECT_ROOT / "data/raw/student_query_dataset.xlsx")
    parser.add_argument("--corrections", type=Path, required=True, help="Staff-approved corrections CSV exported from Admin.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/processed/approved_training.csv")
    args = parser.parse_args(); print(merge(args.base, args.corrections, args.output))

if __name__ == "__main__": main()
