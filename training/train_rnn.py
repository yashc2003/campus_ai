from __future__ import annotations

import argparse
import json
import random
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from nlp.preprocessing import clean_dataset, encode_and_split, read_dataset, standardize_dataset
from utils.config import PROJECT_ROOT


class RecurrentClassifier(nn.Module):
    def __init__(self, vocab_size: int, classes: int, cell: str, hidden: int = 96):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, 96, padding_idx=0)
        recurrent = nn.LSTM if cell == "lstm" else nn.GRU
        self.encoder = recurrent(96, hidden, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(.25)
        self.head = nn.Linear(hidden * 2, classes)

    def forward(self, tokens):
        embedded = self.embedding(tokens)
        _, state = self.encoder(embedded)
        hidden = state[0] if isinstance(state, tuple) else state
        pooled = torch.cat((hidden[-2], hidden[-1]), dim=1)
        return self.head(self.dropout(pooled))


def tokenize(text: str) -> list[str]:
    return re.findall(r"[\w]+|[^\w\s]", text.casefold(), flags=re.UNICODE)


def train(cell: str, dataset: Path, epochs: int = 16, seed: int = 42) -> Path:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    with dataset.open("rb") as source:
        raw = read_dataset(source, dataset.name)
    frame, report = clean_dataset(standardize_dataset(raw))
    if len(frame) < 8 or frame.intent.nunique() < 2:
        raise ValueError("At least 8 clean rows across at least 2 labels are required for recurrent training.")
    indices = np.arange(len(frame))
    classes = frame.intent.value_counts()
    can_stratify = classes.min() >= 3 and int(len(frame) * .2) >= len(classes)
    train_ids, test_ids = train_test_split(indices, test_size=.2, random_state=seed,
                                           stratify=frame.intent if can_stratify else None)
    train_labels = frame.iloc[train_ids].intent
    validation_stratify = train_labels if train_labels.value_counts().min() >= 2 else None
    train_ids, val_ids = train_test_split(train_ids, test_size=.125, random_state=seed,
        stratify=validation_stratify)
    training = frame.iloc[train_ids].copy()
    validation = frame.iloc[val_ids].copy()
    testing = frame.iloc[test_ids].copy()
    if training.intent.nunique() < 2:
        raise ValueError("The dataset needs more examples per intent for a recurrent model.")
    labels = LabelEncoder().fit(frame.intent)
    vocab = {"<pad>": 0, "<unk>": 1}
    for query in training["query"]:
        for word in tokenize(query):
            if word not in vocab:
                vocab[word] = len(vocab)
    max_length = 64
    def encode(series):
        return torch.tensor([[vocab.get(word, 1) for word in tokenize(text)[:max_length]]
                             + [0] * max(0, max_length - len(tokenize(text)[:max_length])) for text in series], dtype=torch.long)
    x_train, x_val, x_test = encode(training["query"]), encode(validation["query"]), encode(testing["query"])
    y_train = torch.tensor(labels.transform(training.intent), dtype=torch.long)
    y_val = torch.tensor(labels.transform(validation.intent), dtype=torch.long)
    y_test = torch.tensor(labels.transform(testing.intent), dtype=torch.long)
    loader = DataLoader(TensorDataset(x_train, y_train), batch_size=16, shuffle=True)
    model = RecurrentClassifier(len(vocab), len(labels.classes_), cell)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.002)
    criterion = nn.CrossEntropyLoss()
    started = time.perf_counter()
    best_state = None; best_validation_loss = float("inf"); patience_left = 3; epochs_trained = 0
    for _ in range(epochs):
        model.train()
        for batch_x, batch_y in loader:
            optimizer.zero_grad(); loss = criterion(model(batch_x), batch_y); loss.backward(); optimizer.step()
        model.eval()
        with torch.no_grad(): validation_loss = float(criterion(model(x_val), y_val))
        epochs_trained += 1
        if validation_loss < best_validation_loss:
            best_validation_loss = validation_loss
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
            patience_left = 3
        else:
            patience_left -= 1
            if patience_left == 0: break
    training_seconds = time.perf_counter() - started
    if best_state is not None: model.load_state_dict(best_state)
    model.eval()
    inference_started = time.perf_counter()
    with torch.no_grad():
        predictions = model(x_test).argmax(1).numpy()
    inference_seconds_per_query = (time.perf_counter() - inference_started) / max(1, len(testing))
    truth = y_test.numpy()
    precision, recall, f1, _ = precision_recall_fscore_support(truth, predictions, average="weighted", zero_division=0)
    output = PROJECT_ROOT / "models" / cell
    output.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "vocab": vocab, "labels": labels.classes_.tolist(),
                "max_length": max_length, "hidden": 96, "cell": cell}, output / "model.pt")
    metrics = {"model": cell.upper(), "accuracy": float(accuracy_score(truth, predictions)),
        "precision": float(precision), "recall": float(recall), "f1": float(f1),
        "training_seconds": training_seconds, "inference_seconds_per_query": inference_seconds_per_query,
        "epochs_trained": epochs_trained, "best_validation_loss": best_validation_loss,
        "validation_rows": len(validation),
        "test_rows": len(testing), "test_split_stratified": can_stratify,
        "dataset_rows": len(frame), "dataset_cleaning": report, "seed": seed,
        "warning": "Small synthetic source dataset; validation scores are not evidence of real-student performance."}
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return output / "metrics.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["lstm", "gru"], required=True)
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "data/raw/student_query_dataset.xlsx")
    parser.add_argument("--epochs", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(train(args.model, args.dataset, args.epochs, args.seed))


if __name__ == "__main__": main()
