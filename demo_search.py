"""
Demo script to show MVP 1 search capabilities
"""

from src.document_loader import DocumentLoader
from src.sparse_search import BM25SearchEngine


def demo():
    """Run a demonstration of the search system"""
    
    print("=" * 70)
    print("MVP 1: Document Search System Demo")
    print("=" * 70)
    
    # Load documents
    print("\n1. Loading documents from data/ folder...")
    loader = DocumentLoader("data")
    documents = loader.load_documents()
    print(f"   ✓ Loaded {len(documents)} documents")
    
    # Build search index
    print("\n2. Building BM25 search index...")
    search_engine = BM25SearchEngine(documents)
    print(f"   ✓ Index ready!")
    
    # Demo queries
    demo_queries = [
        "Epstein billionaire",
        "oversight committee",
        "Jeffrey Maxwell",
        "court case",
        "investigation"
    ]
    
    print("\n3. Running demo queries:")
    print("-" * 70)
    
    for query in demo_queries:
        print(f"\n📝 Query: '{query}'")
        results = search_engine.search(query, top_k=3)
        
        if results:
            print(f"   Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"\n   {i}. {result['filename']}")
                print(f"      Score: {result['score']:.2f}")
                print(f"      Preview: {result['preview'][:100]}...")
        else:
            print("   No results found")
    
    print("\n" + "=" * 70)
    print("Demo complete! Run 'python run_search.py' for interactive search")
    print("=" * 70)


if __name__ == "__main__":
    demo()

