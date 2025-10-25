"""
Simple RAG Implementation
This example demonstrates a basic RAG system without a vector database.
It uses simple keyword matching to retrieve relevant document chunks.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client for GitHub Models
# GitHub Models provides free access to various LLMs
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN")
)


def load_documents(directory: str = "documents") -> list[str]:
    """Load all text documents from the specified directory."""
    documents = []
    doc_path = Path(directory)
    
    if not doc_path.exists():
        print(f"Creating {directory} directory...")
        doc_path.mkdir(parents=True, exist_ok=True)
        return documents
    
    for file_path in doc_path.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                documents.append(content)
                print(f"Loaded: {file_path.name}")
        except Exception as e:
            print(f"Error loading {file_path.name}: {e}")
    
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
    """
    Simple keyword-based retrieval.
    Finds chunks that contain words from the question.
    """
    question_words = set(question.lower().split())
    scored_chunks = []
    
    for chunk in chunks:
        chunk_words = set(chunk.lower().split())
        # Calculate overlap score
        overlap = len(question_words & chunk_words)
        if overlap > 0:
            scored_chunks.append((overlap, chunk))
    
    # Sort by score and return top_k
    scored_chunks.sort(reverse=True, key=lambda x: x[0])
    return [chunk for _, chunk in scored_chunks[:top_k]]


def generate_answer(question: str, context_chunks: list[str]) -> str:
    """Generate an answer using the LLM with retrieved context."""
    
    # Combine chunks into context
    context = "\n\n".join(context_chunks)
    
    # Create the prompt
    prompt = f"""You are a helpful assistant. Answer the question based on the context provided below.
If the answer is not in the context, say "I don't have enough information to answer that."

Context:
{context}

Question: {question}

Answer:"""
    
    # Call the LLM
    response = client.chat.completions.create(
        model="gpt-4.1-mini",  # Fast and efficient model
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content


def main():
    """Main function to run the simple RAG system."""
    
    print("=" * 60)
    print("Simple RAG System")
    print("=" * 60)
    
    # Step 1: Load documents
    print("\n📂 Loading documents...")
    documents = load_documents()
    
    if not documents:
        print("⚠️  No documents found in 'documents' folder.")
        print("Please add .txt files to the 'documents' folder and try again.")
        return
    
    # Step 2: Chunk documents
    print("\n✂️  Chunking documents...")
    all_chunks = []
    for doc in documents:
        chunks = chunk_text(doc)
        all_chunks.extend(chunks)
    print(f"Created {len(all_chunks)} chunks")
    
    # Step 3: Interactive Q&A loop
    print("\n🤖 RAG system ready! Ask questions (type 'quit' to exit)")
    print("-" * 60)
    
    while True:
        question = input("\n❓ Your question: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not question:
            continue
        
        # Retrieve relevant chunks
        print("🔍 Retrieving relevant information...")
        relevant_chunks = simple_retrieval(all_chunks, question, top_k=3)
        
        if not relevant_chunks:
            print("❌ No relevant information found in the documents.")
            continue
        
        # Generate answer
        print("💭 Generating answer...")
        answer = generate_answer(question, relevant_chunks)
        
        print("\n" + "=" * 60)
        print("📝 Answer:")
        print(answer)
        print("=" * 60)


if __name__ == "__main__":
    # Check if GitHub token is set
    if not os.environ.get("GITHUB_TOKEN"):
        print("❌ Error: GITHUB_TOKEN not found in environment variables")
        print("\n📋 Setup instructions:")
        print("1. Copy .env.example to .env")
        print("2. Get a GitHub Personal Access Token from: https://github.com/settings/tokens")
        print("3. Add it to .env as: GITHUB_TOKEN=your_token_here")
        print("4. Run this script again")
    else:
        main()
