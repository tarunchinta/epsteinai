"""
Simple command-line interface for MVP1
"""

import sys
from loguru import logger
from src.document_loader import DocumentLoader
from src.sparse_search import BM25SearchEngine


def main():
    """MVP1 CLI - Basic keyword search"""
    
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    print("=" * 60)
    print("Document Search System - MVP1")
    print("Epstein Document Collection")
    print("=" * 60)
    
    # Load documents
    print("\nLoading documents from data/ folder...")
    loader = DocumentLoader("data")
    documents = loader.load_documents()
    
    if not documents:
        print("Error: No documents found in data/")
        return
    
    print(f"✓ Loaded {len(documents)} documents")
    
    # Build search index
    print("\nBuilding search index...")
    search_engine = BM25SearchEngine(documents)
    print("✓ Index ready!")
    
    # Interactive search loop
    print("\n" + "=" * 60)
    print("Enter search queries (or 'quit' to exit)")
    print("Example: 'meeting 2019' or 'Maxwell Paris'")
    print("=" * 60)
    
    while True:
        print("\n")
        query = input("Search: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
            
        if not query:
            continue
        
        # Search
        results = search_engine.search(query, top_k=10)
        
        # Display results
        if not results:
            print("No results found.")
            continue
        
        print(f"\nFound {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['filename']}")
            print(f"   Score: {result['score']:.2f}")
            print(f"   Preview: {result['preview']}")
            print()


if __name__ == "__main__":
    main()

