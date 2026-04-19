from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
import os


def _resolve_embedding_model(model: str | None = None) -> str:
    if model and model.strip():
        return model.strip()

    env_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "").strip()
    if env_model:
        return env_model

    env_legacy_model = os.getenv("EMBEDDING_MODEL", "").strip()
    if env_legacy_model:
        return env_legacy_model

    return "nomic-embed-text-v2-moe:latest"



class FAISSStore:
    def __init__(
        self,
        model: str = "nomic-embed-text-v2-moe:latest",
        base_url: str = "http://localhost:11434",
    ):
        self.embeddings = OllamaEmbeddings(model=_resolve_embedding_model(model), base_url=base_url)

    def create_store(self, documents):
        vectorstore = FAISS.from_documents(documents, self.embeddings)
        return vectorstore