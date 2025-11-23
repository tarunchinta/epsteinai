"""
Export cleaned and validated entities to CSV format
"""

import csv
from typing import List, Dict, Optional
from pathlib import Path
from src.metadata_store import MetadataStore
from src.metadata_tags import MetadataTagsRetriever
from loguru import logger


class EntityCSVExporter:
    """Export metadata entities to CSV files"""
    
    def __init__(self, metadata_store: MetadataStore):
        """
        Initialize exporter
        
        Args:
            metadata_store: MetadataStore instance
        """
        self.metadata_store = metadata_store
        self.retriever = MetadataTagsRetriever(metadata_store)
    
    def export_entities_with_frequencies(self, 
                                        output_file: str,
                                        entity_type: str = 'all',
                                        min_frequency: int = 1) -> None:
        """
        Export entities with their document frequencies
        
        Args:
            output_file: Path to output CSV file
            entity_type: 'all', 'people', 'organizations', 'locations', 'dates', 'emails'
            min_frequency: Minimum document frequency to include
        """
        # Get frequencies
        frequencies = self.retriever.get_tag_frequencies(entity_type)
        
        # Prepare output path
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Entity Type', 'Entity', 'Document Count'])
            
            # Write data
            total_exported = 0
            for ent_type, entity_freqs in frequencies.items():
                # Sort by frequency descending
                sorted_entities = sorted(
                    entity_freqs.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                
                for entity, count in sorted_entities:
                    if count >= min_frequency:
                        writer.writerow([ent_type, entity, count])
                        total_exported += 1
        
        logger.info(f"Exported {total_exported} entities to {output_file}")
    
    def export_entities_with_documents(self,
                                      output_file: str,
                                      entity_type: str = 'people',
                                      limit: Optional[int] = None) -> None:
        """
        Export entities with the list of documents they appear in
        
        Args:
            output_file: Path to output CSV file
            entity_type: 'people', 'organizations', 'locations', 'dates', 'emails'
            limit: Maximum number of entities to export (most frequent first)
        """
        cursor = self.metadata_store.conn.cursor()
        
        # Map entity type to table
        table_map = {
            'people': 'people',
            'organizations': 'organizations',
            'locations': 'locations',
            'dates': 'dates',
            'emails': 'emails'
        }
        
        if entity_type not in table_map:
            raise ValueError(f"Invalid entity_type: {entity_type}")
        
        table_name = table_map[entity_type]
        name_column = 'name' if table_name != 'dates' and table_name != 'emails' else ('date_str' if table_name == 'dates' else 'email')
        
        # Get entities with their documents
        query = f"""
            SELECT {name_column} as entity, 
                   GROUP_CONCAT(doc_id, '; ') as doc_ids,
                   COUNT(DISTINCT doc_id) as doc_count
            FROM {table_name}
            GROUP BY {name_column}
            ORDER BY doc_count DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Write to CSV
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Entity', 'Document Count', 'Document IDs'])
            
            for row in results:
                writer.writerow([row['entity'], row['doc_count'], row['doc_ids']])
        
        logger.info(f"Exported {len(results)} {entity_type} to {output_file}")
    
    def export_document_metadata(self,
                                output_file: str,
                                doc_ids: Optional[List[str]] = None) -> None:
        """
        Export document-level metadata with all entities
        
        Args:
            output_file: Path to output CSV file
            doc_ids: Optional list of specific document IDs to export
        """
        cursor = self.metadata_store.conn.cursor()
        
        # Get all documents or specific ones
        if doc_ids:
            placeholders = ','.join(['?'] * len(doc_ids))
            query = f"SELECT doc_id FROM document_metadata WHERE doc_id IN ({placeholders})"
            cursor.execute(query, doc_ids)
        else:
            query = "SELECT doc_id FROM document_metadata ORDER BY doc_id"
            cursor.execute(query)
        
        doc_ids = [row['doc_id'] for row in cursor.fetchall()]
        
        # Write to CSV
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Document ID',
                'Word Count',
                'People',
                'Organizations',
                'Locations',
                'Dates',
                'Emails',
                'People Count',
                'Organizations Count',
                'Locations Count',
                'Dates Count',
                'Emails Count'
            ])
            
            for doc_id in doc_ids:
                metadata = self.metadata_store.get_metadata(doc_id)
                if metadata:
                    writer.writerow([
                        doc_id,
                        metadata['word_count'],
                        '; '.join(metadata['people']),
                        '; '.join(metadata['organizations']),
                        '; '.join(metadata['locations']),
                        '; '.join(metadata['dates']),
                        '; '.join(metadata['emails']),
                        len(metadata['people']),
                        len(metadata['organizations']),
                        len(metadata['locations']),
                        len(metadata['dates']),
                        len(metadata['emails'])
                    ])
        
        logger.info(f"Exported {len(doc_ids)} documents to {output_file}")
    
    def export_entity_matrix(self,
                           output_file: str,
                           entity_type: str = 'people',
                           top_n: int = 100) -> None:
        """
        Export entity co-occurrence matrix (which entities appear together)
        
        Args:
            output_file: Path to output CSV file
            entity_type: 'people', 'organizations', or 'locations'
            top_n: Number of top entities to include
        """
        # Get top entities
        top_entities = self.retriever.get_top_tags(entity_type, limit=top_n)
        entity_names = [entity for entity, _ in top_entities]
        
        if not entity_names:
            logger.warning(f"No entities found for type: {entity_type}")
            return
        
        # Build co-occurrence matrix
        matrix = {}
        for entity in entity_names:
            co_occurring = self.retriever.get_co_occurring_tags(
                entity, 
                entity_type, 
                limit=top_n
            )
            matrix[entity] = dict(co_occurring)
        
        # Write to CSV
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(['Entity'] + entity_names)
            
            # Data rows
            for entity in entity_names:
                row = [entity]
                for other_entity in entity_names:
                    if entity == other_entity:
                        row.append(0)  # Don't count self
                    else:
                        count = matrix.get(entity, {}).get(other_entity, 0)
                        row.append(count)
                writer.writerow(row)
        
        logger.info(f"Exported {len(entity_names)}x{len(entity_names)} co-occurrence matrix to {output_file}")
    
    def export_all_entities_comprehensive(self, output_dir: str = 'exports') -> Dict[str, str]:
        """
        Export all entities in multiple formats for comprehensive analysis
        
        Args:
            output_dir: Directory to save export files
            
        Returns:
            Dictionary mapping export type to file path
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        exports = {}
        
        # 1. All entities with frequencies
        file1 = f"{output_dir}/all_entities_frequencies.csv"
        self.export_entities_with_frequencies(file1, entity_type='all')
        exports['all_frequencies'] = file1
        
        # 2. People with documents
        file2 = f"{output_dir}/people_with_documents.csv"
        self.export_entities_with_documents(file2, entity_type='people', limit=None)
        exports['people_documents'] = file2
        
        # 3. Organizations with documents
        file3 = f"{output_dir}/organizations_with_documents.csv"
        self.export_entities_with_documents(file3, entity_type='organizations', limit=None)
        exports['organizations_documents'] = file3
        
        # 4. Locations with documents
        file4 = f"{output_dir}/locations_with_documents.csv"
        self.export_entities_with_documents(file4, entity_type='locations', limit=None)
        exports['locations_documents'] = file4
        
        # 5. Document metadata
        file5 = f"{output_dir}/document_metadata.csv"
        self.export_document_metadata(file5)
        exports['document_metadata'] = file5
        
        # 6. Top 50 people co-occurrence matrix
        file6 = f"{output_dir}/people_cooccurrence_matrix.csv"
        self.export_entity_matrix(file6, entity_type='people', top_n=50)
        exports['people_matrix'] = file6
        
        logger.info(f"Comprehensive export complete. {len(exports)} files created in {output_dir}/")
        
        return exports


# Convenience functions
def export_entities_to_csv(output_file: str, 
                          entity_type: str = 'all',
                          min_frequency: int = 1,
                          db_path: str = "data/metadata.db") -> None:
    """
    Quick function to export entities to CSV
    
    Args:
        output_file: Path to output CSV file
        entity_type: 'all', 'people', 'organizations', 'locations', 'dates', 'emails'
        min_frequency: Minimum document frequency to include
        db_path: Path to metadata database
    """
    store = MetadataStore(db_path)
    exporter = EntityCSVExporter(store)
    exporter.export_entities_with_frequencies(output_file, entity_type, min_frequency)
    store.close()


def export_all_entities(output_dir: str = 'exports',
                       db_path: str = "data/metadata.db") -> Dict[str, str]:
    """
    Quick function to export all entities in multiple formats
    
    Args:
        output_dir: Directory to save export files
        db_path: Path to metadata database
        
    Returns:
        Dictionary mapping export type to file path
    """
    store = MetadataStore(db_path)
    exporter = EntityCSVExporter(store)
    exports = exporter.export_all_entities_comprehensive(output_dir)
    store.close()
    return exports


# Usage Example
if __name__ == "__main__":
    print("=" * 70)
    print("ENTITY CSV EXPORT TOOL")
    print("=" * 70)
    
    # Create exporter
    store = MetadataStore("data/metadata.db")
    exporter = EntityCSVExporter(store)
    
    # Example 1: Export all entities with frequencies
    print("\n1. Exporting all entities with frequencies...")
    exporter.export_entities_with_frequencies(
        'exports/all_entities.csv',
        entity_type='all',
        min_frequency=1
    )
    
    # Example 2: Export people with their documents
    print("\n2. Exporting people with document lists...")
    exporter.export_entities_with_documents(
        'exports/people_detailed.csv',
        entity_type='people',
        limit=100  # Top 100 most frequent
    )
    
    # Example 3: Export document metadata
    print("\n3. Exporting document metadata...")
    exporter.export_document_metadata('exports/documents.csv')
    
    # Example 4: Export co-occurrence matrix
    print("\n4. Exporting people co-occurrence matrix...")
    exporter.export_entity_matrix(
        'exports/people_cooccurrence.csv',
        entity_type='people',
        top_n=50
    )
    
    # Example 5: Comprehensive export
    print("\n5. Performing comprehensive export...")
    exports = exporter.export_all_entities_comprehensive('exports')
    
    print("\n" + "=" * 70)
    print("EXPORT COMPLETE!")
    print("=" * 70)
    print("\nFiles created:")
    for export_type, filepath in exports.items():
        print(f"  - {export_type}: {filepath}")
    
    store.close()

