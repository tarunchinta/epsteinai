"""
Fuzzy entity matching for flexible metadata filtering
"""

from typing import List
import re
from difflib import SequenceMatcher


class EntityMatcher:
    """Match entities with fuzzy logic and normalization"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize entity matcher
        
        Args:
            similarity_threshold: Minimum similarity score (0-1) for fuzzy match
        """
        self.similarity_threshold = similarity_threshold
    
    def normalize_name(self, name: str) -> str:
        """
        Normalize entity name for comparison
        
        Examples:
            "G. Maxwell" → "maxwell"
            "Ghislaine Maxwell" → "ghislaine maxwell"
            "The Clinton Foundation" → "clinton foundation"
        
        Args:
            name: Entity name to normalize
            
        Returns:
            Normalized name (lowercase, no prefixes, no initials)
        """
        # Lowercase
        normalized = name.lower()
        
        # Remove common prefixes
        prefixes = ['the ', 'mr. ', 'ms. ', 'mrs. ', 'dr. ', 'prof. ']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
        
        # Remove single letter initials and dots
        normalized = re.sub(r'\b[a-z]\.\s*', '', normalized)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def fuzzy_match(self, query_entity: str, doc_entity: str) -> bool:
        """
        Check if two entities match with fuzzy logic
        
        Matching strategies (in order):
        1. Exact match after normalization
        2. Substring match (one contains the other)
        3. Fuzzy similarity match (SequenceMatcher)
        
        Args:
            query_entity: Entity from user query
            doc_entity: Entity from document metadata
            
        Returns:
            True if entities match (exact, substring, or fuzzy)
        """
        # Normalize both
        query_norm = self.normalize_name(query_entity)
        doc_norm = self.normalize_name(doc_entity)
        
        # Exact match after normalization
        if query_norm == doc_norm:
            return True
        
        # Substring match (one contains the other)
        if query_norm in doc_norm or doc_norm in query_norm:
            return True
        
        # Fuzzy similarity match
        similarity = SequenceMatcher(None, query_norm, doc_norm).ratio()
        if similarity >= self.similarity_threshold:
            return True
        
        return False
    
    def match_any(self, query_entities: List[str], doc_entities: List[str]) -> bool:
        """
        Check if any query entity matches any doc entity
        
        Args:
            query_entities: List of entities from query
            doc_entities: List of entities from document
            
        Returns:
            True if at least one match found
        """
        for query_ent in query_entities:
            for doc_ent in doc_entities:
                if self.fuzzy_match(query_ent, doc_ent):
                    return True
        return False
    
    def match_score(self, query_entities: List[str], doc_entities: List[str]) -> float:
        """
        Calculate match score (0-1) based on entity overlap
        
        Score represents how many query entities match document entities.
        
        Args:
            query_entities: List of entities from query
            doc_entities: List of entities from document
            
        Returns:
            Score from 0 (no matches) to 1 (all query entities match)
        """
        if not query_entities:
            return 0.0
        
        matches = sum(
            1 for q_ent in query_entities
            if any(self.fuzzy_match(q_ent, d_ent) for d_ent in doc_entities)
        )
        
        return matches / len(query_entities)
    
    def get_best_match(self, query_entity: str, doc_entities: List[str]) -> tuple:
        """
        Find the best matching entity from a list
        
        Args:
            query_entity: Single entity to match
            doc_entities: List of candidate entities
            
        Returns:
            Tuple of (best_match, similarity_score) or (None, 0.0) if no match
        """
        best_match = None
        best_score = 0.0
        
        query_norm = self.normalize_name(query_entity)
        
        for doc_ent in doc_entities:
            doc_norm = self.normalize_name(doc_ent)
            
            # Calculate similarity
            if query_norm == doc_norm:
                similarity = 1.0
            elif query_norm in doc_norm or doc_norm in query_norm:
                # Substring match gets high score
                similarity = 0.95
            else:
                similarity = SequenceMatcher(None, query_norm, doc_norm).ratio()
            
            if similarity > best_score:
                best_score = similarity
                best_match = doc_ent
        
        # Only return if above threshold
        if best_score >= self.similarity_threshold:
            return (best_match, best_score)
        
        return (None, 0.0)


# Usage Example
if __name__ == "__main__":
    matcher = EntityMatcher()
    
    # Test normalization
    print("Normalization Examples:")
    print(f"  'G. Maxwell' -> '{matcher.normalize_name('G. Maxwell')}'")
    print(f"  'The Clinton Foundation' -> '{matcher.normalize_name('The Clinton Foundation')}'")
    print(f"  'Dr. Jeffrey Epstein' -> '{matcher.normalize_name('Dr. Jeffrey Epstein')}'")
    print()
    
    # Test fuzzy matching
    print("Fuzzy Matching Examples:")
    test_cases = [
        ("Maxwell", "Ghislaine Maxwell"),
        ("Maxwell", "G. Maxwell"),
        ("Epstein", "Jeffrey Epstein"),
        ("Clinton", "Clinton Foundation"),
        ("Maxwell", "Einstein"),  # Should not match
    ]
    
    for query, doc in test_cases:
        match = matcher.fuzzy_match(query, doc)
        print(f"  '{query}' vs '{doc}': {match}")
    print()
    
    # Test match score
    print("Match Score Examples:")
    query_entities = ["Maxwell", "Paris"]
    doc_entities_1 = ["Ghislaine Maxwell", "Paris", "London", "Jeffrey Epstein"]
    doc_entities_2 = ["Bill Clinton", "New York"]
    
    score1 = matcher.match_score(query_entities, doc_entities_1)
    score2 = matcher.match_score(query_entities, doc_entities_2)
    
    print(f"  Query: {query_entities}")
    print(f"  Doc 1 entities: {doc_entities_1} -> Score: {score1:.2f}")
    print(f"  Doc 2 entities: {doc_entities_2} -> Score: {score2:.2f}")

