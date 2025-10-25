"""
Advanced RAG Implementation with Vector Database
This example uses ChromaDB for semantic search and embeddings for better retrieval.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from chromadb.config import Settings

# Load environment variables
load_dotenv()

# Initialize OpenAI client for GitHub Models
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN")
)


def load_documents(directory: str = "documents") -> list[dict]:
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
                documents.append({
                    "content": content,
                    "source": file_path.name
                })
                print(f"Loaded: {file_path.name}")
        except Exception as e:
            print(f"Error loading {file_path.name}: {e}")
    
    return documents


def chunk_documents(documents: list[dict], chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """Split documents into overlapping chunks with metadata."""
    chunks = []
    
    for doc in documents:
        text = doc["content"]
        source = doc["source"]
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "source": source,
                    "chunk_id": chunk_id
                })
                chunk_id += 1
            
            start = end - overlap
    
    return chunks


def get_embedding(text: str) -> list[float]:
    """Get embedding vector for text using OpenAI's embedding model."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def create_vector_database(chunks: list[dict]) -> chromadb.Collection:
    """Create a ChromaDB collection and add document chunks."""
    
    # Initialize ChromaDB client
    chroma_client = chromadb.Client(Settings(
        anonymized_telemetry=False,
        allow_reset=True
    ))
    
    # Create or get collection
    collection = chroma_client.get_or_create_collection(
        name="document_collection",
        metadata={"description": "RAG document chunks"}
    )
    
    print(f"\n🔄 Creating embeddings for {len(chunks)} chunks...")
    
    # Prepare data for ChromaDB
    documents = []
    metadatas = []
    ids = []
    embeddings = []
    
    for i, chunk in enumerate(chunks):
        documents.append(chunk["text"])
        metadatas.append({
            "source": chunk["source"],
            "chunk_id": chunk["chunk_id"]
        })
        ids.append(f"chunk_{i}")
        
        # Get embedding
        embedding = get_embedding(chunk["text"])
        embeddings.append(embedding)
        
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(chunks)} chunks...")
    
    # Add to collection
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
        embeddings=embeddings
    )
    
    print("✅ Vector database created successfully!")
    return collection


def semantic_search(collection: chromadb.Collection, question: str, top_k: int = 3) -> list[dict]:
    """Perform semantic search using embeddings."""
    
    # Get embedding for the question
    question_embedding = get_embedding(question)
    
    # Query the collection
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k
    )
    
    # Format results
    retrieved_chunks = []
    for i in range(len(results["documents"][0])):
        retrieved_chunks.append({
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "chunk_id": results["metadatas"][0][i]["chunk_id"],
            "distance": results["distances"][0][i] if "distances" in results else None
        })
    
    return retrieved_chunks


def generate_answer(question: str, retrieved_chunks: list[dict]) -> str:
    """Generate an answer using the LLM with retrieved context."""
    
    # Build context from chunks
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        context_parts.append(f"[Source {i}: {chunk['source']}]\n{chunk['text']}")
    
    context = "\n\n".join(context_parts)
    
    # Create the prompt
    prompt = f"""You are a helpful assistant. Answer the question based on the context provided below.
If the answer is not in the context, say "I don't have enough information to answer that."
When possible, mention which source the information comes from.

Context:
{context}

Question: {question}

Answer:"""
    
    # Call the LLM
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content


def main():
    """Main function to run the advanced RAG system."""
    
    print("=" * 60)
    print("Advanced RAG System with Vector Database")
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
    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks")
    
    # Step 3: Create vector database
    print("\n🗄️  Creating vector database...")
    collection = create_vector_database(chunks)
    
    # Step 4: Interactive Q&A loop
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
        print("🔍 Searching knowledge base...")
        retrieved_chunks = semantic_search(collection, question, top_k=3)
        
        if not retrieved_chunks:
            print("❌ No relevant information found.")
            continue
        
        # Show retrieved sources
        print("\n📚 Retrieved sources:")
        for i, chunk in enumerate(retrieved_chunks, 1):
            print(f"  {i}. {chunk['source']} (chunk {chunk['chunk_id']})")
        
        # Generate answer
        print("\n💭 Generating answer...")
        answer = generate_answer(question, retrieved_chunks)
        
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
