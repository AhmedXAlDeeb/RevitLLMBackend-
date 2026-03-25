from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

class FAISSStore:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()

    def create_store(self, documents):
        vectorstore = FAISS.from_documents(documents, self.embeddings)
        return vectorstore