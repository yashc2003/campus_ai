from __future__ import annotations

from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from database.datasets import (add_intent_category, get_intent_categories,
                              list_dataset_imports, load_category_defaults,
                              save_dataset_import, update_intent_category)
from database.mongodb import get_connection_status, get_database
from nlp.preprocessing import (clean_dataset, encode_and_split, load_default_dataset,
                               read_dataset, standardize_dataset)
from utils.ui import load_theme
from utils.auth import require_admin

load_theme()
if not require_admin():
    st.stop()
st.markdown('<div class="eyebrow">PHASE 2 · DATA QUALITY & INTENT CONFIGURATION</div>', unsafe_allow_html=True)
st.title("Dataset & Intents")
st.caption("Prepare labeled questions for later model training. This workspace cleans and splits data; model training and measured evaluation are separate workflows.")

connected, connection_message = get_connection_status()
database = None
if connected:
    try:
        database = get_database()
    except Exception as exc:
        connection_message = f"MongoDB data access failed: {exc.__class__.__name__}"
        connected = False

if connected and database is not None:
    try:
        categories = get_intent_categories(database)
    except Exception as exc:
        connected = False
        connection_message = f"MongoDB category access failed: {exc.__class__.__name__}"
        categories = [{**item, "active": True} for item in load_category_defaults()]
        st.warning(f"MongoDB is not available for edits ({connection_message}). The bundled categories are shown read-only.")
else:
    categories = [{**item, "active": True} for item in load_category_defaults()]
    st.info(f"MongoDB is offline ({connection_message}). You can preview and clean datasets; category edits and saved imports require MongoDB.")

active_categories = [item["name"] for item in categories if item.get("active", True)]
tabs = st.tabs(["Dataset workspace", "Intent categories", "Import history"])

with tabs[0]:
    st.markdown("#### Import a labeled dataset")
    uploaded = st.file_uploader("Upload CSV or Excel workbook", type=["csv", "xlsx", "xlsm"],
                                help="Required columns: query and intent. The provided survey workbook is also supported.")
    file_name = "student_query_dataset.xlsx"
    if uploaded is not None:
        file_name = uploaded.name
        try:
            raw = read_dataset(BytesIO(uploaded.getvalue()), uploaded.name)
        except Exception as exc:
            st.error(f"Could not read the uploaded dataset: {exc}")
            raw = pd.DataFrame()
    else:
        raw = load_default_dataset()
        if not raw.empty:
            st.caption("Loaded the supplied student survey workbook from `data/raw/`.")

    if raw.empty:
        st.warning("No dataset is available yet. Upload a CSV or Excel file with query and intent columns.")
    else:
        try:
            standardized = standardize_dataset(raw, active_categories)
            cleaned, cleaning = clean_dataset(standardized)
            test_fraction = st.slider("Holdout fraction for a reproducible data split", 0.1, 0.4, 0.2, 0.05)
            seed = st.number_input("Random seed", min_value=0, max_value=999999, value=42, step=1)
            encoded, split = encode_and_split(cleaned, float(test_fraction), int(seed))
            unknown = sorted(set(cleaned["intent"]) - set(active_categories))

            if any(str(value).lower() == "synthetic" for value in cleaned["source"].unique()):
                st.warning("This workbook marks its responses as synthetic. Its rows are useful for demonstrating preparation, not for claiming real-student model performance.")

            stat_cols = st.columns(5)
            for column, label, value in zip(stat_cols,
                    ["IMPORTED EXAMPLES", "MISSING QUERY", "MISSING INTENT", "DUPLICATES REMOVED", "CLEAN EXAMPLES"],
                    [cleaning["rows_before_cleaning"], cleaning["missing_query_rows"],
                     cleaning["missing_intent_rows"], cleaning["duplicate_rows_removed"],
                     cleaning["rows_after_cleaning"]]):
                with column:
                    st.metric(label, f"{value:,}")
            if cleaning["conflicting_label_rows_excluded"]:
                st.warning(f"Excluded {cleaning['conflicting_label_rows_excluded']} rows where the same normalized question had conflicting intent labels.")
            if unknown:
                st.warning("These labels are not active categories yet: " + ", ".join(unknown))
                st.caption("Add or activate matching categories in Intent categories before saving a model-ready batch.")

            left, right = st.columns([1.15, 1], gap="large")
            with left:
                st.markdown("##### Cleaned query preview")
                st.dataframe(encoded.head(30), use_container_width=True, hide_index=True)
            with right:
                st.markdown("##### Class distribution")
                if cleaned.empty:
                    st.info("No labeled examples to chart.")
                else:
                    distribution = cleaned["intent"].value_counts().rename_axis("intent").reset_index(name="examples")
                    chart = px.bar(distribution, x="examples", y="intent", orientation="h",
                                   color="examples", color_continuous_scale=["#536a9a", "#6be2ff"])
                    chart.update_layout(height=max(300, 30 * len(distribution)), margin=dict(l=0,r=5,t=5,b=0),
                                        coloraxis_showscale=False, paper_bgcolor="rgba(0,0,0,0)",
                                        plot_bgcolor="rgba(0,0,0,0)", font_color="#aab7cb")
                    chart.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,.06)")
                    chart.update_yaxes(showgrid=False, autorange="reversed")
                    st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})

            train_rows = int((encoded["split"] == "train").sum())
            test_rows = int((encoded["split"] == "test").sum())
            st.caption(f"Label IDs: {split['label_mapping']} · Split: {train_rows} train / {test_rows} holdout · Stratified: {'yes' if split['stratified'] else 'no'} · Seed: {split['random_seed']}")
            st.download_button("Download cleaned CSV", encoded.to_csv(index=False).encode("utf-8"),
                               file_name="campus_ai_cleaned_dataset.csv", mime="text/csv")
            if st.button("Save prepared dataset to MongoDB", type="primary", disabled=not connected):
                try:
                    batch_id = save_dataset_import(database, file_name, encoded, cleaning, split)
                    st.success(f"Saved {len(encoded):,} examples as import {batch_id}.")
                except Exception as exc:
                    st.error(f"Dataset was not saved: {exc.__class__.__name__}")
        except ValueError as exc:
            st.error(str(exc))

with tabs[1]:
    st.markdown("#### Configurable intent categories")
    st.caption("The initial category list is configuration data. Rename labels carefully: previously imported batches keep their original label values for reproducibility.")
    categories_frame = pd.DataFrame(categories)
    if not categories_frame.empty:
        st.dataframe(categories_frame[[column for column in ("name", "description", "active") if column in categories_frame]],
                     use_container_width=True, hide_index=True)
    with st.form("add-intent-form", clear_on_submit=True):
        new_name = st.text_input("New category name", placeholder="e.g. Transport")
        new_description = st.text_input("Description", placeholder="Questions about campus transport")
        add_category = st.form_submit_button("Add category", disabled=not connected)
    if add_category and database is not None:
        try:
            add_intent_category(database, new_name, new_description)
            st.success(f"Added intent category: {new_name.strip()}")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    if categories:
        selected_name = st.selectbox("Edit category settings", [item["name"] for item in categories])
        selected = next(item for item in categories if item["name"] == selected_name)
        with st.form("edit-intent-form"):
            description = st.text_input("Description", value=selected.get("description", ""))
            active = st.checkbox("Category active for new datasets", value=selected.get("active", True))
            save_category = st.form_submit_button("Save category settings", disabled=not connected)
        if save_category and database is not None:
            try:
                update_intent_category(database, selected_name, description, active)
                st.success("Category settings saved.")
                st.rerun()
            except Exception as exc:
                st.error(f"Category was not updated: {exc.__class__.__name__}")

with tabs[2]:
    st.markdown("#### Saved dataset imports")
    if not connected or database is None:
        st.info("Connect MongoDB to view previously saved imports.")
    else:
        imports = list_dataset_imports(database)
        if imports:
            history = pd.DataFrame([{key: batch.get(key) for key in
                                     ("dataset_id", "filename", "created_at", "rows_before_cleaning",
                                      "rows_after_cleaning", "classes")} for batch in imports])
            st.dataframe(history, use_container_width=True, hide_index=True)
        else:
            st.info("No dataset imports have been saved yet.")
