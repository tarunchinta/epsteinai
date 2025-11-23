"""
Example: Retrieve and work with unique metadata tags

This script demonstrates how to retrieve and analyze unique metadata tags
from your document corpus.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.metadata_store import MetadataStore
from src.metadata_tags import MetadataTagsRetriever, get_unique_tags


def example_1_get_all_tags():
    """Example 1: Get all unique tags"""
    print("=" * 70)
    print("EXAMPLE 1: Get All Unique Tags")
    print("=" * 70)
    
    # Simple method using convenience function
    tags = get_unique_tags("data/metadata.db")
    
    print("\nAll unique tags:")
    for entity_type, tag_list in tags.items():
        print(f"  {entity_type}: {len(tag_list)} unique tags")
        print(f"    Sample: {', '.join(tag_list[:5])}")
        if len(tag_list) > 5:
            print(f"    ... and {len(tag_list) - 5} more")


def example_2_get_frequencies():
    """Example 2: Get tag frequencies"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Get Tag Frequencies")
    print("=" * 70)
    
    store = MetadataStore("data/metadata.db")
    retriever = MetadataTagsRetriever(store)
    
    # Get frequencies for people
    frequencies = retriever.get_tag_frequencies('people')
    
    print("\nMost frequent people (top 10):")
    people_freqs = sorted(
        frequencies['people'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    for i, (person, count) in enumerate(people_freqs, 1):
        print(f"  {i:2}. {person:<40} appears in {count} documents")
    
    store.close()


def example_3_search_tags():
    """Example 3: Search for specific tags"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Search Tags")
    print("=" * 70)
    
    store = MetadataStore("data/metadata.db")
    retriever = MetadataTagsRetriever(store)
    
    # Search for tags containing "Maxwell"
    search_term = "Maxwell"
    results = retriever.search_tags(search_term, entity_type='all')
    
    print(f"\nSearching for '{search_term}':")
    for entity_type, matches in results.items():
        print(f"\n  {entity_type.upper()}: {len(matches)} matches")
        for match in matches[:5]:
            print(f"    - {match}")
        if len(matches) > 5:
            print(f"    ... and {len(matches) - 5} more")
    
    store.close()


def example_4_get_statistics():
    """Example 4: Get statistics about tags"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Get Statistics")
    print("=" * 70)
    
    store = MetadataStore("data/metadata.db")
    retriever = MetadataTagsRetriever(store)
    
    stats = retriever.get_tags_statistics()
    
    print(f"\nTotal unique tags across all types: {stats['total_unique_tags']}")
    
    print("\nBreakdown by entity type:")
    for entity_type, count in stats['total_counts'].items():
        avg = stats['average_frequency'].get(entity_type, 0)
        print(f"  {entity_type:<20}: {count:>6} unique tags (avg {avg:.1f} docs/tag)")
    
    print("\nMost common tag in each category:")
    for entity_type, data in stats['most_common'].items():
        print(f"  {entity_type:<20}: '{data['tag']}' ({data['count']} documents)")
    
    store.close()


def example_5_top_tags():
    """Example 5: Get top N most frequent tags"""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Top Tags by Category")
    print("=" * 70)
    
    store = MetadataStore("data/metadata.db")
    retriever = MetadataTagsRetriever(store)
    
    categories = [
        ('people', 'PEOPLE'),
        ('locations', 'LOCATIONS'),
        ('organizations', 'ORGANIZATIONS')
    ]
    
    for category, label in categories:
        print(f"\nTop 5 {label}:")
        top_tags = retriever.get_top_tags(category, limit=5)
        
        for i, (tag, count) in enumerate(top_tags, 1):
            print(f"  {i}. {tag:<35} ({count} docs)")
    
    store.close()


def example_6_co_occurring_tags():
    """Example 6: Find co-occurring tags"""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Co-occurring Tags")
    print("=" * 70)
    
    store = MetadataStore("data/metadata.db")
    retriever = MetadataTagsRetriever(store)
    
    # Get top person
    top_people = retriever.get_top_tags('people', limit=1)
    
    if top_people:
        target_person = top_people[0][0]
        print(f"\nFinding tags that co-occur with '{target_person}':")
        
        # Get co-occurring people
        co_people = retriever.get_co_occurring_tags(target_person, 'people', limit=5)
        print(f"\n  Co-occurring PEOPLE:")
        for person, count in co_people:
            print(f"    - {person:<40} ({count} documents)")
        
        # Get co-occurring locations
        co_locations = retriever.get_co_occurring_tags(target_person, 'locations', limit=5)
        if co_locations:
            print(f"\n  Co-occurring LOCATIONS:")
            for location, count in co_locations:
                print(f"    - {location:<40} ({count} documents)")
    
    store.close()


def example_7_export_tags():
    """Example 7: Export tags to file"""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Export Tags to File")
    print("=" * 70)
    
    store = MetadataStore("data/metadata.db")
    retriever = MetadataTagsRetriever(store)
    
    # Export all tags with frequencies
    output_file = "data/exported_tags.txt"
    retriever.export_tags_to_file(
        output_file,
        entity_type='all',
        include_frequencies=True
    )
    
    print(f"\n✓ Exported all tags with frequencies to: {output_file}")
    
    # Export just people (no frequencies)
    output_file_people = "data/people_tags.txt"
    retriever.export_tags_to_file(
        output_file_people,
        entity_type='people',
        include_frequencies=False
    )
    
    print(f"✓ Exported people tags to: {output_file_people}")
    
    store.close()


def example_8_filter_by_frequency():
    """Example 8: Filter tags by minimum frequency"""
    print("\n" + "=" * 70)
    print("EXAMPLE 8: Filter Tags by Frequency")
    print("=" * 70)
    
    store = MetadataStore("data/metadata.db")
    retriever = MetadataTagsRetriever(store)
    
    # Get tags that appear in at least 5 documents
    min_frequency = 5
    frequencies = retriever.get_tag_frequencies('people')
    
    frequent_people = {
        person: count 
        for person, count in frequencies['people'].items() 
        if count >= min_frequency
    }
    
    print(f"\nPeople appearing in at least {min_frequency} documents:")
    print(f"Found {len(frequent_people)} people")
    
    # Show top 10
    sorted_people = sorted(
        frequent_people.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    for person, count in sorted_people:
        print(f"  {person:<40} ({count} documents)")
    
    store.close()


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("METADATA TAGS RETRIEVAL EXAMPLES")
    print("=" * 70)
    print("\nThis script demonstrates how to retrieve and work with unique")
    print("metadata tags from your document corpus.")
    
    try:
        example_1_get_all_tags()
        example_2_get_frequencies()
        example_3_search_tags()
        example_4_get_statistics()
        example_5_top_tags()
        example_6_co_occurring_tags()
        example_7_export_tags()
        example_8_filter_by_frequency()
        
        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETE!")
        print("=" * 70)
        print("\nYou can now use these patterns in your own code.")
        print("See src/metadata_tags.py for the full API.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("  1. Built the metadata index: python build_metadata_index.py")
        print("  2. The database exists at: data/metadata.db")


if __name__ == "__main__":
    main()

