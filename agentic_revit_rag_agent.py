"""
Agentic Revit Compliance Reviewer - LangChain + RAG

Pipeline:
  1. Input_Analyst_Agent       -> parses Revit model + review request
  2. Code_Retriever_Agent      -> retrieves relevant code clauses via RAG
  3. Compliance_Reviewer_Agent -> evaluates model elements against clauses
  4. Reporter_Agent            -> saves final compliance report

Inputs:
  - revit_model.json           : exported Revit room/element data (JSON)
  - docs/revit_notes.txt       : code notes / regulations corpus

Outputs (./revit_review_output/):
  - compliance_report.md
  - compliance_report.json

Usage:
  python agentic_revit_rag_agent.py

Programmatic:
  from agentic_revit_rag_agent import run_revit_review_pipeline
  await run_revit_review_pipeline(
      revit_file="revit_model.json",
      code_file="docs/revit_notes.txt",
      review_request="Check room area compliance for bedrooms and kitchens."
  )
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from sentence_transformers import SentenceTransformer


OUTPUT_DIR = Path("./revit_review_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FAISS_INDEX = None
INDEX_CHUNKS: List[str] = []
EMBEDDING_MODEL_INSTANCE = None


def _load_env_file(env_path: str = ".env"):
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_env_file()


def _resolve_ollama_model(model: str | None) -> str:
    if model and model.strip():
        return model.strip()
    env_model = os.getenv("OLLAMA_MODEL", "").strip()
    if env_model:
        return env_model
    return "qwen2.5:7b"


def _resolve_embedding_model(model: str | None) -> str:
    """Map user-provided embedding model names to valid SentenceTransformer repos."""
    if model and model.strip():
        normalized = model.strip()
    else:
        normalized = os.getenv("EMBEDDING_MODEL", "").strip()

    if not normalized:
        return "sentence-transformers/all-MiniLM-L6-v2"

    # Common mismatch: Ollama embedding tag passed to SentenceTransformer.
    if normalized in {"nomic-embed-text", "nomic-embed-text:latest"}:
        return "sentence-transformers/all-MiniLM-L6-v2"

    return normalized


def _build_llm(model: str | None, base_url: str) -> ChatOllama:
    return ChatOllama(model=_resolve_ollama_model(model), base_url=base_url, temperature=0)


def _read_text(filepath: str) -> str:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    return path.read_text(encoding="utf-8").strip()


def _read_json(filepath: str) -> Dict[str, Any]:
    raw = _read_text(filepath)
    if not raw:
        raise ValueError(f"Empty JSON file: {filepath}")
    return json.loads(raw)


def _extract_json(text: str) -> Any:
    """Parse JSON output from model responses, with fence cleanup fallback."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1])


def _save_output(filename: str, content: str) -> str:
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    return str(path.resolve())


def init_code_vectorstore(
    code_file: str,
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    base_url: str = "http://localhost:11434",
) -> str:
    global FAISS_INDEX, INDEX_CHUNKS, EMBEDDING_MODEL_INSTANCE
    code_path = Path(code_file)
    if not code_path.exists():
        raise FileNotFoundError(f"Missing code file: {code_file}")

    if code_path.suffix.lower() == ".pdf":
        loader = PyPDFLoader(str(code_path))
        pages = loader.load()
        document_text = "\n".join(page.page_content for page in pages if page.page_content)
    else:
        document_text = code_path.read_text(encoding="utf-8")

    if not document_text.strip():
        raise ValueError(f"No text extracted from code file: {code_file}")

    chunk_size = 500
    chunks = [document_text[i : i + chunk_size] for i in range(0, len(document_text), chunk_size)]
    chunks = [chunk for chunk in chunks if chunk.strip()]
    if not chunks:
        raise ValueError(f"No chunks generated from code file: {code_file}")

    EMBEDDING_MODEL_INSTANCE = SentenceTransformer(_resolve_embedding_model(embedding_model))
    embeddings = EMBEDDING_MODEL_INSTANCE.encode(chunks)
    if len(embeddings) == 0:
        raise ValueError("No embeddings generated from chunks.")

    embedding_array = np.array(embeddings, dtype="float32")
    dimension = embedding_array.shape[1]

    FAISS_INDEX = faiss.IndexFlatL2(dimension)
    FAISS_INDEX.add(embedding_array)
    INDEX_CHUNKS = chunks

    return f"Indexed {len(chunks)} code chunks from {code_file}."


def retrieve_code_context(query: str, k: int = 4) -> List[Dict[str, Any]]:
    global FAISS_INDEX, INDEX_CHUNKS, EMBEDDING_MODEL_INSTANCE
    if FAISS_INDEX is None or EMBEDDING_MODEL_INSTANCE is None or not INDEX_CHUNKS:
        raise RuntimeError("Vector store not initialized.")

    query_embedding = EMBEDDING_MODEL_INSTANCE.encode([query])
    query_array = np.array(query_embedding, dtype="float32")
    distances, indices = FAISS_INDEX.search(query_array, k)

    results: List[Dict[str, Any]] = []
    ranked_indices = indices[0] if len(indices) > 0 else []
    ranked_distances = distances[0] if len(distances) > 0 else []

    for i, idx in enumerate(ranked_indices, start=1):
        if idx < 0 or idx >= len(INDEX_CHUNKS):
            continue
        results.append(
            {
                "rank": i,
                "content": INDEX_CHUNKS[idx],
                "metadata": {
                    "chunk_index": int(idx),
                    "distance": float(ranked_distances[i - 1]),
                },
            }
        )
    return results


def answer_question_with_rules(
    question: str,
    code_file: str,
    top_k: int = 6,
    model: str | None = None,
    base_url: str = "http://localhost:11434",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    embedding_base_url: str | None = None,
) -> Dict[str, Any]:
    """Answer a compliance question and extract normalized rules from retrieved code context."""
    if not question.strip():
        raise ValueError("Question must not be empty.")

    init_message = init_code_vectorstore(
        code_file=code_file,
        embedding_model=embedding_model,
        base_url=embedding_base_url or base_url,
    )
    hits = retrieve_code_context(query=question, k=top_k)

    llm = _build_llm(model=model, base_url=base_url)
    prompt = ChatPromptTemplate.from_template(
        """
You are a building-code QA and rule-extraction assistant.

Question:
{question}

Retrieved code snippets:
{hits}

Tasks:
1) Answer the question using only the retrieved snippets.
2) Extract rules relevant to the question.
3) Normalize each rule to:
   {{"rule": "VARIABLE_NAME", "value": number}}

Rule formatting requirements:
- VARIABLE_NAME must be uppercase with underscores (example: MIN_BEDROOM_AREA).
- value must be numeric.
- If no numeric rule can be extracted, return an empty list.
- Do not invent values.

Return ONLY valid JSON using this shape:
{{
  "answer": "string",
  "rules": [
    {{"rule": "VARIABLE_NAME", "value": 0}}
  ]
}}
"""
    )

    try:
        raw = llm.invoke(
            prompt.format_messages(
                question=question,
                hits=json.dumps(hits, ensure_ascii=True),
            )
        ).content
    except Exception as exc:
        message = str(exc)
        if "not found" in message.lower() and "model" in message.lower():
            selected_model = _resolve_ollama_model(model)
            raise RuntimeError(
                f"Ollama model '{selected_model}' was not found on endpoint '{base_url}'. "
                "Set OLLAMA_MODEL in .env to an available model name or pass model explicitly."
            ) from exc
        raise
    parsed = _extract_json(raw)

    if not isinstance(parsed, dict):
        raise ValueError("Model returned non-object JSON for question answering.")

    rules = parsed.get("rules", [])
    cleaned_rules: List[Dict[str, Any]] = []
    for item in rules:
        if not isinstance(item, dict):
            continue
        rule = item.get("rule")
        value = item.get("value")
        if not isinstance(rule, str):
            continue
        if not isinstance(value, (int, float)):
            continue
        cleaned_rules.append({"rule": rule.strip().upper().replace(" ", "_"), "value": value})

    return {
        "status": "ok",
        "message": init_message,
        "question": question,
        "answer": parsed.get("answer", ""),
        "rules": cleaned_rules,
        "retrieval_hits": hits,
    }


def input_analyst_agent(llm: Any, revit_file: str, review_request: str) -> Dict[str, Any]:
    model_json = _read_json(revit_file)

    prompt = ChatPromptTemplate.from_template(
        """
You are Input_Analyst_Agent for a Revit compliance pipeline.

Task:
1) Parse the Revit model JSON into normalized elements.
2) Extract requested checks from the user review request.
3) Keep unknown fields as null.

Review request:
{review_request}

Revit model JSON:
{model_json}

Return ONLY valid JSON with this schema:
{{
  "project_name": "string or null",
  "requested_checks": ["string"],
  "elements": [
    {{"id": "string or null", "name": "string or null", "category": "string or null", "area": "number or null", "level": "string or null"}}
  ],
  "assumptions": ["string"]
}}
"""
    )

    raw = llm.invoke(
        prompt.format_messages(
            review_request=review_request,
            model_json=json.dumps(model_json, ensure_ascii=True),
        )
    ).content

    return _extract_json(raw)


def code_retriever_agent(
    llm: Any,
    input_analysis: Dict[str, Any],
    code_file: str,
    embedding_model: str,
    embedding_base_url: str,
    top_k: int = 4,
) -> Dict[str, Any]:
    init_code_vectorstore(
        code_file=code_file,
        embedding_model=embedding_model,
        base_url=embedding_base_url,
    )

    checks = input_analysis.get("requested_checks", []) or ["general code compliance"]
    categories = sorted(
        {
            (elem.get("category") or "unknown")
            for elem in input_analysis.get("elements", [])
            if isinstance(elem, dict)
        }
    )

    retrieval_bundle: List[Dict[str, Any]] = []
    for check in checks:
        query = f"{check}; categories: {', '.join(categories[:8])}"
        evidence = retrieve_code_context(query, k=top_k)
        retrieval_bundle.append({"check": check, "evidence": evidence})

    prompt = ChatPromptTemplate.from_template(
        """
You are Code_Retriever_Agent.

Input retrieval payload:
{retrieval_bundle}

Task:
1) Consolidate duplicated evidence.
2) Keep evidence text exactly as retrieved.
3) Add short retrieval notes.

Return ONLY valid JSON:
{{
  "retrieved_clauses": [
    {{
      "check": "string",
      "evidence": [
        {{"rank": 1, "content": "string", "metadata": {{}}}}
      ]
    }}
  ],
  "retrieval_notes": ["string"]
}}
"""
    )

    raw = llm.invoke(
        prompt.format_messages(
            retrieval_bundle=json.dumps(retrieval_bundle, ensure_ascii=True),
        )
    ).content

    return _extract_json(raw)


def compliance_reviewer_agent(
    llm: Any,
    input_analysis: Dict[str, Any],
    retrieval_output: Dict[str, Any],
) -> Dict[str, Any]:
    prompt = ChatPromptTemplate.from_template(
        """
You are Compliance_Reviewer_Agent.

Task:
Evaluate each relevant element against retrieved clauses.

Rules:
- Output pass, fail, or needs-manual-review.
- If code evidence is ambiguous, choose needs-manual-review.
- Use cited evidence snippets directly from retrieval output.

Input analysis:
{input_analysis}

Retrieved clauses:
{retrieval_output}

Return ONLY valid JSON:
{{
  "summary": {{
    "total_elements": 0,
    "pass_count": 0,
    "fail_count": 0,
    "manual_review_count": 0
  }},
  "findings": [
    {{
      "element_id": "string",
      "element_name": "string",
      "check": "string",
      "status": "pass|fail|needs-manual-review",
      "reason": "string",
      "evidence": ["string"]
    }}
  ],
  "global_notes": ["string"]
}}
"""
    )

    raw = llm.invoke(
        prompt.format_messages(
            input_analysis=json.dumps(input_analysis, ensure_ascii=True),
            retrieval_output=json.dumps(retrieval_output, ensure_ascii=True),
        )
    ).content

    return _extract_json(raw)


def _build_markdown_report(report_json: Dict[str, Any]) -> str:
    summary = report_json.get("summary", {})
    findings = report_json.get("findings", [])
    notes = report_json.get("global_notes", [])

    lines: List[str] = []
    lines.append("# Revit Compliance Review Report")
    lines.append("")
    lines.append("## Quick Stats")
    lines.append(f"- Total elements: {summary.get('total_elements', 0)}")
    lines.append(f"- Pass: {summary.get('pass_count', 0)}")
    lines.append(f"- Fail: {summary.get('fail_count', 0)}")
    lines.append(f"- Needs manual review: {summary.get('manual_review_count', 0)}")
    lines.append("")

    lines.append("## Findings")
    lines.append("| Element | Check | Status | Reason |")
    lines.append("|---|---|---|---|")
    for item in findings:
        element = item.get("element_name") or item.get("element_id") or "unknown"
        check = item.get("check", "unknown")
        status = item.get("status", "needs-manual-review")
        reason = (item.get("reason", "") or "").replace("|", "/")
        lines.append(f"| {element} | {check} | {status} | {reason} |")
    lines.append("")

    lines.append("## Evidence")
    for idx, item in enumerate(findings, start=1):
        lines.append(f"### Finding {idx}")
        lines.append(f"- Element: {item.get('element_name') or item.get('element_id')}")
        lines.append(f"- Check: {item.get('check')}")
        lines.append(f"- Status: {item.get('status')}")
        for ev in item.get("evidence", []):
            lines.append(f"- Evidence: {ev}")
        lines.append("")

    lines.append("## Limitations And Manual Review Notes")
    if notes:
        for note in notes:
            lines.append(f"- {note}")
    else:
        lines.append("- No additional notes.")

    return "\n".join(lines).strip() + "\n"


def reporter_agent(
    input_analysis: Dict[str, Any],
    retrieval_output: Dict[str, Any],
    review_output: Dict[str, Any],
) -> Dict[str, str]:
    combined = {
        "pipeline_version": "1.0-langchain",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_analysis": input_analysis,
        "retrieval_output": retrieval_output,
        "review_output": review_output,
        "summary": review_output.get("summary", {}),
        "findings": review_output.get("findings", []),
        "global_notes": review_output.get("global_notes", []),
    }

    json_path = _save_output("compliance_report.json", json.dumps(combined, indent=2, ensure_ascii=True))
    md_path = _save_output("compliance_report.md", _build_markdown_report(review_output))

    return {"json_report": json_path, "markdown_report": md_path}


async def run_revit_review_pipeline(
    revit_file: str = "revit_model.json",
    code_file: str = "docs/revit_notes.txt",
    review_request: str = "Review Revit model for code compliance with focus on room areas.",
    model: str | None = None,
    base_url: str = "http://localhost:11434",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    embedding_base_url: str = "http://localhost:11434",
) -> Dict[str, Any]:
    """Run a LangChain-only multi-stage RAG compliance workflow."""

    if not Path(revit_file).exists():
        raise FileNotFoundError(f"Missing input file: {revit_file}")
    if not Path(code_file).exists():
        raise FileNotFoundError(f"Missing input file: {code_file}")

    llm = _build_llm(model=model, base_url=base_url)

    print("=" * 72)
    print("Agentic Revit Compliance Reviewer - LangChain")
    print("=" * 72)
    print(f"Revit file : {revit_file}")
    print(f"Code file  : {code_file}")
    print(f"Output dir : {OUTPUT_DIR.resolve()}")

    input_analysis = input_analyst_agent(llm, revit_file, review_request)
    retrieval_output = code_retriever_agent(
        llm,
        input_analysis,
        code_file,
        embedding_model=embedding_model,
        embedding_base_url=embedding_base_url,
    )
    review_output = compliance_reviewer_agent(llm, input_analysis, retrieval_output)
    paths = reporter_agent(input_analysis, retrieval_output, review_output)

    print("=" * 72)
    print("Pipeline finished.")
    print(f"JSON report: {paths['json_report']}")
    print(f"MD report  : {paths['markdown_report']}")
    print("=" * 72)

    return {
        "output_directory": str(OUTPUT_DIR.resolve()),
        "json_report": paths["json_report"],
        "markdown_report": paths["markdown_report"],
    }


if __name__ == "__main__":
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(
        run_revit_review_pipeline(
            revit_file="revit_model.json",
            code_file="docs/revit_notes.txt",
            review_request="Check room and space compliance against code requirements.",
        )
    )
