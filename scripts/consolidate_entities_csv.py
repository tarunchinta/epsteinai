"""
Consolidate redundant and duplicate entities in CSV

This script merges entities that refer to the same thing but are spelled differently:
- "U.S.", "US", "United States", "America" → "United States"
- "Jeffrey Epstein", "jeffrey E.", "Jeff Epstein" → "Jeffrey Epstein"
- "New York", "NY", "new york" → "New York"
"""

import csv
import re
from collections import defaultdict
from typing import Dict, List, Tuple
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class EntityConsolidator:
    """Consolidate duplicate and redundant entities"""
    
    def __init__(self):
        # Predefined consolidation rules
        self.consolidation_rules = {
            # Countries and regions
            'united states': ['u.s.', 'us', 'usa', 'the united states', 'america', 'u.s', 'united states'],
            'united kingdom': ['uk', 'u.k.', 'britain', 'england', 'the uk', 'united kingdom'],
            'european union': ['eu', 'e.u.', 'european union'],
            
            # Cities
            'new york': ['ny', 'nyc', 'new york city', 'new york'],
            'washington': ['washington d.c.', 'washington dc', 'dc', 'washington'],
            'los angeles': ['la', 'l.a.', 'los angeles'],
            
            # Organizations
            'fbi': ['f.b.i.', 'federal bureau of investigation', 'fbi'],
            'cia': ['c.i.a.', 'central intelligence agency', 'cia'],
            'new york times': ['nyt', 'the new york times', 'ny times', 'new york times'],
            'wall street journal': ['wsj', 'the wall street journal', 'wall street journal'],
            'washington post': ['the washington post', 'wapo', 'washington post'],
            'cnn': ['c.n.n.', 'cable news network', 'cnn'],
            'bbc': ['b.b.c.', 'british broadcasting corporation', 'bbc'],
            'harvard university': ['harvard', 'harvard university'],
            'white house': ['the white house', 'white house'],
            
            # People (common variations)
            'jeffrey epstein': ['jeffrey e.', 'jeff epstein', 'epstein', 'jeffrey epstein', 'jeffrey epstein\'s'],
            'donald trump': ['trump', 'donald', 'donald trump', 'donald trump\'s'],
            'bill clinton': ['clinton', 'bill', 'bill clinton', 'william clinton'],
            'hillary clinton': ['hillary', 'hillary clinton'],
            'ghislaine maxwell': ['maxwell', 'ghislaine', 'g. maxwell', 'ghislaine maxwell'],
            'barack obama': ['obama', 'barack', 'barack obama'],
            'prince andrew': ['andrew', 'prince andrew'],
            'alan dershowitz': ['dershowitz', 'alan dershowitz'],
        }
        
        # Build reverse lookup
        self.entity_to_canonical = {}
        for canonical, variations in self.consolidation_rules.items():
            for variation in variations:
                self.entity_to_canonical[variation.lower()] = canonical
    
    def normalize_entity(self, entity: str) -> str:
        """
        Normalize entity for comparison
        
        Args:
            entity: Entity string
            
        Returns:
            Normalized entity string
        """
        # Remove "the" prefix
        normalized = entity.lower().strip()
        if normalized.startswith('the '):
            normalized = normalized[4:]
        
        # Remove possessives
        normalized = re.sub(r"'s$", '', normalized)
        
        # Remove dots from abbreviations
        normalized = normalized.replace('.', '')
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def get_canonical_name(self, entity: str, entity_type: str) -> str:
        """
        Get canonical name for an entity
        
        Args:
            entity: Entity string
            entity_type: Type of entity
            
        Returns:
            Canonical name (properly capitalized)
        """
        normalized = self.normalize_entity(entity)
        
        # Check if we have a predefined canonical form
        if normalized in self.entity_to_canonical:
            canonical = self.entity_to_canonical[normalized]
            # Return with proper capitalization
            return self._capitalize_properly(canonical, entity_type)
        
        # Otherwise, use the original with proper capitalization
        return self._capitalize_properly(entity, entity_type)
    
    def _capitalize_properly(self, text: str, entity_type: str) -> str:
        """
        Apply proper capitalization based on entity type
        
        Args:
            text: Text to capitalize
            entity_type: Type of entity
            
        Returns:
            Properly capitalized text
        """
        # For people, use title case but preserve some lowercase words
        if entity_type == 'people':
            words = text.split()
            result = []
            for i, word in enumerate(words):
                # Keep certain words lowercase unless they're first
                if i > 0 and word.lower() in ['von', 'van', 'de', 'la', 'le', 'of', 'the']:
                    result.append(word.lower())
                else:
                    result.append(word.capitalize())
            return ' '.join(result)
        
        # For locations and organizations, use title case
        elif entity_type in ['locations', 'organizations']:
            # Special case: abbreviations
            if len(text) <= 4 and text.isupper():
                return text.upper()
            return text.title()
        
        # For dates and emails, keep as-is
        return text
    
    def consolidate_csv(self, input_file: str, output_file: str, verbose: bool = True) -> Dict:
        """
        Consolidate entities in CSV file
        
        Args:
            input_file: Input CSV file path
            output_file: Output CSV file path
            verbose: Print progress
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'input_entities': 0,
            'output_entities': 0,
            'consolidated': 0,
            'by_type': {}
        }
        
        # Read and group entities
        entities_by_type = defaultdict(lambda: defaultdict(list))
        
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            
            for row in reader:
                if len(row) < 3:
                    continue
                
                entity_type, entity, doc_count = row[0], row[1], int(row[2])
                stats['input_entities'] += 1
                
                # Get canonical name
                canonical = self.get_canonical_name(entity, entity_type)
                normalized_key = self.normalize_entity(canonical)
                
                # Store with original entity and count
                entities_by_type[entity_type][normalized_key].append((entity, canonical, doc_count))
        
        # Consolidate and write output
        consolidated_data = []
        
        for entity_type, entities in entities_by_type.items():
            type_stats = {
                'original': 0,
                'consolidated': 0,
                'merged': 0
            }
            
            for normalized_key, entity_list in entities.items():
                type_stats['original'] += len(entity_list)
                
                # Sum counts
                total_count = sum(count for _, _, count in entity_list)
                
                # Choose best canonical name (prefer longer, more complete names)
                canonical_name = max(
                    set(canonical for _, canonical, _ in entity_list),
                    key=lambda x: (len(x), x)
                )
                
                consolidated_data.append((entity_type, canonical_name, total_count))
                type_stats['consolidated'] += 1
                
                if len(entity_list) > 1:
                    type_stats['merged'] += 1
                    if verbose:
                        merged_names = [f"{entity} ({count})" for entity, _, count in entity_list]
                        print(f"  Merged: {', '.join(merged_names[:3])} → {canonical_name} ({total_count})")
                        if len(merged_names) > 3:
                            print(f"          ...and {len(merged_names) - 3} more")
            
            stats['by_type'][entity_type] = type_stats
        
        # Sort by type, then by count descending
        consolidated_data.sort(key=lambda x: (x[0], -x[2]))
        
        # Write output
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Entity Type', 'Entity', 'Document Count'])
            writer.writerows(consolidated_data)
        
        stats['output_entities'] = len(consolidated_data)
        stats['consolidated'] = stats['input_entities'] - stats['output_entities']
        
        if verbose:
            self._print_stats(stats, input_file, output_file)
        
        return stats
    
    def _print_stats(self, stats: Dict, input_file: str, output_file: str):
        """Print consolidation statistics"""
        print("\n" + "=" * 70)
        print("ENTITY CONSOLIDATION COMPLETE")
        print("=" * 70)
        
        print(f"\nInput:  {input_file}")
        print(f"Output: {output_file}")
        
        print(f"\nInput entities:  {stats['input_entities']:,}")
        print(f"Output entities: {stats['output_entities']:,}")
        print(f"Consolidated:    {stats['consolidated']:,} ({stats['consolidated']/stats['input_entities']*100:.1f}%)")
        
        print("\nBy Entity Type:")
        for entity_type, type_stats in stats['by_type'].items():
            reduction = type_stats['original'] - type_stats['consolidated']
            pct = (reduction / type_stats['original'] * 100) if type_stats['original'] > 0 else 0
            print(f"\n  {entity_type.upper()}:")
            print(f"    Original:     {type_stats['original']:,}")
            print(f"    Consolidated: {type_stats['consolidated']:,}")
            print(f"    Merged:       {type_stats['merged']:,} groups")
            print(f"    Reduction:    {reduction:,} ({pct:.1f}%)")
    
    def preview_consolidations(self, input_file: str, limit: int = 50) -> List[Tuple]:
        """
        Preview what would be consolidated
        
        Args:
            input_file: Input CSV file path
            limit: Maximum number of consolidations to show
            
        Returns:
            List of (canonical_name, variations, total_count) tuples
        """
        # Read and group entities
        entities_by_canonical = defaultdict(list)
        
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            
            for row in reader:
                if len(row) < 3:
                    continue
                
                entity_type, entity, doc_count = row[0], row[1], int(row[2])
                canonical = self.get_canonical_name(entity, entity_type)
                normalized_key = f"{entity_type}:{self.normalize_entity(canonical)}"
                
                entities_by_canonical[normalized_key].append((entity, doc_count))
        
        # Find consolidations (groups with multiple entities)
        consolidations = []
        for key, entity_list in entities_by_canonical.items():
            if len(entity_list) > 1:
                entity_type, canonical_normalized = key.split(':', 1)
                # Get best canonical name
                canonical = max(set(e for e, _ in entity_list), key=lambda x: (len(x), x))
                total_count = sum(count for _, count in entity_list)
                consolidations.append((canonical, entity_list, total_count))
        
        # Sort by total count
        consolidations.sort(key=lambda x: x[2], reverse=True)
        
        return consolidations[:limit]


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Consolidate duplicate and redundant entities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Consolidate entities
  python scripts/consolidate_entities_csv.py --input all_entities_cleaned.csv --output consolidated.csv
  
  # Preview consolidations
  python scripts/consolidate_entities_csv.py --input all_entities_cleaned.csv --preview
  
  # Consolidate with custom output
  python scripts/consolidate_entities_csv.py -i cleaned.csv -o final.csv
        """
    )
    
    parser.add_argument('--input', '-i',
                       required=True,
                       help='Input CSV file to consolidate')
    
    parser.add_argument('--output', '-o',
                       default=None,
                       help='Output CSV file (default: <input>_consolidated.csv)')
    
    parser.add_argument('--preview', '-p',
                       action='store_true',
                       help='Preview consolidations without processing')
    
    parser.add_argument('--preview-limit',
                       type=int,
                       default=100,
                       help='Number of consolidations to preview (default: 100)')
    
    args = parser.parse_args()
    
    # Set default output filename
    if not args.output:
        base, ext = os.path.splitext(args.input)
        args.output = f"{base}_consolidated{ext}"
    
    consolidator = EntityConsolidator()
    
    if args.preview:
        # Preview mode
        print("\n" + "=" * 70)
        print("PREVIEW: ENTITY CONSOLIDATIONS")
        print("=" * 70)
        
        consolidations = consolidator.preview_consolidations(args.input, limit=args.preview_limit)
        
        print(f"\nShowing top {len(consolidations)} consolidations by document count:\n")
        
        for i, (canonical, variations, total_count) in enumerate(consolidations, 1):
            print(f"\n{i}. {canonical} (Total: {total_count:,} docs)")
            print("   Merging:")
            for entity, count in sorted(variations, key=lambda x: x[1], reverse=True):
                print(f"     - {entity:<40} ({count:,} docs)")
        
        print(f"\n\nTotal consolidation groups found: {len(consolidations)}")
        print("\nTo perform the consolidation, run without --preview flag")
        
    else:
        # Consolidation mode
        stats = consolidator.consolidate_csv(
            args.input,
            args.output,
            verbose=True
        )


if __name__ == "__main__":
    main()

