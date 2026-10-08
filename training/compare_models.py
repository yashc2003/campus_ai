from __future__ import annotations
import json
import pandas as pd
import matplotlib.pyplot as plt
from utils.config import PROJECT_ROOT

def main():
    rows = []
    for name, folder in [("Baseline", "baseline"), ("LSTM", "lstm"), ("GRU", "gru"), ("BERT", "bert_classifier")]:
        path = PROJECT_ROOT / "models" / folder / "metrics.json"
        if path.exists(): rows.append(json.loads(path.read_text(encoding="utf-8")))
    if not rows: raise SystemExit("No evaluated model metrics found; train and evaluate models first.")
    frame = pd.DataFrame(rows)
    metrics = [column for column in ("accuracy", "precision", "recall", "f1") if column in frame]
    ax = frame.set_index("model")[metrics].plot(kind="bar", ylim=(0, 1), figsize=(9, 5), rot=0)
    ax.set_ylabel("Held-out score"); ax.set_title("Measured model comparison"); ax.grid(axis="y", alpha=.2)
    ax.figure.tight_layout(); ax.figure.savefig(PROJECT_ROOT / "models" / "model_comparison.png", dpi=180)
    print(PROJECT_ROOT / "models" / "model_comparison.png")

if __name__ == "__main__": main()
