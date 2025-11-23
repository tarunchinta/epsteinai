"""
Tests for fuzzy entity matching
"""

import pytest
from src.entity_matcher import EntityMatcher


class TestNameNormalization:
    """Test name normalization"""
    
    @pytest.fixture
    def matcher(self):
        """Create entity matcher instance"""
        return EntityMatcher()
    
    def test_remove_initials(self, matcher):
        """Should remove single letter initials"""
        assert matcher.normalize_name("G. Maxwell") == "maxwell"
        assert matcher.normalize_name("J. Epstein") == "epstein"
        assert matcher.normalize_name("A. B. Smith") == "smith"
    
    def test_remove_prefixes(self, matcher):
        """Should remove common prefixes"""
        assert matcher.normalize_name("The Clinton Foundation") == "clinton foundation"
        assert matcher.normalize_name("Mr. Jeffrey Epstein") == "jeffrey epstein"
        assert matcher.normalize_name("Dr. Smith") == "smith"
        assert matcher.normalize_name("Ms. Maxwell") == "maxwell"
    
    def test_lowercase_conversion(self, matcher):
        """Should convert to lowercase"""
        assert matcher.normalize_name("Jeffrey EPSTEIN") == "jeffrey epstein"
        assert matcher.normalize_name("MAXWELL") == "maxwell"
    
    def test_whitespace_normalization(self, matcher):
        """Should normalize whitespace"""
        assert matcher.normalize_name("Jeffrey   Epstein") == "jeffrey epstein"
        assert matcher.normalize_name("  Maxwell  ") == "maxwell"


class TestFuzzyMatching:
    """Test fuzzy matching logic"""
    
    @pytest.fixture
    def matcher(self):
        """Create entity matcher instance"""
        return EntityMatcher(similarity_threshold=0.85)
    
    def test_exact_match_after_normalization(self, matcher):
        """Should match if exact after normalization"""
        assert matcher.fuzzy_match("G. Maxwell", "Maxwell")
        assert matcher.fuzzy_match("The Clinton Foundation", "Clinton Foundation")
        assert matcher.fuzzy_match("Dr. Epstein", "epstein")
    
    def test_substring_match(self, matcher):
        """Should match if one is substring of other"""
        assert matcher.fuzzy_match("Maxwell", "Ghislaine Maxwell")
        assert matcher.fuzzy_match("Ghislaine Maxwell", "Maxwell")
        assert matcher.fuzzy_match("Epstein", "Jeffrey Epstein")
        assert matcher.fuzzy_match("Clinton", "Clinton Foundation")
    
    def test_fuzzy_similarity_match(self, matcher):
        """Should match similar strings"""
        # High similarity
        assert matcher.fuzzy_match("Jeffrey Epstein", "Jeffrey Epstien")  # Typo
        assert matcher.fuzzy_match("Ghislaine", "Ghislane")  # Typo
    
    def test_no_match_different_names(self, matcher):
        """Should not match completely different names"""
        assert not matcher.fuzzy_match("Maxwell", "Einstein")
        assert not matcher.fuzzy_match("Clinton", "Trump")
        assert not matcher.fuzzy_match("Paris", "London")
    
    def test_case_insensitive(self, matcher):
        """Should be case insensitive"""
        assert matcher.fuzzy_match("maxwell", "MAXWELL")
        assert matcher.fuzzy_match("Paris", "paris")


class TestMatchAny:
    """Test match_any function"""
    
    @pytest.fixture
    def matcher(self):
        """Create entity matcher instance"""
        return EntityMatcher()
    
    def test_match_any_found(self, matcher):
        """Should return True if any entity matches"""
        query_entities = ["Maxwell", "Epstein"]
        doc_entities = ["Ghislaine Maxwell", "Bill Clinton", "Paris"]
        
        assert matcher.match_any(query_entities, doc_entities)
    
    def test_match_any_not_found(self, matcher):
        """Should return False if no entity matches"""
        query_entities = ["Maxwell", "Epstein"]
        doc_entities = ["Bill Clinton", "Donald Trump", "Paris"]
        
        assert not matcher.match_any(query_entities, doc_entities)
    
    def test_match_any_empty_lists(self, matcher):
        """Should handle empty lists"""
        assert not matcher.match_any([], ["Maxwell"])
        assert not matcher.match_any(["Maxwell"], [])
        assert not matcher.match_any([], [])


class TestMatchScore:
    """Test match_score function"""
    
    @pytest.fixture
    def matcher(self):
        """Create entity matcher instance"""
        return EntityMatcher()
    
    def test_perfect_score(self, matcher):
        """Should return 1.0 for all matches"""
        query_entities = ["Maxwell", "Paris"]
        doc_entities = ["Ghislaine Maxwell", "Paris", "New York"]
        
        score = matcher.match_score(query_entities, doc_entities)
        assert score == 1.0
    
    def test_partial_score(self, matcher):
        """Should return partial score for some matches"""
        query_entities = ["Maxwell", "Paris", "London"]
        doc_entities = ["Ghislaine Maxwell", "Paris", "New York"]
        
        score = matcher.match_score(query_entities, doc_entities)
        assert score == pytest.approx(2/3, abs=0.01)  # 2 out of 3 match
    
    def test_zero_score(self, matcher):
        """Should return 0.0 for no matches"""
        query_entities = ["Maxwell", "Paris"]
        doc_entities = ["Clinton", "Trump", "New York"]
        
        score = matcher.match_score(query_entities, doc_entities)
        assert score == 0.0
    
    def test_empty_query_entities(self, matcher):
        """Should return 0.0 for empty query entities"""
        score = matcher.match_score([], ["Maxwell", "Paris"])
        assert score == 0.0


class TestGetBestMatch:
    """Test get_best_match function"""
    
    @pytest.fixture
    def matcher(self):
        """Create entity matcher instance"""
        return EntityMatcher()
    
    def test_find_best_match(self, matcher):
        """Should find the best matching entity"""
        query = "Maxwell"
        candidates = ["Bill Clinton", "Ghislaine Maxwell", "G. Maxwell", "Einstein"]
        
        best_match, score = matcher.get_best_match(query, candidates)
        
        # Should find exact match or substring match
        assert best_match in ["Ghislaine Maxwell", "G. Maxwell"]
        assert score >= 0.85
    
    def test_no_match_below_threshold(self, matcher):
        """Should return None if no match above threshold"""
        query = "Maxwell"
        candidates = ["Clinton", "Trump", "Biden"]
        
        best_match, score = matcher.get_best_match(query, candidates)
        
        assert best_match is None
        assert score == 0.0
    
    def test_exact_match_highest_score(self, matcher):
        """Exact match should have highest score"""
        query = "Paris"
        candidates = ["Paris", "Parris", "Pari"]
        
        best_match, score = matcher.get_best_match(query, candidates)
        
        assert best_match == "Paris"
        assert score >= 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

