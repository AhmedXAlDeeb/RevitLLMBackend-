# RevitLLMBackend

RevitLLMBackend is a FastAPI + LangChain project for Revit code-compliance review.

It uses:
- Ollama chat model for reasoning and report generation
- Ollama embedding model for semantic retrieval
- FAISS for vector search over building-code text
- A multi-stage agent pipeline for analysis, retrieval, compliance decisions, and reporting

## 1. Current Project Structure

```text
RevitLLMBackend-/
	src/
		revit_backend/
			api/
				main.py
			pipeline/
				agentic_revit_rag_agent.py
			loaders/
				pdf_loader.py
			vectorstore/
				faiss_store.py
	scripts/
		build_index.py
		test_agent_retrieval.py
		test_rag.py
	data/
	docs/
	revit_review_output/
	revit_model_test.json
	requirements.txt
	.env.example
```

## 2. What Each File Does

- `src/revit_backend/api/main.py`
	- FastAPI service entrypoint
	- Exposes endpoints for compliance check, retrieval testing, and QA/rule extraction

- `src/revit_backend/pipeline/agentic_revit_rag_agent.py`
	- Core pipeline and business logic
	- Handles document chunking, embedding, FAISS indexing/retrieval, LLM prompting, and report generation

- `src/revit_backend/loaders/pdf_loader.py`
	- PDF loading and text chunk splitting utility

- `src/revit_backend/vectorstore/faiss_store.py`
	- Reusable FAISS vectorstore wrapper using Ollama embeddings

- `scripts/build_index.py`
	- Standalone script to generate and save FAISS index artifacts from `data/`

- `scripts/test_rag.py`
	- Basic retrieval smoke test (PDF load -> chunk -> embed -> similarity search)

- `scripts/test_agent_retrieval.py`
	- End-to-end smoke test for retrieval, QA/rule extraction, and full pipeline execution

## 3. Prerequisites

1. Python 3.10+ (recommended)
2. Ollama installed and running
3. Local Ollama models available

Expected models:
- Chat model: `qwen2.5:7b` (or another compatible chat model)
- Embedding model: `nomic-embed-text-v2-moe:latest`

## 4. Environment Configuration

Create `.env` from `.env.example` and set values:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text-v2-moe:latest
```

Notes:
- `OLLAMA_MODEL` controls chat/reasoning model.
- `OLLAMA_EMBEDDING_MODEL` controls retrieval embedding model.
- Both can be overridden from API payloads if needed.

## 5. Installation

From repo root:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Start Ollama service:

```powershell
ollama serve
```

Verify models:

```powershell
ollama list
```

## 6. Running the Application

### A) Run API Server

```powershell
uvicorn src.revit_backend.api.main:app --reload
```

Then open:
- Swagger docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Available endpoints:
- `POST /check-compliance`
- `POST /agent/check-compliance`
- `POST /agent/test-retrieval`
- `POST /agent/ask-rules`
- `POST /agent/extract-rules`
- `POST /rules/engine-check`
- `POST /agent/full-check`
- `POST /integration/revit/check`
- `GET /health`

### B) Run Pipeline Directly (without API)

```powershell
python -m src.revit_backend.pipeline.agentic_revit_rag_agent
```

Expected output files:
- `revit_review_output/compliance_report.json`
- `revit_review_output/compliance_report.md`

## 7. How the Pipeline Works

High-level sequence:

1. Read Revit model JSON and user review request.
2. Load code document (`.pdf` or `.txt`).
3. Split code text into 500-char chunks.
4. Generate chunk embeddings via Ollama embedding model.
5. Build FAISS index in memory.
6. Embed query and retrieve top-k relevant chunks.
7. Ask chat model to answer and extract numeric rules.
8. Evaluate compliance and generate structured report outputs.

Main stages in code:
- Input_Analyst_Agent
- Code_Retriever_Agent
- Compliance_Reviewer_Agent
- Reporter_Agent

## 8. Testing Guide

### Test 1: Basic Retrieval Smoke Test

```powershell
python scripts/test_rag.py
```

What it checks:
- PDF loading works
- chunking works
- embedding calls to Ollama work
- FAISS similarity search returns results

Expected console pattern:
- `Loaded <N> chunks`
- Printed top search matches

### Test 2: End-to-End Pipeline Smoke Test

```powershell
python scripts/test_agent_retrieval.py
```

What it checks:
- Vectorstore initialization
- retrieval results
- QA and rule extraction
- full compliance pipeline run
- report files are generated

### Test 3: API Endpoint Tests (Swagger)

1. Start API server.
2. Open `/docs`.
3. Run these endpoints in order:
	 - `POST /agent/test-retrieval`
	 - `POST /agent/ask-rules`
	 - `POST /agent/check-compliance`

Sample body for `POST /agent/test-retrieval`:

```json
{
	"query": "minimum bedroom area",
	"code_file": "data/2015_International_Building_Code-238-323.pdf",
	"top_k": 4,
	"embedding_model": "nomic-embed-text-v2-moe:latest",
	"embedding_base_url": "http://localhost:11434"
}
```

Sample body for `POST /agent/check-compliance`:

```json
{
	"revit_file": "revit_model_test.json",
	"code_file": "data/2015_International_Building_Code-238-323.pdf",
	"review_request": "Check room area compliance against the provided code.",
	"model": "qwen2.5:7b",
	"base_url": "http://localhost:11434",
	"embedding_model": "nomic-embed-text-v2-moe:latest",
	"embedding_base_url": "http://localhost:11434"
}
```

## 9. Building Saved Index Artifacts

Run:

```powershell
python scripts/build_index.py
```

This writes:
- `vector.index`
- `chunks.pkl`

Use this when you want persistent index files built from everything in `data/`.

## 10. Typical Workflow

1. Ensure Ollama is running and models are present.
2. Run `python scripts/test_rag.py` for quick retrieval sanity check.
3. Run `python scripts/test_agent_retrieval.py` for end-to-end validation.
4. Start API server and test via Swagger.
5. Review generated reports in `revit_review_output/`.

## 11. Phase Completion Mapping

This backend now covers the requested project phases:

- Phase 1 (backend foundation):
	- `POST /check-compliance` (hardcoded min-area baseline)
- Phase 4 (RAG):
	- `POST /agent/test-retrieval`
- Phase 5 (LLM rule extraction):
	- `POST /agent/extract-rules`
- Phase 6 (deterministic rule engine):
	- `POST /rules/engine-check`
- Phase 7 (full integration orchestration):
	- `POST /integration/revit/check` (alias of full flow)

Phases 2, 3, 8, and 9 are implemented on the Revit add-in side, with backend contracts provided for that integration.

## 12. Revit Add-in Integration (How It Should Appear)

Integration target in Revit UI:

- Add-in button: `Run AI Compliance Check`
- On click:
	1. collect rooms/spaces from active model
	2. call `POST /integration/revit/check`
	3. color failed elements red and passed elements green
	4. show findings panel/table with reasons
	5. click finding -> select/zoom element

Backend integration contract is documented in:
- `docs/revit_addin_integration.md`

### Minimal request expected from add-in

```json
{
	"elements": [
		{"id": "101", "name": "Bedroom 1", "category": "room", "area": 8.5, "height": 2.7}
	],
	"question": "What is the minimum bedroom area requirement?",
	"code_file": "data/2015_International_Building_Code-238-323.pdf"
}
```

### Critical response fields for visualization

- `engine.visualization.failed_ids`
- `engine.visualization.passed_ids`
- `engine.findings`
- `engine.summary`

## 13. Troubleshooting

### Error: model not found

Cause:
- wrong model name in `.env` or request payload

Fix:
1. `ollama list`
2. set `OLLAMA_MODEL` and `OLLAMA_EMBEDDING_MODEL` to installed names

### Error: Ollama connection refused / timeout

Cause:
- Ollama server is not running or wrong base URL

Fix:
1. start `ollama serve`
2. verify `OLLAMA_BASE_URL`

### Retrieval returns poor results

Cause:
- wrong or noisy source document
- insufficient query specificity

Fix:
1. verify `code_file` path
2. use a more specific query
3. retest with `scripts/test_rag.py`

### File not found errors

Cause:
- incorrect relative path

Fix:
1. run commands from repository root
2. verify input files exist in `data/`, `docs/`, or root

## 14. Notes

- The pipeline currently uses in-memory FAISS for runtime retrieval in the agent flow.
- The standalone index builder creates on-disk artifacts for offline/prebuilt indexing use cases.
