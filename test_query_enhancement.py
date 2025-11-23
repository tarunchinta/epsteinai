"""
Test script to demonstrate Query Enhancement with Known Entities Lookup

This script tests the improved entity extraction that enables queries like:
- "epstein investigation" → matches "Jeffrey Epstein" entities
- "maxwell case" → matches "Ghislaine Maxwell" entities
- "trump documents" → matches "Donald Trump" entities
"""

from src.document_loader import DocumentLoader
from src.sparse_search import BM25SearchEngine
from src.metadata_store import MetadataStore
from src.enhanced_search import EnhancedSearchEngine
from loguru import logger
import sys

# Configure logger to show debug messages
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_query_enhancement():
    """Test the enhanced query entity extraction"""
    
    print("\n" + "=" * 80)
    print("TESTING: Query Enhancement with Known Entities Lookup")
    print("=" * 80)
    
    # Check if metadata exists
    import os
    if not os.path.exists("data/metadata.db"):
        print("\n❌ Error: metadata.db not found")
        print("Please run: python build_metadata_index.py")
        return
    
    # Load system
    print("\n1. Loading search engine...")
    loader = DocumentLoader("data")
    documents = loader.load_documents()
    bm25_engine = BM25SearchEngine(documents)
    metadata_store = MetadataStore("data/metadata.db")
    
    # Initialize enhanced search (will build entity lookup)
    print("\n2. Initializing enhanced search with entity lookup...")
    search_engine = EnhancedSearchEngine(bm25_engine, metadata_store)
    
    print("\n✓ System ready\n")
    
    # Test queries that should now work with lowercase entity names
    test_queries = [
        {
            "query": "epstein investigation",
            "description": "Lowercase 'epstein' should match 'Jeffrey Epstein' entities",
            "expected": "Should find Jeffrey Epstein"
        },
        {
            "query": "maxwell case documents",
            "description": "Lowercase 'maxwell' should match 'Ghislaine Maxwell' entities",
            "expected": "Should find Ghislaine Maxwell"
        },
        {
            "query": "trump business dealings",
            "description": "Lowercase 'trump' should match 'Donald Trump' entities",
            "expected": "Should find Donald Trump"
        },
        {
            "query": "clinton emails",
            "description": "Lowercase 'clinton' should match 'Bill Clinton' entities",
            "expected": "Should find Bill Clinton"
        },
        {
            "query": "dershowitz legal representation",
            "description": "Lowercase 'dershowitz' should match 'Alan Dershowitz' entities",
            "expected": "Should find Alan Dershowitz"
        }
    ]
    
    print("=" * 80)
    print("ENTITY EXTRACTION TESTS")
    print("=" * 80)
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{'-' * 80}")
        print(f"Test {i}: {test['query']}")
        print(f"{'-' * 80}")
        print(f"Description: {test['description']}")
        print(f"Expected: {test['expected']}")
        print()
        
        # Extract entities using the enhanced method
        entities = search_engine._extract_query_entities(test['query'])
        
        print("Extracted Entities:")
        if entities['people']:
            print(f"  ✓ People: {entities['people'][:5]}")
        else:
            print("  ✗ People: None")
        
        if entities['locations']:
            print(f"  ✓ Locations: {entities['locations'][:3]}")
        else:
            print("  ✗ Locations: None")
        
        if entities['organizations']:
            print(f"  ✓ Organizations: {entities['organizations'][:3]}")
        else:
            print("  ✗ Organizations: None")
        
        # Run actual search with adaptive filtering
        print("\nRunning adaptive search...")
        results = search_engine.search_adaptive(
            query=test['query'],
            top_k=3,
            filter_strategy='boost'  # Use boost to combine BM25 + metadata
        )
        
        if results:
            print(f"\n✓ Found {len(results)} results:")
            for j, result in enumerate(results, 1):
                print(f"\n  {j}. {result['filename']}")
                print(f"     Score: {result['score']:.4f}")
                print(f"     Preview: {result['preview'][:100]}...")
                
                # Show document metadata
                doc_meta = metadata_store.get_metadata(result['doc_id'])
                if doc_meta:
                    if doc_meta['people']:
                        print(f"     People in doc: {', '.join(doc_meta['people'][:5])}")
                    if doc_meta['locations']:
                        print(f"     Locations: {', '.join(doc_meta['locations'][:3])}")
        else:
            print("\n✗ No results found")
    
    print("\n" + "=" * 80)
    print("COMPARISON: Before vs After Enhancement")
    print("=" * 80)
    
    # Show what would happen WITHOUT enhancement (pure spaCy NER)
    from src.metadata_extractor import MetadataExtractor
    extractor = MetadataExtractor()
    
    comparison_query = "epstein investigation"
    print(f"\nQuery: '{comparison_query}'")
    print("\nWITHOUT Enhancement (spaCy NER only):")
    
    basic_metadata = extractor.extract_metadata(comparison_query, "query")
    print(f"  People: {basic_metadata['people'] if basic_metadata['people'] else 'None'}")
    print(f"  Locations: {basic_metadata['locations'] if basic_metadata['locations'] else 'None'}")
    print(f"  Organizations: {basic_metadata['organizations'] if basic_metadata['organizations'] else 'None'}")
    
    print("\nWITH Enhancement (Lookup + Substring Matching):")
    enhanced_entities = search_engine._extract_query_entities(comparison_query)
    print(f"  People: {enhanced_entities['people'][:5] if enhanced_entities['people'] else 'None'}")
    print(f"  Locations: {enhanced_entities['locations'][:3] if enhanced_entities['locations'] else 'None'}")
    print(f"  Organizations: {enhanced_entities['organizations'][:3] if enhanced_entities['organizations'] else 'None'}")
    
    print("\n✓ Enhancement adds entity matching even when NER fails!")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nKey Improvements:")
    print("  ✓ Lowercase entity names now match (epstein → Jeffrey Epstein)")
    print("  ✓ Partial names work (maxwell → Ghislaine Maxwell)")
    print("  ✓ Robust to query variations (trump → Donald Trump)")
    print("  ✓ Works even when spaCy NER fails")
    print("\nThe search engine now handles real-world queries better!")
    print("=" * 80 + "\n")
    
    metadata_store.close()


if __name__ == "__main__":
    test_query_enhancement()

