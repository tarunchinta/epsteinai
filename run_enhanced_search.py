"""
Interactive CLI for enhanced search with metadata filtering
"""

import os
import sys
from src.document_loader import DocumentLoader
from src.sparse_search import BM25SearchEngine
from src.metadata_store import MetadataStore
from src.enhanced_search import EnhancedSearchEngine


def main():
    """Interactive enhanced search CLI"""
    
    print("=" * 70)
    print("MVP 2: Enhanced Document Search")
    print("Keyword Search + Metadata Filtering")
    print("=" * 70)
    
    # Check if metadata index exists
    if not os.path.exists("data/metadata.db"):
        print("\n❌ Error: Metadata index not found!")
        print("\nPlease run: python build_metadata_index.py")
        sys.exit(1)
    
    # Load documents and build index
    print("\nLoading search system...")
    loader = DocumentLoader("data")
    documents = loader.load_documents()
    
    bm25_engine = BM25SearchEngine(documents)
    metadata_store = MetadataStore("data/metadata.db")
    enhanced_search = EnhancedSearchEngine(bm25_engine, metadata_store)
    
    # Get available entities
    entities = metadata_store.get_all_entities()
    
    print(f"✓ Loaded {len(documents)} documents")
    print(f"✓ Metadata: {len(entities['people'])} people, "
          f"{len(entities['locations'])} locations, "
          f"{len(entities['organizations'])} organizations")
    
    print("\n" + "=" * 70)
    print("Search Commands:")
    print("  - Enter a query to search")
    print("  - Type 'entities' to see available filters")
    print("  - Type 'quit' to exit")
    print("=" * 70)
    
    while True:
        print("\n")
        query = input("Search: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if query.lower() == 'entities':
            print("\nAvailable Entities for Filtering:")
            print(f"\nPeople ({len(entities['people'])}):")
            print(", ".join(entities['people'][:20]))
            if len(entities['people']) > 20:
                print(f"... and {len(entities['people']) - 20} more")
            
            print(f"\nLocations ({len(entities['locations'])}):")
            print(", ".join(entities['locations'][:20]))
            if len(entities['locations']) > 20:
                print(f"... and {len(entities['locations']) - 20} more")
            
            print(f"\nOrganizations ({len(entities['organizations'])}):")
            print(", ".join(entities['organizations'][:20]))
            if len(entities['organizations']) > 20:
                print(f"... and {len(entities['organizations']) - 20} more")
            continue
        
        if not query:
            continue
        
        # Search with auto-filters
        results = enhanced_search.search_with_auto_filters(query, top_k=10)
        
        # Display results
        if not results:
            print("No results found.")
            continue
        
        print(f"\nFound {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['filename']}")
            print(f"   Score: {result['score']:.2f}")
            print(f"   Preview: {result['preview']}")
            
            # Show metadata
            doc_metadata = metadata_store.get_metadata(result['doc_id'])
            if doc_metadata:
                meta_info = []
                if doc_metadata['people']:
                    meta_info.append(f"People: {', '.join(doc_metadata['people'][:3])}")
                if doc_metadata['locations']:
                    meta_info.append(f"Locations: {', '.join(doc_metadata['locations'][:3])}")
                if doc_metadata['organizations']:
                    meta_info.append(f"Orgs: {', '.join(doc_metadata['organizations'][:2])}")
                
                if meta_info:
                    print(f"   Metadata: {' | '.join(meta_info)}")
            print()
    
    metadata_store.close()


if __name__ == "__main__":
    main()

