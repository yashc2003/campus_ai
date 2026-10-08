from __future__ import annotations

import json
import pandas as pd
import plotly.express as px
import streamlit as st
from utils.config import PROJECT_ROOT
from utils.ui import load_theme

load_theme(); st.markdown('<div class="eyebrow">MEASURED MODEL EVALUATION</div>', unsafe_allow_html=True)
st.title("Model Performance")
st.caption("Only metrics written by training/evaluation scripts are shown. Bundled workbook scores are not real-student performance claims.")
rows = []
for model_name, folder in [("TF-IDF baseline", "baseline"), ("LSTM", "lstm"), ("GRU", "gru"), ("BERT", "bert_classifier")]:
    path = PROJECT_ROOT / "models" / folder / "metrics.json"
    if path.exists():
        try: rows.append(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, OSError): pass
if rows:
    frame = pd.DataFrame([{key: row.get(key) for key in ("model", "accuracy", "precision", "recall", "f1", "training_seconds", "inference_seconds_per_query", "test_rows", "dataset_rows")} for row in rows])
    st.dataframe(frame, use_container_width=True, hide_index=True)
    plot = frame.melt(id_vars="model", value_vars=["accuracy", "precision", "recall", "f1"], var_name="metric", value_name="score")
    st.plotly_chart(px.bar(plot, x="model", y="score", color="metric", barmode="group", range_y=[0, 1]), use_container_width=True)
    for row in rows:
        st.caption(f"{row.get('model')}: {row.get('warning', 'Metrics calculated from held-out rows.')}")
        folder = "bert_classifier" if row.get("model") == "BERT" else str(row.get("model", "")).lower()
        matrix = PROJECT_ROOT / "models" / folder / "confusion_matrix.png"
        if matrix.exists():
            with st.expander(f"{row.get('model')} confusion matrix"): st.image(str(matrix))
        evaluation = PROJECT_ROOT / "models" / folder / "evaluation.json"
        if evaluation.exists():
            details = json.loads(evaluation.read_text(encoding="utf-8"))
            per_intent = pd.DataFrame(details.get("classification_report", {})).T
            if not per_intent.empty:
                with st.expander(f"{row.get('model')} per-intent metrics"): st.dataframe(per_intent, use_container_width=True)
else:
    st.info("No model metrics exist yet. Train models with the commands below; no example scores are displayed.")
st.markdown("#### Reproducible training commands")
st.code("python -m training.evaluate_baseline --dataset data/raw/student_query_dataset.xlsx\npython -m training.train_lstm --dataset data/raw/student_query_dataset.xlsx\npython -m training.train_gru --dataset data/raw/student_query_dataset.xlsx\npython -m training.train_bert --dataset data/raw/student_query_dataset.xlsx\npython -m training.evaluate --model bert", language="powershell")
