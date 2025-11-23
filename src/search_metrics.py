"""
Track metadata filtering performance
"""

from typing import Dict, List
import time
from collections import defaultdict
from loguru import logger


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
        """
        Log a search operation
        
        Args:
            query: The search query
            bm25_count: Number of candidates from BM25
            filtered_count: Number after filtering
            final_count: Number of final results returned
            filter_strategy: Strategy used ('strict', 'loose', 'boost', 'adaptive')
            time_ms: Time taken in milliseconds
        """
        
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
    
    def get_queries(self) -> List[Dict]:
        """Get list of all logged queries"""
        return self.metrics['queries']
    
    def clear(self):
        """Clear all metrics"""
        self.metrics = defaultdict(list)
        logger.info("Metrics cleared")
    
    def export_to_dict(self) -> Dict:
        """Export metrics as dictionary"""
        return {
            'queries': self.metrics['queries'],
            'statistics': self.get_statistics()
        }


# Usage Example
if __name__ == "__main__":
    metrics = SearchMetrics()
    
    # Simulate some searches
    metrics.log_search(
        query="Maxwell Paris meetings",
        bm25_count=500,
        filtered_count=80,
        final_count=10,
        filter_strategy='adaptive',
        time_ms=150.5
    )
    
    metrics.log_search(
        query="Epstein flight logs",
        bm25_count=500,
        filtered_count=120,
        final_count=10,
        filter_strategy='loose',
        time_ms=175.2
    )
    
    metrics.log_search(
        query="Clinton Foundation meetings",
        bm25_count=500,
        filtered_count=500,
        final_count=10,
        filter_strategy='boost',
        time_ms=180.8
    )
    
    # Print report
    print(metrics.report())
    
    # Get statistics
    stats = metrics.get_statistics()
    print(f"\nDetailed stats: {stats}")

