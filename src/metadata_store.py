"""
Store and query metadata using SQLite
"""

import sqlite3
import json
from typing import List, Dict, Optional
from pathlib import Path
from loguru import logger
from src.entity_matcher import EntityMatcher


class MetadataStore:
    """SQLite-based metadata storage"""
    
    def __init__(self, db_path: str = "data/metadata.db", similarity_threshold: float = 0.85):
        """Initialize database connection"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts
        self._create_tables()
        
        # Initialize entity matcher for fuzzy matching
        self.entity_matcher = EntityMatcher(similarity_threshold=similarity_threshold)
        
    def _create_tables(self):
        """Create database schema"""
        cursor = self.conn.cursor()
        
        # Main metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_metadata (
                doc_id TEXT PRIMARY KEY,
                word_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Entity tables (many-to-many relationships)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                name TEXT,
                FOREIGN KEY (doc_id) REFERENCES document_metadata(doc_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                name TEXT,
                FOREIGN KEY (doc_id) REFERENCES document_metadata(doc_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                name TEXT,
                FOREIGN KEY (doc_id) REFERENCES document_metadata(doc_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                date_str TEXT,
                FOREIGN KEY (doc_id) REFERENCES document_metadata(doc_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                email TEXT,
                FOREIGN KEY (doc_id) REFERENCES document_metadata(doc_id)
            )
        """)
        
        # Create indexes for fast lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_people_name ON people(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_people_doc ON people(doc_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orgs_name ON organizations(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_name ON locations(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_doc ON locations(doc_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dates_str ON dates(date_str)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_emails_email ON emails(email)")
        
        self.conn.commit()
        logger.info("Database schema initialized")
    
    def store_metadata(self, metadata: Dict):
        """Store metadata for a document"""
        cursor = self.conn.cursor()
        doc_id = metadata['doc_id']
        
        try:
            # Insert main metadata
            cursor.execute("""
                INSERT OR REPLACE INTO document_metadata (doc_id, word_count)
                VALUES (?, ?)
            """, (doc_id, metadata['word_count']))
            
            # Delete existing entities (for updates)
            for table in ['people', 'organizations', 'locations', 'dates', 'emails']:
                cursor.execute(f"DELETE FROM {table} WHERE doc_id = ?", (doc_id,))
            
            # Insert entities
            for person in metadata['people']:
                cursor.execute("INSERT INTO people (doc_id, name) VALUES (?, ?)",
                             (doc_id, person))
            
            for org in metadata['organizations']:
                cursor.execute("INSERT INTO organizations (doc_id, name) VALUES (?, ?)",
                             (doc_id, org))
            
            for loc in metadata['locations']:
                cursor.execute("INSERT INTO locations (doc_id, name) VALUES (?, ?)",
                             (doc_id, loc))
            
            for date in metadata['dates']:
                cursor.execute("INSERT INTO dates (doc_id, date_str) VALUES (?, ?)",
                             (doc_id, date))
            
            for email in metadata['emails']:
                cursor.execute("INSERT INTO emails (doc_id, email) VALUES (?, ?)",
                             (doc_id, email))
            
            self.conn.commit()
            logger.debug(f"Stored metadata for {doc_id}")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error storing metadata for {doc_id}: {e}")
            raise
    
    def filter_documents(self, 
                        doc_ids: List[str],
                        people: Optional[List[str]] = None,
                        locations: Optional[List[str]] = None,
                        organizations: Optional[List[str]] = None,
                        date_range: Optional[tuple] = None) -> List[str]:
        """
        Filter document IDs by metadata criteria
        
        Args:
            doc_ids: Initial set of document IDs to filter
            people: List of person names to match (OR logic)
            locations: List of locations to match (OR logic)
            organizations: List of organizations to match (OR logic)
            date_range: Tuple of (start_date, end_date) strings
            
        Returns:
            Filtered list of document IDs
        """
        if not doc_ids:
            return []
        
        # Start with initial set
        filtered_ids = set(doc_ids)
        cursor = self.conn.cursor()
        
        # Filter by people
        if people:
            placeholders = ','.join(['?'] * len(people))
            doc_placeholders = ','.join(['?'] * len(filtered_ids))
            query = f"""
                SELECT DISTINCT doc_id FROM people 
                WHERE name IN ({placeholders})
                AND doc_id IN ({doc_placeholders})
            """
            cursor.execute(query, people + list(filtered_ids))
            people_ids = {row['doc_id'] for row in cursor.fetchall()}
            filtered_ids &= people_ids
            logger.debug(f"After people filter: {len(filtered_ids)} docs")
        
        # Filter by locations
        if locations:
            placeholders = ','.join(['?'] * len(locations))
            doc_placeholders = ','.join(['?'] * len(filtered_ids))
            query = f"""
                SELECT DISTINCT doc_id FROM locations 
                WHERE name IN ({placeholders})
                AND doc_id IN ({doc_placeholders})
            """
            cursor.execute(query, locations + list(filtered_ids))
            loc_ids = {row['doc_id'] for row in cursor.fetchall()}
            filtered_ids &= loc_ids
            logger.debug(f"After location filter: {len(filtered_ids)} docs")
        
        # Filter by organizations
        if organizations:
            placeholders = ','.join(['?'] * len(organizations))
            doc_placeholders = ','.join(['?'] * len(filtered_ids))
            query = f"""
                SELECT DISTINCT doc_id FROM organizations 
                WHERE name IN ({placeholders})
                AND doc_id IN ({doc_placeholders})
            """
            cursor.execute(query, organizations + list(filtered_ids))
            org_ids = {row['doc_id'] for row in cursor.fetchall()}
            filtered_ids &= org_ids
            logger.debug(f"After organization filter: {len(filtered_ids)} docs")
        
        # Filter by date range
        if date_range:
            start_date, end_date = date_range
            doc_placeholders = ','.join(['?'] * len(filtered_ids))
            query = f"""
                SELECT DISTINCT doc_id FROM dates 
                WHERE date_str BETWEEN ? AND ?
                AND doc_id IN ({doc_placeholders})
            """
            cursor.execute(query, [start_date, end_date] + list(filtered_ids))
            date_ids = {row['doc_id'] for row in cursor.fetchall()}
            filtered_ids &= date_ids
            logger.debug(f"After date filter: {len(filtered_ids)} docs")
        
        return list(filtered_ids)
    
    def get_metadata(self, doc_id: str) -> Optional[Dict]:
        """Retrieve metadata for a document"""
        cursor = self.conn.cursor()
        
        # Get main metadata
        cursor.execute("SELECT * FROM document_metadata WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        metadata = {
            'doc_id': doc_id,
            'word_count': row['word_count'],
            'people': [],
            'organizations': [],
            'locations': [],
            'dates': [],
            'emails': []
        }
        
        # Get entities
        cursor.execute("SELECT name FROM people WHERE doc_id = ?", (doc_id,))
        metadata['people'] = [row['name'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT name FROM organizations WHERE doc_id = ?", (doc_id,))
        metadata['organizations'] = [row['name'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT name FROM locations WHERE doc_id = ?", (doc_id,))
        metadata['locations'] = [row['name'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT date_str FROM dates WHERE doc_id = ?", (doc_id,))
        metadata['dates'] = [row['date_str'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT email FROM emails WHERE doc_id = ?", (doc_id,))
        metadata['emails'] = [row['email'] for row in cursor.fetchall()]
        
        return metadata
    
    def get_all_entities(self) -> Dict[str, List[str]]:
        """Get all unique entities across all documents"""
        cursor = self.conn.cursor()
        
        entities = {
            'people': [],
            'organizations': [],
            'locations': [],
            'dates': []
        }
        
        cursor.execute("SELECT DISTINCT name FROM people ORDER BY name")
        entities['people'] = [row['name'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT name FROM organizations ORDER BY name")
        entities['organizations'] = [row['name'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT name FROM locations ORDER BY name")
        entities['locations'] = [row['name'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT date_str FROM dates ORDER BY date_str")
        entities['dates'] = [row['date_str'] for row in cursor.fetchall()]
        
        return entities
    
    def filter_documents_fuzzy(self,
                               doc_ids: List[str],
                               people: Optional[List[str]] = None,
                               locations: Optional[List[str]] = None,
                               organizations: Optional[List[str]] = None,
                               match_mode: str = 'fuzzy') -> List[str]:
        """
        Filter documents with fuzzy entity matching
        
        Uses the EntityMatcher to find documents where entities match fuzzily
        (e.g., "Maxwell" matches "Ghislaine Maxwell", "G. Maxwell", etc.)
        
        Args:
            doc_ids: Document IDs to filter
            people: People to match (fuzzy)
            locations: Locations to match (fuzzy)
            organizations: Organizations to match (fuzzy)
            match_mode: 'exact' (use SQL), 'fuzzy' (use EntityMatcher), 'any' (OR logic)
            
        Returns:
            Filtered list of document IDs
        """
        if not doc_ids:
            return []
        
        # If exact mode, use the original filter_documents
        if match_mode == 'exact':
            return self.filter_documents(doc_ids, people, locations, organizations)
        
        matched_docs = []
        
        for doc_id in doc_ids:
            doc_metadata = self.get_metadata(doc_id)
            if not doc_metadata:
                continue
            
            # Track whether document matches
            matches = True
            
            if match_mode == 'fuzzy':
                # AND logic: ALL criteria must match (if specified)
                if people and not self.entity_matcher.match_any(people, doc_metadata['people']):
                    matches = False
                
                if locations and not self.entity_matcher.match_any(locations, doc_metadata['locations']):
                    matches = False
                
                if organizations and not self.entity_matcher.match_any(organizations, doc_metadata['organizations']):
                    matches = False
            
            elif match_mode == 'any':
                # OR logic: ANY criteria can match
                matches = False
                
                if people and self.entity_matcher.match_any(people, doc_metadata['people']):
                    matches = True
                elif locations and self.entity_matcher.match_any(locations, doc_metadata['locations']):
                    matches = True
                elif organizations and self.entity_matcher.match_any(organizations, doc_metadata['organizations']):
                    matches = True
            
            if matches:
                matched_docs.append(doc_id)
        
        logger.debug(f"Fuzzy filter ({match_mode}): {len(doc_ids)} → {len(matched_docs)} docs")
        return matched_docs
    
    def close(self):
        """Close database connection"""
        self.conn.close()


# Usage Example
if __name__ == "__main__":
    store = MetadataStore()
    
    # Example metadata
    metadata = {
        'doc_id': 'doc_001',
        'people': ['Jeffrey Epstein', 'Ghislaine Maxwell'],
        'organizations': ['Clinton Foundation'],
        'locations': ['Paris', 'New York'],
        'dates': ['2015-07-12'],
        'emails': ['example@test.com'],
        'word_count': 1500
    }
    
    store.store_metadata(metadata)
    print("Stored metadata")
    
    retrieved = store.get_metadata('doc_001')
    print("Retrieved:", retrieved)
    
    store.close()

