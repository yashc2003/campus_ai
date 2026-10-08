from __future__ import annotations
import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from utils.config import PROJECT_ROOT


def deploy(model: str) -> Path:
    if model != "bert":
        raise ValueError("Only a fine-tuned BERT artifact is supported by the production inference loader.")
    candidate = PROJECT_ROOT / "models" / "bert_classifier"
    metrics_path = candidate / "metrics.json"
    evaluation_path = candidate / "evaluation.json"
    if not (candidate / "config.json").exists() or not metrics_path.exists() or not evaluation_path.exists():
        raise ValueError("Train the BERT candidate and run training.evaluate before deployment.")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    if int(evaluation.get("test_rows", 0)) < 1:
        raise ValueError("Evaluation report has no held-out test rows.")
    score = float(evaluation.get("classification_report", {}).get("weighted avg", {}).get("f1-score", -1))
    if score < 0:
        raise ValueError("The evaluation report has no weighted F1 score.")
    minimum = float(os.getenv("MIN_DEPLOY_F1", ".70"))
    if score < minimum:
        raise ValueError(f"Candidate weighted F1 {score:.3f} is below configured gate {minimum:.3f}.")
    production = PROJECT_ROOT / "models" / "production"
    old_metrics = production / "metrics.json"
    if old_metrics.exists():
        previous = json.loads(old_metrics.read_text(encoding="utf-8"))
        if score < float(previous.get("f1", 0)):
            raise ValueError("Candidate scores below the current production model; deployment stopped.")
    stage = PROJECT_ROOT / "models" / ("production_staging_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"))
    shutil.copytree(candidate, stage, ignore=shutil.ignore_patterns("evaluation.json", "confusion_matrix.png"))
    metrics["f1"] = score
    metrics["deployed_at"] = datetime.now(timezone.utc).isoformat()
    (stage / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    backup = None
    if production.exists():
        backup = PROJECT_ROOT / "models" / ("production_previous_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"))
        production.replace(backup)
    try:
        stage.replace(production)
    except Exception:
        if backup and backup.exists() and not production.exists(): backup.replace(production)
        raise
    return production


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--model", choices=["bert"], required=True)
    args = parser.parse_args(); print(deploy(args.model))
