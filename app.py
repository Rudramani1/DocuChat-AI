import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from rag_pipeline import extract_text, split_text, generate_embeddings, build_faiss_index, retrieve, generate_answer

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max size

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory temporary storage (as requested: "Store data temporarily")
# For a production app, we would use a persistent vector database
global_index = None
global_chunks = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global global_index, global_chunks
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # 1. Extract text from the uploaded document
            text = extract_text(filepath)
            if not text:
                return jsonify({'error': 'Could not extract text from the file.'}), 400
                
            # 2. Split text into chunks (~500 chars, ~50 overlap)
            global_chunks = split_text(text, chunk_size=500, overlap=50)
            
            # 3. Generate embeddings for the chunks
            embeddings = generate_embeddings(global_chunks)
            
            # 4. Build FAISS index for fast retrieval
            global_index = build_faiss_index(embeddings)
            
            return jsonify({'message': 'File successfully processed and indexed!'})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            # Clean up the uploaded file to save space (since data is in memory)
            if os.path.exists(filepath):
                os.remove(filepath)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
        
    if global_index is None or not global_chunks:
        return jsonify({'error': 'Please upload a document first.'}), 400
        
    try:
        # 1. Retrieve top 3 relevant chunks
        relevant_chunks = retrieve(query, global_index, global_chunks, top_k=3)
        context = "\n\n".join(relevant_chunks)
        
        # 2. Generate answer strictly based on context
        answer = generate_answer(query, context)
        
        return jsonify({'answer': answer, 'context_used': relevant_chunks})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
