"""
Simple script to list all unique metadata tags from the database

Usage:
    python scripts/list_metadata_tags.py
    python scripts/list_metadata_tags.py --type people
    python scripts/list_metadata_tags.py --top 20
    python scripts/list_metadata_tags.py --search Maxwell
    python scripts/list_metadata_tags.py --export tags_output.txt
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.metadata_store import MetadataStore
from src.metadata_tags import MetadataTagsRetriever


def main():
    parser = argparse.ArgumentParser(description='Retrieve unique metadata tags')
    parser.add_argument('--type', '-t', 
                       choices=['all', 'people', 'organizations', 'locations', 'dates', 'emails'],
                       default='all',
                       help='Entity type to retrieve (default: all)')
    parser.add_argument('--top', '-n', type=int, default=None,
                       help='Show only top N most frequent tags')
    parser.add_argument('--search', '-s', type=str, default=None,
                       help='Search for tags containing this string')
    parser.add_argument('--export', '-e', type=str, default=None,
                       help='Export tags to file')
    parser.add_argument('--frequencies', '-f', action='store_true',
                       help='Include document frequencies')
    parser.add_argument('--stats', action='store_true',
                       help='Show statistics only')
    parser.add_argument('--db', default='data/metadata.db',
                       help='Path to metadata database (default: data/metadata.db)')
    
    args = parser.parse_args()
    
    # Create retriever
    print(f"Loading metadata from: {args.db}")
    metadata_store = MetadataStore(args.db)
    retriever = MetadataTagsRetriever(metadata_store)
    
    try:
        # Handle different modes
        if args.stats:
            show_statistics(retriever)
        elif args.search:
            search_tags(retriever, args.search, args.type)
        elif args.export:
            export_tags(retriever, args.export, args.type, args.frequencies)
        elif args.top:
            show_top_tags(retriever, args.type, args.top, args.frequencies)
        else:
            show_all_tags(retriever, args.type, args.frequencies)
    
    finally:
        metadata_store.close()


def show_all_tags(retriever, entity_type, include_frequencies):
    """Show all unique tags"""
    print("\n" + "=" * 70)
    print("UNIQUE METADATA TAGS")
    print("=" * 70)
    
    if include_frequencies:
        frequencies = retriever.get_tag_frequencies(entity_type)
        
        for ent_type, tag_freqs in frequencies.items():
            print(f"\n{ent_type.upper()} ({len(tag_freqs)} unique):")
            print("-" * 70)
            
            # Sort by frequency
            sorted_tags = sorted(tag_freqs.items(), key=lambda x: x[1], reverse=True)
            
            for tag, count in sorted_tags[:50]:  # Show first 50
                print(f"  {tag:<50} ({count} docs)")
            
            if len(sorted_tags) > 50:
                print(f"  ... and {len(sorted_tags) - 50} more")
    else:
        all_tags = retriever.get_all_unique_tags()
        
        if entity_type == 'all':
            for ent_type, tags in all_tags.items():
                print(f"\n{ent_type.upper()} ({len(tags)} unique):")
                print("-" * 70)
                for tag in tags[:50]:  # Show first 50
                    print(f"  {tag}")
                if len(tags) > 50:
                    print(f"  ... and {len(tags) - 50} more")
        else:
            tags = all_tags.get(entity_type, [])
            print(f"\n{entity_type.upper()} ({len(tags)} unique):")
            print("-" * 70)
            for tag in tags:
                print(f"  {tag}")


def show_top_tags(retriever, entity_type, limit, include_frequencies):
    """Show top N most frequent tags"""
    print("\n" + "=" * 70)
    print(f"TOP {limit} MOST FREQUENT TAGS")
    print("=" * 70)
    
    if entity_type == 'all':
        types_to_show = ['people', 'organizations', 'locations', 'dates', 'emails']
    else:
        types_to_show = [entity_type]
    
    for ent_type in types_to_show:
        print(f"\n{ent_type.upper()}:")
        print("-" * 70)
        
        top_tags = retriever.get_top_tags(ent_type, limit)
        
        if not top_tags:
            print("  (no data)")
            continue
        
        for i, (tag, count) in enumerate(top_tags, 1):
            print(f"{i:3}. {tag:<50} ({count} documents)")


def search_tags(retriever, query, entity_type):
    """Search for tags matching query"""
    print("\n" + "=" * 70)
    print(f"SEARCH RESULTS FOR: '{query}'")
    print("=" * 70)
    
    results = retriever.search_tags(query, entity_type, case_sensitive=False)
    
    if not results:
        print("\nNo matches found.")
        return
    
    total_matches = sum(len(matches) for matches in results.values())
    print(f"\nFound {total_matches} matches:")
    
    for ent_type, matches in results.items():
        print(f"\n{ent_type.upper()} ({len(matches)} matches):")
        print("-" * 70)
        for match in matches:
            print(f"  {match}")


def export_tags(retriever, filepath, entity_type, include_frequencies):
    """Export tags to file"""
    print("\n" + "=" * 70)
    print("EXPORTING TAGS")
    print("=" * 70)
    
    retriever.export_tags_to_file(filepath, entity_type, include_frequencies)
    
    print(f"\n✓ Exported to: {filepath}")
    print(f"  Entity type: {entity_type}")
    print(f"  Include frequencies: {include_frequencies}")


def show_statistics(retriever):
    """Show statistics about tags"""
    print("\n" + "=" * 70)
    print("METADATA TAGS STATISTICS")
    print("=" * 70)
    
    stats = retriever.get_tags_statistics()
    
    print(f"\nTotal unique tags: {stats['total_unique_tags']}")
    
    print("\n" + "-" * 70)
    print("COUNTS BY TYPE")
    print("-" * 70)
    for entity_type, count in stats['total_counts'].items():
        print(f"  {entity_type:<20} {count:>6} unique")
    
    print("\n" + "-" * 70)
    print("MOST COMMON TAGS")
    print("-" * 70)
    for entity_type, data in stats['most_common'].items():
        print(f"  {entity_type:<20} '{data['tag']}' ({data['count']} documents)")
    
    print("\n" + "-" * 70)
    print("AVERAGE FREQUENCY (docs per tag)")
    print("-" * 70)
    for entity_type, avg_freq in stats['average_frequency'].items():
        print(f"  {entity_type:<20} {avg_freq:>6.2f} documents/tag")


if __name__ == "__main__":
    main()

