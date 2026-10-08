from __future__ import annotations

import argparse
import json
import time
import inspect
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.preprocessing import LabelEncoder

from nlp.preprocessing import clean_dataset, read_dataset, standardize_dataset
from utils.config import PROJECT_ROOT


def train(dataset: Path, base_model: str, epochs: int, seed: int, local_only: bool) -> Path:
    import torch
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              Trainer, TrainingArguments)
    from torch.utils.data import Dataset
    torch.manual_seed(seed); np.random.seed(seed)
    torch.set_num_threads(min(4, torch.get_num_threads()))
    with dataset.open("rb") as source:
        raw = read_dataset(source, dataset.name)
    frame, report = clean_dataset(standardize_dataset(raw))
    if len(frame) < 10 or frame.intent.nunique() < 2:
        raise ValueError("At least 10 clean rows across two intents are required for fine-tuning.")
    # Deterministic 70/10/20 train/validation/test partition.
    order = np.random.default_rng(seed).permutation(len(frame))
    train_cut = max(1, int(len(frame) * .7)); validation_cut = max(train_cut + 1, int(len(frame) * .8))
    train_frame = frame.iloc[order[:train_cut]]
    validation_frame = frame.iloc[order[train_cut:validation_cut]]
    test_frame = frame.iloc[order[validation_cut:]]
    if test_frame.empty:
        raise ValueError("Dataset is too small for a held-out test set.")
    labels = LabelEncoder().fit(frame.intent)
    tokenizer = AutoTokenizer.from_pretrained(base_model, local_files_only=local_only)
    model = AutoModelForSequenceClassification.from_pretrained(base_model,
        num_labels=len(labels.classes_), id2label=dict(enumerate(labels.classes_)),
        label2id={name: int(i) for i, name in enumerate(labels.classes_)}, local_files_only=local_only)
    class QueryDataset(Dataset):
        def __init__(self, subset):
            self.tokens = tokenizer(subset["query"].tolist(), truncation=True, padding="max_length", max_length=64)
            self.labels = labels.transform(subset.intent).tolist()
        def __len__(self): return len(self.labels)
        def __getitem__(self, index):
            return {**{key: torch.tensor(value[index]) for key, value in self.tokens.items()},
                    "labels": torch.tensor(self.labels[index])}
    output = PROJECT_ROOT / "models" / "bert_classifier"
    started = time.perf_counter()
    run_dir = PROJECT_ROOT / "models" / "bert_tmp" / f"run_{seed}_{time.time_ns()}"
    args = TrainingArguments(output_dir=str(run_dir),
        num_train_epochs=epochs, learning_rate=2e-5, per_device_train_batch_size=16,
        per_device_eval_batch_size=32, weight_decay=.01, seed=seed, report_to=[],
        eval_strategy="epoch", save_strategy="epoch", save_total_limit=1,
        load_best_model_at_end=True, metric_for_best_model="eval_loss",
        greater_is_better=False, logging_strategy="no", disable_tqdm=True,
        dataloader_pin_memory=False)
    trainer_args = {"model": model, "args": args, "train_dataset": QueryDataset(train_frame),
                    "eval_dataset": QueryDataset(validation_frame)}
    tokenizer_parameter = "processing_class" if "processing_class" in inspect.signature(Trainer.__init__).parameters else "tokenizer"
    trainer_args[tokenizer_parameter] = tokenizer
    trainer = Trainer(**trainer_args)
    trainer.train()
    training_seconds = time.perf_counter() - started
    inference_started = time.perf_counter()
    result = trainer.predict(QueryDataset(test_frame))
    inference_seconds_per_query = (time.perf_counter() - inference_started) / max(1, len(test_frame))
    predicted = result.predictions.argmax(axis=1)
    truth = labels.transform(test_frame.intent)
    precision, recall, f1, _ = precision_recall_fscore_support(truth, predicted, average="weighted", zero_division=0)
    output.mkdir(parents=True, exist_ok=True); model.save_pretrained(output); tokenizer.save_pretrained(output)
    metrics = {"model": "BERT", "base_model": base_model, "accuracy": float(accuracy_score(truth, predicted)),
        "precision": float(precision), "recall": float(recall), "f1": float(f1),
        "training_seconds": training_seconds, "inference_seconds_per_query": inference_seconds_per_query,
        "validation_rows": len(validation_frame), "test_rows": len(test_frame), "dataset_rows": len(frame),
        "classes": labels.classes_.tolist(), "dataset_cleaning": report, "seed": seed,
        "warning": "Source workbook is synthetic; scores are a pipeline check, not real-student performance."}
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return output / "metrics.json"


def main():
    parser = argparse.ArgumentParser(description="Fine-tune and evaluate a Hugging Face BERT-family classifier.")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "data/raw/student_query_dataset.xlsx")
    parser.add_argument("--base-model", default="bert-base-multilingual-cased")
    parser.add_argument("--epochs", type=int, default=3); parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--local-only", action="store_true", help="Use only model files already cached locally.")
    args = parser.parse_args()
    print(train(args.dataset, args.base_model, args.epochs, args.seed, args.local_only))


if __name__ == "__main__": main()
