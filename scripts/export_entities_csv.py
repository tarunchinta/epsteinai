"""
Command-line tool to export cleaned and validated entities to CSV

Usage:
    python scripts/export_entities_csv.py
    python scripts/export_entities_csv.py --type people --output people.csv
    python scripts/export_entities_csv.py --comprehensive --output-dir exports
    python scripts/export_entities_csv.py --type people --with-documents
    python scripts/export_entities_csv.py --matrix --top 100
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.metadata_store import MetadataStore
from src.export_entities import EntityCSVExporter


def main():
    parser = argparse.ArgumentParser(
        description='Export cleaned and validated entities to CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all entities with frequencies
  python scripts/export_entities_csv.py --output all_entities.csv
  
  # Export only people
  python scripts/export_entities_csv.py --type people --output people.csv
  
  # Export people with document IDs
  python scripts/export_entities_csv.py --type people --with-documents --output people_docs.csv
  
  # Export top 50 people with minimum 5 mentions
  python scripts/export_entities_csv.py --type people --min-freq 5 --limit 50 --output top_people.csv
  
  # Export co-occurrence matrix for top 100 people
  python scripts/export_entities_csv.py --matrix --type people --top 100 --output cooccurrence.csv
  
  # Comprehensive export (all formats)
  python scripts/export_entities_csv.py --comprehensive --output-dir exports
        """
    )
    
    parser.add_argument('--type', '-t',
                       choices=['all', 'people', 'organizations', 'locations', 'dates', 'emails'],
                       default='all',
                       help='Entity type to export (default: all)')
    
    parser.add_argument('--output', '-o',
                       default='exports/entities.csv',
                       help='Output CSV file path (default: exports/entities.csv)')
    
    parser.add_argument('--output-dir', '-d',
                       default='exports',
                       help='Output directory for comprehensive export (default: exports)')
    
    parser.add_argument('--min-freq', '-m',
                       type=int,
                       default=1,
                       help='Minimum document frequency to include (default: 1)')
    
    parser.add_argument('--limit', '-l',
                       type=int,
                       default=None,
                       help='Limit number of entities to export')
    
    parser.add_argument('--with-documents', '-w',
                       action='store_true',
                       help='Include list of document IDs for each entity')
    
    parser.add_argument('--matrix',
                       action='store_true',
                       help='Export co-occurrence matrix')
    
    parser.add_argument('--top',
                       type=int,
                       default=50,
                       help='For matrix export, number of top entities to include (default: 50)')
    
    parser.add_argument('--comprehensive', '-c',
                       action='store_true',
                       help='Export all entities in multiple formats')
    
    parser.add_argument('--db',
                       default='data/metadata.db',
                       help='Path to metadata database (default: data/metadata.db)')
    
    args = parser.parse_args()
    
    # Create exporter
    print(f"Loading metadata from: {args.db}")
    try:
        store = MetadataStore(args.db)
        exporter = EntityCSVExporter(store)
    except Exception as e:
        print(f"Error loading database: {e}")
        print("\nMake sure you have:")
        print("  1. Built the metadata index: python build_metadata_index.py")
        print("  2. The database exists at: data/metadata.db")
        return 1
    
    try:
        if args.comprehensive:
            # Comprehensive export
            print("\nPerforming comprehensive export...")
            exports = exporter.export_all_entities_comprehensive(args.output_dir)
            
            print("\n" + "=" * 70)
            print("COMPREHENSIVE EXPORT COMPLETE!")
            print("=" * 70)
            print(f"\n{len(exports)} files created in '{args.output_dir}/':\n")
            for export_type, filepath in exports.items():
                print(f"  ✓ {export_type:<30} → {filepath}")
            
        elif args.matrix:
            # Co-occurrence matrix export
            print(f"\nExporting {args.type} co-occurrence matrix...")
            print(f"  Top {args.top} entities")
            print(f"  Output: {args.output}")
            
            exporter.export_entity_matrix(
                args.output,
                entity_type=args.type,
                top_n=args.top
            )
            
            print(f"\n✓ Co-occurrence matrix exported to: {args.output}")
            
        elif args.with_documents:
            # Export with document IDs
            print(f"\nExporting {args.type} with document IDs...")
            print(f"  Limit: {args.limit if args.limit else 'None (all)'}")
            print(f"  Output: {args.output}")
            
            exporter.export_entities_with_documents(
                args.output,
                entity_type=args.type,
                limit=args.limit
            )
            
            print(f"\n✓ Entities with documents exported to: {args.output}")
            
        else:
            # Standard frequency export
            print(f"\nExporting {args.type} entities...")
            print(f"  Minimum frequency: {args.min_freq}")
            print(f"  Output: {args.output}")
            
            exporter.export_entities_with_frequencies(
                args.output,
                entity_type=args.type,
                min_frequency=args.min_freq
            )
            
            print(f"\n✓ Entities exported to: {args.output}")
        
        print("\n" + "=" * 70)
        print("EXPORT SUCCESSFUL!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error during export: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        store.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

