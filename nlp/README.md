# NLP pipeline

`preprocessing.py` reads CSV/Excel, maps query/category fields, cleans missing and duplicate rows, excludes conflicting labels, and creates reproducible label IDs and splits. `language_detection.py` detects English vs Devanagari and uses phrase hints to distinguish common Marathi/Hindi wording; ambiguous Devanagari remains uncertain. `intent_classifier.py` supplies the lightweight local TF-IDF/logistic baseline. `inference.py` prefers an explicitly deployed local BERT model and otherwise uses the baseline. Confidence values are model probabilities, not accuracy.
