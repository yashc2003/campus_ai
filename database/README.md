# MongoDB schema

Connection credentials come from `.env` through `utils/config.py`. Indexes are created when a connection is first requested. The project uses queries, tickets, documents, document_chunks, embeddings_metadata, intents, dataset_imports, training_examples, feedback, calendar_events, notifications, and application_settings.

No demonstration records are seeded. Intent category defaults are configuration and are written on first request to the category collection. Query content is retained for campus analytics and staff-reviewed learning; optional student names are collected only when creating a ticket.
