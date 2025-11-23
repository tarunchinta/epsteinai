"""
Example: Export cleaned and validated entities to CSV

This script demonstrates various ways to export your cleaned metadata entities.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.metadata_store import MetadataStore
from src.export_entities import EntityCSVExporter, export_entities_to_csv, export_all_entities


def example_1_simple_export():
    """Example 1: Simple export using convenience function"""
    print("=" * 70)
    print("EXAMPLE 1: Simple Export")
    print("=" * 70)
    
    # One-liner to export all entities
    export_entities_to_csv(
        output_file='exports/example_all_entities.csv',
        entity_type='all',
        min_frequency=1
    )
    
    print("\n✓ Exported all entities to: exports/example_all_entities.csv")


def example_2_export_specific_type():
    """Example 2: Export specific entity type"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Export Specific Entity Type")
    print("=" * 70)
    
    store = MetadataStore("data/metadata.db")
    exporter = EntityCSVExporter(store)
    
    # Export only people
    print("\nExporting people...")
    exporter.export_entities_with_frequencies(
        'exports/example_people.csv',
        entity_type='people',
        min_frequency=1
    )
    print("✓ Exported to: exports/example_people.csv")
    
    # Export only locations
    print("\nExporting locations...")
    exporter.export_entities_with_frequencies(
        'exports/example_locations.csv',
        entity_type='locations',
        min_frequency=1
    )
    print("✓ Exported to: exports/example_locations.csv")
    
    store.close()


def example_3_export_with_documents():
    """Example 3: Export entities with document IDs"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Export With Document IDs")
    print("=" * 70)
    
    store = MetadataStore("data/metadata.db")
    exporter = EntityCSVExporter(store)
    
    # Export people with all documents they appear in
    print("\nExporting people with document IDs (top 50)...")
    exporter.export_entities_with_documents(
        'exports/example_people_with_docs.csv',
        entity_type='people',
        limit=50
    )
    print("✓ Exported to: exports/example_people_with_docs.csv")
    print("  (Shows which documents each person appears in)")
    
    store.close()


def example_4_filter_by_frequency():
    """Example 4: Export only frequently mentioned entities"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Filter by Minimum Frequency")
    print("=" * 70)
    
    store = MetadataStore("data/metadata.db")
    exporter = EntityCSVExporter(store)
    
    # Export only people mentioned in at least 5 documents
    print("\nExporting people mentioned in 5+ documents...")
    exporter.export_entities_with_frequencies(
        'exports/example_frequent_people.csv',
        entity_type='people',
        min_frequency=5
    )
    print("✓ Exported to: exports/example_frequent_people.csv")
    print("  (Only entities appearing in 5+ documents)")
    
    store.close()


def example_5_export_document_metadata():
    """Example 5: Export document-level metadata"""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Export Document Metadata")
    print("=" * 70)
    
    store = MetadataStore("data/metadata.db")
    exporter = EntityCSVExporter(store)
    
    # Export metadata for all documents
    print("\nExporting document metadata...")
    exporter.export_document_metadata('exports/example_documents.csv')
    print("✓ Exported to: exports/example_documents.csv")
    print("  (Shows all entities for each document)")
    
    store.close()


def example_6_cooccurrence_matrix():
    """Example 6: Export entity co-occurrence matrix"""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Co-occurrence Matrix")
    print("=" * 70)
    
    store = MetadataStore("data/metadata.db")
    exporter = EntityCSVExporter(store)
    
    # Export co-occurrence matrix for top 30 people
    print("\nExporting co-occurrence matrix for top 30 people...")
    exporter.export_entity_matrix(
        'exports/example_cooccurrence.csv',
        entity_type='people',
        top_n=30
    )
    print("✓ Exported to: exports/example_cooccurrence.csv")
    print("  (Shows which people appear together in documents)")
    
    store.close()


def example_7_comprehensive_export():
    """Example 7: Comprehensive export (all formats)"""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Comprehensive Export")
    print("=" * 70)
    
    # One-liner to export everything
    print("\nPerforming comprehensive export...")
    exports = export_all_entities(output_dir='exports/comprehensive')
    
    print("\n✓ Comprehensive export complete!")
    print(f"\nCreated {len(exports)} files:")
    for export_type, filepath in exports.items():
        print(f"  - {export_type}: {filepath}")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("ENTITY CSV EXPORT EXAMPLES")
    print("=" * 70)
    print("\nThis script demonstrates how to export cleaned and validated")
    print("entities to CSV format for analysis.")
    
    try:
        example_1_simple_export()
        example_2_export_specific_type()
        example_3_export_with_documents()
        example_4_filter_by_frequency()
        example_5_export_document_metadata()
        example_6_cooccurrence_matrix()
        example_7_comprehensive_export()
        
        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETE!")
        print("=" * 70)
        print("\nCheck the 'exports/' directory for all generated CSV files.")
        print("You can open these files in Excel, Google Sheets, or any CSV viewer.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("  1. Built the metadata index: python build_metadata_index.py")
        print("  2. The database exists at: data/metadata.db")


if __name__ == "__main__":
    main()

