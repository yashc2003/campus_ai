from __future__ import annotations

from pathlib import Path

from utils.config import PROJECT_ROOT


def predict(text: str) -> dict:
    """Prefer a locally fine-tuned BERT; fall back to a trainable local baseline."""
    bert_dir = PROJECT_ROOT / "models" / "production"
    if (bert_dir / "config.json").exists():
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(bert_dir, local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(bert_dir, local_files_only=True)
            with torch.no_grad():
                logits = model(**tokenizer(text, return_tensors="pt", truncation=True, max_length=128)).logits[0]
                scores = torch.softmax(logits, dim=0)
            index = int(scores.argmax())
            return {"intent": model.config.id2label[index], "confidence": float(scores[index]),
                    "backend": "Fine-tuned local BERT", "model_version": "bert_classifier"}
        except Exception as exc:
            raise RuntimeError(f"The local BERT model could not be loaded: {exc.__class__.__name__}") from exc
    from nlp.intent_classifier import MODEL_PATH, load_model, predict_intent, save_model, train_baseline
    model = load_model()
    if model is None:
        model = train_baseline()
        save_model(model)
    return predict_intent(text, model)
