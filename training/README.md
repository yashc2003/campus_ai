# Training and deployment

`evaluate_baseline.py` measures the TF-IDF/logistic-regression baseline. `train_lstm.py` and `train_gru.py` train recurrent intent classifiers on a cleaned 70/10/20 train/validation/test partition. `train_bert.py` fine-tunes a Hugging Face model and records a held-out report. `evaluate.py` writes per-intent precision/recall/F1 and a confusion matrix. `compare_models.py` creates `models/model_comparison.png` from model metrics that actually exist.

The BERT trainer downloads nothing in `--local-only` mode; the selected model must already be in the Hugging Face cache. Model outputs and measured metrics are local artifacts and excluded from source control. The supplied workbook is synthetic and is unsuitable for real-world accuracy claims.

Only BERT is currently eligible for the production loader. `deploy_model.py` requires a BERT candidate and its held-out evaluation report, enforces `MIN_DEPLOY_F1`, and refuses a score below an existing production BERT model. LSTM/GRU are comparison models, not production inference backends.
