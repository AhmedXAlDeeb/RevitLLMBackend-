import os
import faiss
import pickle
import numpy as np
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import OllamaEmbeddings


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


# Folder containing your documents
DOCS_FOLDER = "data"

# Output files
INDEX_FILE = "vector.index"
CHUNKS_FILE = "chunks.pkl"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Load embedding model
print("Loading embedding model...")
model = OllamaEmbeddings(model=_resolve_embedding_model(), base_url=OLLAMA_BASE_URL)

documents = []

print("Reading documents...")

for file in os.listdir(DOCS_FOLDER):
    path = os.path.join(DOCS_FOLDER, file)

    if file.endswith(".txt"):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
            documents.append(text)
    elif file.endswith(".pdf"):
        loader = PyPDFLoader(path)
        pages = loader.load()
        pdf_text = "\n".join(page.page_content for page in pages if page.page_content)
        if pdf_text.strip():
            documents.append(pdf_text)

print("Splitting documents into chunks...")

chunks = []
chunk_size = 500

for doc in documents:
    for i in range(0, len(doc), chunk_size):
        chunks.append(doc[i:i+chunk_size])

print(f"Total chunks: {len(chunks)}")

print("Generating embeddings...")
embeddings = model.embed_documents(chunks)

if len(embeddings) == 0:
    raise ValueError("No embeddings generated. Check docs folder.")

dimension = embeddings.shape[1]

print("Building FAISS index...")
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings))

print("Saving index...")
faiss.write_index(index, INDEX_FILE)

print("Saving chunks...")
with open(CHUNKS_FILE, "wb") as f:
    pickle.dump(chunks, f)

print("Index built successfully.")