"""
Demo script showcasing MVP 2 → MVP 3 improvements

This script demonstrates:
1. Entity validation
2. Fuzzy matching
3. Flexible filtering strategies
4. Metadata scoring
5. Performance monitoring
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.entity_matcher import EntityMatcher
from src.enhanced_search import MetadataScorer
from src.metadata_extractor import MetadataExtractor
from src.search_metrics import SearchMetrics


def demo_entity_validation():
    """Demonstrate entity validation"""
    print("=" * 70)
    print("1. ENTITY VALIDATION DEMO")
    print("=" * 70)
    
    extractor = MetadataExtractor()
    
    # Test noisy entities
    noisy_entities = [
        ('%%', 'LOC'),
        ('& Alcorta', 'LOC'),
        ('","textStyle":', 'PERSON'),
        ('06-04-2007', 'PERSON'),
        ('ALLLCAPSNAME', 'PERSON'),
    ]
    
    print("\nNoisy entities (should be rejected):")
    for entity, entity_type in noisy_entities:
        is_valid = extractor._is_valid_entity(entity, entity_type)
        print(f"  '{entity}' ({entity_type}): {'✗ REJECTED' if not is_valid else '✓ ACCEPTED'}")
    
    # Test clean entities
    clean_entities = [
        ('Jeffrey Epstein', 'PERSON'),
        ('Paris', 'GPE'),
        ('Clinton Foundation', 'ORG'),
    ]
    
    print("\nClean entities (should be accepted):")
    for entity, entity_type in clean_entities:
        is_valid = extractor._is_valid_entity(entity, entity_type)
        print(f"  '{entity}' ({entity_type}): {'✓ ACCEPTED' if is_valid else '✗ REJECTED'}")
    
    # Extract from sample text
    sample_text = """
    Jeffrey Epstein and Ghislaine Maxwell flew to Paris.
    ","textStyle":"bodyTextStyle
    Page 33
    %%
    """
    
    print("\nExtracting from noisy text:")
    metadata = extractor.extract_metadata(sample_text, "demo_doc")
    print(f"  People found: {metadata['people']}")
    print(f"  Locations found: {metadata['locations']}")
    print(f"  ✓ Noise automatically filtered out!")


def demo_fuzzy_matching():
    """Demonstrate fuzzy entity matching"""
    print("\n" + "=" * 70)
    print("2. FUZZY MATCHING DEMO")
    print("=" * 70)
    
    matcher = EntityMatcher(similarity_threshold=0.85)
    
    # Test name normalization
    print("\nName Normalization:")
    names = [
        "G. Maxwell",
        "The Clinton Foundation",
        "Dr. Jeffrey Epstein",
        "Mr. Bill Clinton"
    ]
    
    for name in names:
        normalized = matcher.normalize_name(name)
        print(f"  '{name}' → '{normalized}'")
    
    # Test fuzzy matching
    print("\nFuzzy Matching:")
    test_cases = [
        ("Maxwell", "Ghislaine Maxwell"),
        ("Maxwell", "G. Maxwell"),
        ("Epstein", "Jeffrey Epstein"),
        ("Clinton", "Clinton Foundation"),
        ("Maxwell", "Einstein"),
    ]
    
    for query, doc in test_cases:
        matches = matcher.fuzzy_match(query, doc)
        symbol = "✓" if matches else "✗"
        print(f"  {symbol} '{query}' vs '{doc}': {matches}")
    
    # Test match scoring
    print("\nMatch Scoring:")
    query_entities = ["Maxwell", "Paris"]
    doc_entities_1 = ["Ghislaine Maxwell", "Paris", "London", "Jeffrey Epstein"]
    doc_entities_2 = ["Bill Clinton", "New York"]
    
    score1 = matcher.match_score(query_entities, doc_entities_1)
    score2 = matcher.match_score(query_entities, doc_entities_2)
    
    print(f"  Query: {query_entities}")
    print(f"  Doc 1: {doc_entities_1}")
    print(f"    Score: {score1:.2f} (perfect match)")
    print(f"  Doc 2: {doc_entities_2}")
    print(f"    Score: {score2:.2f} (no match)")


def demo_filtering_strategies():
    """Demonstrate filtering strategies"""
    print("\n" + "=" * 70)
    print("3. FILTERING STRATEGIES DEMO")
    print("=" * 70)
    
    print("\nAvailable Strategies:")
    print("\n  1. STRICT (AND logic)")
    print("     - Requires ALL entities to match")
    print("     - Best for: Specific queries")
    print("     - Example result: 500 → 10-20 docs")
    
    print("\n  2. LOOSE (OR logic)")
    print("     - Matches ANY entity")
    print("     - Best for: Broad exploration")
    print("     - Example result: 500 → 80-120 docs")
    
    print("\n  3. BOOST (Soft ranking)")
    print("     - No filtering, just boost scores")
    print("     - Best for: MVP 3 (preserves candidates)")
    print("     - Example result: 500 → 500 docs (reranked)")
    
    print("\n  4. ADAPTIVE (Smart fallback)")
    print("     - Tries strict → loose → boost")
    print("     - Best for: General queries (default)")
    print("     - Example result: Adaptive based on results")
    
    print("\n  5. NONE (Pure BM25)")
    print("     - No metadata filtering")
    print("     - Best for: Keyword-only search")
    print("     - Example result: 500 → 500 docs (BM25 order)")
    
    print("\nUsage Example:")
    print("""
    results = search_engine.search_adaptive(
        query="Maxwell Paris meetings",
        filter_strategy='adaptive',  # or 'strict', 'loose', 'boost', 'none'
        min_candidates=50,
        top_k=10
    )
    """)


def demo_metadata_scoring():
    """Demonstrate metadata scoring"""
    print("\n" + "=" * 70)
    print("4. METADATA SCORING DEMO")
    print("=" * 70)
    
    scorer = MetadataScorer()
    
    print("\nScoring Weights:")
    for component, weight in scorer.weights.items():
        print(f"  - {component}: {weight:.0%}")
    
    # Test perfect match
    print("\nScenario 1: Perfect Match")
    doc_metadata = {
        'people': ['Jeffrey Epstein', 'Ghislaine Maxwell'],
        'locations': ['Paris', 'New York'],
        'organizations': ['Clinton Foundation']
    }
    query_entities = {
        'people': ['Epstein', 'Maxwell'],
        'locations': ['Paris'],
        'organizations': ['Clinton Foundation']
    }
    
    score = scorer.calculate_metadata_score(doc_metadata, query_entities)
    print(f"  Doc: {doc_metadata['people']}, {doc_metadata['locations']}")
    print(f"  Query: {query_entities['people']}, {query_entities['locations']}")
    print(f"  Score: {score:.2f} (high - good match)")
    
    # Test no match
    print("\nScenario 2: No Match")
    doc_metadata_2 = {
        'people': ['Bill Clinton'],
        'locations': ['London'],
        'organizations': []
    }
    
    score2 = scorer.calculate_metadata_score(doc_metadata_2, query_entities)
    print(f"  Doc: {doc_metadata_2['people']}, {doc_metadata_2['locations']}")
    print(f"  Query: {query_entities['people']}, {query_entities['locations']}")
    print(f"  Score: {score2:.2f} (low - poor match)")
    
    # Test partial match
    print("\nScenario 3: Partial Match")
    doc_metadata_3 = {
        'people': ['Jeffrey Epstein', 'Bill Clinton'],
        'locations': ['London', 'New York'],
        'organizations': []
    }
    query_entities_3 = {
        'people': ['Epstein'],
        'locations': ['Paris'],
        'organizations': []
    }
    
    score3 = scorer.calculate_metadata_score(doc_metadata_3, query_entities_3)
    print(f"  Doc: {doc_metadata_3['people']}, {doc_metadata_3['locations']}")
    print(f"  Query: {query_entities_3['people']}, {query_entities_3['locations']}")
    print(f"  Score: {score3:.2f} (medium - partial match)")


def demo_search_metrics():
    """Demonstrate search metrics"""
    print("\n" + "=" * 70)
    print("5. SEARCH METRICS DEMO")
    print("=" * 70)
    
    metrics = SearchMetrics()
    
    # Simulate some searches
    print("\nLogging search operations...")
    searches = [
        ("Maxwell Paris meetings", 500, 80, 10, 'adaptive', 150.5),
        ("Epstein flight logs", 500, 120, 10, 'loose', 175.2),
        ("Clinton Foundation", 500, 500, 10, 'boost', 180.8),
        ("Island meetings", 500, 40, 10, 'strict', 165.3),
    ]
    
    for query, bm25, filtered, final, strategy, time_ms in searches:
        metrics.log_search(query, bm25, filtered, final, strategy, time_ms)
        print(f"  ✓ Logged: '{query}' ({strategy})")
    
    # Display report
    print(metrics.report())
    
    # Show statistics
    stats = metrics.get_statistics()
    print("Key Insights:")
    print(f"  - Average filter ratio: {stats['avg_filter_ratio']:.1%}")
    print(f"    (Lower = more candidates preserved)")
    print(f"  - Average query time: {stats['avg_time_ms']:.0f}ms")
    print(f"  - Most used strategy: {max(stats['strategies_used'], key=stats['strategies_used'].get)}")


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("MVP 2 → MVP 3 IMPROVEMENTS DEMO")
    print("=" * 70)
    print("\nThis demo showcases the new features for MVP 3 preparation:")
    print("  1. Entity Validation - Filter noisy entities")
    print("  2. Fuzzy Matching - Match entity variations")
    print("  3. Filtering Strategies - Flexible filtering modes")
    print("  4. Metadata Scoring - Relevance scoring")
    print("  5. Search Metrics - Performance monitoring")
    
    # Run all demos
    demo_entity_validation()
    demo_fuzzy_matching()
    demo_filtering_strategies()
    demo_metadata_scoring()
    demo_search_metrics()
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETE!")
    print("=" * 70)
    print("\nNext Steps:")
    print("  1. Run tests: pytest tests/ -v")
    print("  2. Read guide: documentation/MVP3_FEATURES_GUIDE.md")
    print("  3. Integrate with your search pipeline")
    print("  4. Prepare for MVP 3 dense embeddings")
    print()


if __name__ == "__main__":
    main()

