# MVP 1: Basic Keyword Search

## Overview
Basic keyword search system using BM25 algorithm for the Epstein document collection.

## Features
✓ Load .txt files from `data/` folder  
✓ BM25 keyword search  
✓ Interactive CLI interface  
✓ Fast search (< 1 second for 1000+ documents)

## Installation

### 1. Activate Virtual Environment
```powershell
# Windows PowerShell
.\epsteinai-venv\Scripts\Activate.ps1

# Or use batch file
.\epsteinai-venv\Scripts\activate.bat
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

This will install:
- `chardet` - Character encoding detection
- `rank-bm25` - BM25 implementation
- `loguru` - Logging
- `numpy` - Required by rank-bm25

## Usage

### Run the Search CLI
```bash
python -m src.cli
```

### Example Queries
```
Search: Maxwell Paris
Search: meeting 2019
Search: financial transactions
Search: oversight committee
```

### Programmatic Usage
```python
from src.document_loader import DocumentLoader
from src.sparse_search import BM25SearchEngine

# Load documents
loader = DocumentLoader("data")
documents = loader.load_documents()

# Create search engine
search_engine = BM25SearchEngine(documents)

# Search
results = search_engine.search("your query here", top_k=10)

# Process results
for result in results:
    print(f"{result['filename']}: {result['score']}")
    print(f"Preview: {result['preview']}")
```

## File Structure
```
├── data/                      # Your .txt files
├── src/
│   ├── __init__.py
│   ├── document_loader.py     # Load documents
│   ├── text_processor.py      # Clean text
│   ├── sparse_search.py       # BM25 search
│   └── cli.py                 # Command-line interface
├── tests/
│   └── test_basic_search.py   # Unit tests
└── requirements.txt           # Dependencies
```

## Testing

Run the tests:
```bash
pytest tests/test_basic_search.py -v
```

Or run individual component tests:
```bash
# Test document loader
python src/document_loader.py

# Test text processor
python src/text_processor.py

# Test search engine
python src/sparse_search.py
```

## How It Works

1. **Document Loading**: Loads all `.txt` files from `data/` folder with automatic encoding detection
2. **Text Processing**: Cleans and tokenizes text (lowercase, remove punctuation)
3. **BM25 Indexing**: Builds BM25 index from tokenized documents
4. **Search**: Queries are tokenized and matched against index using BM25 scoring
5. **Results**: Returns top-K documents ranked by relevance score

## Performance
- **Index Build Time**: ~1-2 seconds for 10 documents
- **Query Time**: < 100ms per search
- **Memory Usage**: ~10MB for 10 small documents

## Next Steps (Future MVPs)

### MVP 2: Metadata Extraction
- Extract named entities (people, locations, dates)
- Filter search results by metadata
- SQLite storage

### MVP 3: Semantic Search
- Chunk documents
- Generate embeddings
- Combine BM25 + semantic search
- ChromaDB vector storage

### MVP 4: Production API
- FastAPI REST API
- PostgreSQL database
- Docker deployment
- Authentication

## Troubleshooting

### No results found
- Check that `.txt` files are in `data/` folder
- Try simpler queries with common words
- Check file encoding (should auto-detect)

### Import errors
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt`

### Slow performance
- For large documents (>100MB), consider chunking
- Reduce `top_k` parameter for faster results

## Current Limitations
- No semantic understanding (exact keyword matching only)
- No entity extraction or metadata filtering
- In-memory only (no persistence)
- CLI interface only (no API)

These will be addressed in future MVP releases.

