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

