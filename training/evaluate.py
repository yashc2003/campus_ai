from __future__ import annotations

import argparse
import json
from pathlib import Path
import argparse

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from nlp.preprocessing import clean_dataset, read_dataset, standardize_dataset
from training.train_rnn import RecurrentClassifier, tokenize
from utils.config import PROJECT_ROOT


def evaluate(model_name: str, dataset: Path) -> Path:
    import torch
    from sklearn.preprocessing import LabelEncoder
    frame, _ = clean_dataset(standardize_dataset(read_dataset(dataset.open("rb"), dataset.name)))
    order = np.arange(len(frame))
    if model_name in {"lstm", "gru"}:
        can_stratify = frame.intent.value_counts().min() >= 3 and int(len(frame) * .2) >= frame.intent.nunique()
        _, test_ids = train_test_split(order, test_size=.2, random_state=42,
            stratify=frame.intent if can_stratify else None)
        test = frame.iloc[test_ids]
    else:
        order = np.random.default_rng(42).permutation(len(frame))
        test = frame.iloc[order[max(1, int(len(frame)*.8)):]]
    path = PROJECT_ROOT / "models" / ("bert_classifier" if model_name == "bert" else model_name)
    if model_name in {"lstm", "gru"}:
        state = torch.load(path / "model.pt", map_location="cpu", weights_only=False)
        model = RecurrentClassifier(len(state["vocab"]), len(state["labels"]), model_name, state["hidden"])
        model.load_state_dict(state["state_dict"]); model.eval()
        max_len = state["max_length"]; vocab = state["vocab"]
        data = [[vocab.get(word, 1) for word in tokenize(text)[:max_len]] for text in test["query"]]
        x = torch.tensor([row + [0] * (max_len-len(row)) for row in data])
        with torch.no_grad(): predicted = model(x).argmax(1).numpy()
        names = state["labels"]
    else:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True)
        inputs = tokenizer(test["query"].tolist(), truncation=True, padding=True, max_length=128, return_tensors="pt")
        with torch.no_grad(): predicted = model(**inputs).logits.argmax(1).numpy()
        names = [model.config.id2label[i] for i in range(model.config.num_labels)]
    encoder = LabelEncoder().fit(frame.intent)
    truth = encoder.transform(test.intent)
    report = classification_report(truth, predicted, labels=range(len(names)), target_names=names,
                                   output_dict=True, zero_division=0)
    matrix = confusion_matrix(truth, predicted, labels=range(len(names)))
    output = path / "evaluation.json"; output.write_text(json.dumps({"model": model_name,
        "test_rows": len(test), "classification_report": report,
        "confusion_matrix": matrix.tolist(), "labels": names}, indent=2), encoding="utf-8")
    fig, ax = plt.subplots(figsize=(max(7, len(names)*.65), max(5, len(names)*.55)))
    ax.imshow(matrix, cmap="Blues"); ax.set_xticks(range(len(names)), names, rotation=70, ha="right")
    ax.set_yticks(range(len(names)), names); ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    fig.tight_layout(); fig.savefig(path / "confusion_matrix.png", dpi=160); plt.close(fig)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["lstm", "gru", "bert"], required=True)
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "data/raw/student_query_dataset.xlsx")
    args = parser.parse_args()
    print(evaluate(args.model, args.dataset))


if __name__ == "__main__":
    main()
