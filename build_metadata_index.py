"""
Build metadata index for all documents
Run this once to extract and store metadata
"""

from src.document_loader import DocumentLoader
from src.metadata_extractor import MetadataExtractor
from src.metadata_store import MetadataStore
from loguru import logger
import sys
from tqdm import tqdm


def build_index():
    """Extract metadata from all documents and store in database"""
    
    print("=" * 70)
    print("MVP 2: Building Metadata Index")
    print("=" * 70)
    
    # Load documents
    print("\n1. Loading documents...")
    loader = DocumentLoader("data")
    documents = loader.load_documents()
    print(f"   ✓ Loaded {len(documents)} documents")
    
    # Initialize extractor and store
    print("\n2. Initializing metadata extractor...")
    try:
        extractor = MetadataExtractor()
        print("   ✓ spaCy model loaded")
    except OSError as e:
        print(f"\n   ❌ Error: {e}")
        print("\n   Please install spaCy model:")
        print("   python -m spacy download en_core_web_sm")
        return False
    
    store = MetadataStore("data/metadata.db")
    print("   ✓ Database initialized")
    
    # Extract and store metadata for each document
    print("\n3. Extracting metadata from documents...")
    
    total_people = set()
    total_locations = set()
    total_organizations = set()
    total_dates = set()
    
    for doc in tqdm(documents, desc="Processing"):
        try:
            # Extract metadata
            metadata = extractor.extract_metadata(doc['text'], doc['doc_id'])
            
            # Store in database
            store.store_metadata(metadata)
            
            # Collect statistics
            total_people.update(metadata['people'])
            total_locations.update(metadata['locations'])
            total_organizations.update(metadata['organizations'])
            total_dates.update(metadata['dates'])
            
        except Exception as e:
            logger.error(f"Error processing {doc['filename']}: {e}")
    
    print(f"\n   ✓ Metadata extracted and stored")
    
    # Display statistics
    print("\n" + "=" * 70)
    print("Metadata Index Statistics")
    print("=" * 70)
    print(f"\nDocuments indexed:    {len(documents)}")
    print(f"Unique people:        {len(total_people)}")
    print(f"Unique locations:     {len(total_locations)}")
    print(f"Unique organizations: {len(total_organizations)}")
    print(f"Unique dates:         {len(total_dates)}")
    
    # Show sample entities
    if total_people:
        print(f"\nSample people: {', '.join(list(total_people)[:10])}")
    if total_locations:
        print(f"Sample locations: {', '.join(list(total_locations)[:10])}")
    if total_organizations:
        print(f"Sample organizations: {', '.join(list(total_organizations)[:5])}")
    
    print("\n" + "=" * 70)
    print("✅ Metadata index built successfully!")
    print("Database saved to: data/metadata.db")
    print("=" * 70)
    
    store.close()
    return True


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="WARNING")  # Only show warnings and errors
    
    success = build_index()
    sys.exit(0 if success else 1)

