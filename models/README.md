# Model artifacts

LSTM, GRU and BERT weights, measured metrics, reports and the generated `model_comparison.png` are written here. Weights are kept local and ignored by Git. Use the training commands in the root README to reproduce them.

The BERT inference loader uses `models/production/` only after an administrator runs the quality-gated deployment command. Otherwise it loads the local TF-IDF baseline, trained from the configured labeled dataset. The included workbook is synthetic.
