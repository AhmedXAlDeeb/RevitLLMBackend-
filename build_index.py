import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer
import numpy as np


# Folder containing your documents
DOCS_FOLDER = "docs"

# Output files
INDEX_FILE = "vector.index"
CHUNKS_FILE = "chunks.pkl"

# Load embedding model
print("Loading embedding model...")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

documents = []

print("Reading documents...")

for file in os.listdir(DOCS_FOLDER):
    path = os.path.join(DOCS_FOLDER, file)

    if file.endswith(".txt"):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
            documents.append(text)

print("Splitting documents into chunks...")

chunks = []
chunk_size = 500

for doc in documents:
    for i in range(0, len(doc), chunk_size):
        chunks.append(doc[i:i+chunk_size])

print(f"Total chunks: {len(chunks)}")

print("Generating embeddings...")
embeddings = model.encode(chunks)

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