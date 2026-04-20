import os
import faiss
from sentence_transformers import SentenceTransformer
import PyPDF2
import docx
import requests

# Load model globally to avoid reloading on every request
# all-MiniLM-L6-v2 is fast, lightweight, and local as requested
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def extract_text(file_path):
    """Extract text from PDF, DOCX, or TXT files."""
    text = ""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    elif ext == '.docx':
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        raise ValueError(f"Unsupported file format: {ext}")
        
    return text.strip()

def split_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks for better context retrieval."""
    chunks = []
    start = 0
    text_len = len(text)
    
    # Simple character-based splitting
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        # Advance by chunk_size minus the overlap
        start += chunk_size - overlap
        
    return chunks

def generate_embeddings(chunks):
    """Generate vector embeddings for text chunks."""
    embeddings = embedder.encode(chunks)
    return embeddings

def build_faiss_index(embeddings):
    """Build an in-memory FAISS index from the embeddings."""
    if len(embeddings) == 0:
        raise ValueError("No embeddings to index.")
        
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index

def retrieve(query, index, chunks, top_k=3):
    """Retrieve the top_k most relevant chunks for a given query."""
    query_embedding = embedder.encode([query])
    distances, indices = index.search(query_embedding, top_k)
    
    results = []
    for i in indices[0]:
        if i < len(chunks) and i != -1:
            results.append(chunks[i])
    return results

def generate_answer(query, context):
    """Generate an answer using Gemini API (if deployed) or local Ollama model."""
    prompt = f"""You are a helpful assistant.
Answer the question ONLY using the provided context.
If the answer is not in the context, say 'Not found in the document.'

Context:
{context}

Question:
{query}

Answer:"""

    # If GEMINI_API_KEY is present, we assume the app is deployed and use Gemini
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    
    if gemini_api_key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={gemini_api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        try:
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return f"Error communicating with Gemini API: {str(e)}"
    else:
        # Using Ollama locally. Assuming standard port 11434.
        # Llama3 is a standard fast default, but can be changed.
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "tinyllama", 
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json().get("response", "Error: Empty response from LLM.")
        except requests.exceptions.ConnectionError:
            return ("Error: Could not connect to local LLM (Ollama). "
                    "Please make sure Ollama is installed and running locally, "
                    "and that the 'llama3' model is pulled (`ollama run llama3`).")
        except Exception as e:
            return f"Error communicating with LLM: {str(e)}"
