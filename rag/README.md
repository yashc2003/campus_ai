# Document retrieval

The Knowledge Base admin workflow extracts PDF pages, DOCX paragraphs/tables, or plain text; splits extracted text into overlapping chunks; stores the source metadata, extracted text and normalized vectors in MongoDB; and retrieves passages by cosine similarity.

When a locally cached multilingual Sentence Transformers model is available, new chunks use its sentence embeddings. Otherwise the app stores deterministic sparse character n-gram vectors, which support English and Devanagari text without downloading weights. Each chunk records its encoder so retrieval can use the matching query encoder.

The answer function is extractive: it returns a retrieved source passage only when the relevance threshold is met. It does not synthesize or fabricate deadlines. PDF page citations are available; DOCX/TXT source sections do not have page numbers. Scanned image PDFs require OCR, which is not bundled.
