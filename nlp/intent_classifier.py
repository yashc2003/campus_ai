from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from nlp.preprocessing import clean_dataset, encode_and_split, load_default_dataset, standardize_dataset
from utils.config import PROJECT_ROOT

MODEL_PATH = PROJECT_ROOT / "models" / "intent_baseline.joblib"


def train_baseline(frame: pd.DataFrame | None = None) -> Pipeline:
    source = frame if frame is not None else load_default_dataset()
    clean, _ = clean_dataset(standardize_dataset(source))
    if clean["intent"].nunique() < 2 or len(clean) < 4:
        raise ValueError("Need at least four labeled examples across two intents to train a baseline.")
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", sublinear_tf=True)),
        ("classifier", LogisticRegression(max_iter=1200, class_weight="balanced", random_state=42)),
    ])
    model.fit(clean["query"], clean["intent"])
    return model


def save_model(model: Pipeline, path: Path = MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_model(path: Path = MODEL_PATH) -> Pipeline | None:
    return joblib.load(path) if path.exists() else None


def predict_intent(text: str, model: Pipeline) -> dict:
    probabilities = model.predict_proba([text])[0]
    index = int(probabilities.argmax())
    return {"intent": str(model.classes_[index]), "confidence": float(probabilities[index]),
            "backend": "TF-IDF + Logistic Regression baseline", "model_version": "baseline"}
