import asyncio
import json
import os


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

from src.revit_backend.pipeline.agentic_revit_rag_agent import (
    answer_question_with_rules,
    init_code_vectorstore,
    retrieve_code_context,
    run_revit_review_pipeline,
)


async def main():
    code_file = "data/2015_International_Building_Code-238-323.pdf"
    revit_file = "revit_model_test.json"
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    print("Initializing retrieval index...")
    print(init_code_vectorstore(code_file=code_file, base_url=ollama_base_url))

    query = "minimum bedroom area requirements"
    print(f"\nRetrieval query: {query}")
    hits = retrieve_code_context(query=query, k=3)
    print(json.dumps(hits, indent=2))

    print("\nQuestion answering + rule extraction test...")
    qa_result = answer_question_with_rules(
        question="What is the minimum bedroom area? Return the rule.",
        code_file=code_file,
        top_k=6,
        model=ollama_model,
        base_url=ollama_base_url,
        embedding_base_url=ollama_base_url,
    )
    print(json.dumps(qa_result, indent=2))

    print("\nRunning full agent compliance pipeline...")
    result = await run_revit_review_pipeline(
        revit_file=revit_file,
        code_file=code_file,
        review_request="Check bedroom and kitchen area compliance against code.",
        model=ollama_model,
        base_url=ollama_base_url,
        embedding_base_url=ollama_base_url,
    )

    print("\nPipeline result paths:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
