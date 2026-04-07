from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader



class PDFLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    '''def load(self):
        loader = PyPDFLoader(self.file_path)
        documents = loader.load()
        return documents '''

    def load_and_split(self):
        loader = PyPDFLoader(self.file_path)
        documents = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )

        chunks = splitter.split_documents(documents)
        return chunks