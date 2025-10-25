# Simple RAG (Retrieval-Augmented Generation) LLM Example

This is a simple example demonstrating how to build a RAG system that retrieves relevant information from documents and uses an LLM to generate answers.

## What is RAG?

RAG (Retrieval-Augmented Generation) combines:
1. **Retrieval**: Finding relevant information from a knowledge base
2. **Augmentation**: Enhancing the LLM prompt with retrieved context
3. **Generation**: Using an LLM to generate accurate answers based on the context

## Project Structure

```
rag-llm-example/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── simple_rag.py            # Basic RAG implementation
├── advanced_rag.py          # Advanced RAG with vector database
├── documents/               # Sample documents directory
│   └── sample_docs.txt      # Sample knowledge base
└── .env.example             # Environment variables template
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Copy `.env.example` to `.env` and add your API key:

```bash
# For GitHub Models (Free to start)
GITHUB_TOKEN=your_github_personal_access_token

# OR for Azure OpenAI
# AZURE_OPENAI_ENDPOINT=your_endpoint
# AZURE_OPENAI_API_KEY=your_key
```

To get a GitHub Personal Access Token:
- Go to https://github.com/settings/tokens
- Generate a new token (classic)
- No special scopes needed for GitHub Models

### 3. Run the Examples

**Simple RAG (no vector database):**
```bash
python simple_rag.py
```

**Advanced RAG (with ChromaDB vector database):**
```bash
python advanced_rag.py
```

## How It Works

### Simple RAG (`simple_rag.py`)
1. Loads documents from the `documents/` folder
2. Chunks documents into smaller pieces
3. Uses simple keyword matching to find relevant chunks
4. Sends relevant chunks + user question to the LLM
5. Returns AI-generated answer based on the context

### Advanced RAG (`advanced_rag.py`)
1. Loads and chunks documents
2. Creates embeddings (vector representations) of chunks
3. Stores embeddings in ChromaDB vector database
4. Uses semantic search to find relevant chunks
5. Sends relevant chunks + user question to the LLM
6. Returns AI-generated answer with sources

## Example Questions to Try

- "What is machine learning?"
- "Explain neural networks"
- "What are the benefits of deep learning?"

## Customization

### Add Your Own Documents
1. Place `.txt`, `.pdf`, or `.md` files in the `documents/` folder
2. The system will automatically load and process them

### Change the LLM Model
Edit the model name in the Python files:
```python
model = "gpt-4.1-mini"  # Change to any supported model
```

### Adjust Retrieval Settings
In `advanced_rag.py`, modify:
```python
results = collection.query(
    query_texts=[question],
    n_results=3  # Number of chunks to retrieve
)
```

## Architecture Diagram

```
User Question
     ↓
[Document Loader]
     ↓
[Text Chunker]
     ↓
[Embedding Model] → [Vector Database (ChromaDB)]
     ↓
[Semantic Search] ← User Question
     ↓
[Retrieved Chunks]
     ↓
[LLM (GPT-4.1-mini)] ← Question + Context
     ↓
Generated Answer
```

## Technologies Used

- **LLM**: OpenAI GPT-4.1-mini (via GitHub Models)
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector Database**: ChromaDB
- **Document Processing**: LangChain
- **API Client**: OpenAI Python SDK

## Next Steps

1. Add support for more document types (PDF, DOCX, HTML)
2. Implement conversation history
3. Add a web interface with Streamlit or Gradio
4. Deploy to Azure or other cloud platforms
5. Add caching for faster responses
6. Implement query rewriting for better retrieval

## Resources

- [GitHub Models Documentation](https://github.com/marketplace/models)
- [LangChain Documentation](https://python.langchain.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
