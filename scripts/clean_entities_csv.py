"""
Clean up noisy entities from CSV export

This script removes:
- HTML/XML entities and tags
- Email addresses and headers
- Entities with embedded newlines
- Special symbols and encoding artifacts
- Non-name words (dates, email headers, etc.)
"""

import csv
import re
import sys
import os
from collections import Counter

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class EntityCleaner:
    """Clean noisy entities from extracted data"""
    
    def __init__(self):
        # Patterns to reject
        self.reject_patterns = [
            # HTML/XML entities and tags
            r'&[a-z]+;',                    # &lt;, &gt;, &nbsp;, &quot;
            r'<[^>]+>',                     # <br>, </a>, <span>, etc.
            r'</?[a-z]+',                   # Incomplete tags
            
            # HTML attributes
            r'href=',
            r'target=',
            r'class=',
            r'style=',
            r'font-',
            
            # Email addresses
            r'@gmail\.com',
            r'@hotmail\.com',
            r'@yahoo\.com',
            r'@jeffreyepstein\.org',
            r'@[a-z]+\.(com|org|net)',
            r'mailto:',
            r'\[mailto:',
            
            # Email headers
            r'^Sender:',
            r'^Subject:',
            r'^From:',
            r'^To:',
            r'\bSent$',
            r'\bUnauthorized$',
            
            # Special encoding
            r'=\d{2}',                      # =20, =3D, etc.
            r'3D""',                        # Encoded quotes
            r'Â©',                          # Bad encoding
            r'&amp;',
            
            # Programming artifacts
            r'HASH\(0x',                    # Perl hash references
            r'DefaultOcxName',
            
            # Angle brackets with content
            r'<[^>]*>',
            r'\[.*?@.*?\]',                 # [mailto:...]
            
            # Embedded newlines
            r'\n',
            r'\r',
            
            # URL-like patterns
            r'https?://',
            r'www\.',
            
            # Special characters in wrong places
            r'^\W',                         # Starts with non-word char
            r'[<>{}[\]\\|~`]',             # Angle brackets, braces, pipes
        ]
        
        # Compile patterns
        self.reject_regexes = [re.compile(p, re.IGNORECASE) for p in self.reject_patterns]
        
        # Exact words to reject
        self.reject_exact = {
            'sender', 'subject', 'from', 'to', 'sent', 'unauthorized',
            'fri', 'mon', 'tue', 'wed', 'thu', 'sat', 'sun',
            'twitter', 'facebook', 'brexit',  # Not people names
            'hash', 'target', 'href', 'class',
        }
        
        # Patterns for non-name content
        self.non_name_patterns = [
            r'^\d+$',                       # Pure numbers
            r'^[A-Z]{10,}$',                # All caps long strings
            r'^\W+$',                       # Only special chars
            r'^\s*$',                       # Empty/whitespace
        ]
        
        self.non_name_regexes = [re.compile(p) for p in self.non_name_patterns]
    
    def is_valid_entity(self, entity: str) -> bool:
        """
        Check if entity should be kept
        
        Args:
            entity: Entity string to validate
            
        Returns:
            True if entity is clean and valid
        """
        if not entity or not entity.strip():
            return False
        
        entity_lower = entity.lower().strip()
        
        # Check exact reject list
        if entity_lower in self.reject_exact:
            return False
        
        # Check reject patterns
        for regex in self.reject_regexes:
            if regex.search(entity):
                return False
        
        # Check non-name patterns
        for regex in self.non_name_regexes:
            if regex.match(entity):
                return False
        
        # Check for excessive special characters
        special_count = sum(1 for c in entity if not c.isalnum() and c not in [' ', '-', '.', "'"])
        if len(entity) > 0 and special_count / len(entity) > 0.4:
            return False
        
        # Must have at least one letter
        if not any(c.isalpha() for c in entity):
            return False
        
        # Reasonable length
        if len(entity) < 2 or len(entity) > 100:
            return False
        
        return True
    
    def clean_csv(self, input_file: str, output_file: str, 
                  min_frequency: int = 1,
                  verbose: bool = True) -> dict:
        """
        Clean entities from CSV file
        
        Args:
            input_file: Input CSV file path
            output_file: Output CSV file path
            min_frequency: Minimum document count to include
            verbose: Print progress
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'total_read': 0,
            'rejected': 0,
            'kept': 0,
            'rejection_reasons': Counter()
        }
        
        cleaned_entities = []
        
        with open(input_file, 'r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            header = next(reader)  # Skip header
            
            for row in reader:
                stats['total_read'] += 1
                
                if len(row) < 3:
                    continue
                
                entity_type, entity, doc_count = row[0], row[1], int(row[2])
                
                # Check frequency threshold
                if doc_count < min_frequency:
                    stats['rejected'] += 1
                    stats['rejection_reasons']['below_min_frequency'] += 1
                    continue
                
                # Check if valid
                if self.is_valid_entity(entity):
                    cleaned_entities.append(row)
                    stats['kept'] += 1
                else:
                    stats['rejected'] += 1
                    
                    # Determine rejection reason for stats
                    if any(regex.search(entity) for regex in self.reject_regexes):
                        stats['rejection_reasons']['special_chars_or_html'] += 1
                    elif entity.lower().strip() in self.reject_exact:
                        stats['rejection_reasons']['email_header_or_common_word'] += 1
                    else:
                        stats['rejection_reasons']['other'] += 1
        
        # Write cleaned data
        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(header)
            writer.writerows(cleaned_entities)
        
        if verbose:
            self._print_stats(stats, input_file, output_file)
        
        return stats
    
    def _print_stats(self, stats: dict, input_file: str, output_file: str):
        """Print cleaning statistics"""
        print("\n" + "=" * 70)
        print("ENTITY CLEANING COMPLETE")
        print("=" * 70)
        
        print(f"\nInput:  {input_file}")
        print(f"Output: {output_file}")
        
        print(f"\nTotal entities read: {stats['total_read']:,}")
        print(f"Kept:                {stats['kept']:,} ({stats['kept']/stats['total_read']*100:.1f}%)")
        print(f"Rejected:            {stats['rejected']:,} ({stats['rejected']/stats['total_read']*100:.1f}%)")
        
        print("\nRejection Reasons:")
        for reason, count in stats['rejection_reasons'].most_common():
            print(f"  - {reason:<35} {count:>6,} entities")
    
    def preview_rejections(self, input_file: str, limit: int = 50) -> list:
        """
        Preview entities that would be rejected
        
        Args:
            input_file: Input CSV file path
            limit: Maximum number of rejections to show
            
        Returns:
            List of (entity, doc_count) tuples that would be rejected
        """
        rejections = []
        
        with open(input_file, 'r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            next(reader)  # Skip header
            
            for row in reader:
                if len(row) < 3:
                    continue
                
                entity_type, entity, doc_count = row[0], row[1], int(row[2])
                
                if not self.is_valid_entity(entity):
                    rejections.append((entity, doc_count))
                    
                    if len(rejections) >= limit:
                        break
        
        return rejections


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Clean noisy entities from CSV export',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clean with defaults
  python scripts/clean_entities_csv.py --input all_entities.csv --output cleaned_entities.csv
  
  # Preview what will be rejected
  python scripts/clean_entities_csv.py --input all_entities.csv --preview
  
  # Clean with minimum frequency filter
  python scripts/clean_entities_csv.py --input all_entities.csv --output cleaned.csv --min-freq 5
        """
    )
    
    parser.add_argument('--input', '-i',
                       required=True,
                       help='Input CSV file to clean')
    
    parser.add_argument('--output', '-o',
                       default=None,
                       help='Output CSV file (default: cleaned_<input>)')
    
    parser.add_argument('--min-freq', '-m',
                       type=int,
                       default=1,
                       help='Minimum document frequency to include (default: 1)')
    
    parser.add_argument('--preview', '-p',
                       action='store_true',
                       help='Preview rejections without cleaning')
    
    parser.add_argument('--preview-limit',
                       type=int,
                       default=100,
                       help='Number of rejections to preview (default: 100)')
    
    args = parser.parse_args()
    
    # Set default output filename
    if not args.output:
        base, ext = os.path.splitext(args.input)
        args.output = f"{base}_cleaned{ext}"
    
    cleaner = EntityCleaner()
    
    if args.preview:
        # Preview mode
        print("\n" + "=" * 70)
        print("PREVIEW: ENTITIES THAT WILL BE REJECTED")
        print("=" * 70)
        
        rejections = cleaner.preview_rejections(args.input, limit=args.preview_limit)
        
        print(f"\nShowing first {len(rejections)} rejections:\n")
        print(f"{'Entity':<60} {'Doc Count'}")
        print("-" * 70)
        
        for entity, count in rejections:
            # Truncate long entities
            display_entity = entity[:57] + "..." if len(entity) > 60 else entity
            print(f"{display_entity:<60} {count:>6,}")
        
        print(f"\nTotal previewed: {len(rejections)}")
        print("\nTo perform the cleaning, run without --preview flag")
        
    else:
        # Cleaning mode
        stats = cleaner.clean_csv(
            args.input,
            args.output,
            min_frequency=args.min_freq,
            verbose=True
        )


if __name__ == "__main__":
    main()

