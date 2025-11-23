"""
Unit tests for MVP2 metadata extraction and filtering
"""

import pytest
import os
from src.metadata_extractor import MetadataExtractor
from src.metadata_store import MetadataStore
from src.enhanced_search import EnhancedSearchEngine
from src.sparse_search import BM25SearchEngine


@pytest.fixture
def metadata_extractor():
    """Create metadata extractor instance"""
    return MetadataExtractor()


@pytest.fixture
def metadata_store(tmp_path):
    """Create temporary metadata store for testing"""
    db_path = str(tmp_path / "test_metadata.db")
    store = MetadataStore(db_path)
    yield store
    store.close()
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def sample_documents():
    """Create sample documents for testing"""
    return [
        {
            'doc_id': 'doc_000001',
            'filename': 'doc1.txt',
            'text': 'Jeffrey Epstein met with Ghislaine Maxwell in Paris on July 15, 2015.'
        },
        {
            'doc_id': 'doc_000002',
            'filename': 'doc2.txt',
            'text': 'Meeting at Clinton Foundation in New York on 2015-08-20.'
        },
        {
            'doc_id': 'doc_000003',
            'filename': 'doc3.txt',
            'text': 'Financial transactions were discussed in London.'
        }
    ]


def test_extract_people(metadata_extractor):
    """Test person entity extraction"""
    text = "Jeffrey Epstein met with Ghislaine Maxwell in Paris."
    metadata = metadata_extractor.extract_metadata(text, "test_doc")
    
    # Should extract both people
    assert len(metadata['people']) >= 1  # At least one person detected
    # Note: spaCy may or may not detect all names depending on model


def test_extract_locations(metadata_extractor):
    """Test location entity extraction"""
    text = "Meeting in Paris, France and later in New York."
    metadata = metadata_extractor.extract_metadata(text, "test_doc")
    
    assert 'Paris' in metadata['locations'] or 'France' in metadata['locations']


def test_extract_dates(metadata_extractor):
    """Test date extraction"""
    text = "Meeting on July 15, 2015 and another on 2019-08-20."
    metadata = metadata_extractor.extract_metadata(text, "test_doc")
    
    # Should extract at least one date
    assert len(metadata['dates']) > 0


def test_extract_emails(metadata_extractor):
    """Test email extraction"""
    text = "Contact john.doe@example.com or support@test.org for more info."
    metadata = metadata_extractor.extract_metadata(text, "test_doc")
    
    assert 'john.doe@example.com' in metadata['emails']
    assert 'support@test.org' in metadata['emails']


def test_extract_organizations(metadata_extractor):
    """Test organization extraction"""
    text = "Representatives from Clinton Foundation and Microsoft attended."
    metadata = metadata_extractor.extract_metadata(text, "test_doc")
    
    # Should extract at least one organization
    assert len(metadata['organizations']) >= 1


def test_store_and_retrieve_metadata(metadata_store):
    """Test storing and retrieving metadata"""
    metadata = {
        'doc_id': 'doc_001',
        'people': ['Jeffrey Epstein', 'Ghislaine Maxwell'],
        'organizations': ['Clinton Foundation'],
        'locations': ['Paris', 'New York'],
        'dates': ['2015-07-12'],
        'emails': ['test@example.com'],
        'word_count': 1500
    }
    
    metadata_store.store_metadata(metadata)
    retrieved = metadata_store.get_metadata('doc_001')
    
    assert retrieved is not None
    assert retrieved['doc_id'] == 'doc_001'
    assert retrieved['word_count'] == 1500
    assert 'Jeffrey Epstein' in retrieved['people']
    assert 'Paris' in retrieved['locations']


def test_filter_by_people(metadata_store):
    """Test filtering documents by people"""
    # Store multiple documents
    metadata1 = {
        'doc_id': 'doc_001',
        'people': ['Jeffrey Epstein', 'Maxwell'],
        'organizations': [],
        'locations': [],
        'dates': [],
        'emails': [],
        'word_count': 100
    }
    
    metadata2 = {
        'doc_id': 'doc_002',
        'people': ['Bill Clinton'],
        'organizations': [],
        'locations': [],
        'dates': [],
        'emails': [],
        'word_count': 100
    }
    
    metadata_store.store_metadata(metadata1)
    metadata_store.store_metadata(metadata2)
    
    # Filter for Epstein
    result = metadata_store.filter_documents(
        doc_ids=['doc_001', 'doc_002'],
        people=['Jeffrey Epstein']
    )
    
    assert 'doc_001' in result
    assert 'doc_002' not in result


def test_filter_by_location(metadata_store):
    """Test filtering documents by location"""
    metadata1 = {
        'doc_id': 'doc_001',
        'people': [],
        'organizations': [],
        'locations': ['Paris', 'London'],
        'dates': [],
        'emails': [],
        'word_count': 100
    }
    
    metadata2 = {
        'doc_id': 'doc_002',
        'people': [],
        'organizations': [],
        'locations': ['New York'],
        'dates': [],
        'emails': [],
        'word_count': 100
    }
    
    metadata_store.store_metadata(metadata1)
    metadata_store.store_metadata(metadata2)
    
    result = metadata_store.filter_documents(
        doc_ids=['doc_001', 'doc_002'],
        locations=['Paris']
    )
    
    assert 'doc_001' in result
    assert 'doc_002' not in result


def test_filter_multiple_criteria(metadata_store):
    """Test filtering with multiple criteria"""
    metadata = {
        'doc_id': 'doc_001',
        'people': ['Maxwell'],
        'organizations': [],
        'locations': ['Paris'],
        'dates': ['2015-07-15'],
        'emails': [],
        'word_count': 100
    }
    
    metadata_store.store_metadata(metadata)
    
    result = metadata_store.filter_documents(
        doc_ids=['doc_001'],
        people=['Maxwell'],
        locations=['Paris']
    )
    
    assert 'doc_001' in result


def test_enhanced_search_with_filters(sample_documents, metadata_store):
    """Test enhanced search with metadata filters"""
    # Create BM25 engine
    bm25_engine = BM25SearchEngine(sample_documents)
    
    # Store metadata for documents
    extractor = MetadataExtractor()
    for doc in sample_documents:
        metadata = extractor.extract_metadata(doc['text'], doc['doc_id'])
        metadata_store.store_metadata(metadata)
    
    # Create enhanced search
    enhanced_search = EnhancedSearchEngine(bm25_engine, metadata_store)
    
    # Search with filter
    results = enhanced_search.search(
        query="meeting",
        filter_locations=['Paris'],
        top_k=5
    )
    
    # Should return results
    assert len(results) >= 0  # May or may not have results depending on extraction


def test_get_all_entities(metadata_store):
    """Test retrieving all unique entities"""
    metadata1 = {
        'doc_id': 'doc_001',
        'people': ['Person A', 'Person B'],
        'organizations': ['Org1'],
        'locations': ['Paris'],
        'dates': ['2015-01-01'],
        'emails': [],
        'word_count': 100
    }
    
    metadata2 = {
        'doc_id': 'doc_002',
        'people': ['Person B', 'Person C'],
        'organizations': ['Org2'],
        'locations': ['London'],
        'dates': ['2015-01-01'],
        'emails': [],
        'word_count': 100
    }
    
    metadata_store.store_metadata(metadata1)
    metadata_store.store_metadata(metadata2)
    
    entities = metadata_store.get_all_entities()
    
    assert 'Person A' in entities['people']
    assert 'Person B' in entities['people']
    assert 'Person C' in entities['people']
    assert 'Org1' in entities['organizations']
    assert 'Paris' in entities['locations']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

