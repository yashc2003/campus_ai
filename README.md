# CAMPUS AI — Intelligent Student Academic Support System

**Smart Queries → Better Answers → Smarter Campus**

CAMPUS AI is a Streamlit exhibition project for academic questions. It connects local intent classification, confidence fallback, retrieval over uploaded college documents, source citations, staff tickets, calendar events, in-app notices, feedback review, and live MongoDB analytics.

## Problem and objectives

Students often search several channels to find deadlines, policies, and course information. CAMPUS AI gives them one place to ask a question, see the predicted intent and confidence, and retrieve an answer only when an indexed campus document contains relevant text. Questions without reliable evidence can be sent to staff.

The supplied workbook is **synthetic**. It is included to exercise cleaning and model workflows; it is not evidence of real-student accuracy. No app screen invents query counts, document citations, tickets, or model metrics.

## Features

- Student question workflow: intent, confidence band, script-based language hint, source-only retrieval, helpful/unhelpful feedback, suggested category correction, support ticket creation and ticket status lookup.
- Account access: student registration and email/password sign-in backed by salted PBKDF2 password hashes; a separate administrator sign-in uses credentials from `.env`.
- Dataset import: CSV/Excel, survey-column mapping, missing value and duplicate reports, conflicting-label exclusion, configurable categories, class counts, label IDs, seeded train/holdout split, cleaned CSV, and MongoDB import history.
- Model training: PyTorch LSTM and GRU; Hugging Face BERT-family fine-tuning; held-out accuracy, precision, recall, F1, per-intent report, confusion matrix, training time, inference time, and comparison chart.
- Controlled BERT inference: production uses only a locally deployed BERT candidate that passes the evaluation gate; otherwise it uses a local TF-IDF/logistic-regression baseline trained from the available labeled data.
- College knowledge base: PDF/DOCX/TXT parsing, page-aware text chunks, stored local multilingual sentence embeddings when model weights are cached, and deterministic sparse character-vector search otherwise. Retrieved answers quote actual document passages and show file/page/relevance. No match means no answer or citation.
- Multilingual support: English plus Hindi/Marathi script and phrase hints. A locally cached multilingual sentence model improves document retrieval. Whisper can transcribe English, Hindi and Marathi audio when installed. Do not claim language/model accuracy until tested on representative real data.
- Tickets: priority and department suggestions, status, staff assignment, resolution, creation timestamp, and student lookup using the ticket ID. There is intentionally no separate Support Tickets sidebar page; ticket actions live in Ask Campus AI and Admin, following the requested page removal.
- Staff tools: calendar CRUD, notification publish/disable, notice extraction for staff review, approved feedback export, model comparison, and threshold settings.
- Role gates: one successful student or administrator sign-in is shared across all pages for the current app session, including staff tools.

## Architecture

```text
app.py / pages/                 Streamlit navigation and student/admin interfaces
nlp/                            cleaning, language hints, confidence, local inference
training/                       LSTM, GRU, BERT training, evaluation, comparison, deployment gate
rag/                            PDF/DOCX/TXT extraction, chunking, vector encoding and retrieval
database/                        MongoDB connection, indexes and collection operations
analytics/                       metrics and Plotly dashboards
voice/                           optional local Whisper transcription
data/raw/                        supplied synthetic workbook
models/                          local model artifacts and generated measured reports
```

MongoDB collections used: `students`, `queries`, `tickets`, `documents`, `document_chunks`, `embeddings_metadata`, `intents`, `dataset_imports`, `training_examples`, `feedback`, `calendar_events`, `notifications`, and `application_settings`. Indexes are created on first database access. Passwords are never stored in plain text. Student queries and tickets are associated with a generated student ID.

## Requirements and installation

Use Python 3.10 or later. Install MongoDB Community locally or configure MongoDB Atlas. BERT model weights and Whisper checkpoints are downloaded separately and can be large.

```powershell
cd D:\campus_ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `.env` values:

```dotenv
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=campus_ai
CAMPUS_AI_ENV=development
ADMIN_USERNAME=campus-admin
ADMIN_PASSWORD=replace-with-a-strong-secret-of-at-least-12-characters
MIN_DEPLOY_F1=0.70
```

Never commit `.env`. The app does not display credentials. Student pages can open without MongoDB, but persistence, official documents, tickets, calendar, notifications and live analytics need a working database. After a student or administrator signs in, all pages are available for that app session.

## Run the application

```powershell
streamlit run app.py
```

Open **Student / Admin sign in**. Students can create an account or sign in with their email and password; staff use the separate Admin sign-in tab with the `.env` credentials. After student sign-in, open **Ask Campus AI** or **Voice Assistant**. The supplied workbook can train the local baseline on first use. Upload official documents in **Knowledge Base**. PDF and DOCX parsers are listed in the main requirements. Scanned PDFs need OCR; this project refuses to claim text was indexed when extraction returns no text.

### Voice setup (optional)

Install the optional local speech packages (includes a bundled FFmpeg executable):

```powershell
python -m pip install -r requirements-voice.txt
```

Whisper runs locally. Choose Tiny, Base, or Small in Voice Assistant; model weights download once on first use. If the optional package is not installed, the page shows the install command.

### Semantic retrieval (optional)

The default installation uses stored sparse character n-gram vectors and needs no model download. To use the multilingual sentence transformer encoder, install the main requirement `sentence-transformers` (already included) and make `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` available in the local Hugging Face cache, or set `RAG_EMBEDDING_MODEL` to another locally cached sentence-transformers model. The app never downloads weights while a student submits a question. Documents indexed before changing the encoder keep their original vectors and remain searchable.

## Dataset preparation

Admin sign-in → **Dataset & Intents**. Upload a CSV with `query,intent` columns or an Excel workbook. The supplied survey workbook maps its academic question/category and additional question/category columns into the canonical schema. Review the cleaning report and distribution, then download the processed CSV or save an import to MongoDB.

Canonical columns are `query`, `intent`, `language`, `course`, `semester`, `timestamp`, and `source`. The default category file contains the 15 categories from the project brief. The supplied workbook contains 800 survey responses and expands the primary and additional question fields; blank question/category pairs are removed during cleaning.

## Model training and evaluation

All commands use the bundled synthetic workbook by default. Supply a real, consented, labeled CSV for meaningful evaluation. Training outputs are ignored by Git, and metrics are written only after running the scripts.

```powershell
python -m training.train_lstm --dataset data/raw/student_query_dataset.xlsx
python -m training.train_gru --dataset data/raw/student_query_dataset.xlsx
python -m training.train_bert --dataset data/raw/student_query_dataset.xlsx --base-model bert-base-multilingual-cased
python -m training.evaluate_baseline --dataset data/raw/student_query_dataset.xlsx
python -m training.evaluate --model lstm --dataset data/raw/student_query_dataset.xlsx
python -m training.evaluate --model gru --dataset data/raw/student_query_dataset.xlsx
python -m training.evaluate --model bert --dataset data/raw/student_query_dataset.xlsx
python -m training.compare_models
```

`models/model_comparison.png` and each model’s `metrics.json`, `evaluation.json`, and `confusion_matrix.png` come from actual script runs. BERT training needs pretrained weights available locally or network access. For an offline check, add `--local-only`; the script stops clearly if those weights are not cached.

To promote a fine-tuned BERT candidate, set a deployment threshold and run the evaluation first:

```powershell
$env:MIN_DEPLOY_F1 = "0.70"
python -m training.deploy_model --model bert
```

Deployment requires `models/bert_classifier/evaluation.json`, a non-empty held-out test set, and a weighted F1 at or above the threshold. It also refuses a candidate that scores below the current production model. LSTM/GRU reports are for comparison; production inference currently supports BERT or the local TF-IDF baseline.

## RAG and notice review

Admin uploads PDFs, DOCX or text files under the Knowledge Base page. The parser keeps PDF page numbers, chunks the extracted text with overlap, and stores vectors and source metadata in MongoDB. Retrieval uses cosine similarity over vectors. The assistant returns the selected passage itself so its factual wording remains in the source; it does not generate unsupported dates or citations. Notices use a separate extraction page that lists written dates/action statements with source context and requires staff confirmation before calendar publication.

## Feedback and controlled learning

Student corrections enter `feedback` for staff review. Admin must approve the corrected intent before it can be exported as CSV. The app never retrains on live queries. Save the downloaded correction CSV under `data/processed/`, merge it with the base dataset (corrections override an old label for the same normalized query), train a candidate, evaluate it on held-out rows, and use the deployment gate to promote only an eligible BERT candidate.

```powershell
python -m training.merge_training_data --corrections data/processed/staff_approved_training_corrections.csv
python -m training.train_bert --dataset data/processed/approved_training.csv
python -m training.evaluate --model bert --dataset data/processed/approved_training.csv
python -m training.deploy_model --model bert
```

## Five-minute exhibition walkthrough

1. Open the Overview and show live MongoDB values (or the honest offline state).
2. Ask an academic question; show predicted intent, raw classifier confidence and the model backend.
3. Index an official notice and repeat the question to show the retrieved passage, filename, page and relevance score.
4. Ask an unrelated or unsupported question; show the no-source fallback and create a ticket.
5. Submit a Hindi or Marathi question and explain that language identification is a script/phrase hint; do not state unmeasured accuracy.
6. If Whisper is installed, record a brief question on Voice Assistant.
7. Open Admin to update a ticket, review feedback, approve a correction, and export corrections.
8. Upload a notice, review extracted dates, and confirm one as a calendar event/reminder.
9. Show Analytics and Model Performance with actual database/training reports. Synthetic workbook scores must be described as pipeline checks only.

## Checks and troubleshooting

```powershell
python -m compileall -q app.py pages utils database analytics nlp rag training voice
```

- `MONGODB_URI is missing`: copy `.env.example` to `.env`, enter a URI, restart Streamlit.
- MongoDB offline: start the service or check the Atlas IP allowlist and credentials.
- PDF package unavailable: reinstall requirements; scanned PDFs require OCR before text extraction works.
- BERT model unavailable: cache the selected Hugging Face model before training; app inference remains on the local baseline until a candidate is explicitly deployed.
- Whisper unavailable: install `requirements-voice.txt` and FFmpeg, or use text.
- No citation: confirm the source is active and contains extractable text that overlaps the question.
- Charts have no rows: no stored events exist yet. The dashboards do not seed demonstration records.

## Screenshots

Add screenshots of Overview, Ask Campus AI with a real indexed source, Admin, and the Model Performance page after connecting a development database and loading documents. Do not present the bundled synthetic model results as real-world accuracy.
