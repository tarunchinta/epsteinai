"""
Tests for entity validation and quality filtering
"""

import pytest
from src.metadata_extractor import MetadataExtractor


class TestEntityValidation:
    """Test entity quality validation"""
    
    @pytest.fixture
    def extractor(self):
        """Create metadata extractor instance"""
        return MetadataExtractor()
    
    def test_reject_noisy_locations(self, extractor):
        """Should reject noisy location entities"""
        # Special characters
        assert not extractor._is_valid_entity('%%', 'LOC')
        assert not extractor._is_valid_entity('& Alcorta', 'LOC')
        assert not extractor._is_valid_entity('#Section', 'GPE')
        
        # Page references
        assert not extractor._is_valid_entity('Page 33', 'LOC')
    
    def test_reject_noisy_people(self, extractor):
        """Should reject noisy person entities"""
        # JSON fragments
        assert not extractor._is_valid_entity('","textStyle":"bodyTextStyle', 'PERSON')
        
        # Dates (should be extracted separately)
        assert not extractor._is_valid_entity('06-04-2007', 'PERSON')
        
        # All caps (likely acronyms)
        assert not extractor._is_valid_entity('ALLLCAPSNAME', 'PERSON')
        
        # Common false positives
        assert not extractor._is_valid_entity('The', 'PERSON')
        assert not extractor._is_valid_entity('and', 'PERSON')
        assert not extractor._is_valid_entity('page', 'PERSON')
    
    def test_reject_noisy_organizations(self, extractor):
        """Should reject noisy organization entities"""
        # Too many special characters
        assert not extractor._is_valid_entity('Dai-ichi!!!Life@@@', 'ORG')
        
        # JSON keys
        assert not extractor._is_valid_entity('textStyle', 'ORG')
        assert not extractor._is_valid_entity('identifier', 'ORG')
    
    def test_accept_valid_entities(self, extractor):
        """Should accept valid entities"""
        # People
        assert extractor._is_valid_entity('Jeffrey Epstein', 'PERSON')
        assert extractor._is_valid_entity('G. Maxwell', 'PERSON')
        assert extractor._is_valid_entity('Bill Clinton', 'PERSON')
        
        # Locations
        assert extractor._is_valid_entity('Paris', 'GPE')
        assert extractor._is_valid_entity('New York', 'GPE')
        assert extractor._is_valid_entity('Little St. James', 'LOC')
        
        # Organizations
        assert extractor._is_valid_entity('Clinton Foundation', 'ORG')
        assert extractor._is_valid_entity('FBI', 'ORG')
        assert extractor._is_valid_entity('U.S. Department of Justice', 'ORG')
    
    def test_length_validation(self, extractor):
        """Should validate entity length"""
        # Too short
        assert not extractor._is_valid_entity('ab', 'PERSON')
        assert not extractor._is_valid_entity('a', 'LOC')
        
        # Too long (> 100 chars)
        long_name = 'a' * 101
        assert not extractor._is_valid_entity(long_name, 'PERSON')
        
        # Just right
        assert extractor._is_valid_entity('abc', 'PERSON')
        assert extractor._is_valid_entity('a' * 50, 'PERSON')
    
    def test_json_bracket_rejection(self, extractor):
        """Should reject entities with JSON/HTML brackets"""
        assert not extractor._is_valid_entity('{"name":"test"}', 'PERSON')
        assert not extractor._is_valid_entity('[Array]', 'ORG')
        assert not extractor._is_valid_entity('<div>', 'LOC')
    
    def test_pure_number_rejection(self, extractor):
        """Should reject pure numbers"""
        assert not extractor._is_valid_entity('12345', 'PERSON')
        assert not extractor._is_valid_entity('999', 'ORG')
    
    def test_person_must_contain_letter(self, extractor):
        """Person names should contain at least one letter"""
        assert not extractor._is_valid_entity('123-456', 'PERSON')
        assert extractor._is_valid_entity('John123', 'PERSON')


class TestEntityExtraction:
    """Test entity extraction with validation"""
    
    @pytest.fixture
    def extractor(self):
        """Create metadata extractor instance"""
        return MetadataExtractor()
    
    def test_extract_clean_people(self, extractor):
        """Should extract only clean person entities"""
        text = """
        Jeffrey Epstein and Ghislaine Maxwell met in Paris.
        ","textStyle":"bodyTextStyle
        Page 33
        """
        
        metadata = extractor.extract_metadata(text, "test_doc")
        
        # Should include valid people
        assert 'Jeffrey Epstein' in metadata['people']
        assert 'Ghislaine Maxwell' in metadata['people']
        
        # Should not include noise
        assert '","textStyle":"bodyTextStyle' not in metadata['people']
        assert 'Page 33' not in metadata['people']
    
    def test_extract_clean_locations(self, extractor):
        """Should extract only clean location entities"""
        text = """
        The meeting was in Paris and New York.
        %%
        & Alcorta
        """
        
        metadata = extractor.extract_metadata(text, "test_doc")
        
        # Should include valid locations
        assert 'Paris' in metadata['locations']
        assert 'New York' in metadata['locations']
        
        # Should not include noise
        assert '%%' not in metadata['locations']
        assert '& Alcorta' not in metadata['locations']
    
    def test_extract_clean_organizations(self, extractor):
        """Should extract only clean organization entities"""
        text = """
        Representatives from Clinton Foundation and FBI attended.
        textStyle
        identifier
        """
        
        metadata = extractor.extract_metadata(text, "test_doc")
        
        # Should include valid organizations
        assert 'Clinton Foundation' in metadata['organizations']
        
        # Should not include noise
        assert 'textStyle' not in metadata['organizations']
        assert 'identifier' not in metadata['organizations']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

