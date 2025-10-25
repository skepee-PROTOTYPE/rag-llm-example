"""
Advanced RAG with Persistent ChromaDB
This version saves the vector database to disk so it can be accessed later.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN")
)

# ChromaDB persistent path
CHROMA_PATH = "./chroma_db"


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
    """Get embedding vector for text."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def get_or_create_collection(reset: bool = False):
    """Get or create a persistent ChromaDB collection."""
    
    # Initialize persistent ChromaDB client
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    collection_name = "document_collection"
    
    # Reset if requested
    if reset:
        try:
            chroma_client.delete_collection(name=collection_name)
            print("🗑️  Deleted existing collection")
        except:
            pass
    
    # Get or create collection
    try:
        collection = chroma_client.get_collection(name=collection_name)
        print(f"✅ Loaded existing collection with {collection.count()} documents")
        return collection, chroma_client
    except:
        print("📦 Creating new collection...")
        collection = chroma_client.create_collection(
            name=collection_name,
            metadata={"description": "RAG document chunks"}
        )
        return collection, chroma_client


def index_documents(collection, chunks: list[dict]):
    """Add documents to the collection."""
    
    if collection.count() > 0:
        print(f"ℹ️  Collection already has {collection.count()} documents")
        response = input("Reindex documents? (y/n): ").strip().lower()
        if response != 'y':
            return
        # Clear collection
        collection_name = collection.name
        collection._client.delete_collection(name=collection_name)
        collection = collection._client.create_collection(
            name=collection_name,
            metadata={"description": "RAG document chunks"}
        )
    
    print(f"\n🔄 Creating embeddings for {len(chunks)} chunks...")
    
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
        
        embedding = get_embedding(chunk["text"])
        embeddings.append(embedding)
        
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(chunks)} chunks...")
    
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
        embeddings=embeddings
    )
    
    print(f"✅ Indexed {len(chunks)} documents!")
    return collection


def semantic_search(collection, question: str, top_k: int = 3) -> list[dict]:
    """Perform semantic search."""
    question_embedding = get_embedding(question)
    
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k
    )
    
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
    """Generate answer using LLM."""
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        context_parts.append(f"[Source {i}: {chunk['source']}]\n{chunk['text']}")
    
    context = "\n\n".join(context_parts)
    
    prompt = f"""Answer the question based on the context below.
If the answer is not in the context, say "I don't have enough information."

Context:
{context}

Question: {question}

Answer:"""
    
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content


def main():
    """Main function."""
    
    print("=" * 60)
    print("Persistent RAG System")
    print("=" * 60)
    
    # Load or create collection
    collection, client = get_or_create_collection()
    
    # If collection is empty, index documents
    if collection.count() == 0:
        print("\n📂 Loading documents...")
        documents = load_documents()
        
        if not documents:
            print("⚠️  No documents found!")
            return
        
        print("\n✂️  Chunking documents...")
        chunks = chunk_documents(documents)
        print(f"Created {len(chunks)} chunks")
        
        print("\n🗄️  Indexing documents...")
        collection = index_documents(collection, chunks)
    
    # Interactive Q&A
    print(f"\n🤖 RAG system ready! ({collection.count()} docs indexed)")
    print("💾 Database persisted to:", CHROMA_PATH)
    print("Type 'quit' to exit\n" + "-" * 60)
    
    while True:
        question = input("\n❓ Your question: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not question:
            continue
        
        print("🔍 Searching...")
        retrieved_chunks = semantic_search(collection, question, top_k=3)
        
        print("\n📚 Sources:")
        for i, chunk in enumerate(retrieved_chunks, 1):
            print(f"  {i}. {chunk['source']} (chunk {chunk['chunk_id']})")
        
        print("\n💭 Generating answer...")
        answer = generate_answer(question, retrieved_chunks)
        
        print("\n" + "=" * 60)
        print("📝 Answer:")
        print(answer)
        print("=" * 60)


if __name__ == "__main__":
    if not os.environ.get("GITHUB_TOKEN"):
        print("❌ Error: GITHUB_TOKEN not found")
        print("Please set GITHUB_TOKEN in .env file")
    else:
        main()
