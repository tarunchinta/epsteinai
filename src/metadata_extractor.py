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
    print("Organizations:", metadata['organizations'])

