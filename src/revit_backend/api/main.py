from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List
from pathlib import Path
import sys

try:
    from ..pipeline.agentic_revit_rag_agent import (
        answer_question_with_rules,
        extract_structured_rules,
        init_code_vectorstore,
        retrieve_code_context,
        run_revit_review_pipeline,
    )
    from ..pipeline.rule_engine import evaluate_rules_for_elements
except ImportError:
    # Support direct execution: `python src/revit_backend/api/main.py`.
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.revit_backend.pipeline.agentic_revit_rag_agent import (
        answer_question_with_rules,
        extract_structured_rules,
        init_code_vectorstore,
        retrieve_code_context,
        run_revit_review_pipeline,
    )
    from src.revit_backend.pipeline.rule_engine import evaluate_rules_for_elements


app = FastAPI()

MIN_AREA = 14

# Define Room model
class Room(BaseModel):
    id: int
    name: str
    area: float


class RoomElement(BaseModel):
    id: str | int
    name: str | None = None
    category: str | None = "room"
    level: str | None = None
    area: float | None = None
    height: float | None = None
    width: float | None = None


class ComplianceRule(BaseModel):
    element: str = "room"
    property: str
    operator: str
    value: float
    unit: str = "unknown"
    source_excerpt: str | None = None


class AgentReviewRequest(BaseModel):
    revit_file: str = "revit_model_test.json"
    code_file: str = "data/2015_International_Building_Code-238-323.pdf"
    review_request: str = "Check room area compliance against the provided code."
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text-v2-moe:latest"
    embedding_base_url: str = "http://localhost:11434"


class RetrievalTestRequest(BaseModel):
    query: str = "minimum bedroom area"
    code_file: str = "data/2015_International_Building_Code-238-323.pdf"
    top_k: int = 4
    embedding_model: str = "nomic-embed-text-v2-moe:latest"
    embedding_base_url: str = "http://localhost:11434"


class QuestionRulesRequest(BaseModel):
    question: str
    code_file: str = "data/2015_International_Building_Code-238-323.pdf"
    top_k: int = 6
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text-v2-moe:latest"
    embedding_base_url: str = "http://localhost:11434"


class StructuredRuleExtractionRequest(BaseModel):
    question: str
    code_file: str = "data/2015_International_Building_Code-238-323.pdf"
    top_k: int = 6
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text-v2-moe:latest"
    embedding_base_url: str = "http://localhost:11434"


class RuleEngineCheckRequest(BaseModel):
    elements: List[RoomElement]
    rules: List[ComplianceRule]


class FullComplianceRequest(BaseModel):
    elements: List[RoomElement]
    question: str = "Check room area compliance against the provided code."
    code_file: str = "data/2015_International_Building_Code-238-323.pdf"
    top_k: int = 6
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text-v2-moe:latest"
    embedding_base_url: str = "http://localhost:11434"

def check_room(room):
    if room.area < MIN_AREA:
        return {
            "id": room.id,
            "status": "fail",
            "message": "Area is below minimum"
        }
    return {
        "id": room.id,
        "status": "pass"
    }

@app.post("/check-compliance")
def check_compliance(rooms: List[Room]):
    return [check_room(room) for room in rooms]


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "revit-backend"}


@app.post("/agent/check-compliance")
async def agent_check_compliance(payload: AgentReviewRequest):
    try:
        result = await run_revit_review_pipeline(
            revit_file=payload.revit_file,
            code_file=payload.code_file,
            review_request=payload.review_request,
            model=payload.model,
            base_url=payload.base_url,
            embedding_model=payload.embedding_model,
            embedding_base_url=payload.embedding_base_url,
        )
        return {"status": "ok", "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {exc}")


@app.post("/agent/test-retrieval")
def agent_test_retrieval(payload: RetrievalTestRequest):
    try:
        init_msg = init_code_vectorstore(
            code_file=payload.code_file,
            embedding_model=payload.embedding_model,
            base_url=payload.embedding_base_url,
        )
        hits = retrieve_code_context(query=payload.query, k=payload.top_k)
        return {
            "status": "ok",
            "message": init_msg,
            "query": payload.query,
            "results": hits,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retrieval test failed: {exc}")


@app.post("/agent/ask-rules")
def agent_ask_rules(payload: QuestionRulesRequest):
    try:
        result = answer_question_with_rules(
            question=payload.question,
            code_file=payload.code_file,
            top_k=payload.top_k,
            model=payload.model,
            base_url=payload.base_url,
            embedding_model=payload.embedding_model,
            embedding_base_url=payload.embedding_base_url,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Question rule extraction failed: {exc}")


@app.post("/agent/extract-rules")
def agent_extract_structured_rules(payload: StructuredRuleExtractionRequest):
    try:
        return extract_structured_rules(
            question=payload.question,
            code_file=payload.code_file,
            top_k=payload.top_k,
            model=payload.model,
            base_url=payload.base_url,
            embedding_model=payload.embedding_model,
            embedding_base_url=payload.embedding_base_url,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Structured rule extraction failed: {exc}")


@app.post("/rules/engine-check")
def rules_engine_check(payload: RuleEngineCheckRequest):
    try:
        elements = [item.model_dump() for item in payload.elements]
        rules = [item.model_dump() for item in payload.rules]
        return {"status": "ok", **evaluate_rules_for_elements(elements, rules)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Rule engine execution failed: {exc}")


@app.post("/agent/full-check")
def full_agentic_check(payload: FullComplianceRequest):
    """Phase-7 endpoint: Revit BIM -> RAG -> LLM rules -> deterministic rule engine."""
    try:
        extraction = extract_structured_rules(
            question=payload.question,
            code_file=payload.code_file,
            top_k=payload.top_k,
            model=payload.model,
            base_url=payload.base_url,
            embedding_model=payload.embedding_model,
            embedding_base_url=payload.embedding_base_url,
        )
        elements = [item.model_dump() for item in payload.elements]
        engine_result = evaluate_rules_for_elements(elements, extraction.get("rules", []))

        return {
            "status": "ok",
            "phase": "full-integration",
            "question": payload.question,
            "rules": extraction.get("rules", []),
            "retrieval_hits": extraction.get("retrieval_hits", []),
            "answer": extraction.get("answer", ""),
            "engine": engine_result,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Full compliance flow failed: {exc}")


@app.post("/integration/revit/check")
def revit_integration_check(payload: FullComplianceRequest):
    """Stable integration alias for Revit add-in callers."""
    return full_agentic_check(payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="revit-backend", port=8000)   