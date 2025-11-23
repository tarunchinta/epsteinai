"""
Utility for retrieving and analyzing unique metadata tags
"""

from typing import Dict, List, Optional, Set
from collections import Counter
from src.metadata_store import MetadataStore
from loguru import logger


class MetadataTagsRetriever:
    """Retrieve and analyze unique metadata tags from the metadata store"""
    
    def __init__(self, metadata_store: MetadataStore):
        """
        Initialize with metadata store
        
        Args:
            metadata_store: MetadataStore instance
        """
        self.metadata_store = metadata_store
    
    def get_all_unique_tags(self) -> Dict[str, List[str]]:
        """
        Get all unique metadata tags across all entity types
        
        Returns:
            Dictionary with keys: 'people', 'organizations', 'locations', 'dates', 'emails'
        """
        cursor = self.metadata_store.conn.cursor()
        
        tags = {
            'people': [],
            'organizations': [],
            'locations': [],
            'dates': [],
            'emails': []
        }
        
        # Get unique people
        cursor.execute("SELECT DISTINCT name FROM people ORDER BY name")
        tags['people'] = [row['name'] for row in cursor.fetchall()]
        
        # Get unique organizations
        cursor.execute("SELECT DISTINCT name FROM organizations ORDER BY name")
        tags['organizations'] = [row['name'] for row in cursor.fetchall()]
        
        # Get unique locations
        cursor.execute("SELECT DISTINCT name FROM locations ORDER BY name")
        tags['locations'] = [row['name'] for row in cursor.fetchall()]
        
        # Get unique dates
        cursor.execute("SELECT DISTINCT date_str FROM dates ORDER BY date_str")
        tags['dates'] = [row['date_str'] for row in cursor.fetchall()]
        
        # Get unique emails
        cursor.execute("SELECT DISTINCT email FROM emails ORDER BY email")
        tags['emails'] = [row['email'] for row in cursor.fetchall()]
        
        logger.info(f"Retrieved {len(tags['people'])} people, "
                   f"{len(tags['organizations'])} organizations, "
                   f"{len(tags['locations'])} locations, "
                   f"{len(tags['dates'])} dates, "
                   f"{len(tags['emails'])} emails")
        
        return tags
    
    def get_tag_frequencies(self, entity_type: str = 'all') -> Dict[str, Dict[str, int]]:
        """
        Get frequency counts for each tag (how many documents contain each tag)
        
        Args:
            entity_type: 'people', 'organizations', 'locations', 'dates', 'emails', or 'all'
        
        Returns:
            Dictionary mapping entity_type -> {tag: count}
        """
        cursor = self.metadata_store.conn.cursor()
        frequencies = {}
        
        entity_tables = {
            'people': 'people',
            'organizations': 'organizations',
            'locations': 'locations',
            'dates': 'dates',
            'emails': 'emails'
        }
        
        # Determine which tables to query
        if entity_type == 'all':
            tables_to_query = entity_tables
        elif entity_type in entity_tables:
            tables_to_query = {entity_type: entity_tables[entity_type]}
        else:
            raise ValueError(f"Invalid entity_type: {entity_type}. Must be one of {list(entity_tables.keys())} or 'all'")
        
        # Query each table
        for entity_name, table_name in tables_to_query.items():
            if table_name in ['people', 'organizations', 'locations']:
                query = f"""
                    SELECT name, COUNT(DISTINCT doc_id) as count 
                    FROM {table_name} 
                    GROUP BY name 
                    ORDER BY count DESC, name
                """
                cursor.execute(query)
                frequencies[entity_name] = {
                    row['name']: row['count'] for row in cursor.fetchall()
                }
            elif table_name == 'dates':
                query = """
                    SELECT date_str, COUNT(DISTINCT doc_id) as count 
                    FROM dates 
                    GROUP BY date_str 
                    ORDER BY count DESC, date_str
                """
                cursor.execute(query)
                frequencies['dates'] = {
                    row['date_str']: row['count'] for row in cursor.fetchall()
                }
            elif table_name == 'emails':
                query = """
                    SELECT email, COUNT(DISTINCT doc_id) as count 
                    FROM emails 
                    GROUP BY email 
                    ORDER BY count DESC, email
                """
                cursor.execute(query)
                frequencies['emails'] = {
                    row['email']: row['count'] for row in cursor.fetchall()
                }
        
        return frequencies
    
    def get_top_tags(self, entity_type: str, limit: int = 10) -> List[tuple]:
        """
        Get the most frequent tags for a given entity type
        
        Args:
            entity_type: 'people', 'organizations', 'locations', 'dates', or 'emails'
            limit: Number of top tags to return
        
        Returns:
            List of (tag, count) tuples sorted by count descending
        """
        frequencies = self.get_tag_frequencies(entity_type)
        
        if entity_type not in frequencies:
            return []
        
        # Sort by count descending
        sorted_tags = sorted(
            frequencies[entity_type].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_tags[:limit]
    
    def search_tags(self, query: str, entity_type: str = 'all', 
                   case_sensitive: bool = False) -> Dict[str, List[str]]:
        """
        Search for tags matching a query string
        
        Args:
            query: Search query
            entity_type: Entity type to search ('all' or specific type)
            case_sensitive: Whether search is case sensitive
        
        Returns:
            Dictionary of matching tags by entity type
        """
        all_tags = self.get_all_unique_tags()
        results = {}
        
        # Determine which entity types to search
        if entity_type == 'all':
            search_types = all_tags.keys()
        else:
            search_types = [entity_type] if entity_type in all_tags else []
        
        # Search each entity type
        for ent_type in search_types:
            matches = []
            for tag in all_tags[ent_type]:
                if case_sensitive:
                    if query in tag:
                        matches.append(tag)
                else:
                    if query.lower() in tag.lower():
                        matches.append(tag)
            
            if matches:
                results[ent_type] = matches
        
        return results
    
    def get_tags_statistics(self) -> Dict:
        """
        Get statistics about all tags in the metadata store
        
        Returns:
            Dictionary with statistics
        """
        all_tags = self.get_all_unique_tags()
        all_frequencies = self.get_tag_frequencies('all')
        
        stats = {
            'total_counts': {
                entity_type: len(tags) 
                for entity_type, tags in all_tags.items()
            },
            'total_unique_tags': sum(len(tags) for tags in all_tags.values()),
            'most_common': {},
            'average_frequency': {}
        }
        
        # Get most common for each type
        for entity_type in ['people', 'organizations', 'locations', 'dates', 'emails']:
            if entity_type in all_frequencies and all_frequencies[entity_type]:
                most_common = max(
                    all_frequencies[entity_type].items(),
                    key=lambda x: x[1]
                )
                stats['most_common'][entity_type] = {
                    'tag': most_common[0],
                    'count': most_common[1]
                }
                
                # Calculate average frequency
                avg_freq = sum(all_frequencies[entity_type].values()) / len(all_frequencies[entity_type])
                stats['average_frequency'][entity_type] = round(avg_freq, 2)
        
        return stats
    
    def export_tags_to_file(self, filepath: str, entity_type: str = 'all',
                           include_frequencies: bool = False):
        """
        Export tags to a text file
        
        Args:
            filepath: Path to output file
            entity_type: Which entity type to export ('all' or specific)
            include_frequencies: Whether to include frequency counts
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            if include_frequencies:
                frequencies = self.get_tag_frequencies(entity_type)
                
                for ent_type, tag_freqs in frequencies.items():
                    f.write(f"\n=== {ent_type.upper()} ===\n")
                    for tag, count in sorted(tag_freqs.items(), 
                                            key=lambda x: x[1], 
                                            reverse=True):
                        f.write(f"{tag}: {count} documents\n")
            else:
                all_tags = self.get_all_unique_tags()
                
                if entity_type == 'all':
                    for ent_type, tags in all_tags.items():
                        f.write(f"\n=== {ent_type.upper()} ===\n")
                        for tag in tags:
                            f.write(f"{tag}\n")
                elif entity_type in all_tags:
                    for tag in all_tags[entity_type]:
                        f.write(f"{tag}\n")
        
        logger.info(f"Exported tags to {filepath}")
    
    def get_co_occurring_tags(self, tag: str, entity_type: str, 
                             limit: int = 10) -> List[tuple]:
        """
        Find tags that frequently co-occur with a given tag
        
        Args:
            tag: The tag to find co-occurrences for
            entity_type: Entity type of the tag
            limit: Number of results to return
        
        Returns:
            List of (co_occurring_tag, count) tuples
        """
        cursor = self.metadata_store.conn.cursor()
        
        # Map entity type to table name
        table_map = {
            'people': 'people',
            'organizations': 'organizations',
            'locations': 'locations'
        }
        
        if entity_type not in table_map:
            logger.warning(f"Co-occurrence not supported for entity type: {entity_type}")
            return []
        
        table_name = table_map[entity_type]
        
        # Find documents containing the tag
        cursor.execute(
            f"SELECT DISTINCT doc_id FROM {table_name} WHERE name = ?",
            (tag,)
        )
        doc_ids = [row['doc_id'] for row in cursor.fetchall()]
        
        if not doc_ids:
            return []
        
        # Find other tags in those documents
        placeholders = ','.join(['?'] * len(doc_ids))
        query = f"""
            SELECT name, COUNT(*) as count 
            FROM {table_name} 
            WHERE doc_id IN ({placeholders}) AND name != ?
            GROUP BY name 
            ORDER BY count DESC
            LIMIT ?
        """
        
        cursor.execute(query, doc_ids + [tag, limit])
        results = [(row['name'], row['count']) for row in cursor.fetchall()]
        
        return results


# Convenience function
def get_unique_tags(db_path: str = "data/metadata.db") -> Dict[str, List[str]]:
    """
    Quick function to get all unique tags
    
    Args:
        db_path: Path to metadata database
    
    Returns:
        Dictionary of unique tags by entity type
    """
    store = MetadataStore(db_path)
    retriever = MetadataTagsRetriever(store)
    tags = retriever.get_all_unique_tags()
    store.close()
    return tags


# Usage Example
if __name__ == "__main__":
    # Create retriever
    metadata_store = MetadataStore("data/metadata.db")
    retriever = MetadataTagsRetriever(metadata_store)
    
    # Get all unique tags
    print("=" * 70)
    print("ALL UNIQUE TAGS")
    print("=" * 70)
    all_tags = retriever.get_all_unique_tags()
    for entity_type, tags in all_tags.items():
        print(f"\n{entity_type.upper()} ({len(tags)} unique):")
        print(f"  {', '.join(tags[:10])}")
        if len(tags) > 10:
            print(f"  ... and {len(tags) - 10} more")
    
    # Get statistics
    print("\n" + "=" * 70)
    print("STATISTICS")
    print("=" * 70)
    stats = retriever.get_tags_statistics()
    print(f"Total unique tags: {stats['total_unique_tags']}")
    print(f"\nCounts by type:")
    for entity_type, count in stats['total_counts'].items():
        print(f"  - {entity_type}: {count}")
    
    print(f"\nMost common tags:")
    for entity_type, data in stats['most_common'].items():
        print(f"  - {entity_type}: '{data['tag']}' ({data['count']} docs)")
    
    # Get top tags
    print("\n" + "=" * 70)
    print("TOP 10 PEOPLE")
    print("=" * 70)
    top_people = retriever.get_top_tags('people', limit=10)
    for i, (person, count) in enumerate(top_people, 1):
        print(f"{i:2}. {person:<40} ({count} documents)")
    
    # Search tags
    print("\n" + "=" * 70)
    print("SEARCH: 'Maxwell'")
    print("=" * 70)
    search_results = retriever.search_tags('Maxwell')
    for entity_type, matches in search_results.items():
        print(f"\n{entity_type.upper()}: {matches}")
    
    # Get co-occurring tags
    if top_people:
        top_person = top_people[0][0]
        print("\n" + "=" * 70)
        print(f"TAGS CO-OCCURRING WITH: '{top_person}'")
        print("=" * 70)
        co_occurring = retriever.get_co_occurring_tags(top_person, 'people', limit=10)
        for i, (tag, count) in enumerate(co_occurring, 1):
            print(f"{i:2}. {tag:<40} ({count} co-occurrences)")
    
    # Export to file
    print("\n" + "=" * 70)
    print("EXPORTING TO FILE")
    print("=" * 70)
    retriever.export_tags_to_file(
        'data/unique_tags.txt',
        entity_type='all',
        include_frequencies=True
    )
    print("✓ Exported to data/unique_tags.txt")
    
    metadata_store.close()

