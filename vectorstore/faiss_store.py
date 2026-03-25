from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

class FAISSStore:
    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        self.embeddings = OllamaEmbeddings(model=model, base_url=base_url)

    def create_store(self, documents):
        vectorstore = FAISS.from_documents(documents, self.embeddings)
        return vectorstore