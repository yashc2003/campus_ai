# CAMPUS AI — Complete Project Documentation

**Smart Queries → Better Answers → Smarter Campus**

This document describes the CAMPUS AI exhibition project: its goals, pages, data and models, architecture, setup, operation, limitations, and GitHub project credits.

## 1. Project overview

CAMPUS AI is a Streamlit academic support application. Students can ask questions about college processes, receive a predicted topic and confidence score, search indexed college documents, and create a support ticket when an answer is uncertain or missing. Staff features include dataset management, notice review, calendar and notification management, feedback review, analytics, and model evaluation.

Answers are grounded in retrieved passages from indexed documents. If the system cannot find a relevant passage, it reports that it cannot verify an answer instead of inventing a policy, date, or citation.

## 2. Project objectives

- Provide one interface for common academic questions.
- Classify questions into academic intents and report confidence.
- Retrieve evidence from official college documents and display its source.
- Offer staff follow-up for unresolved or low-confidence questions.
- Prepare labeled data and compare traditional and neural intent models.
- Support English, Hindi, and Marathi script/phrase hints and optional local speech transcription.
- Maintain campus dates, notices, and operational analytics in MongoDB.

## 3. Application pages

| Page | Purpose |
| --- | --- |
| Overview | Project introduction and live MongoDB dashboard metrics. |
| System Status | MongoDB, account configuration, model availability, and setup status. |
| Student / Admin sign in | Student registration, student sign-in, and separate Admin sign-in. |
| Dataset & Intents | Import, clean, inspect, and manage question datasets and intent categories. |
| AI Assistant | Text-based intent prediction, evidence retrieval, feedback, and ticket creation/status lookup. |
| Knowledge Base | Upload and index PDF, DOCX, and text sources; inspect retrieved passages. |
| Voice Assistant | Record or upload audio, transcribe locally with Whisper, and run the query workflow. |
| Academic Calendar | View campus dates and manage calendar events. |
| Notifications | View campus notices and publish or disable notifications. |
| Analytics | Live query, intent, language, confidence, and ticket metrics. |
| Model Performance | Compare measured model results and reports. |
| Notice Summarizer | Extract written dates and action statements for staff review. |
| Admin | Manage tickets, review feedback, and export approved corrections. |
| Settings | Manage assistant confidence thresholds and inspect deployment settings. |

There is no separate Support Tickets sidebar page. Ticket creation and status lookup are in AI Assistant; staff ticket management is in Admin.

## 4. Sign-in and access

- Students register with a name, email, optional student ID, and password of at least 10 characters. Passwords are stored as salted PBKDF2 hashes, never as plain text.
- Admin sign-in uses `ADMIN_USERNAME` and an `ADMIN_PASSWORD` of at least 12 characters from the local `.env` file.
- After a successful student or Admin sign-in, the app keeps the account role in the Streamlit session and opens all pages for that session, including staff tools. Sign out from the Account page.
- Because the exhibition requirement is full-page access after one sign-in, student accounts can also use staff editing tools. Do not deploy this access policy to a public production service without adding role-specific authorization.
- Student queries and tickets are associated with a generated student ID. Admin credentials are not stored in MongoDB.

## 5. Technology and architecture

| Component | Technology / responsibility |
| --- | --- |
| User interface | Python, Streamlit, Plotly, custom CSS. |
| Database | MongoDB and PyMongo for accounts, queries, tickets, sources, events, notifications, feedback, and settings. |
| Baseline intent model | Scikit-learn TF-IDF features and Logistic Regression. |
| Neural intent models | PyTorch LSTM and GRU; Hugging Face Transformers BERT fine-tuning. |
| Document retrieval | PDF/DOCX/TXT extraction, chunking, and retrieval from MongoDB. Uses cached multilingual sentence embeddings when available, otherwise deterministic sparse character n-gram vectors. |
| Voice | Optional local OpenAI Whisper package; imageio-ffmpeg provides a bundled FFmpeg runtime. |
| Configuration | `.env` for local configuration; `.env.example` documents the expected keys. |

Important source folders:

- `app.py`, `pages/` — navigation and user-facing pages.
- `database/` — MongoDB connection, indexes, and collection operations.
- `nlp/` — preprocessing, language hints, confidence, and intent inference.
- `training/` — training, evaluation, comparison, and deployment checks.
- `rag/` — document parsing, embeddings, retrieval, and source-backed answers.
- `voice/` — local audio transcription.
- `analytics/` — MongoDB-backed metrics.
- `data/raw/` — supplied workbook; `models/` — model reports and chart.

MongoDB collections include `students`, `queries`, `tickets`, `documents`, `document_chunks`, `embeddings_metadata`, `intents`, `dataset_imports`, `training_examples`, `feedback`, `calendar_events`, `notifications`, and `application_settings`.

## 6. Dataset and preparation

The supplied file is `data/raw/student_query_dataset.xlsx`. It contains 800 survey responses and is explicitly **synthetic**. The preparation flow expands question/category pairs from the workbook, standardizes them into canonical columns, removes missing pairs and duplicates, excludes conflicting labels, and encodes intents for training.

Measured cleaning summary:

- 1,600 candidate question/intent rows after expansion.
- 554 rows dropped for missing query or intent fields.
- 0 conflicting-label rows excluded and 0 exact duplicates removed.
- 1,046 cleaned examples across 10 intent classes.
- LSTM, GRU, and BERT use seeded, stratified train/validation/test splits; the held-out test set contains 210 rows.

Canonical dataset fields are `query`, `intent`, `language`, `course`, `semester`, `timestamp`, and `source`.

## 7. Model results and interpretation

These are recorded runs on the supplied synthetic workbook. The workbook is highly templated, so the scores check that the training and evaluation pipelines work; they do **not** establish performance on real student questions.

| Model | Accuracy | Weighted F1 | Training time | Inference time/query | Test rows |
| --- | ---: | ---: | ---: | ---: | ---: |
| TF-IDF + Logistic Regression | 1.000 | 1.000 | 0.19 s | 0.000038 s | 210 |
| LSTM | 1.000 | 1.000 | 8.74 s | 0.000258 s | 210 |
| GRU | 0.995 | 0.995 | 60.10 s | 0.000364 s | 210 |
| BERT (`bert-base-uncased`) | 0.443 | 0.375 | 700.46 s | 0.1042 s | 210 |

The deployment gate requires weighted F1 of at least 0.70 and also checks against the currently deployed model. The trained BERT candidate scored about 0.375 F1 and did not pass the gate. The app therefore uses the TF-IDF baseline unless an eligible BERT model is explicitly deployed. LSTM and GRU are comparison models, not production inference backends.

## 8. Question and retrieval workflow

1. A signed-in user submits typed or transcribed audio.
2. The local classifier predicts an intent, confidence, and backend.
3. The app detects a language/script hint and searches active indexed document chunks.
4. If relevant evidence is found, the app returns the source passage with its filename, page when available, and relevance score.
5. Without a sufficiently relevant source, the app displays a no-source response and may offer staff follow-up.
6. Queries, feedback, and tickets are saved to MongoDB when it is available. Live queries never trigger automatic model retraining.

The notice review tool extracts dates and action statements for staff confirmation; it does not publish guessed deadlines.

## 9. Requirements and local setup

Use Python 3.10 or later. MongoDB Community can run locally, or use a MongoDB Atlas connection URI.

```powershell
cd D:\campus_ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` in the project root. For a local MongoDB service, use:

```dotenv
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=campus_ai
CAMPUS_AI_ENV=development
ADMIN_USERNAME=campus-admin
ADMIN_PASSWORD=<set a private password of at least 12 characters>
MIN_DEPLOY_F1=0.70
```

Keep `.env` private; it is ignored by Git. Never replace it with a real credential in `.env.example`.

Start the application:

```powershell
streamlit run app.py
```

Register or sign in from **Student / Admin sign in**. MongoDB is required for persistent accounts and saved application data. If the service is stopped, the application can still show local model availability but database-backed actions will not persist.

### Optional voice setup

```powershell
python -m pip install -r requirements-voice.txt
```

Choose Tiny, Base, or Small on Voice Assistant. Whisper downloads the selected model weights once on first use; audio transcription is local.

### Optional semantic embeddings

The default retrieval fallback uses sparse vectors and does not need a model download. For multilingual sentence embeddings, make the configured sentence-transformers model available in the local Hugging Face cache. The app does not download embedding weights during a student question.

## 10. Model training and deployment commands

The commands below use the supplied workbook by default; use a real, consented, representative labeled dataset for meaningful evaluation.

```powershell
python -m training.evaluate_baseline --dataset data/raw/student_query_dataset.xlsx
python -m training.train_lstm --dataset data/raw/student_query_dataset.xlsx
python -m training.train_gru --dataset data/raw/student_query_dataset.xlsx
python -m training.train_bert --dataset data/raw/student_query_dataset.xlsx --base-model bert-base-multilingual-cased
python -m training.evaluate --model lstm --dataset data/raw/student_query_dataset.xlsx
python -m training.evaluate --model gru --dataset data/raw/student_query_dataset.xlsx
python -m training.evaluate --model bert --dataset data/raw/student_query_dataset.xlsx
python -m training.compare_models
```

Deploy an eligible BERT candidate only after evaluation:

```powershell
$env:MIN_DEPLOY_F1 = "0.70"
python -m training.deploy_model --model bert
```

Deployment requires a held-out report, a non-empty test set, the configured F1 threshold, and a score at least as strong as the existing production BERT model.

## 11. GitHub repository and project credit

Repository: [github.com/yashc2003/campus_ai](https://github.com/yashc2003/campus_ai)

The project was pushed to branch `main`. The project commit credits **yashc2003** as the primary author and includes co-author attribution for:

- [atharvsalokhe30](https://github.com/atharvsalokhe30)
- [Vedlehgaonkar](https://github.com/Vedlehgaonkar)
- [AshleshaPatil24](https://github.com/AshleshaPatil24)
- [Raushan8554](https://github.com/Raushan8554)

The supplied workbook and source code are included. `.env`, local model weights, runtime data, and generated training metric files are excluded by `.gitignore`.

## 12. Known limitations

- The workbook is synthetic and highly templated; its metrics are not real-world quality claims.
- The current BERT candidate did not pass the deployment gate; production inference falls back to TF-IDF + Logistic Regression.
- Verified answers depend on the quality and coverage of official indexed documents. No evidence means no claimed verified answer.
- Voice model checkpoints may require a first-use download and additional disk space.
- MongoDB must be available for persistent accounts, queries, source indexes, tickets, events, notifications, and analytics.
- The current exhibition access policy gives all signed-in accounts access to staff pages. Add role-specific authorization before deploying this app for real students or staff.
