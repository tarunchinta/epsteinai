"""
Demo script for MVP 2 enhanced search with metadata filtering
"""

from src.document_loader import DocumentLoader
from src.sparse_search import BM25SearchEngine
from src.metadata_store import MetadataStore
from src.enhanced_search import EnhancedSearchEngine
import os


def demo():
    """Run a demonstration of enhanced search with metadata filtering"""
    
    print("=" * 70)
    print("MVP 2: Enhanced Search with Metadata Filtering Demo")
    print("=" * 70)
    
    # Check if metadata index exists
    if not os.path.exists("data/metadata.db"):
        print("\n❌ Error: Metadata index not found!")
        print("\nPlease run: python build_metadata_index.py")
        return
    
    # Load documents
    print("\n1. Loading documents...")
    loader = DocumentLoader("data")
    documents = loader.load_documents()
    print(f"   ✓ Loaded {len(documents)} documents")
    
    # Build BM25 index
    print("\n2. Building BM25 search index...")
    bm25_engine = BM25SearchEngine(documents)
    print(f"   ✓ Index ready")
    
    # Load metadata store
    print("\n3. Loading metadata store...")
    metadata_store = MetadataStore("data/metadata.db")
    print(f"   ✓ Metadata loaded")
    
    # Get entity statistics
    entities = metadata_store.get_all_entities()
    print(f"\n   Metadata contains:")
    print(f"   - {len(entities['people'])} unique people")
    print(f"   - {len(entities['locations'])} unique locations")
    print(f"   - {len(entities['organizations'])} unique organizations")
    print(f"   - {len(entities['dates'])} unique dates")
    
    # Create enhanced search engine
    enhanced_search = EnhancedSearchEngine(bm25_engine, metadata_store)
    
    # Demo queries
    print("\n" + "=" * 70)
    print("Demo Queries")
    print("=" * 70)
    
    demo_queries = [
        {
            'query': 'Epstein investigation',
            'filters': {},
            'description': 'Basic keyword search (no filters)'
        },
        {
            'query': 'meeting discussion',
            'filters': {'filter_people': entities['people'][:3]} if entities['people'] else {},
            'description': f'Filtered by people: {entities["people"][:3] if entities["people"] else "none"}'
        },
        {
            'query': 'court case',
            'filters': {'filter_locations': entities['locations'][:2]} if entities['locations'] else {},
            'description': f'Filtered by locations: {entities["locations"][:2] if entities["locations"] else "none"}'
        },
    ]
    
    for i, demo_query in enumerate(demo_queries, 1):
        print(f"\n{'─' * 70}")
        print(f"Query {i}: '{demo_query['query']}'")
        print(f"Filters: {demo_query['description']}")
        print(f"{'─' * 70}")
        
        # Run search
        results = enhanced_search.search(
            query=demo_query['query'],
            top_k=3,
            **demo_query['filters']
        )
        
        if results:
            print(f"\n✓ Found {len(results)} results:\n")
            for j, result in enumerate(results, 1):
                print(f"  {j}. {result['filename']}")
                print(f"     Score: {result['score']:.2f}")
                print(f"     Preview: {result['preview'][:80]}...")
                
                # Show metadata for this document
                doc_metadata = metadata_store.get_metadata(result['doc_id'])
                if doc_metadata:
                    if doc_metadata['people']:
                        print(f"     People: {', '.join(doc_metadata['people'][:3])}")
                    if doc_metadata['locations']:
                        print(f"     Locations: {', '.join(doc_metadata['locations'][:3])}")
                print()
        else:
            print("\n  No results found")
    
    # Auto-filter demo
    print("\n" + "=" * 70)
    print("Auto-Filter Demo (Extracts entities from query)")
    print("=" * 70)
    
    auto_query = "What did Maxwell do in Paris?"
    print(f"\nQuery: '{auto_query}'")
    print("(Will automatically detect 'Maxwell' and 'Paris' as filters)")
    
    results = enhanced_search.search_with_auto_filters(auto_query, top_k=3)
    
    if results:
        print(f"\n✓ Found {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['filename']} (score: {result['score']:.2f})")
            print(f"     {result['preview'][:100]}...")
    else:
        print("\n  No results found")
    
    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)
    
    metadata_store.close()


if __name__ == "__main__":
    demo()

