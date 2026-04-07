# RevitLLMBackend

This project is a small FastAPI and LangChain-based Revit compliance assistant. It uses Ollama for both chat and embedding models, FAISS for vector search, and a simple RAG pipeline to answer code-compliance questions from building-code documents.

## What each part does

- `agentic_revit_rag_agent.py` is the main pipeline. It reads the Revit JSON, chunks the code document, builds a FAISS index with Ollama embeddings, retrieves the most relevant code chunks, asks the Ollama chat model to reason over them, and writes `revit_review_output/compliance_report.json` and `revit_review_output/compliance_report.md`.
- `main.py` exposes the pipeline through FastAPI endpoints for manual testing or integration.
- `build_index.py` is a standalone script that builds a FAISS index from files in `data/` and saves the index to `vector.index` and the chunks to `chunks.pkl`.
- `vectorstore/faiss_store.py` is a reusable FAISS wrapper built on `langchain_ollama.OllamaEmbeddings`.
- `loaders/pdf_loader.py` loads PDF documents and splits them into chunks.
- `test_agent_retrieval.py` runs the full Ollama-based pipeline as a smoke test.
- `test_rag.py` is a smaller FAISS similarity-search demo.

## Environment

Required local Ollama models:

- Chat model: `qwen2.5:7b` or another installed chat model
- Embedding model: `nomic-embed-text-v2-moe:latest`

Required environment variables are usually loaded from `.env`:

- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_MODEL=qwen2.5:7b`
- `OLLAMA_EMBEDDING_MODEL=nomic-embed-text-v2-moe:latest`

If you want to override the defaults for a single run, pass them in the request payload or set them in `.env`.

## Install

From the project root:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Make sure Ollama is running locally before you test:

```powershell
ollama serve
```

In a second terminal, verify the models are available:

```powershell
ollama list
```

## Run the project

Run the full pipeline directly:

```powershell
python agentic_revit_rag_agent.py
```

Run the FastAPI app:

```powershell
uvicorn main:app --reload
```

Useful API endpoints:

- `POST /agent/check-compliance`
- `POST /agent/test-retrieval`
- `POST /agent/ask-rules`

## How to test it

### 1) Smoke test the Ollama retrieval pipeline

```powershell
python test_agent_retrieval.py
```

This script does three things:

- builds the vector store from the code document
- runs a retrieval query like `minimum bedroom area`
- runs the full agent pipeline and writes the reports

### 2) Test the FAISS + embedding wrapper

```powershell
python test_rag.py
```

This loads a PDF, chunks it, creates a FAISS vector store with Ollama embeddings, and prints the top similarity matches.

### 3) Test the API

Start the API with `uvicorn`, then send a request to `/agent/test-retrieval` or `/agent/check-compliance` using Swagger UI at `/docs` or a tool like `curl` or Postman.

## Common flow

1. A code document such as `data/2015_International_Building_Code-238-323.pdf` is loaded.
2. The text is split into 500-character chunks.
3. Ollama embeddings are generated for each chunk using `nomic-embed-text-v2-moe:latest`.
4. FAISS stores the chunk vectors.
5. A user query is embedded with the same model and compared to the stored vectors.
6. The retrieved snippets are passed to the Ollama chat model for answer generation and report creation.

## Troubleshooting

- If you get `model not found`, run `ollama list` and update `OLLAMA_MODEL` or `OLLAMA_EMBEDDING_MODEL` in `.env`.
- If retrieval fails, rebuild the index with `python build_index.py` or rerun `test_agent_retrieval.py`.
- If Ollama cannot be reached, confirm `OLLAMA_BASE_URL` matches the running server.
- If a file path fails, check that the document path in the request exists in the workspace.
