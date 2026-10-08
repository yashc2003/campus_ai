from __future__ import annotations
import json
import time
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from nlp.intent_classifier import train_baseline
from nlp.preprocessing import clean_dataset, read_dataset, standardize_dataset
from utils.config import PROJECT_ROOT

def evaluate(dataset: Path, seed: int = 42) -> Path:
    with dataset.open("rb") as source: raw = read_dataset(source, dataset.name)
    frame, cleaning = clean_dataset(standardize_dataset(raw))
    indices = np.arange(len(frame)); counts = frame.intent.value_counts()
    stratify = frame.intent if counts.min() >= 3 and int(len(frame)*.2) >= len(counts) else None
    train_ids, test_ids = train_test_split(indices, test_size=.2, random_state=seed, stratify=stratify)
    train, test = frame.iloc[train_ids], frame.iloc[test_ids]
    started = time.perf_counter(); model = train_baseline(train); training_seconds = time.perf_counter()-started
    started = time.perf_counter(); predictions = model.predict(test["query"]); inference_seconds = (time.perf_counter()-started)/max(1,len(test))
    precision, recall, f1, _ = precision_recall_fscore_support(test.intent, predictions, average="weighted", zero_division=0)
    labels = list(model.classes_); matrix = confusion_matrix(test.intent, predictions, labels=labels)
    report = classification_report(test.intent, predictions, labels=labels, output_dict=True, zero_division=0)
    output = PROJECT_ROOT / "models" / "baseline"; output.mkdir(parents=True, exist_ok=True)
    payload = {"model": "TF-IDF + Logistic Regression", "accuracy": float(accuracy_score(test.intent,predictions)),
        "precision": float(precision), "recall": float(recall), "f1": float(f1),
        "training_seconds": training_seconds, "inference_seconds_per_query": inference_seconds,
        "test_rows": len(test), "dataset_rows": len(frame), "seed": seed, "test_split_stratified": stratify is not None,
        "dataset_cleaning": cleaning,
        "warning": "The source workbook is synthetic and highly templated; this random held-out score is not real-student generalization."}
    (output/"metrics.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    (output/"evaluation.json").write_text(json.dumps({"model":"baseline","test_rows":len(test),"labels":labels,
        "confusion_matrix":matrix.tolist(),"classification_report":report},indent=2),encoding="utf-8")
    fig,ax=plt.subplots(figsize=(max(7,len(labels)*.65),max(5,len(labels)*.55)))
    ax.imshow(matrix,cmap="Blues"); ax.set_xticks(range(len(labels)),labels,rotation=70,ha="right")
    ax.set_yticks(range(len(labels)),labels); ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    fig.tight_layout(); fig.savefig(output/"confusion_matrix.png",dpi=160); plt.close(fig)
    return output/"metrics.json"

if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("--dataset",type=Path,default=PROJECT_ROOT/"data/raw/student_query_dataset.xlsx")
    parser.add_argument("--seed",type=int,default=42); args=parser.parse_args(); print(evaluate(args.dataset,args.seed))
