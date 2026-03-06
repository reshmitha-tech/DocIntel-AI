# Standard imports
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class RAGPipeline:
    def __init__(self, vectorstore_path="data/vectorstore"):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.vectorstore_path = vectorstore_path
        self.embeddings = None
        self.vectorstore = None
        self.llm = None
        self.qa_chain = None
        self.direct_genai_model = None
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.direct_genai_model = genai.GenerativeModel('gemini-3-flash-preview')
            self._initialize_real()
        else:
            print("Warning: GOOGLE_API_KEY not found. Running in mock mode.")

    def _initialize_real(self):
        try:
            # Try loading LangChain components
            from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
            from langchain_community.vectorstores import Chroma
            # Initialize embeddings
            self.embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
            
            if os.path.exists(self.vectorstore_path):
                self.vectorstore = Chroma(
                    persist_directory=self.vectorstore_path,
                    embedding_function=self.embeddings
                )
                self.llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)
                
                try:
                    from langchain.chains import RetrievalQA
                    from langchain.prompts import PromptTemplate
                    
                    prompt_template = """
                    You are DocIntel AI, an intelligent assistant. Use the following context to answer:
                    {context}
                    Question: {question}
                    """
                    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
                    self.qa_chain = RetrievalQA.from_chain_type(
                        llm=self.llm, retriever=self.vectorstore.as_retriever(),
                        return_source_documents=True, chain_type_kwargs={"prompt": PROMPT}
                    )
                except:
                    print("RetrievalQA missing, using similarity search fallback.")
                    self.qa_chain = "similarity_search"
            else:
                print("Vectorstore path does not exist yet.")
                self.qa_chain = "llm_only"
                    
        except Exception as e:
            print(f"LangChain Init Error (Falling back to Direct GenAI): {e}")
            self.qa_chain = "llm_only"

    def generate_response(self, query):
        if not self.api_key:
            return self._mock_response(query)
            
        try:
            # Case 1: Full RetrievalQA
            if hasattr(self.qa_chain, 'invoke'):
                result = self.qa_chain.invoke({"query": query})
                answer = result["result"]
                citations = [f"[{os.path.basename(doc.metadata.get('source', 'Doc'))}, P.{doc.metadata.get('page', '?')}]" for doc in result["source_documents"]]
                return answer, list(set(citations))

            # Case 2: Similarity Search + Direct GenAI (if LangChain partial fail)
            elif self.qa_chain == "similarity_search" and self.vectorstore:
                docs = self.vectorstore.similarity_search(query, k=3)
                context = "\n".join([d.page_content for d in docs])
                prompt = f"Context: {context}\n\nQuestion: {query}\nAnswer based ONLY on context. If not found, say so."
                response = self.direct_genai_model.generate_content(prompt)
                citations = [f"[{os.path.basename(doc.metadata.get('source', 'Doc'))}, P.{doc.metadata.get('page', '?')}]" for doc in docs]
                return response.text, list(set(citations))

            # Case 3: Direct LLM (No documents indexed yet or LangChain fully broken)
            else: 
                response = self.direct_genai_model.generate_content(query)
                return response.text, ["[Direct AI Response]"]
                
        except Exception as e:
            print(f"Generation Error: {e}")
            return f"I encountered an error: {str(e)}. Please check your API key and connection.", []

    def _mock_response(self, query):
        return (
            f"API Key missing or invalid. Please check your .env file. Query: {query}",
            ["[System Error]"]
        )
