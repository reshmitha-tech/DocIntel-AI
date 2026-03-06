import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

def ingest_documents(file_path, vectorstore_path="data/vectorstore"):
    """
    Ingest a document (PDF) into the Chroma vector store.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in environment.")
        return False

    try:
        # Load the document
        if file_path.lower().endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        else:
            # Fallback for text/docx if needed (basic implementation)
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(file_path)
            
        documents = loader.load()
        print(f"Loaded {len(documents)} pages from {file_path}")

        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        texts = text_splitter.split_documents(documents)
        print(f"Split into {len(texts)} chunks")

        # Initialize embeddings
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

        # Create or update vector store
        if os.path.exists(vectorstore_path):
            vectorstore = Chroma(
                persist_directory=vectorstore_path,
                embedding_function=embeddings
            )
            vectorstore.add_documents(texts)
        else:
            vectorstore = Chroma.from_documents(
                documents=texts,
                embedding=embeddings,
                persist_directory=vectorstore_path
            )
        
        # In newer LangChain/Chroma, persistence is often automatic or handled differently
        try:
            vectorstore.persist()
        except AttributeError:
            pass # Automatic persistence in newer versions
            
        print(f"Successfully ingested {file_path}")
        return True
    except Exception as e:
        print(f"Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Example usage
    # ingest_documents("path/to/your/document.pdf")
    pass
