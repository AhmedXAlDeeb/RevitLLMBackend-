import json
import os
from pathlib import Path

import requests


def _base_url() -> str:
    return os.getenv("BACKEND_URL", "http://127.0.0.1:8080")


def _code_file_path() -> str:
    env_path = os.getenv("CODE_FILE")
    if env_path:
        return env_path

    project_root = Path(__file__).resolve().parents[1]
    candidates = [
        project_root / "data" / "all-pages.pdf",
        project_root / "data" / "2015_International_Building_Code-238-323.pdf",
    ]
    for path in candidates:
        if path.exists():
            return str(path)

    raise FileNotFoundError(
        "No code PDF found. Set CODE_FILE or place a PDF in data/"
    )


def _assert_response_shape(data: dict) -> None:
    assert data.get("status") == "ok", f"Unexpected status: {data.get('status')}"
    assert data.get("phase") == "full-integration", "Missing/invalid phase"
    assert "engine" in data and isinstance(data["engine"], dict), "Missing engine section"
    engine = data["engine"]
    assert "summary" in engine and isinstance(engine["summary"], dict), "Missing engine.summary"
    assert "results" in engine and isinstance(engine["results"], list), "Missing engine.results"
    assert len(engine["results"]) > 0, "No rule evaluation results returned"


def main() -> None:
    base_url = _base_url()
    health_url = f"{base_url}/health"
    url = f"{base_url}/integration/revit/check"

    health_response = requests.get(health_url, timeout=10)
    health_response.raise_for_status()

    payload = {
        "elements": [
            {"id": "101", "name": "Bedroom 1", "category": "room", "area": 8.5, "height": 2.7, "level": "L1"},
            {"id": "102", "name": "Bedroom 2", "category": "room", "area": 12.1, "height": 2.7, "level": "L1"},
        ],
        "question": "What is the minimum bedroom area requirement? Extract rules and check these rooms.",
        "code_file": _code_file_path(),
        "top_k": 6,
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "embedding_model": os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text-v2-moe:latest"),
        "embedding_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }

    print(f"Health check OK: {health_response.json()}")
    print(f"POST {url}")

    response = requests.post(url, json=payload, timeout=300)
    response.raise_for_status()
    data = response.json()
    _assert_response_shape(data)

    print("Integration test passed.")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
