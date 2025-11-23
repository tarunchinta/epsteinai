"""
Unit tests for MVP1 components
"""

import pytest
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
    docs = [{'doc_id': 'doc1', 'filename': 'test.txt', 'text': 'Sample text'}]
    engine = BM25SearchEngine(docs)
    
    results = engine.search("nonexistent query terms xyz", top_k=5)
    assert len(results) == 0


def test_preview_extraction():
    """Test text preview extraction"""
    processor = TextProcessor()
    
    long_text = "A" * 300
    preview = processor.extract_preview(long_text, max_length=200)
    
    assert len(preview) <= 203  # 200 + "..."
    assert preview.endswith("...")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

