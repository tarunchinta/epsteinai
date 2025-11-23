"""
Enhanced search combining BM25 keyword search with metadata filtering
"""

from typing import List, Dict, Optional
from loguru import logger
from src.sparse_search import BM25SearchEngine
from src.metadata_store import MetadataStore
from src.metadata_extractor import MetadataExtractor


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

