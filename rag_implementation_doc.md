# RAG Pipeline Implementation Guide
## Document Search System for Epstein Document Collection

**Scope:** Text files (.txt) only - no OCR or vision models required  
**Architecture:** Three-tier retrieval (Sparse → Metadata → Dense)  
**Goal:** Fast, accurate semantic search with source traceability

---

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Technology Stack](#technology-stack)
3. [MVP Roadmap](#mvp-roadmap)
4. [Detailed Implementation](#detailed-implementation)
5. [Testing Strategy](#testing-strategy)
6. [Deployment Considerations](#deployment-considerations)

---

## System Architecture Overview

```
Input: .txt files → Processing Pipeline → Three-Tier Index → Query Interface → Results
```

### Three-Tier Retrieval Strategy

**Tier 1: Sparse Index (BM25)**
- Purpose: Fast keyword-based filtering
- Searches: Full document text
- Output: Top 100 candidate documents
- Speed: <100ms

**Tier 2: Metadata Index (Structured Data)**
- Purpose: Entity-based filtering
- Searches: Extracted names, dates, locations, emails
- Output: Top 50 filtered documents
- Speed: <50ms

**Tier 3: Dense Vector Index (Semantic)**
- Purpose: Semantic similarity ranking
- Searches: Document chunk embeddings
- Output: Top 10 most relevant chunks
- Speed: <200ms

**Total Query Time:** ~350ms for end-to-end search

---

## Technology Stack

### Core Dependencies

```python
# requirements.txt

# Document Processing
python-magic==0.4.27          # File type detection
chardet==5.2.0                # Character encoding detection

# Text Processing
spacy==3.7.2                  # NER and text preprocessing
en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0-py3-none-any.whl

# Sparse Retrieval
rank-bm25==0.2.2              # BM25 implementation

# Dense Retrieval
sentence-transformers==2.2.2   # For embeddings
openai==1.6.1                 # Alternative: OpenAI embeddings

# Vector Database (choose one)
chromadb==0.4.22              # Local vector DB (MVP)
# pinecone-client==3.0.0      # Production alternative
# weaviate-client==4.4.0      # Production alternative

# Storage
sqlalchemy==2.0.25            # Metadata storage
psycopg2-binary==2.9.9        # PostgreSQL driver (production)
# sqlite3 (built-in)          # SQLite for MVP

# API Framework
fastapi==0.108.0              # REST API
uvicorn==0.25.0               # ASGI server
pydantic==2.5.3               # Data validation

# Utilities
tqdm==4.66.1                  # Progress bars
python-dotenv==1.0.0          # Environment variables
loguru==0.7.2                 # Logging
```

### Installation Commands

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

---

## MVP Roadmap

### MVP 1: Basic Search (Week 1)
**Goal:** Search documents by keywords, return results

**Features:**
- Load .txt files from folder
- Basic text cleaning
- BM25 keyword search
- Simple CLI interface
- Return top 10 results

**No Requirements:**
- No metadata extraction
- No semantic search
- No API
- No database (in-memory only)

**Success Metric:** Can search 1000+ documents in <1 second

---

### MVP 2: Metadata Extraction (Week 2)
**Goal:** Filter results by entities (names, dates, locations)

**Features:**
- Extract named entities with spaCy
- Extract dates with regex
- Extract emails with regex
- Store metadata in SQLite
- Filter search results by metadata
- Basic web UI (optional)

**Success Metric:** Can filter results by "documents mentioning [person] in [year]"

---

### MVP 3: Semantic Search (Week 3)
**Goal:** Understand query meaning, not just keywords

**Features:**
- Chunk documents (500-1000 tokens)
- Generate embeddings with sentence-transformers
- Store vectors in ChromaDB
- Combine BM25 + semantic search
- Rerank results by relevance
- Show source excerpts with highlighting

**Success Metric:** Finds relevant documents even with different wording (e.g., "financial transfers" finds "money transactions")

---

### MVP 4: Production-Ready (Week 4)
**Goal:** Deploy as API service with proper architecture

**Features:**
- FastAPI REST API
- PostgreSQL for metadata
- Pinecone/Weaviate for vectors
- Query caching
- Async processing
- Error handling & logging
- Docker deployment
- Basic authentication

**Success Metric:** Can handle 10+ concurrent users, <500ms query time

---

## Detailed Implementation

---

## MVP 1: Basic Keyword Search

### File Structure
```
rag-pipeline/
├── data/
│   └── raw/                 # Place .txt files here
├── src/
│   ├── __init__.py
│   ├── document_loader.py   # Load documents
│   ├── text_processor.py    # Clean text
│   ├── sparse_search.py     # BM25 implementation
│   └── cli.py              # Command-line interface
├── tests/
│   └── test_basic_search.py
├── requirements.txt
└── README.md
```

### 1.1 Document Loader

**File:** `src/document_loader.py`

```python
"""
Load and validate .txt files from directory
"""

from pathlib import Path
from typing import List, Dict
import chardet
from loguru import logger


class DocumentLoader:
    """Load text documents from filesystem"""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        
    def load_documents(self) -> List[Dict]:
        """
        Load all .txt files from directory
        
        Returns:
            List of document dictionaries with structure:
            {
                'doc_id': str,
                'filename': str,
                'text': str,
                'metadata': {
                    'size': int,
                    'encoding': str
                }
            }
        """
        documents = []
        txt_files = list(self.data_dir.glob("**/*.txt"))
        
        logger.info(f"Found {len(txt_files)} text files")
        
        for idx, filepath in enumerate(txt_files):
            try:
                doc = self._load_single_file(filepath, idx)
                documents.append(doc)
            except Exception as e:
                logger.error(f"Failed to load {filepath}: {e}")
                
        logger.info(f"Successfully loaded {len(documents)} documents")
        return documents
    
    def _load_single_file(self, filepath: Path, doc_id: int) -> Dict:
        """Load a single text file with encoding detection"""
        
        # Detect encoding
        with open(filepath, 'rb') as f:
            raw_data = f.read()
            detected = chardet.detect(raw_data)
            encoding = detected['encoding'] or 'utf-8'
        
        # Read with detected encoding
        try:
            text = raw_data.decode(encoding)
        except UnicodeDecodeError:
            # Fallback to utf-8 with error handling
            text = raw_data.decode('utf-8', errors='ignore')
            logger.warning(f"Encoding issue in {filepath}, used fallback")
        
        return {
            'doc_id': f"doc_{doc_id:06d}",
            'filename': filepath.name,
            'filepath': str(filepath),
            'text': text,
            'metadata': {
                'size': len(text),
                'encoding': encoding,
                'file_size_bytes': filepath.stat().st_size
            }
        }


# Usage Example
if __name__ == "__main__":
    loader = DocumentLoader("data/raw")
    documents = loader.load_documents()
    print(f"Loaded {len(documents)} documents")
    print(f"First doc: {documents[0]['filename']}")
    print(f"First 100 chars: {documents[0]['text'][:100]}")
```

### 1.2 Text Processor

**File:** `src/text_processor.py`

```python
"""
Clean and normalize text for search
"""

import re
from typing import List


class TextProcessor:
    """Preprocess text for indexing and search"""
    
    def __init__(self, min_token_length: int = 2):
        self.min_token_length = min_token_length
        
    def clean_text(self, text: str) -> str:
        """
        Basic text cleaning
        - Remove extra whitespace
        - Normalize line breaks
        - Remove control characters
        """
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization for BM25
        - Lowercase
        - Split on whitespace and punctuation
        - Remove short tokens
        """
        
        # Lowercase
        text = text.lower()
        
        # Replace punctuation with spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split and filter
        tokens = text.split()
        tokens = [t for t in tokens if len(t) >= self.min_token_length]
        
        return tokens
    
    def extract_preview(self, text: str, max_length: int = 200) -> str:
        """Extract first N characters as preview"""
        preview = text[:max_length]
        if len(text) > max_length:
            preview += "..."
        return preview


# Usage Example
if __name__ == "__main__":
    processor = TextProcessor()
    
    sample_text = """
    This is a    sample document.
    It has multiple   spaces and
    
    
    extra newlines!!!
    """
    
    cleaned = processor.clean_text(sample_text)
    print("Cleaned:", repr(cleaned))
    
    tokens = processor.tokenize(cleaned)
    print("Tokens:", tokens)
```

### 1.3 BM25 Search Engine

**File:** `src/sparse_search.py`

```python
"""
BM25-based keyword search implementation
"""

from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
from loguru import logger
from src.text_processor import TextProcessor


class BM25SearchEngine:
    """
    Sparse retrieval using BM25 algorithm
    """
    
    def __init__(self, documents: List[Dict]):
        """
        Initialize search engine with documents
        
        Args:
            documents: List of document dicts with 'doc_id' and 'text'
        """
        self.documents = documents
        self.processor = TextProcessor()
        
        # Tokenize all documents
        logger.info("Tokenizing documents for BM25...")
        self.tokenized_corpus = [
            self.processor.tokenize(doc['text']) 
            for doc in documents
        ]
        
        # Build BM25 index
        logger.info("Building BM25 index...")
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        logger.info(f"BM25 index built for {len(documents)} documents")
        
    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Search documents using BM25
        
        Args:
            query: Search query string
            top_k: Number of results to return
            
        Returns:
            List of documents with scores, sorted by relevance
        """
        
        # Tokenize query
        query_tokens = self.processor.tokenize(query)
        
        if not query_tokens:
            logger.warning("Query resulted in no tokens after processing")
            return []
        
        # Get BM25 scores for all documents
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top K document indices
        top_indices = scores.argsort()[-top_k:][::-1]
        
        # Build results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include docs with positive scores
                doc = self.documents[idx].copy()
                doc['score'] = float(scores[idx])
                doc['preview'] = self.processor.extract_preview(doc['text'])
                results.append(doc)
        
        logger.info(f"Found {len(results)} results for query: '{query}'")
        return results


# Usage Example
if __name__ == "__main__":
    from src.document_loader import DocumentLoader
    
    # Load documents
    loader = DocumentLoader("data/raw")
    documents = loader.load_documents()
    
    # Create search engine
    search_engine = BM25SearchEngine(documents)
    
    # Search
    results = search_engine.search("Maxwell Paris meeting", top_k=10)
    
    # Display results
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['filename']} (score: {result['score']:.2f})")
        print(f"   {result['preview']}")
```

### 1.4 Command-Line Interface

**File:** `src/cli.py`

```python
"""
Simple command-line interface for MVP1
"""

import sys
from loguru import logger
from src.document_loader import DocumentLoader
from src.sparse_search import BM25SearchEngine


def main():
    """MVP1 CLI - Basic keyword search"""
    
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    print("=" * 60)
    print("Document Search System - MVP1")
    print("=" * 60)
    
    # Load documents
    print("\nLoading documents...")
    loader = DocumentLoader("data/raw")
    documents = loader.load_documents()
    
    if not documents:
        print("Error: No documents found in data/raw/")
        return
    
    print(f"Loaded {len(documents)} documents")
    
    # Build search index
    print("\nBuilding search index...")
    search_engine = BM25SearchEngine(documents)
    print("Index ready!")
    
    # Interactive search loop
    print("\n" + "=" * 60)
    print("Enter search queries (or 'quit' to exit)")
    print("=" * 60)
    
    while True:
        print("\n")
        query = input("Search: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
            
        if not query:
            continue
        
        # Search
        results = search_engine.search(query, top_k=10)
        
        # Display results
        if not results:
            print("No results found.")
            continue
        
        print(f"\nFound {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['filename']}")
            print(f"   Score: {result['score']:.2f}")
            print(f"   Preview: {result['preview']}")
            print()


if __name__ == "__main__":
    main()
```

### 1.5 Testing

**File:** `tests/test_basic_search.py`

```python
"""
Unit tests for MVP1 components
"""

import pytest
from pathlib import Path
from src.document_loader import DocumentLoader
from src.text_processor import TextProcessor
from src.sparse_search import BM25SearchEngine


@pytest.fixture
def sample_documents():
    """Create sample documents for testing"""
    return [
        {
            'doc_id': 'doc_000001',
            'filename': 'doc1.txt',
            'text': 'Jeffrey Epstein met with Maxwell in Paris.'
        },
        {
            'doc_id': 'doc_000002',
            'filename': 'doc2.txt',
            'text': 'Flight logs show trips to Paris and London.'
        },
        {
            'doc_id': 'doc_000003',
            'filename': 'doc3.txt',
            'text': 'Maxwell sent emails about financial transactions.'
        }
    ]


def test_text_processor():
    """Test text cleaning and tokenization"""
    processor = TextProcessor()
    
    text = "Hello   World!!!  Multiple   spaces."
    cleaned = processor.clean_text(text)
    assert "  " not in cleaned
    
    tokens = processor.tokenize("Hello World 123")
    assert tokens == ['hello', 'world', '123']


def test_bm25_search(sample_documents):
    """Test BM25 search functionality"""
    engine = BM25SearchEngine(sample_documents)
    
    # Search for "Maxwell Paris"
    results = engine.search("Maxwell Paris", top_k=5)
    
    # Should find doc1 as top result (has both terms)
    assert len(results) > 0
    assert results[0]['filename'] == 'doc1.txt'
    assert results[0]['score'] > 0


def test_no_results():
    """Test search with no matches"""
    docs = [{'doc_id': 'doc1', 'text': 'Sample text'}]
    engine = BM25SearchEngine(docs)
    
    results = engine.search("nonexistent query terms", top_k=5)
    assert len(results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 1.6 Running MVP1

```bash
# Setup
cd rag-pipeline
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Add your .txt files to data/raw/

# Run tests
pytest tests/test_basic_search.py -v

# Run CLI
python -m src.cli

# Example queries:
# - "Maxwell Paris"
# - "financial transactions"
# - "flight logs"
```

**MVP1 Complete!** You now have working keyword search.

---

## PostgreSQL Setup Guide

### For MVP 2 & 3: Use SQLite (No Setup Required)
SQLite is built into Python and requires zero configuration. Perfect for development and MVP stages.

```python
# Just works - no installation needed!
import sqlite3
conn = sqlite3.connect('data/metadata.db')
```

### For MVP 4 (Production): PostgreSQL Options

---

### Option 1: Local PostgreSQL (Best for Development)

**macOS:**
```bash
# Install via Homebrew
brew install postgresql@15
brew services start postgresql@15

# Create database
createdb rag_pipeline

# Connection string:
# postgresql://localhost/rag_pipeline
```

**Ubuntu/Debian:**
```bash
# Install
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres createdb rag_pipeline
sudo -u postgres createuser rag_user --password

# Connection string:
# postgresql://rag_user:password@localhost/rag_pipeline
```

**Windows:**
1. Download installer: https://www.postgresql.org/download/windows/
2. Run installer (includes pgAdmin GUI tool)
3. Default connection: `postgresql://postgres:yourpassword@localhost/postgres`

---

### Option 2: Docker PostgreSQL (Easiest for Any OS)

**Best option for consistent local development across all platforms**

```bash
# Create docker-compose.yml file:
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: rag-postgres
    environment:
      POSTGRES_DB: rag_pipeline
      POSTGRES_USER: rag_user
      POSTGRES_PASSWORD: rag_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rag_user -d rag_pipeline"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

```bash
# Start PostgreSQL
docker-compose up -d

# Check status
docker-compose ps

# Stop PostgreSQL
docker-compose down

# Connection string:
# postgresql://rag_user:rag_password@localhost:5432/rag_pipeline
```

**Advantages:**
- ✓ Works identically on Mac, Windows, Linux
- ✓ Isolated from system
- ✓ Easy to reset/rebuild
- ✓ Matches production environment

---

### Option 3: Cloud PostgreSQL (Production-Ready)

#### **Supabase (Easiest, Free Tier)**

**Best for quick deployment with generous free tier**

1. Sign up: https://supabase.com/
2. Create new project (takes ~2 minutes)
3. Get connection string from Settings → Database

```python
# Connection string format:
# postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
```

**Free tier:**
- 500MB database
- Unlimited API requests
- Automatic backups
- Built-in auth & storage

**Pros:**
- ✓ Zero setup
- ✓ Generous free tier
- ✓ Web UI included
- ✓ Auto-scaling

**Cons:**
- ✗ 500MB limit on free tier
- ✗ Cold starts on free tier

---

#### **Neon (Best Developer Experience)**

**Serverless PostgreSQL with instant branching**

1. Sign up: https://neon.tech/
2. Create project (instant)
3. Copy connection string

```python
# Connection string:
# postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname
```

**Free tier:**
- 3GB storage
- Branches for testing
- Auto-pause (saves resources)

**Pros:**
- ✓ Instant setup
- ✓ Database branching (like git)
- ✓ Auto-scales to zero
- ✓ Fast cold starts

**Cons:**
- ✗ 3GB storage limit

---

#### **Railway (Simplest Deployment)**

**All-in-one platform with PostgreSQL + app hosting**

1. Sign up: https://railway.app/
2. New Project → Add PostgreSQL
3. Get connection string from Variables tab

**Free tier:**
- $5/month credit
- 1GB RAM
- PostgreSQL included

**Pros:**
- ✓ Deploy entire app + DB together
- ✓ Auto-deploy from GitHub
- ✓ Simple pricing

**Cons:**
- ✗ Credit-based (not truly free)
- ✗ Limited to $5/month on free tier

---

#### **AWS RDS (Production Scale)**

**For serious production workloads**

```bash
# Via AWS CLI
aws rds create-db-instance \
    --db-instance-identifier rag-pipeline-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username admin \
    --master-user-password yourpassword \
    --allocated-storage 20

# Connection string:
# postgresql://admin:password@rag-pipeline-db.xxx.rds.amazonaws.com:5432/postgres
```

**Free tier:**
- 750 hours/month (t3.micro)
- 20GB storage
- First 12 months

**Pros:**
- ✓ Enterprise-grade
- ✓ Auto-backups
- ✓ Multi-AZ replication
- ✓ Fully managed

**Cons:**
- ✗ Complex setup
- ✗ Expensive after free tier
- ✗ Overkill for small projects

---

### Recommended Path

**Development Journey:**

```
MVP 1-2: SQLite (built-in)
    ↓
MVP 3: SQLite or Docker PostgreSQL (test production setup)
    ↓
MVP 4: Supabase or Neon (easy cloud deployment)
    ↓
Production: Neon, Railway, or AWS RDS (based on scale)
```

**My Recommendation for Your Project:**

1. **MVP 1-3:** Stick with SQLite
   - Zero setup
   - Fast enough for 20k+ documents
   - Easy to migrate later

2. **MVP 4 (Initial Production):** Supabase
   - Free tier is generous
   - Dead simple signup
   - Good for testing with real users
   - Easy to upgrade

3. **Scale Up (If Needed):** Neon or Railway
   - If you hit Supabase limits
   - Better performance
   - Still simple to manage

---

### Migration Guide: SQLite → PostgreSQL

When you're ready to move from SQLite to PostgreSQL:

**Step 1: Export SQLite data**
```bash
sqlite3 data/metadata.db .dump > metadata_dump.sql
```

**Step 2: Clean up dump for PostgreSQL**
```bash
# Remove SQLite-specific commands
sed -i 's/AUTOINCREMENT/SERIAL/g' metadata_dump.sql
```

**Step 3: Import to PostgreSQL**
```bash
psql postgresql://user:pass@host/db < metadata_dump.sql
```

**Step 4: Update connection string in code**
```python
# Before (SQLite)
conn = sqlite3.connect('data/metadata.db')

# After (PostgreSQL)
import psycopg2
conn = psycopg2.connect('postgresql://user:pass@host/db')
```

**Or use SQLAlchemy for database-agnostic code:**
```python
from sqlalchemy import create_engine

# Works with both!
engine = create_engine('sqlite:///data/metadata.db')
# engine = create_engine('postgresql://user:pass@host/db')
```

---

### Quick Start: Supabase Setup (2 minutes)

```bash
# 1. Sign up at supabase.com
# 2. Create new project
# 3. Wait 2 minutes for provisioning
# 4. Go to Settings → Database
# 5. Copy "Connection string" under "Connection pooling"

# 6. Install Python client
pip install psycopg2-binary

# 7. Test connection
python -c "import psycopg2; conn = psycopg2.connect('your-connection-string'); print('Connected!')"
```

**Environment Variable Setup:**
```bash
# .env file
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres

# Load in Python
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv('DATABASE_URL')
```

---

## MVP 2: Metadata Extraction & Filtering

### Additional File Structure
```
rag-pipeline/
├── src/
│   ├── metadata_extractor.py    # NEW
│   ├── metadata_store.py         # NEW
│   └── enhanced_search.py        # NEW
├── tests/
│   └── test_metadata.py          # NEW
└── data/
    └── metadata.db               # NEW: SQLite database
```

### 2.1 Metadata Extractor

**File:** `src/metadata_extractor.py`

```python
"""
Extract structured metadata from documents using spaCy NER and regex
"""

import re
from typing import Dict, List, Set
from datetime import datetime
import spacy
from loguru import logger


class MetadataExtractor:
    """Extract entities and structured data from text"""
    
    def __init__(self):
        """Load spaCy model for NER"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.error("spaCy model not found. Run: python -m spacy download en_core_web_sm")
            raise
        
        # Compile regex patterns
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        # Date patterns (various formats)
        self.date_patterns = [
            re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),  # 2015-07-12
            re.compile(r'\b\d{1,2}/\d{1,2}/\d{4}\b'),  # 7/12/2015
            re.compile(r'\b\d{1,2}-\d{1,2}-\d{4}\b'),  # 7-12-2015
            re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'),  # July 12, 2015
        ]
        
    def extract_metadata(self, text: str, doc_id: str) -> Dict:
        """
        Extract all metadata from document
        
        Returns:
            {
                'doc_id': str,
                'people': List[str],
                'organizations': List[str],
                'locations': List[str],
                'dates': List[str],
                'emails': List[str],
                'phone_numbers': List[str],
                'word_count': int
            }
        """
        
        # Process with spaCy (limit to first 100k chars for speed)
        doc = self.nlp(text[:100000])
        
        # Extract named entities
        people = self._extract_people(doc)
        organizations = self._extract_organizations(doc)
        locations = self._extract_locations(doc)
        
        # Extract with regex
        dates = self._extract_dates(text)
        emails = self._extract_emails(text)
        
        # Basic statistics
        word_count = len([token for token in doc if not token.is_punct])
        
        metadata = {
            'doc_id': doc_id,
            'people': sorted(list(people)),
            'organizations': sorted(list(organizations)),
            'locations': sorted(list(locations)),
            'dates': sorted(list(dates)),
            'emails': sorted(list(emails)),
            'word_count': word_count
        }
        
        logger.debug(f"Extracted metadata for {doc_id}: "
                    f"{len(people)} people, {len(locations)} locations, "
                    f"{len(dates)} dates")
        
        return metadata
    
    def _extract_people(self, doc) -> Set[str]:
        """Extract PERSON entities"""
        people = set()
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                # Clean up name
                name = ent.text.strip()
                # Filter out single letters and common false positives
                if len(name) > 2 and not name.isupper():
                    people.add(name)
        return people
    
    def _extract_organizations(self, doc) -> Set[str]:
        """Extract ORG entities"""
        orgs = set()
        for ent in doc.ents:
            if ent.label_ == "ORG":
                org = ent.text.strip()
                if len(org) > 1:
                    orgs.add(org)
        return orgs
    
    def _extract_locations(self, doc) -> Set[str]:
        """Extract GPE (geo-political entity) and LOC entities"""
        locations = set()
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                loc = ent.text.strip()
                if len(loc) > 1:
                    locations.add(loc)
        return locations
    
    def _extract_dates(self, text: str) -> Set[str]:
        """Extract dates using regex patterns"""
        dates = set()
        for pattern in self.date_patterns:
            matches = pattern.findall(text)
            dates.update(matches)
        return dates
    
    def _extract_emails(self, text: str) -> Set[str]:
        """Extract email addresses"""
        emails = set(self.email_pattern.findall(text))
        return emails


# Usage Example
if __name__ == "__main__":
    extractor = MetadataExtractor()
    
    sample_text = """
    On July 15, 2015, Jeffrey Epstein met with Ghislaine Maxwell in Paris.
    The meeting was arranged via email at ghislaine@example.com.
    Representatives from the Clinton Foundation were also present.
    """
    
    metadata = extractor.extract_metadata(sample_text, "doc_001")
    
    print("People:", metadata['people'])
    print("Locations:", metadata['locations'])
    print("Dates:", metadata['dates'])
    print("Emails:", metadata['emails'])
```

### 2.2 Metadata Storage

**File:** `src/metadata_store.py`

```python
"""
Store and query metadata using SQLite
"""

import sqlite3
import json
from typing import List, Dict, Optional
from pathlib import Path
from loguru import logger


class MetadataStore:
    """SQLite-based metadata storage"""
    
    def __init__(self, db_path: str = "data/metadata.db"):
        """Initialize database connection"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts
        self._create_tables()
        
    def _create_tables(self):
        """Create database schema"""
        cursor = self.conn.cursor()
        
        # Main metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_metadata (
                doc_id TEXT PRIMARY KEY,
                word_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Entity tables (many-to-many relationships)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                name TEXT,
                FOREIGN KEY (doc_id) REFERENCES document_metadata(doc_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                name TEXT,
                FOREIGN KEY (doc_id) REFERENCES document_metadata(doc_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                name TEXT,
                FOREIGN KEY (doc_id) REFERENCES document_metadata(doc_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                date_str TEXT,
                FOREIGN KEY (doc_id) REFERENCES document_metadata(doc_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                email TEXT,
                FOREIGN KEY (doc_id) REFERENCES document_metadata(doc_id)
            )
        """)
        
        # Create indexes for fast lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_people_name ON people(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_name ON locations(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dates_str ON dates(date_str)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emails_email ON emails(email)")
        
        self.conn.commit()
        logger.info("Database schema initialized")
    
    def store_metadata(self, metadata: Dict):
        """Store metadata for a document"""
        cursor = self.conn.cursor()
        doc_id = metadata['doc_id']
        
        try:
            # Insert main metadata
            cursor.execute("""
                INSERT OR REPLACE INTO document_metadata (doc_id, word_count)
                VALUES (?, ?)
            """, (doc_id, metadata['word_count']))
            
            # Delete existing entities (for updates)
            for table in ['people', 'organizations', 'locations', 'dates', 'emails']:
                cursor.execute(f"DELETE FROM {table} WHERE doc_id = ?", (doc_id,))
            
            # Insert entities
            for person in metadata['people']:
                cursor.execute("INSERT INTO people (doc_id, name) VALUES (?, ?)",
                             (doc_id, person))
            
            for org in metadata['organizations']:
                cursor.execute("INSERT INTO organizations (doc_id, name) VALUES (?, ?)",
                             (doc_id, org))
            
            for loc in metadata['locations']:
                cursor.execute("INSERT INTO locations (doc_id, name) VALUES (?, ?)",
                             (doc_id, loc))
            
            for date in metadata['dates']:
                cursor.execute("INSERT INTO dates (doc_id, date_str) VALUES (?, ?)",
                             (doc_id, date))
            
            for email in metadata['emails']:
                cursor.execute("INSERT INTO emails (doc_id, email) VALUES (?, ?)",
                             (doc_id, email))
            
            self.conn.commit()
            logger.debug(f"Stored metadata for {doc_id}")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error storing metadata for {doc_id}: {e}")
            raise
    
    def filter_documents(self, 
                        doc_ids: List[str],
                        people: Optional[List[str]] = None,
                        locations: Optional[List[str]] = None,
                        date_range: Optional[tuple] = None) -> List[str]:
        """
        Filter document IDs by metadata criteria
        
        Args:
            doc_ids: Initial set of document IDs to filter
            people: List of person names to match (OR logic)
            locations: List of locations to match (OR logic)
            date_range: Tuple of (start_date, end_date) strings
            
        Returns:
            Filtered list of document IDs
        """
        if not doc_ids:
            return []
        
        # Start with initial set
        filtered_ids = set(doc_ids)
        cursor = self.conn.cursor()
        
        # Filter by people
        if people:
            placeholders = ','.join(['?'] * len(people))
            query = f"""
                SELECT DISTINCT doc_id FROM people 
                WHERE name IN ({placeholders})
                AND doc_id IN ({','.join(['?'] * len(filtered_ids))})
            """
            cursor.execute(query, people + list(filtered_ids))
            people_ids = {row['doc_id'] for row in cursor.fetchall()}
            filtered_ids &= people_ids
            logger.debug(f"After people filter: {len(filtered_ids)} docs")
        
        # Filter by locations
        if locations:
            placeholders = ','.join(['?'] * len(locations))
            query = f"""
                SELECT DISTINCT doc_id FROM locations 
                WHERE name IN ({placeholders})
                AND doc_id IN ({','.join(['?'] * len(filtered_ids))})
            """
            cursor.execute(query, locations + list(filtered_ids))
            loc_ids = {row['doc_id'] for row in cursor.fetchall()}
            filtered_ids &= loc_ids
            logger.debug(f"After location filter: {len(filtered_ids)} docs")
        
        # Filter by date range
        if date_range:
            start_date, end_date = date_range
            query = f"""
                SELECT DISTINCT doc_id FROM dates 
                WHERE date_str BETWEEN ? AND ?
                AND doc_id IN ({','.join(['?'] * len(filtered_ids))})
            """
            cursor.execute(query, [start_date, end_date] + list(filtered_ids))
            date_ids = {row['doc_id'] for row in cursor.fetchall()}
            filtered_ids &= date_ids
            logger.debug(f"After date filter: {len(filtered_ids)} docs")
        
        return list(filtered_ids)
    
    def get_metadata(self, doc_id: str) -> Optional[Dict]:
        """Retrieve metadata for a document"""
        cursor = self.conn.cursor()
        
        # Get main metadata
        cursor.execute("SELECT * FROM document_metadata WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        metadata = {
            'doc_id': doc_id,
            'word_count': row['word_count'],
            'people': [],
            'organizations': [],
            'locations': [],
            'dates': [],
            'emails': []
        }
        
        # Get entities
        cursor.execute("SELECT name FROM people WHERE doc_id = ?", (doc_id,))
        metadata['people'] = [row['name'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT name FROM organizations WHERE doc_id = ?", (doc_id,))
        metadata['organizations'] = [row['name'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT name FROM locations WHERE doc_id = ?", (doc_id,))
        metadata['locations'] = [row['name'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT date_str FROM dates WHERE doc_id = ?", (doc_id,))
        metadata['dates'] = [row['date_str'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT email FROM emails WHERE doc_id = ?", (doc_id,))
        metadata['emails'] = [row['email'] for row in cursor.fetchall()]
        
        return metadata
    
    def close(self):
        """Close database connection"""
        self.conn.close()
```

This covers the metadata storage implementation. The document continues with MVP 2 enhanced search, MVP 3 semantic search, and MVP 4 production deployment - would you like me to continue completing those sections?
        