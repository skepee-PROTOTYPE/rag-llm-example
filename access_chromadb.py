"""
Script to access and interact with ChromaDB
"""

import chromadb
from pathlib import Path
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN")
)

# ChromaDB persistent path
CHROMA_PATH = "./chroma_db"

# Check if database exists
if not Path(CHROMA_PATH).exists():
    print(f"❌ Database not found at {CHROMA_PATH}")
    print("Run persistent_rag.py first to create the database!")
    exit(1)

# Initialize persistent ChromaDB client
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)


def get_embedding(text: str) -> list[float]:
    """Get embedding vector for text."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

print("=" * 60)
print("ChromaDB Access")
print("=" * 60)

# List all collections
print("\n📚 Available Collections:")
collections = chroma_client.list_collections()
if collections:
    for col in collections:
        print(f"  - {col.name} (count: {col.count()})")
else:
    print("  No collections found")

# If document_collection exists, show details
try:
    collection = chroma_client.get_collection("document_collection")
    
    print("\n🔍 Collection Details:")
    print(f"  Name: {collection.name}")
    print(f"  Total documents: {collection.count()}")
    
    # Get all documents
    print("\n📄 All Documents in Collection:")
    results = collection.get()
    
    for i, (doc_id, doc_text, metadata) in enumerate(zip(
        results['ids'], 
        results['documents'], 
        results['metadatas']
    ), 1):
        print(f"\n  [{i}] ID: {doc_id}")
        print(f"      Source: {metadata.get('source', 'N/A')}")
        print(f"      Chunk ID: {metadata.get('chunk_id', 'N/A')}")
        print(f"      Text Preview: {doc_text[:100]}...")
    
    # Example query
    print("\n" + "=" * 60)
    print("🔎 Example Search: 'deep learning'")
    print("=" * 60)
    
    # Get embedding for search query
    search_embedding = get_embedding("deep learning")
    
    query_results = collection.query(
        query_embeddings=[search_embedding],
        n_results=3
    )
    
    print("\n📊 Top 3 Results:")
    for i, (doc, metadata, distance) in enumerate(zip(
        query_results['documents'][0],
        query_results['metadatas'][0],
        query_results['distances'][0]
    ), 1):
        print(f"\n  Result {i}:")
        print(f"  Source: {metadata.get('source')}")
        print(f"  Similarity Score: {1 - distance:.4f}")
        print(f"  Text: {doc[:200]}...")
    
except Exception as e:
    print(f"\n⚠️ Collection 'document_collection' not found: {e}")
    print("Run advanced_rag.py first to create the collection!")

print("\n" + "=" * 60)
