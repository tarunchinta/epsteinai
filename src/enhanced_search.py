"""
Enhanced search combining BM25 keyword search with metadata filtering
"""

from typing import List, Dict, Optional
from loguru import logger
from src.sparse_search import BM25SearchEngine
from src.metadata_store import MetadataStore
from src.metadata_extractor import MetadataExtractor
from src.entity_matcher import EntityMatcher


class MetadataScorer:
    """Calculate metadata-based relevance scores"""
    
    def __init__(self):
        self.entity_matcher = EntityMatcher()
        
        # Scoring weights
        self.weights = {
            'person_match': 0.30,
            'location_match': 0.20,
            'org_match': 0.20,
            'entity_density': 0.10,
        }
    
    def calculate_metadata_score(self,
                                 doc_metadata: Dict,
                                 query_entities: Dict) -> float:
        """
        Calculate comprehensive metadata relevance score
        
        Args:
            doc_metadata: Document metadata with entities
            query_entities: Query entities (people, locations, organizations)
        
        Returns:
            Score from 0.0 (no match) to 1.0 (perfect match)
        """
        total_score = 0.0
        max_possible = 0.0
        
        # Person matching
        if query_entities.get('people'):
            max_possible += self.weights['person_match']
            person_score = self.entity_matcher.match_score(
                query_entities['people'],
                doc_metadata['people']
            )
            total_score += person_score * self.weights['person_match']
        
        # Location matching
        if query_entities.get('locations'):
            max_possible += self.weights['location_match']
            loc_score = self.entity_matcher.match_score(
                query_entities['locations'],
                doc_metadata['locations']
            )
            total_score += loc_score * self.weights['location_match']
        
        # Organization matching
        if query_entities.get('organizations'):
            max_possible += self.weights['org_match']
            org_score = self.entity_matcher.match_score(
                query_entities['organizations'],
                doc_metadata['organizations']
            )
            total_score += org_score * self.weights['org_match']
        
        # Entity density (more entities = likely more relevant)
        total_entities = (len(doc_metadata['people']) + 
                         len(doc_metadata['locations']) +
                         len(doc_metadata['organizations']))
        max_possible += self.weights['entity_density']
        
        # Normalize (cap at 20 entities)
        density_score = min(total_entities / 20, 1.0)
        total_score += density_score * self.weights['entity_density']
        
        # Normalize to 0-1 range
        if max_possible > 0:
            return total_score / max_possible
        return 0.0


class EnhancedSearchEngine:
    """
    Two-tier search combining BM25 + metadata filtering
    Tier 1: BM25 keyword search (fast, broad)
    Tier 2: Metadata filtering (precise, entity-based)
    """
    
    def __init__(self, 
                 bm25_engine: BM25SearchEngine,
                 metadata_store: MetadataStore):
        """
        Initialize enhanced search engine
        
        Args:
            bm25_engine: BM25 search engine instance
            metadata_store: Metadata store instance
        """
        self.bm25_engine = bm25_engine
        self.metadata_store = metadata_store
        self.metadata_extractor = MetadataExtractor()
        self.entity_matcher = EntityMatcher()
        self.metadata_scorer = MetadataScorer()
        
        # Build entity lookup index for fast query enhancement
        logger.info("Building entity lookup index...")
        self._build_entity_lookup()
        logger.info(f"Entity lookup ready: {len(self.entity_lookup['people'])} people, "
                   f"{len(self.entity_lookup['locations'])} locations, "
                   f"{len(self.entity_lookup['organizations'])} orgs")
    
    def _build_entity_lookup(self):
        """
        Build fast lookup index for entity matching
        
        Creates normalized entity lookups to enable matching of:
        - "epstein" → "Jeffrey Epstein"
        - "maxwell" → "Ghislaine Maxwell"
        - "ny" → "New York"
        
        This enables query enhancement even when spaCy NER fails.
        """
        entities = self.metadata_store.get_all_entities()
        
        # Create normalized entity lookup
        # Maps: normalized_form → [canonical_forms]
        self.entity_lookup = {
            'people': {},
            'locations': {},
            'organizations': {}
        }
        
        # Build lookup for people
        for person in entities['people']:
            normalized = self.entity_matcher.normalize_name(person)
            if normalized not in self.entity_lookup['people']:
                self.entity_lookup['people'][normalized] = []
            self.entity_lookup['people'][normalized].append(person)
        
        # Build lookup for locations
        for loc in entities['locations']:
            normalized = self.entity_matcher.normalize_name(loc)
            if normalized not in self.entity_lookup['locations']:
                self.entity_lookup['locations'][normalized] = []
            self.entity_lookup['locations'][normalized].append(loc)
        
        # Build lookup for organizations
        for org in entities['organizations']:
            normalized = self.entity_matcher.normalize_name(org)
            if normalized not in self.entity_lookup['organizations']:
                self.entity_lookup['organizations'][normalized] = []
            self.entity_lookup['organizations'][normalized].append(org)
        
    def search(self,
               query: str,
               top_k: int = 10,
               filter_people: Optional[List[str]] = None,
               filter_locations: Optional[List[str]] = None,
               filter_organizations: Optional[List[str]] = None,
               filter_date_range: Optional[tuple] = None,
               bm25_candidates: int = 500) -> List[Dict]:
        """
        Search with two-tier retrieval
        
        Args:
            query: Search query string
            top_k: Number of final results to return
            filter_people: Optional list of people names to filter by
            filter_locations: Optional list of locations to filter by
            filter_organizations: Optional list of organizations to filter by
            filter_date_range: Optional (start_date, end_date) tuple
            bm25_candidates: Number of candidates from BM25 (default 100)
            
        Returns:
            List of documents sorted by relevance
        """
        
        # TIER 1: BM25 Keyword Search
        logger.info(f"Tier 1: Running BM25 search for '{query}'")
        bm25_results = self.bm25_engine.search(query, top_k=bm25_candidates)
        
        if not bm25_results:
            logger.info("No BM25 results found")
            return []
        
        logger.info(f"BM25 found {len(bm25_results)} candidates")
        
        # TIER 2: Metadata Filtering (if any filters provided)
        has_filters = any([
            filter_people,
            filter_locations,
            filter_organizations,
            filter_date_range
        ])
        
        if has_filters:
            logger.info("Tier 2: Applying metadata filters")
            doc_ids = [doc['doc_id'] for doc in bm25_results]
            
            filtered_doc_ids = self.metadata_store.filter_documents(
                doc_ids=doc_ids,
                people=filter_people,
                locations=filter_locations,
                organizations=filter_organizations,
                date_range=filter_date_range
            )
            
            logger.info(f"Metadata filtering: {len(doc_ids)} → {len(filtered_doc_ids)} docs")
            
            # Keep only filtered documents, preserve BM25 ranking
            filtered_results = [
                doc for doc in bm25_results 
                if doc['doc_id'] in filtered_doc_ids
            ]
        else:
            logger.info("No metadata filters applied")
            filtered_results = bm25_results
        
        # Return top K results
        final_results = filtered_results[:top_k]
        logger.info(f"Returning {len(final_results)} final results")
        
        return final_results
    
    def search_adaptive(self,
                       query: str,
                       top_k: int = 10,
                       filter_strategy: str = 'adaptive',
                       min_candidates: int = 50,
                       max_candidates: int = 100,
                       bm25_candidates: int = 500) -> List[Dict]:
        """
        Search with adaptive filtering strategy
        
        Args:
            query: Search query
            top_k: Final results to return
            filter_strategy: 'strict', 'loose', 'adaptive', 'boost', or 'none'
            min_candidates: Minimum docs to pass to next tier
            max_candidates: Maximum docs to pass to next tier
            bm25_candidates: Initial BM25 candidates to retrieve
            
        Returns:
            Ranked search results
        """
        # TIER 1: BM25 Search
        logger.info(f"Tier 1: BM25 search")
        bm25_results = self.bm25_engine.search(query, top_k=bm25_candidates)
        logger.info(f"BM25 found {len(bm25_results)} candidates")
        
        if not bm25_results:
            return []
        
        # Extract entities from query
        entities = self._extract_query_entities(query)
        
        if not entities or filter_strategy == 'none':
            # No filtering, return BM25 results
            return bm25_results[:top_k]
        
        # TIER 2: Apply filtering strategy
        if filter_strategy == 'strict':
            filtered = self._filter_strict(bm25_results, entities)
        elif filter_strategy == 'loose':
            filtered = self._filter_loose(bm25_results, entities)
        elif filter_strategy == 'boost':
            filtered = self._filter_with_boost(bm25_results, entities)
        else:  # adaptive
            filtered = self._filter_adaptive(
                bm25_results, 
                entities, 
                min_candidates
            )
        
        logger.info(f"Tier 2: Filtered to {len(filtered)} candidates (strategy: {filter_strategy})")
        
        # Ensure within range
        if len(filtered) < min_candidates and filter_strategy != 'boost':
            logger.warning(f"Only {len(filtered)} candidates, using top BM25 results")
            return bm25_results[:min(max_candidates, len(bm25_results))]
        
        return filtered[:top_k]
    
    def _extract_query_entities(self, query: str) -> Dict:
        """
        Extract entities from query using multiple strategies:
        1. spaCy NER (for properly capitalized names)
        2. Known entity lookup (for lowercase/partial matches)
        3. Substring matching (for partial entity names)
        
        This enables queries like "epstein investigation" to match "Jeffrey Epstein"
        even when spaCy doesn't recognize "epstein" as a PERSON.
        
        Args:
            query: User query string
            
        Returns:
            Dict with 'people', 'locations', 'organizations' lists (or None)
        """
        # Strategy 1: Use spaCy NER (works for properly formatted names)
        metadata = self.metadata_extractor.extract_metadata(query, "query")
        
        people = set(metadata['people']) if metadata['people'] else set()
        locations = set(metadata['locations']) if metadata['locations'] else set()
        organizations = set(metadata['organizations']) if metadata['organizations'] else set()
        
        logger.debug(f"spaCy NER found: people={people}, locations={locations}, orgs={organizations}")
        
        # Strategy 2: Check query tokens against known entities (exact normalized match)
        query_tokens = query.lower().split()
        stopwords = {'the', 'and', 'for', 'with', 'in', 'on', 'at', 'to', 'from', 'by', 'about', 'investigation', 'case', 'documents', 'files'}
        
        for token in query_tokens:
            # Skip short tokens and stopwords
            if len(token) < 3 or token in stopwords:
                continue
            
            # Normalize token (remove punctuation, etc.)
            normalized = self.entity_matcher.normalize_name(token)
            
            # Check against known entities (exact normalized match)
            if normalized in self.entity_lookup['people']:
                matched = self.entity_lookup['people'][normalized]
                people.update(matched)
                logger.debug(f"Token '{token}' matched people: {matched}")
            
            if normalized in self.entity_lookup['locations']:
                matched = self.entity_lookup['locations'][normalized]
                locations.update(matched)
                logger.debug(f"Token '{token}' matched locations: {matched}")
            
            if normalized in self.entity_lookup['organizations']:
                matched = self.entity_lookup['organizations'][normalized]
                organizations.update(matched)
                logger.debug(f"Token '{token}' matched organizations: {matched}")
        
        # Strategy 3: Substring matching for partial entity names
        # This catches "epstein" → "Jeffrey Epstein", "maxwell" → "Ghislaine Maxwell"
        all_entities = self.metadata_store.get_all_entities()
        
        for token in query_tokens:
            if len(token) < 4:  # Too short for meaningful substring matching
                continue
            
            if token in stopwords:
                continue
            
            token_lower = token.lower()
            
            # Search for substring matches in people (limit search for performance)
            for person in list(all_entities['people'])[:2000]:  # Top 2000 people
                if token_lower in person.lower() and person not in people:
                    people.add(person)
                    logger.debug(f"Substring match: '{token}' → person '{person}'")
                    break  # Found one match for this token, move on
            
            # Search for substring matches in locations (limit for performance)
            for location in list(all_entities['locations'])[:1000]:  # Top 1000 locations
                if token_lower in location.lower() and location not in locations:
                    locations.add(location)
                    logger.debug(f"Substring match: '{token}' → location '{location}'")
                    break
            
            # Search for substring matches in organizations (limit for performance)
            for org in list(all_entities['organizations'])[:1000]:  # Top 1000 orgs
                if token_lower in org.lower() and org not in organizations:
                    organizations.add(org)
                    logger.debug(f"Substring match: '{token}' → organization '{org}'")
                    break
        
        # Log final extracted entities
        if people or locations or organizations:
            logger.info(f"Extracted entities - People: {list(people)[:3]}, "
                       f"Locations: {list(locations)[:3]}, "
                       f"Organizations: {list(organizations)[:3]}")
        else:
            logger.info("No entities extracted from query")
        
        return {
            'people': list(people) if people else None,
            'locations': list(locations) if locations else None,
            'organizations': list(organizations) if organizations else None
        }
    
    def _filter_strict(self, 
                       results: List[Dict], 
                       entities: Dict) -> List[Dict]:
        """
        Strict AND filtering: ALL entities must match
        Use for: Highly specific queries
        """
        doc_ids = [r['doc_id'] for r in results]
        
        filtered_ids = self.metadata_store.filter_documents_fuzzy(
            doc_ids=doc_ids,
            people=entities.get('people'),
            locations=entities.get('locations'),
            organizations=entities.get('organizations'),
            match_mode='fuzzy'  # Use fuzzy matching
        )
        
        return [r for r in results if r['doc_id'] in filtered_ids]
    
    def _filter_loose(self,
                      results: List[Dict],
                      entities: Dict) -> List[Dict]:
        """
        Loose OR filtering: ANY entity match counts
        Use for: Broad exploration
        """
        doc_ids = [r['doc_id'] for r in results]
        
        filtered_ids = self.metadata_store.filter_documents_fuzzy(
            doc_ids=doc_ids,
            people=entities.get('people'),
            locations=entities.get('locations'),
            organizations=entities.get('organizations'),
            match_mode='any'  # Use OR logic
        )
        
        return [r for r in results if r['doc_id'] in filtered_ids]
    
    def _filter_with_boost(self,
                          results: List[Dict],
                          entities: Dict) -> List[Dict]:
        """
        Soft boosting: Don't filter out, just boost matching docs
        Use for: MVP 3 (preserves candidates for dense search)
        """
        query_entities = {k: v for k, v in entities.items() if v}
        
        for result in results:
            doc_metadata = self.metadata_store.get_metadata(result['doc_id'])
            if not doc_metadata:
                result['metadata_score'] = 0.0
                continue
            
            # Calculate metadata match score
            metadata_score = self.metadata_scorer.calculate_metadata_score(
                doc_metadata,
                query_entities
            )
            
            # Store metadata score
            result['metadata_score'] = metadata_score
            
            # Apply boost to BM25 score
            result['original_score'] = result['score']
            result['score'] = result['score'] * (1 + metadata_score)
        
        # Re-sort by boosted scores
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def _filter_adaptive(self,
                        results: List[Dict],
                        entities: Dict,
                        min_candidates: int) -> List[Dict]:
        """
        Adaptive filtering: Try strict, fall back to loose if needed
        Use for: General queries (default)
        """
        # Try strict first
        strict_filtered = self._filter_strict(results, entities)
        
        if len(strict_filtered) >= min_candidates:
            logger.info(f"Adaptive: Using strict filter ({len(strict_filtered)} docs)")
            return strict_filtered
        
        # Fall back to loose
        loose_filtered = self._filter_loose(results, entities)
        
        if len(loose_filtered) >= min_candidates:
            logger.info(f"Adaptive: Using loose filter ({len(loose_filtered)} docs)")
            return loose_filtered
        
        # Fall back to boost (no filtering)
        logger.info(f"Adaptive: Using soft boost (preserving all {len(results)} docs)")
        return self._filter_with_boost(results, entities)
    
    def search_with_auto_filters(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Search with automatic entity extraction from query
        
        Args:
            query: Search query string
            top_k: Number of results to return
            
        Returns:
            List of documents sorted by relevance
        """
        
        # Extract entities from query
        logger.info(f"Auto-extracting entities from query: '{query}'")
        
        # Use metadata extractor to find entities in query
        query_metadata = self.metadata_extractor.extract_metadata(query, "query")
        
        # Use extracted entities as filters
        people = query_metadata['people'] if query_metadata['people'] else None
        locations = query_metadata['locations'] if query_metadata['locations'] else None
        organizations = query_metadata['organizations'] if query_metadata['organizations'] else None
        
        if people or locations or organizations:
            logger.info(f"Auto-detected filters - People: {people}, "
                       f"Locations: {locations}, Orgs: {organizations}")
        
        return self.search(
            query=query,
            top_k=top_k,
            filter_people=people,
            filter_locations=locations,
            filter_organizations=organizations
        )


# Usage Example
if __name__ == "__main__":
    from src.document_loader import DocumentLoader
    
    # Load documents
    loader = DocumentLoader("data")
    documents = loader.load_documents()
    
    # Create BM25 engine
    bm25_engine = BM25SearchEngine(documents)
    
    # Create metadata store
    metadata_store = MetadataStore()
    
    # Create enhanced search
    enhanced_search = EnhancedSearchEngine(bm25_engine, metadata_store)
    
    # Search with manual filters
    results = enhanced_search.search(
        query="meeting discussion",
        filter_people=["Maxwell"],
        top_k=5
    )
    
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['filename']} (score: {result['score']:.2f})")

