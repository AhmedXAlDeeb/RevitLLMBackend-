import json
import os

import requests


def _base_url() -> str:
    return os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


def main() -> None:
    url = f"{_base_url()}/integration/revit/check"
    payload = {
        "elements": [
            {"id": "101", "name": "Bedroom 1", "category": "room", "area": 8.5, "height": 2.7, "level": "L1"},
            {"id": "102", "name": "Bedroom 2", "category": "room", "area": 12.1, "height": 2.7, "level": "L1"},
        ],
        "question": "What is the minimum bedroom area requirement? Extract rules and check these rooms.",
        "code_file": "data/2015_International_Building_Code-238-323.pdf",
        "top_k": 6,
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "embedding_model": os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text-v2-moe:latest"),
        "embedding_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }

    response = requests.post(url, json=payload, timeout=300)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
