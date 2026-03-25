from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
from typing import List

from agentic_revit_rag_agent import (
    answer_question_with_rules,
    init_code_vectorstore,
    retrieve_code_context,
    run_revit_review_pipeline,
)


app = FastAPI()

MIN_AREA = 14

# Define Room model
class Room(BaseModel):
    id: int
    name: str
    area: float


class AgentReviewRequest(BaseModel):
    revit_file: str = "revit_model_test.json"
    code_file: str = "data/2015_International_Building_Code-238-323.pdf"
    review_request: str = "Check room area compliance against the provided code."
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_base_url: str = "http://localhost:11434"


class RetrievalTestRequest(BaseModel):
    query: str = "minimum bedroom area"
    code_file: str = "data/2015_International_Building_Code-238-323.pdf"
    top_k: int = 4
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_base_url: str = "http://localhost:11434"


class QuestionRulesRequest(BaseModel):
    question: str
    code_file: str = "data/2015_International_Building_Code-238-323.pdf"
    top_k: int = 6
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
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