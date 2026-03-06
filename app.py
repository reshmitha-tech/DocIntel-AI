from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from core.rag import RAGPipeline
import os
from dotenv import load_dotenv

from werkzeug.utils import secure_filename

# Ensure directories exist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data', 'uploads')
VECTORSTORE_FOLDER = os.path.join(BASE_DIR, 'data', 'vectorstore')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VECTORSTORE_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)

# Initialize RAG Pipeline
rag = RAGPipeline(vectorstore_path=VECTORSTORE_FOLDER)

from flask import send_from_directory

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # We'll trigger indexing but return upload success immediately to the UI
        # The UI will then call an indexing endpoint or handle it via status updates
        return jsonify({
            'message': f'File {filename} uploaded successfully. Indexing starting...',
            'filename': filename,
            'file_path': file_path
        })

@app.route('/api/index', methods=['POST'])
def index_file():
    data = request.json
    file_path = data.get('file_path')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File not found for indexing'}), 404
        
    from core.ingestion import ingest_documents
    success = ingest_documents(file_path, vectorstore_path=VECTORSTORE_FOLDER)
    
    if success:
        rag._initialize_real() # Refresh RAG with new data
        return jsonify({'message': 'Indexing complete'})
    else:
        # Check if it was an API key error
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or len(api_key) < 10:
            return jsonify({'error': 'Invalid or missing GOOGLE_API_KEY in .env file.'}), 500
        return jsonify({'error': 'Failed to index document. Check server logs for details.'}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_query = data.get('query')
    
    if not user_query:
        return jsonify({'error': 'No query provided'}), 400
    
    # Generate RAG response
    response, citations = rag.generate_response(user_query)
    
    return jsonify({
        'response': response,
        'citations': citations
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
