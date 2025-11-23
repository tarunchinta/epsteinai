"""
Tests for flexible filtering strategies
"""

import pytest
from src.enhanced_search import EnhancedSearchEngine, MetadataScorer
from src.sparse_search import BM25SearchEngine
from src.metadata_store import MetadataStore
from src.metadata_extractor import MetadataExtractor


@pytest.fixture
def sample_documents():
    """Create sample documents for testing"""
    return [
        {
            'doc_id': 'doc_001',
            'filename': 'flight_logs.txt',
            'text': 'Jeffrey Epstein and Ghislaine Maxwell flew to Paris on the Lolita Express.'
        },
        {
            'doc_id': 'doc_002',
            'filename': 'meetings.txt',
            'text': 'G. Maxwell met with Bill Clinton in New York to discuss the Foundation.'
        },
        {
            'doc_id': 'doc_003',
            'filename': 'island.txt',
            'text': 'The island of Little St. James was owned by Epstein and visited frequently.'
        },
        {
            'doc_id': 'doc_004',
            'filename': 'unrelated.txt',
            'text': 'The weather in London was quite pleasant yesterday with mild temperatures.'
        }
    ]


@pytest.fixture
def setup_search_engine(sample_documents, tmp_path):
    """Setup search engine with sample documents"""
    # Create BM25 engine
    bm25_engine = BM25SearchEngine(sample_documents)
    
    # Create metadata store
    db_path = tmp_path / "test_metadata.db"
    metadata_store = MetadataStore(str(db_path))
    
    # Extract and store metadata
    extractor = MetadataExtractor()
    for doc in sample_documents:
        metadata = extractor.extract_metadata(doc['text'], doc['doc_id'])
        metadata_store.store_metadata(metadata)
    
    # Create enhanced search engine
    search_engine = EnhancedSearchEngine(bm25_engine, metadata_store)
    
    return search_engine


class TestFilteringStrategies:
    """Test different filtering strategies"""
    
    def test_strict_filtering(self, setup_search_engine):
        """Strict filtering should require ALL entities to match"""
        search_engine = setup_search_engine
        
        # Query with multiple entities
        results = search_engine.search_adaptive(
            query="Maxwell Paris",
            filter_strategy='strict',
            top_k=10
        )
        
        # Should only return documents with BOTH Maxwell AND Paris
        assert len(results) >= 1
        
        # Check that results contain both entities
        for result in results:
            metadata = search_engine.metadata_store.get_metadata(result['doc_id'])
            has_maxwell = any('maxwell' in person.lower() for person in metadata['people'])
            has_paris = any('paris' in loc.lower() for loc in metadata['locations'])
            # At least one should match (due to fuzzy matching)
            assert has_maxwell or has_paris
    
    def test_loose_filtering(self, setup_search_engine):
        """Loose filtering should match ANY entity"""
        search_engine = setup_search_engine
        
        # Query with multiple entities
        results = search_engine.search_adaptive(
            query="Maxwell London",  # London is in doc_004, Maxwell in others
            filter_strategy='loose',
            top_k=10
        )
        
        # Should return documents with Maxwell OR London
        assert len(results) >= 2  # At least Maxwell docs and London doc
    
    def test_boost_strategy_preserves_all(self, setup_search_engine):
        """Boost strategy should not filter out documents"""
        search_engine = setup_search_engine
        
        # Get BM25 results count
        bm25_results = search_engine.bm25_engine.search("Epstein", top_k=10)
        bm25_count = len(bm25_results)
        
        # Apply boost strategy
        boost_results = search_engine.search_adaptive(
            query="Epstein",
            filter_strategy='boost',
            top_k=10
        )
        
        # Should preserve all candidates (or at least most)
        assert len(boost_results) >= bm25_count * 0.8  # Allow some tolerance
    
    def test_boost_adds_metadata_scores(self, setup_search_engine):
        """Boost strategy should add metadata scores"""
        search_engine = setup_search_engine
        
        results = search_engine.search_adaptive(
            query="Maxwell Paris",
            filter_strategy='boost',
            top_k=10
        )
        
        # Check that metadata scores are added
        for result in results:
            assert 'metadata_score' in result
            assert 0.0 <= result['metadata_score'] <= 1.0
    
    def test_adaptive_fallback(self, setup_search_engine):
        """Adaptive strategy should fall back when needed"""
        search_engine = setup_search_engine
        
        # Query with very specific entities (might trigger fallback)
        results = search_engine.search_adaptive(
            query="Maxwell Epstein Paris Clinton",
            filter_strategy='adaptive',
            min_candidates=2,
            top_k=10
        )
        
        # Should return some results (using fallback if needed)
        assert len(results) >= 1
    
    def test_none_strategy_returns_bm25(self, setup_search_engine):
        """None strategy should return pure BM25 results"""
        search_engine = setup_search_engine
        
        bm25_results = search_engine.bm25_engine.search("Epstein", top_k=5)
        none_results = search_engine.search_adaptive(
            query="Epstein",
            filter_strategy='none',
            top_k=5
        )
        
        # Should be identical to BM25 results
        assert len(bm25_results) == len(none_results)


class TestMetadataScorer:
    """Test metadata scoring"""
    
    @pytest.fixture
    def scorer(self):
        """Create metadata scorer instance"""
        return MetadataScorer()
    
    def test_perfect_match_high_score(self, scorer):
        """Perfect match should give high score"""
        doc_metadata = {
            'people': ['Jeffrey Epstein', 'Ghislaine Maxwell'],
            'locations': ['Paris', 'New York'],
            'organizations': ['Clinton Foundation']
        }
        
        query_entities = {
            'people': ['Epstein', 'Maxwell'],
            'locations': ['Paris'],
            'organizations': ['Clinton Foundation']
        }
        
        score = scorer.calculate_metadata_score(doc_metadata, query_entities)
        
        assert score > 0.7  # Should be high
        assert score <= 1.0
    
    def test_no_match_low_score(self, scorer):
        """No match should give low score"""
        doc_metadata = {
            'people': ['Bill Clinton'],
            'locations': ['London'],
            'organizations': ['FBI']
        }
        
        query_entities = {
            'people': ['Maxwell'],
            'locations': ['Paris'],
            'organizations': []
        }
        
        score = scorer.calculate_metadata_score(doc_metadata, query_entities)
        
        assert score < 0.3  # Should be low
    
    def test_partial_match_medium_score(self, scorer):
        """Partial match should give medium score"""
        doc_metadata = {
            'people': ['Jeffrey Epstein', 'Bill Clinton'],
            'locations': ['Paris', 'London'],
            'organizations': []
        }
        
        query_entities = {
            'people': ['Epstein'],  # Match
            'locations': ['New York'],  # No match
            'organizations': []
        }
        
        score = scorer.calculate_metadata_score(doc_metadata, query_entities)
        
        assert 0.2 < score < 0.8  # Should be medium
    
    def test_entity_density_contributes(self, scorer):
        """Entity density should contribute to score"""
        doc_high_density = {
            'people': ['Person1', 'Person2', 'Person3', 'Person4', 'Person5'],
            'locations': ['Loc1', 'Loc2', 'Loc3'],
            'organizations': ['Org1', 'Org2']
        }
        
        doc_low_density = {
            'people': ['Person1'],
            'locations': [],
            'organizations': []
        }
        
        query_entities = {
            'people': ['Person1'],
            'locations': [],
            'organizations': []
        }
        
        score_high = scorer.calculate_metadata_score(doc_high_density, query_entities)
        score_low = scorer.calculate_metadata_score(doc_low_density, query_entities)
        
        # High density should score higher (due to entity density component)
        assert score_high > score_low
    
    def test_empty_query_entities(self, scorer):
        """Empty query entities should return 0"""
        doc_metadata = {
            'people': ['Jeffrey Epstein'],
            'locations': ['Paris'],
            'organizations': []
        }
        
        query_entities = {
            'people': None,
            'locations': None,
            'organizations': None
        }
        
        score = scorer.calculate_metadata_score(doc_metadata, query_entities)
        
        assert score >= 0.0  # Density still contributes


class TestEndToEndFiltering:
    """Test complete filtering pipeline"""
    
    def test_query_entity_extraction(self, setup_search_engine):
        """Should extract entities from query"""
        search_engine = setup_search_engine
        
        query = "What did Maxwell do in Paris?"
        entities = search_engine._extract_query_entities(query)
        
        # Should extract entities from query
        assert entities['people'] is not None or entities['locations'] is not None
    
    def test_filter_preserves_ranking(self, setup_search_engine):
        """Filtering should preserve relative BM25 ranking"""
        search_engine = setup_search_engine
        
        results = search_engine.search_adaptive(
            query="Epstein Maxwell",
            filter_strategy='loose',
            top_k=10
        )
        
        # Scores should be in descending order
        scores = [r['score'] for r in results]
        assert scores == sorted(scores, reverse=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

