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
        
        # Validation patterns for entity quality filtering
        self.invalid_patterns = [
            # JSON/HTML/XML
            r'[{}\[\]<>]',                      # JSON/HTML brackets
            r'&[a-z]+;',                        # HTML entities (&lt;, &gt;, &nbsp;, etc.)
            r'</?\w+',                          # HTML tags
            r'href=|target=|class=|style=',     # HTML attributes
            
            # Dates and times (extracted separately)
            r'^\d{2}-\d{2}-\d{4}',              # Dates
            r'^\d{4}-\d{2}-\d{2}',              # ISO dates
            r'^\w{3}$',                         # 3-letter words (Mon, Tue, Fri, etc.)
            
            # Special characters
            r'^[%&@#$]+',                       # Special char prefixes
            r'^\d+\s*$',                        # Pure numbers
            r'[|\\~`]',                         # Pipes, backslash, tilde, backtick
            
            # Email-related
            r'@\w+\.(com|org|net|edu)',         # Email addresses
            r'mailto:',                         # Email protocol
            r'\[mailto:',                       # Email in brackets
            
            # Email headers
            r'^(Sender|Subject|From|To):',      # Email header keywords
            r'\b(Sent|Unauthorized)$',          # Email suffixes
            
            # Programming/Technical artifacts
            r'textStyle|layout|identifier',     # JSON keys
            r'HASH\(0x',                        # Perl hash references
            r'Default\w+Name',                  # Default object names
            
            # Encoding issues
            r'=\d{2}',                          # Encoded chars (=20, =3D)
            r'3D""',                            # Encoded quotes
            r'Â©|â€™',                          # Bad Unicode encoding
            
            # URLs
            r'https?://',                       # URLs
            r'www\.',                           # Web addresses
        ]
        
        # Exact words to reject (case-insensitive)
        self.reject_exact_words = {
            'sender', 'subject', 'from', 'to', 'sent', 'unauthorized',
            'fri', 'mon', 'tue', 'wed', 'thu', 'sat', 'sun',  # Days
            'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',  # Months
            'twitter', 'facebook', 'instagram',  # Social media (not people)
            'brexit',  # Events, not people
        }
        
        # Minimum quality thresholds
        self.min_name_length = 3
        self.max_name_length = 100
        
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
    
    def _is_valid_entity(self, entity_text: str, entity_type: str) -> bool:
        """
        Validate extracted entity quality
        
        NOTE: This method filters already-extracted entities from spaCy NER.
        It does NOT re-run entity extraction on the original document text.
        Use this to clean noisy entities after extraction.
        
        Args:
            entity_text: The extracted entity string (from spaCy)
            entity_type: Type (PERSON, ORG, GPE, LOC)
            
        Returns:
            True if entity passes quality checks
        """
        text = entity_text.strip()
        
        # Length checks
        if len(text) < self.min_name_length:
            return False
        if len(text) > self.max_name_length:
            return False
        
        # Check exact reject words (case-insensitive)
        if text.lower() in self.reject_exact_words:
            return False
        
        # Invalid pattern checks
        for pattern in self.invalid_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # Type-specific validation
        if entity_type == "PERSON":
            # Person names shouldn't be all caps (likely acronyms/codes)
            if text.isupper() and len(text) > 5:
                return False
            # Should contain at least one letter
            if not any(c.isalpha() for c in text):
                return False
            # Common false positives
            if text.lower() in ['the', 'and', 'page', 'chapter', 'section']:
                return False
        
        elif entity_type in ["GPE", "LOC"]:
            # Locations shouldn't start with special chars
            if text[0] in ['&', '%', '#', '@']:
                return False
            # Likely noise if contains multiple special chars
            if sum(1 for c in text if not c.isalnum() and c not in [' ', '-', '.']) > 2:
                return False
        
        elif entity_type == "ORG":
            # Organizations with excessive special chars are likely noise
            special_char_ratio = sum(1 for c in text if not c.isalnum() and c != ' ') / len(text)
            if special_char_ratio > 0.3:
                return False
        
        return True
    
    def _extract_people(self, doc) -> Set[str]:
        """
        Extract PERSON entities with validation
        
        Flow: spaCy extracts → validation filters → clean entities returned
        (No re-extraction, just filtering what spaCy already found)
        """
        people = set()
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text.strip()
                if self._is_valid_entity(name, "PERSON"):
                    people.add(name)
        return people
    
    def _extract_organizations(self, doc) -> Set[str]:
        """Extract ORG entities with validation"""
        orgs = set()
        for ent in doc.ents:
            if ent.label_ == "ORG":
                org = ent.text.strip()
                if self._is_valid_entity(org, "ORG"):
                    orgs.add(org)
        return orgs
    
    def _extract_locations(self, doc) -> Set[str]:
        """Extract GPE and LOC entities with validation"""
        locations = set()
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                loc = ent.text.strip()
                if self._is_valid_entity(loc, ent.label_):
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
    print("Organizations:", metadata['organizations'])

