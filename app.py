"""
Flask API for RAG System - Production Ready
Provides REST endpoints for document-based question answering
"""

import os
import logging
from pathlib import Path
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize OpenAI client for GitHub Models
def get_openai_client():
    """Get OpenAI client with GitHub Models configuration"""
    api_key = os.environ.get("GITHUB_TOKEN")
    if not api_key:
        logger.error("GITHUB_TOKEN environment variable not set")
        raise ValueError("GITHUB_TOKEN not configured")
    
    logger.info(f"Initializing OpenAI client with token: {api_key[:10]}...")
    return OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=api_key,
        timeout=30.0  # 30 second timeout
    )

# Global storage for document chunks
document_chunks = []


def load_documents(directory: str = "documents") -> list[str]:
    """Load all text documents from the specified directory."""
    documents = []
    doc_path = Path(directory)
    
    if not doc_path.exists():
        logger.warning(f"Documents directory '{directory}' does not exist")
        doc_path.mkdir(parents=True, exist_ok=True)
        return documents
    
    for file_path in doc_path.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                documents.append(content)
                logger.info(f"Loaded: {file_path.name}")
        except Exception as e:
            logger.error(f"Error loading {file_path.name}: {e}")
    
    return documents


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk.strip())
        start = end - overlap
    
    return chunks


def simple_retrieval(chunks: list[str], question: str, top_k: int = 3) -> list[str]:
    """Simple keyword-based retrieval."""
    question_words = set(question.lower().split())
    scored_chunks = []
    
    for chunk in chunks:
        chunk_words = set(chunk.lower().split())
        overlap = len(question_words & chunk_words)
        if overlap > 0:
            scored_chunks.append((overlap, chunk))
    
    scored_chunks.sort(reverse=True, key=lambda x: x[0])
    return [chunk for _, chunk in scored_chunks[:top_k]]


def generate_answer(question: str, context_chunks: list[str]) -> str:
    """Generate an answer using the LLM with retrieved context."""
    context = "\n\n".join(context_chunks)
    
    prompt = f"""You are a helpful assistant. Answer the question based on the context provided below.
If the answer is not in the context, say "I don't have enough information to answer that."

Context:
{context}

Question: {question}

Answer:"""
    
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}", exc_info=True)
        raise


# Initialize documents on startup
def initialize_documents():
    """Load and chunk documents on startup."""
    global document_chunks
    logger.info("Initializing documents...")
    
    documents = load_documents()
    if not documents:
        logger.warning("No documents found. The system will have no knowledge base.")
        return
    
    for doc in documents:
        chunks = chunk_text(doc)
        document_chunks.extend(chunks)
    
    logger.info(f"Initialized with {len(document_chunks)} document chunks")


# Routes
@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "RAG API",
        "chunks_loaded": len(document_chunks)
    })


@app.route("/debug", methods=["GET"])
def debug_info():
    """Debug endpoint to check configuration."""
    token = os.environ.get("GITHUB_TOKEN", "")
    return jsonify({
        "token_configured": bool(token),
        "token_length": len(token) if token else 0,
        "token_preview": token[:10] + "..." if len(token) > 10 else "",
        "chunks_loaded": len(document_chunks),
        "base_url": "https://models.inference.ai.azure.com"
    })


@app.route("/api/ask", methods=["POST"])
def ask_question():
    """
    Answer a question using RAG.
    
    Request body:
    {
        "question": "Your question here",
        "top_k": 3  # Optional, default is 3
    }
    """
    try:
        # Validate request
        data = request.get_json()
        if not data or "question" not in data:
            return jsonify({"error": "Missing 'question' in request body"}), 400
        
        question = data["question"].strip()
        if not question:
            return jsonify({"error": "Question cannot be empty"}), 400
        
        # Input validation
        if len(question) > 500:
            return jsonify({"error": "Question too long (max 500 characters)"}), 400
        
        top_k = data.get("top_k", 3)
        
        # Check if we have documents
        if not document_chunks:
            return jsonify({
                "answer": "No documents are loaded. Please add documents to the knowledge base.",
                "chunks_retrieved": 0
            })
        
        # Retrieve relevant chunks
        logger.info(f"Processing question: {question[:50]}...")
        relevant_chunks = simple_retrieval(document_chunks, question, top_k=top_k)
        
        if not relevant_chunks:
            return jsonify({
                "answer": "I don't have enough information to answer that question.",
                "chunks_retrieved": 0
            })
        
        # Generate answer
        answer = generate_answer(question, relevant_chunks)
        
        return jsonify({
            "question": question,
            "answer": answer,
            "chunks_retrieved": len(relevant_chunks)
        })
    
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get system statistics."""
    return jsonify({
        "total_chunks": len(document_chunks),
        "status": "operational" if document_chunks else "no_documents"
    })


# Initialize on startup (only in production, not during import)
if __name__ != "__main__":
    initialize_documents()


if __name__ == "__main__":
    # Development server
    initialize_documents()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
