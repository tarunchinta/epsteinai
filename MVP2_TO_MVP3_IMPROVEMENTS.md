# MVP 2 → MVP 3: Metadata Filtering Improvements

## 🎯 Executive Summary

**Current Issues Identified:**
1. **Aggressive Filtering**: Tier 2 reduces 500 → 14 docs (too few for dense search)
2. **Noisy Entities**: spaCy extracts JSON fragments, special chars, formatting artifacts
3. **Strict AND Logic**: Requires ALL filters to match, missing relevant docs
4. **Exact Matching**: "Maxwell" doesn't find "G. Maxwell" or "Ghislaine Maxwell"

**Impact on MVP 3:**
- Dense embeddings need 50-100 candidates for effective semantic ranking
- Current filtering is too aggressive, discards relevant documents
- Can't recover docs filtered out in Tier 2

**Goals:**
- Maintain 50-100 documents for Tier 3 (not 14)
- Improve entity quality (reduce noise)
- Add flexible filtering strategies (OR, soft boost, fuzzy)
- Use metadata as ranking signal, not hard filter

---

## 📋 TODO: Entity Quality Improvements

### Priority: HIGH | Effort: MEDIUM | Impact: HIGH

### Problem

spaCy has already extracted noisy entities from documents that need filtering:
```
Bad Entities Already Extracted:
- People: '","textStyle":"bodyTextStyle', '& Shih', '06-04-2007'
- Locations: '%%', '& Alcorta', 'Page 33'
- Organizations: 'Dai-ichi Life 8750 JP Insurance'
```

These entities exist in the current metadata store and need to be filtered out without re-running NER extraction.

### Solution 1: Post-Extraction Validation

**File to Modify:** `src/metadata_extractor.py`

**Note:** This validation filters already-extracted entities to remove noise. It does NOT re-run NER extraction on documents. The validation can be applied to existing metadata in-memory or during the extraction process.

**Implementation:**

```python
import re

class MetadataExtractor:
    """Extract entities and structured data from text"""
    
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        
        # Validation patterns
        self.invalid_patterns = [
            r'[{}\[\]<>]',          # JSON/HTML brackets
            r'^\d{2}-\d{2}-\d{4}',  # Dates (already extracted separately)
            r'^[%&@#$]+',           # Special char prefixes
            r'^\d+\s*$',            # Pure numbers
            r'textStyle|layout|identifier',  # JSON keys
        ]
        
        # Minimum quality thresholds
        self.min_name_length = 3
        self.max_name_length = 100
        
    def _is_valid_entity(self, entity_text: str, entity_type: str) -> bool:
        """
        Validate extracted entity quality
        
        NOTE: This method filters already-extracted entities from spaCy NER.
        It does NOT re-run entity extraction on the original document text.
        Use this to clean noisy entities after extraction.
        
        Args:
            entity_text: The extracted entity string (from spaCy)
            entity_type: Type (PERSON, ORG, GPE, LOC)
            
        Returns:
            True if entity passes quality checks
        """
        text = entity_text.strip()
        
        # Length checks
        if len(text) < self.min_name_length:
            return False
        if len(text) > self.max_name_length:
            return False
        
        # Invalid pattern checks
        for pattern in self.invalid_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # Type-specific validation
        if entity_type == "PERSON":
            # Person names shouldn't be all caps (likely acronyms/codes)
            if text.isupper() and len(text) > 5:
                return False
            # Should contain at least one letter
            if not any(c.isalpha() for c in text):
                return False
            # Common false positives
            if text.lower() in ['the', 'and', 'page', 'chapter', 'section']:
                return False
        
        elif entity_type in ["GPE", "LOC"]:
            # Locations shouldn't start with special chars
            if text[0] in ['&', '%', '#', '@']:
                return False
            # Likely noise if contains multiple special chars
            if sum(1 for c in text if not c.isalnum() and c not in [' ', '-', '.']) > 2:
                return False
        
        elif entity_type == "ORG":
            # Organizations with excessive special chars are likely noise
            special_char_ratio = sum(1 for c in text if not c.isalnum() and c != ' ') / len(text)
            if special_char_ratio > 0.3:
                return False
        
        return True
    
    def _extract_people(self, doc) -> Set[str]:
        """
        Extract PERSON entities with validation
        
        Flow: spaCy extracts → validation filters → clean entities returned
        (No re-extraction, just filtering what spaCy already found)
        """
        people = set()
        for ent in doc.ents:  # doc.ents contains already-extracted entities
            if ent.label_ == "PERSON":
                name = ent.text.strip()
                if self._is_valid_entity(name, "PERSON"):  # Filter out noise
                    people.add(name)
        return people
    
    def _extract_organizations(self, doc) -> Set[str]:
        """Extract ORG entities with validation"""
        orgs = set()
        for ent in doc.ents:
            if ent.label_ == "ORG":
                org = ent.text.strip()
                if self._is_valid_entity(org, "ORG"):
                    orgs.add(org)
        return orgs
    
    def _extract_locations(self, doc) -> Set[str]:
        """Extract GPE and LOC entities with validation"""
        locations = set()
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                loc = ent.text.strip()
                if self._is_valid_entity(loc, ent.label_):
                    locations.add(loc)
        return locations
```

**Testing:**
```python
# Add to tests/test_metadata.py
def test_entity_validation():
    extractor = MetadataExtractor()
    
    # Should reject
    assert not extractor._is_valid_entity('%%', 'LOC')
    assert not extractor._is_valid_entity('& Alcorta', 'LOC')
    assert not extractor._is_valid_entity('","textStyle":', 'PERSON')
    assert not extractor._is_valid_entity('ALLLCAPSNAME', 'PERSON')
    
    # Should accept
    assert extractor._is_valid_entity('Paris', 'GPE')
    assert extractor._is_valid_entity('Jeffrey Epstein', 'PERSON')
    assert extractor._is_valid_entity('Clinton Foundation', 'ORG')
```

**Impact:**
- Reduces noisy entities by ~60-80%
- Improves metadata filter precision
- Better demo experience
- Works on existing extracted metadata without re-running NER
- Re-indexing only needed to persist cleaned entities to database

---

## 📋 TODO: Fuzzy Entity Matching

### Priority: HIGH | Effort: MEDIUM | Impact: HIGH

### Problem

Exact matching misses variations:
```
Query: "Maxwell"
Misses: "G. Maxwell", "Ghislaine Maxwell", "Maxwell Group"
```

### Solution 2: Fuzzy Matching with Normalization

**File to Create:** `src/entity_matcher.py`

**Implementation:**

```python
"""
Fuzzy entity matching for flexible metadata filtering
"""

from typing import List, Set
import re
from difflib import SequenceMatcher


class EntityMatcher:
    """Match entities with fuzzy logic and normalization"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: Minimum similarity score (0-1) for fuzzy match
        """
        self.similarity_threshold = similarity_threshold
    
    def normalize_name(self, name: str) -> str:
        """
        Normalize entity name for comparison
        
        Examples:
            "G. Maxwell" → "maxwell"
            "Ghislaine Maxwell" → "ghislaine maxwell"
            "The Clinton Foundation" → "clinton foundation"
        """
        # Lowercase
        normalized = name.lower()
        
        # Remove common prefixes
        prefixes = ['the ', 'mr. ', 'ms. ', 'mrs. ', 'dr. ']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
        
        # Remove single letter initials and dots
        normalized = re.sub(r'\b[a-z]\.\s*', '', normalized)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def fuzzy_match(self, query_entity: str, doc_entity: str) -> bool:
        """
        Check if two entities match with fuzzy logic
        
        Args:
            query_entity: Entity from user query
            doc_entity: Entity from document metadata
            
        Returns:
            True if entities match (exact, substring, or fuzzy)
        """
        # Normalize both
        query_norm = self.normalize_name(query_entity)
        doc_norm = self.normalize_name(doc_entity)
        
        # Exact match after normalization
        if query_norm == doc_norm:
            return True
        
        # Substring match (one contains the other)
        if query_norm in doc_norm or doc_norm in query_norm:
            return True
        
        # Fuzzy similarity match
        similarity = SequenceMatcher(None, query_norm, doc_norm).ratio()
        if similarity >= self.similarity_threshold:
            return True
        
        return False
    
    def match_any(self, query_entities: List[str], doc_entities: List[str]) -> bool:
        """
        Check if any query entity matches any doc entity
        
        Args:
            query_entities: List of entities from query
            doc_entities: List of entities from document
            
        Returns:
            True if at least one match found
        """
        for query_ent in query_entities:
            for doc_ent in doc_entities:
                if self.fuzzy_match(query_ent, doc_ent):
                    return True
        return False
    
    def match_score(self, query_entities: List[str], doc_entities: List[str]) -> float:
        """
        Calculate match score (0-1) based on entity overlap
        
        Returns:
            Score from 0 (no matches) to 1 (all match)
        """
        if not query_entities:
            return 0.0
        
        matches = sum(
            1 for q_ent in query_entities
            if any(self.fuzzy_match(q_ent, d_ent) for d_ent in doc_entities)
        )
        
        return matches / len(query_entities)
```

**Integration with MetadataStore:**

```python
# Add to src/metadata_store.py

from src.entity_matcher import EntityMatcher

class MetadataStore:
    def __init__(self, db_path: str = "data/metadata.db"):
        # ... existing code ...
        self.entity_matcher = EntityMatcher(similarity_threshold=0.85)
    
    def filter_documents_fuzzy(self,
                               doc_ids: List[str],
                               people: Optional[List[str]] = None,
                               locations: Optional[List[str]] = None,
                               match_mode: str = 'fuzzy') -> List[str]:
        """
        Filter documents with fuzzy entity matching
        
        Args:
            doc_ids: Document IDs to filter
            people: People to match (fuzzy)
            locations: Locations to match (fuzzy)
            match_mode: 'exact', 'fuzzy', or 'any'
        """
        matched_docs = []
        
        for doc_id in doc_ids:
            doc_metadata = self.get_metadata(doc_id)
            if not doc_metadata:
                continue
            
            # Check people match
            if people:
                people_match = self.entity_matcher.match_any(
                    people, 
                    doc_metadata['people']
                )
                if not people_match:
                    continue
            
            # Check locations match
            if locations:
                loc_match = self.entity_matcher.match_any(
                    locations,
                    doc_metadata['locations']
                )
                if not loc_match:
                    continue
            
            matched_docs.append(doc_id)
        
        return matched_docs
```

**Testing:**
```python
def test_fuzzy_matching():
    matcher = EntityMatcher()
    
    # Normalization
    assert matcher.normalize_name("G. Maxwell") == "maxwell"
    assert matcher.normalize_name("The Clinton Foundation") == "clinton foundation"
    
    # Fuzzy matching
    assert matcher.fuzzy_match("Maxwell", "Ghislaine Maxwell")
    assert matcher.fuzzy_match("Maxwell", "G. Maxwell")
    assert matcher.fuzzy_match("Epstein", "Jeffrey Epstein")
    assert not matcher.fuzzy_match("Maxwell", "Einstein")
```

**Impact:**
- Finds 2-3x more relevant documents
- Better recall without sacrificing precision
- Handles name variations automatically

---

## 📋 TODO: Flexible Filtering Strategies

### Priority: HIGH | Effort: HIGH | Impact: CRITICAL

### Problem

Current: Strict AND logic filters too aggressively (500 → 14 docs)
Needed: Flexible strategies to maintain 50-100 docs for MVP 3

### Solution 3: Multi-Mode Filtering

**File to Modify:** `src/enhanced_search.py`

**Implementation:**

```python
class EnhancedSearchEngine:
    """Enhanced search with flexible filtering strategies"""
    
    def search_adaptive(self,
                       query: str,
                       top_k: int = 10,
                       filter_strategy: str = 'adaptive',
                       min_candidates: int = 50,
                       max_candidates: int = 100) -> List[Dict]:
        """
        Search with adaptive filtering strategy
        
        Args:
            query: Search query
            top_k: Final results to return
            filter_strategy: 'strict', 'loose', 'adaptive', 'boost'
            min_candidates: Minimum docs to pass to Tier 3
            max_candidates: Maximum docs to pass to Tier 3
            
        Returns:
            Ranked search results
        """
        # TIER 1: BM25 Search
        logger.info(f"Tier 1: BM25 search")
        bm25_results = self.bm25_engine.search(query, top_k=500)
        logger.info(f"BM25 found {len(bm25_results)} candidates")
        
        if not bm25_results:
            return []
        
        # Extract entities from query
        entities = self._extract_query_entities(query)
        
        if not entities or filter_strategy == 'none':
            # No filtering, return BM25 results
            return bm25_results[:top_k]
        
        # TIER 2: Apply filtering strategy
        if filter_strategy == 'strict':
            filtered = self._filter_strict(bm25_results, entities)
        elif filter_strategy == 'loose':
            filtered = self._filter_loose(bm25_results, entities)
        elif filter_strategy == 'boost':
            filtered = self._filter_with_boost(bm25_results, entities)
        else:  # adaptive
            filtered = self._filter_adaptive(
                bm25_results, 
                entities, 
                min_candidates
            )
        
        logger.info(f"Tier 2: Filtered to {len(filtered)} candidates")
        
        # Ensure within range for Tier 3
        if len(filtered) < min_candidates:
            logger.warning(f"Only {len(filtered)} candidates, using top BM25 results")
            return bm25_results[:max_candidates]
        
        return filtered[:top_k]
    
    def _filter_strict(self, 
                       results: List[Dict], 
                       entities: Dict) -> List[Dict]:
        """
        Strict AND filtering: ALL entities must match
        Use for: Highly specific queries
        """
        doc_ids = [r['doc_id'] for r in results]
        
        filtered_ids = self.metadata_store.filter_documents_fuzzy(
            doc_ids=doc_ids,
            people=entities.get('people'),
            locations=entities.get('locations'),
            organizations=entities.get('organizations')
        )
        
        return [r for r in results if r['doc_id'] in filtered_ids]
    
    def _filter_loose(self,
                      results: List[Dict],
                      entities: Dict) -> List[Dict]:
        """
        Loose OR filtering: ANY entity match counts
        Use for: Broad exploration
        """
        matched_results = []
        
        for result in results:
            doc_metadata = self.metadata_store.get_metadata(result['doc_id'])
            if not doc_metadata:
                continue
            
            # Check if ANY entity matches
            has_match = False
            
            if entities.get('people'):
                if self.entity_matcher.match_any(
                    entities['people'], 
                    doc_metadata['people']
                ):
                    has_match = True
            
            if entities.get('locations'):
                if self.entity_matcher.match_any(
                    entities['locations'],
                    doc_metadata['locations']
                ):
                    has_match = True
            
            if entities.get('organizations'):
                if self.entity_matcher.match_any(
                    entities['organizations'],
                    doc_metadata['organizations']
                ):
                    has_match = True
            
            if has_match:
                matched_results.append(result)
        
        return matched_results
    
    def _filter_with_boost(self,
                          results: List[Dict],
                          entities: Dict) -> List[Dict]:
        """
        Soft boosting: Don't filter out, just boost matching docs
        Use for: MVP 3 (preserves candidates for dense search)
        """
        for result in results:
            doc_metadata = self.metadata_store.get_metadata(result['doc_id'])
            if not doc_metadata:
                continue
            
            # Calculate metadata match score
            boost_score = 0.0
            
            # People match (30% boost)
            if entities.get('people'):
                people_score = self.entity_matcher.match_score(
                    entities['people'],
                    doc_metadata['people']
                )
                boost_score += people_score * 0.3
            
            # Location match (20% boost)
            if entities.get('locations'):
                loc_score = self.entity_matcher.match_score(
                    entities['locations'],
                    doc_metadata['locations']
                )
                boost_score += loc_score * 0.2
            
            # Organization match (20% boost)
            if entities.get('organizations'):
                org_score = self.entity_matcher.match_score(
                    entities['organizations'],
                    doc_metadata['organizations']
                )
                boost_score += org_score * 0.2
            
            # Apply boost to BM25 score
            result['score'] = result['score'] * (1 + boost_score)
            result['metadata_boost'] = boost_score
        
        # Re-sort by boosted scores
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def _filter_adaptive(self,
                        results: List[Dict],
                        entities: Dict,
                        min_candidates: int) -> List[Dict]:
        """
        Adaptive filtering: Try strict, fall back to loose if needed
        Use for: General queries (default)
        """
        # Try strict first
        strict_filtered = self._filter_strict(results, entities)
        
        if len(strict_filtered) >= min_candidates:
            logger.info(f"Adaptive: Using strict filter ({len(strict_filtered)} docs)")
            return strict_filtered
        
        # Fall back to loose
        loose_filtered = self._filter_loose(results, entities)
        
        if len(loose_filtered) >= min_candidates:
            logger.info(f"Adaptive: Using loose filter ({len(loose_filtered)} docs)")
            return loose_filtered
        
        # Fall back to boost (no filtering)
        logger.info(f"Adaptive: Using soft boost (preserving all {len(results)} docs)")
        return self._filter_with_boost(results, entities)
    
    def _extract_query_entities(self, query: str) -> Dict:
        """Extract entities from query with validation"""
        metadata = self.metadata_extractor.extract_metadata(query, "query")
        
        return {
            'people': metadata['people'] if metadata['people'] else None,
            'locations': metadata['locations'] if metadata['locations'] else None,
            'organizations': metadata['organizations'] if metadata['organizations'] else None
        }
```

**Usage Examples:**

```python
# For MVP 2 (current): Strict filtering OK
results = search.search_adaptive(
    "Maxwell Paris meetings",
    filter_strategy='strict'  # Returns 10-20 docs (precise)
)

# For MVP 3 (future): Soft boost preserves candidates
results = search.search_adaptive(
    "Maxwell Paris meetings",
    filter_strategy='boost',   # Returns 50-100 docs (for dense search)
    min_candidates=50
)

# General use: Adaptive (tries strict, falls back)
results = search.search_adaptive(
    "Maxwell Paris meetings",
    filter_strategy='adaptive',  # Smart fallback
    min_candidates=50
)
```

**Impact:**
- **Strict**: 500 → 14 docs (high precision, MVP 2)
- **Loose**: 500 → 80 docs (better recall, good for MVP 3)
- **Boost**: 500 → 500 docs (all preserved, reranked)
- **Adaptive**: Automatically chooses best strategy

---

## 📋 TODO: Metadata as Ranking Signal

### Priority: MEDIUM | Effort: MEDIUM | Impact: HIGH (for MVP 3)

### Problem

Current: Metadata is binary (match or no match)
Needed: Use metadata confidence scores for ranking

### Solution 4: Scoring System

**File to Modify:** `src/enhanced_search.py`

**Implementation:**

```python
class MetadataScorer:
    """Calculate metadata-based relevance scores"""
    
    def __init__(self):
        self.entity_matcher = EntityMatcher()
        
        # Scoring weights
        self.weights = {
            'person_match': 0.30,
            'location_match': 0.20,
            'org_match': 0.20,
            'date_match': 0.15,
            'entity_density': 0.10,
            'exact_match_bonus': 0.05
        }
    
    def calculate_metadata_score(self,
                                 doc_metadata: Dict,
                                 query_entities: Dict) -> float:
        """
        Calculate comprehensive metadata relevance score
        
        Returns:
            Score from 0.0 (no match) to 1.0 (perfect match)
        """
        total_score = 0.0
        max_possible = 0.0
        
        # Person matching
        if query_entities.get('people'):
            max_possible += self.weights['person_match']
            person_score = self.entity_matcher.match_score(
                query_entities['people'],
                doc_metadata['people']
            )
            total_score += person_score * self.weights['person_match']
        
        # Location matching
        if query_entities.get('locations'):
            max_possible += self.weights['location_match']
            loc_score = self.entity_matcher.match_score(
                query_entities['locations'],
                doc_metadata['locations']
            )
            total_score += loc_score * self.weights['location_match']
        
        # Organization matching
        if query_entities.get('organizations'):
            max_possible += self.weights['org_match']
            org_score = self.entity_matcher.match_score(
                query_entities['organizations'],
                doc_metadata['organizations']
            )
            total_score += org_score * self.weights['org_match']
        
        # Entity density (more entities = likely more relevant)
        total_entities = (len(doc_metadata['people']) + 
                         len(doc_metadata['locations']) +
                         len(doc_metadata['organizations']))
        max_possible += self.weights['entity_density']
        
        # Normalize (cap at 20 entities)
        density_score = min(total_entities / 20, 1.0)
        total_score += density_score * self.weights['entity_density']
        
        # Normalize to 0-1 range
        if max_possible > 0:
            return total_score / max_possible
        return 0.0
```

**Integration:**

```python
def hybrid_ranking(self, results: List[Dict], query: str) -> List[Dict]:
    """
    Combine BM25 + Metadata scores for final ranking
    
    Final Score = (BM25 * 0.7) + (Metadata * 0.3)
    """
    query_entities = self._extract_query_entities(query)
    scorer = MetadataScorer()
    
    for result in results:
        doc_metadata = self.metadata_store.get_metadata(result['doc_id'])
        
        if doc_metadata:
            # Calculate metadata score
            metadata_score = scorer.calculate_metadata_score(
                doc_metadata,
                query_entities
            )
            
            # Combine scores
            bm25_normalized = min(result['score'] / 10, 1.0)  # Normalize BM25
            
            result['metadata_score'] = metadata_score
            result['hybrid_score'] = (
                bm25_normalized * 0.7 +
                metadata_score * 0.3
            )
        else:
            result['metadata_score'] = 0.0
            result['hybrid_score'] = result['score']
    
    # Re-rank by hybrid score
    results.sort(key=lambda x: x['hybrid_score'], reverse=True)
    
    return results
```

**Impact:**
- Better ranking quality
- Metadata influences results without filtering
- Perfect for MVP 3 integration

---

## 📋 TODO: Performance Monitoring

### Priority: LOW | Effort: LOW | Impact: MEDIUM

### Solution 5: Filtering Metrics

**File to Create:** `src/search_metrics.py`

```python
"""
Track metadata filtering performance
"""

from typing import Dict, List
import time
from collections import defaultdict


class SearchMetrics:
    """Monitor search and filtering performance"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def log_search(self,
                   query: str,
                   bm25_count: int,
                   filtered_count: int,
                   final_count: int,
                   filter_strategy: str,
                   time_ms: float):
        """Log a search operation"""
        
        self.metrics['queries'].append({
            'query': query,
            'bm25_candidates': bm25_count,
            'after_filtering': filtered_count,
            'final_results': final_count,
            'filter_ratio': filtered_count / bm25_count if bm25_count > 0 else 0,
            'strategy': filter_strategy,
            'time_ms': time_ms
        })
    
    def get_statistics(self) -> Dict:
        """Get aggregated statistics"""
        if not self.metrics['queries']:
            return {}
        
        queries = self.metrics['queries']
        
        return {
            'total_queries': len(queries),
            'avg_bm25_candidates': sum(q['bm25_candidates'] for q in queries) / len(queries),
            'avg_filtered': sum(q['after_filtering'] for q in queries) / len(queries),
            'avg_filter_ratio': sum(q['filter_ratio'] for q in queries) / len(queries),
            'avg_time_ms': sum(q['time_ms'] for q in queries) / len(queries),
            'strategies_used': {
                strategy: sum(1 for q in queries if q['strategy'] == strategy)
                for strategy in set(q['strategy'] for q in queries)
            }
        }
    
    def report(self) -> str:
        """Generate human-readable report"""
        stats = self.get_statistics()
        
        if not stats:
            return "No search metrics recorded"
        
        report = f"""
Search Performance Report
========================
Total Queries: {stats['total_queries']}

Filtering Performance:
- Avg BM25 Candidates: {stats['avg_bm25_candidates']:.0f}
- Avg After Filtering: {stats['avg_filtered']:.0f}
- Avg Filter Ratio: {stats['avg_filter_ratio']:.1%}

Timing:
- Avg Query Time: {stats['avg_time_ms']:.0f}ms

Strategies Used:
"""
        for strategy, count in stats['strategies_used'].items():
            report += f"- {strategy}: {count} times\n"
        
        return report
```

**Usage:**

```python
# In enhanced_search.py
self.metrics = SearchMetrics()

def search_adaptive(self, query, ...):
    start_time = time.time()
    
    bm25_results = self.bm25_search(query, ...)
    filtered_results = self.filter_adaptive(...)
    
    # Log metrics
    self.metrics.log_search(
        query=query,
        bm25_count=len(bm25_results),
        filtered_count=len(filtered_results),
        final_count=len(final_results),
        filter_strategy='adaptive',
        time_ms=(time.time() - start_time) * 1000
    )
    
    return final_results

# Get report
print(search_engine.metrics.report())
```

---

## 🔄 Implementation Roadmap

### Phase 1: Quick Wins (1-2 days)
- [ ] Add entity validation to `metadata_extractor.py`
- [ ] Apply validation to existing extracted entities (no re-extraction needed)
- [ ] Test on sample metadata without re-indexing
- [ ] Measure improvement in entity quality
- [ ] (Optional) Re-index if you want to persist cleaned entities

### Phase 2: Fuzzy Matching (2-3 days)
- [ ] Create `entity_matcher.py`
- [ ] Add fuzzy matching to `metadata_store.py`
- [ ] Update unit tests
- [ ] Benchmark matching performance

### Phase 3: Flexible Filtering (3-4 days)
- [ ] Implement multi-mode filtering in `enhanced_search.py`
- [ ] Add `filter_strategy` parameter
- [ ] Test all strategies (strict, loose, boost, adaptive)
- [ ] Update CLI to allow strategy selection

### Phase 4: Scoring System (2-3 days)
- [ ] Create `MetadataScorer` class
- [ ] Implement hybrid ranking
- [ ] A/B test vs current ranking
- [ ] Tune scoring weights

### Phase 5: Monitoring (1 day)
- [ ] Add `SearchMetrics` class
- [ ] Integrate logging
- [ ] Create dashboard/report

### Phase 6: MVP 3 Preparation (1 day)
- [ ] Set default `filter_strategy='boost'` for dense search
- [ ] Set `min_candidates=50`
- [ ] Document API for MVP 3 integration

**Total Estimated Effort: 10-14 days**

---

## 🧪 Testing Strategy

### Unit Tests to Add

```python
# tests/test_entity_quality.py
def test_entity_validation()
def test_noise_rejection()
def test_fuzzy_matching()
def test_normalization()

# tests/test_filtering_strategies.py
def test_strict_filtering()
def test_loose_filtering()
def test_boost_strategy()
def test_adaptive_fallback()

# tests/test_metadata_scoring.py
def test_score_calculation()
def test_hybrid_ranking()
def test_score_normalization()
```

### Integration Tests

```python
# Test full pipeline
def test_end_to_end_filtering():
    query = "What did Maxwell do in Paris?"
    
    # Test each strategy
    strict_results = search.search_adaptive(query, strategy='strict')
    loose_results = search.search_adaptive(query, strategy='loose')
    boost_results = search.search_adaptive(query, strategy='boost')
    
    # Verify candidate counts
    assert len(strict_results) < len(loose_results) < len(boost_results)
    assert len(boost_results) >= 50  # Enough for MVP 3
```

### Performance Tests

```python
def test_filtering_performance():
    """Ensure filtering doesn't slow down queries"""
    
    start = time.time()
    results = search.search_adaptive(query, strategy='boost')
    elapsed = time.time() - start
    
    assert elapsed < 0.2  # Under 200ms
```

---

## 📊 Success Metrics

### Before Improvements (Current MVP 2)
```
Query: "Maxwell Paris meetings"
├── BM25: 500 candidates
├── Metadata Filter: 14 docs (97% reduction!)
├── Problems:
│   ├── Too aggressive filtering
│   ├── Noisy entities ('%%', '& Alcorta')
│   └── Missing relevant docs (exact match only)
```

### After Improvements (Target)
```
Query: "Maxwell Paris meetings"
├── BM25: 500 candidates
├── Metadata Boost: 80 docs ranked by relevance
│   ├── 50-100 docs preserved for dense search
│   ├── Clean entities (validated)
│   ├── Fuzzy matching (finds variations)
│   └── Soft boosting (no hard filtering)
├── Quality Improvements:
│   ├── +60% recall (finds more relevant docs)
│   ├── -80% entity noise
│   └── Ready for MVP 3 dense search
```

---

## 🎯 Priority Matrix

| Task | Priority | Effort | Impact | MVP | Notes |
|------|----------|--------|--------|-----|-------|
| Entity Validation | HIGH | MED | HIGH | 2 | Quick win, big impact |
| Fuzzy Matching | HIGH | MED | HIGH | 2→3 | Critical for MVP 3 |
| Flexible Strategies | HIGH | HIGH | CRITICAL | 3 | Enables dense search |
| Metadata Scoring | MED | MED | HIGH | 3 | Improves ranking |
| Performance Monitoring | LOW | LOW | MED | 3 | Nice to have |

---

## 📝 Notes for MVP 3 Integration

When implementing dense embeddings (MVP 3), use this configuration:

```python
# Three-tier search for MVP 3
def mvp3_search(query: str, top_k: int = 10):
    # Tier 1: BM25 (broad recall)
    bm25_results = bm25_search(query, top_k=500)
    
    # Tier 2: Metadata (flexible filtering)
    filtered_results = enhanced_search.search_adaptive(
        query,
        filter_strategy='boost',  # ← Use soft boosting!
        min_candidates=50,         # ← Ensure enough for dense search
        max_candidates=100
    )
    
    # Tier 3: Dense embeddings (semantic ranking)
    final_results = dense_search(
        filtered_results,  # Has 50-100 quality candidates
        query,
        top_k=top_k
    )
    
    return final_results
```

**Key Points:**
- Use `strategy='boost'` to preserve candidates
- Set `min_candidates=50` to ensure sufficient docs for dense search
- Metadata scores can be passed to dense layer for hybrid ranking
- Monitor `filter_ratio` to ensure not over-filtering

---

## 🚀 Quick Start

To implement these improvements:

```bash
# 1. Update entity extraction with validation
# Edit: src/metadata_extractor.py (add _is_valid_entity() method)
# NOTE: This filters already-extracted entities, does NOT re-run NER

# 2. (Optional) Re-index to persist cleaned entities to database
# Only needed if you want to save filtered entities permanently
python build_metadata_index.py

# 3. Add fuzzy matching
# Create: src/entity_matcher.py

# 4. Update search engine with flexible strategies
# Edit: src/enhanced_search.py (add strategies)

# 5. Test
pytest tests/test_entity_quality.py -v
pytest tests/test_filtering_strategies.py -v

# 6. Benchmark
python benchmark_filtering.py
```

---

## 📖 References

- **Entity Validation**: See `src/metadata_extractor.py:_is_valid_entity()`
- **Fuzzy Matching**: See `src/entity_matcher.py:fuzzy_match()`
- **Filter Strategies**: See `src/enhanced_search.py:search_adaptive()`
- **Scoring System**: See `src/enhanced_search.py:MetadataScorer`

---

**Status**: TODO - Ready for implementation
**Target**: MVP 2.5 (before MVP 3)
**Estimated Timeline**: 2-3 weeks
**Reviewers**: @team

---

*Generated: November 23, 2025*

