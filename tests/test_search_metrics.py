"""
Tests for search metrics and monitoring
"""

import pytest
from src.search_metrics import SearchMetrics


class TestSearchMetrics:
    """Test search metrics tracking"""
    
    @pytest.fixture
    def metrics(self):
        """Create fresh metrics instance"""
        return SearchMetrics()
    
    def test_log_search(self, metrics):
        """Should log search operations"""
        metrics.log_search(
            query="Maxwell Paris",
            bm25_count=500,
            filtered_count=80,
            final_count=10,
            filter_strategy='adaptive',
            time_ms=150.5
        )
        
        queries = metrics.get_queries()
        assert len(queries) == 1
        assert queries[0]['query'] == "Maxwell Paris"
        assert queries[0]['bm25_candidates'] == 500
        assert queries[0]['after_filtering'] == 80
    
    def test_calculate_filter_ratio(self, metrics):
        """Should calculate filter ratio correctly"""
        metrics.log_search(
            query="Test",
            bm25_count=100,
            filtered_count=50,
            final_count=10,
            filter_strategy='strict',
            time_ms=100.0
        )
        
        queries = metrics.get_queries()
        assert queries[0]['filter_ratio'] == 0.5  # 50/100
    
    def test_get_statistics(self, metrics):
        """Should calculate aggregate statistics"""
        # Log multiple searches
        metrics.log_search("Query1", 500, 100, 10, 'strict', 150.0)
        metrics.log_search("Query2", 500, 200, 10, 'loose', 175.0)
        metrics.log_search("Query3", 500, 500, 10, 'boost', 180.0)
        
        stats = metrics.get_statistics()
        
        assert stats['total_queries'] == 3
        assert stats['avg_bm25_candidates'] == 500.0
        assert stats['avg_filtered'] == (100 + 200 + 500) / 3
        assert stats['avg_time_ms'] == (150 + 175 + 180) / 3
    
    def test_strategies_used_tracking(self, metrics):
        """Should track which strategies were used"""
        metrics.log_search("Q1", 500, 100, 10, 'strict', 150.0)
        metrics.log_search("Q2", 500, 200, 10, 'strict', 175.0)
        metrics.log_search("Q3", 500, 500, 10, 'boost', 180.0)
        
        stats = metrics.get_statistics()
        strategies = stats['strategies_used']
        
        assert strategies['strict'] == 2
        assert strategies['boost'] == 1
    
    def test_report_generation(self, metrics):
        """Should generate readable report"""
        metrics.log_search("Query1", 500, 100, 10, 'adaptive', 150.0)
        
        report = metrics.report()
        
        assert 'Search Performance Report' in report
        assert 'Total Queries: 1' in report
        assert 'adaptive' in report.lower()
    
    def test_empty_metrics_report(self, metrics):
        """Should handle empty metrics"""
        report = metrics.report()
        assert 'No search metrics recorded' in report
        
        stats = metrics.get_statistics()
        assert stats == {}
    
    def test_clear_metrics(self, metrics):
        """Should clear all metrics"""
        metrics.log_search("Query1", 500, 100, 10, 'strict', 150.0)
        assert len(metrics.get_queries()) == 1
        
        metrics.clear()
        assert len(metrics.get_queries()) == 0
        assert metrics.get_statistics() == {}
    
    def test_export_to_dict(self, metrics):
        """Should export metrics as dictionary"""
        metrics.log_search("Query1", 500, 100, 10, 'strict', 150.0)
        metrics.log_search("Query2", 500, 200, 10, 'loose', 175.0)
        
        export = metrics.export_to_dict()
        
        assert 'queries' in export
        assert 'statistics' in export
        assert len(export['queries']) == 2
        assert export['statistics']['total_queries'] == 2
    
    def test_handle_zero_bm25_count(self, metrics):
        """Should handle zero BM25 count gracefully"""
        metrics.log_search(
            query="NoResults",
            bm25_count=0,
            filtered_count=0,
            final_count=0,
            filter_strategy='none',
            time_ms=50.0
        )
        
        queries = metrics.get_queries()
        assert queries[0]['filter_ratio'] == 0  # Should not divide by zero


class TestMetricsIntegration:
    """Test metrics integration with search engine"""
    
    def test_multiple_queries_tracking(self):
        """Should track multiple queries correctly"""
        metrics = SearchMetrics()
        
        # Simulate different query patterns
        queries = [
            ("Maxwell Paris", 500, 80, 10, 'adaptive'),
            ("Epstein flights", 500, 120, 10, 'loose'),
            ("Clinton Foundation", 500, 500, 10, 'boost'),
            ("Island meetings", 500, 40, 10, 'strict'),
        ]
        
        for query, bm25, filtered, final, strategy in queries:
            metrics.log_search(query, bm25, filtered, final, strategy, 150.0)
        
        stats = metrics.get_statistics()
        
        assert stats['total_queries'] == 4
        assert stats['avg_bm25_candidates'] == 500.0
        
        # Check all strategies are tracked
        strategies = stats['strategies_used']
        assert 'adaptive' in strategies
        assert 'loose' in strategies
        assert 'boost' in strategies
        assert 'strict' in strategies


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

