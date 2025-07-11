"""
Strategic Indexing Manager for Normalized Database Schema

This module provides intelligent indexing strategies that optimize query performance
by analyzing actual query patterns and creating targeted indexes. It monitors
query performance and suggests optimizations based on real usage patterns.

Key Features:
1. Query pattern analysis and learning
2. Automatic index recommendation
3. Composite index optimization
4. Partial index creation for filtered queries
5. Index usage monitoring and cleanup
6. Performance impact measurement
"""

import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, Counter

from ..models.normalized_document_models import IndexStrategy, QueryPattern
from ..vector_storage.qdrant_store import QdrantVectorStore
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a specific query"""

    query_signature: str
    execution_time_ms: float
    result_count: int
    filters_used: List[str]
    sort_fields: List[str]
    timestamp: datetime
    collection_name: str
    index_hits: List[str] = field(default_factory=list)
    full_scan: bool = False


@dataclass
class IndexPerformance:
    """Performance metrics for an index"""

    index_name: str
    table_name: str
    size_mb: float
    hit_count: int = 0
    last_used: Optional[datetime] = None
    creation_time: datetime = field(default_factory=datetime.now)
    estimated_benefit_ms: float = 0.0
    maintenance_cost: float = 0.0


@dataclass
class IndexRecommendation:
    """Recommendation for creating or modifying an index"""

    table_name: str
    columns: List[str]
    index_type: str = "btree"
    partial_condition: Optional[str] = None
    priority: int = 1  # 1=high, 2=medium, 3=low
    estimated_improvement_ms: float = 0.0
    estimated_size_mb: float = 0.0
    reasoning: str = ""
    query_patterns_benefited: List[str] = field(default_factory=list)


class IndexingStrategyManager:
    """
    Manages indexing strategies for optimal query performance
    """

    def __init__(self, qdrant_store: QdrantVectorStore):
        """
        Initialize the indexing strategy manager

        Args:
            qdrant_store: Vector database store
        """
        self.qdrant_store = qdrant_store
        self.logger = logger

        # Query pattern tracking
        self.query_patterns: Dict[str, QueryPattern] = {}
        self.query_metrics: List[QueryMetrics] = []
        self.index_performance: Dict[str, IndexPerformance] = {}

        # Configuration
        self.analysis_window_days = 7
        self.min_query_frequency = 5  # Minimum frequency to consider for optimization
        self.slow_query_threshold_ms = 1000  # Queries slower than this are prioritized
        self.index_benefit_threshold_ms = 100  # Minimum benefit to justify an index

        # Collections to monitor
        self.monitored_collections = {
            "legal_matters": [
                "matter_number",
                "client_name",
                "matter_type",
                "access_level",
            ],
            "legal_cases": ["matter_id", "case_number", "case_name", "status"],
            "document_cores": [
                "document_hash",
                "metadata_hash",
                "file_name",
                "box_file_id",
            ],
            "document_metadata": [
                "document_id",
                "document_type",
                "document_date",
                "ai_model_used",
            ],
            "document_case_junctions": ["document_id", "case_id", "production_batch"],
            "document_relationships": [
                "source_document_id",
                "target_document_id",
                "relationship_type",
            ],
            "chunk_metadata": ["document_id", "chunk_index", "semantic_type"],
            "deduplication_records": [
                "content_hash",
                "metadata_hash",
                "primary_document_id",
            ],
        }

    async def analyze_query_patterns(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Analyze query patterns over a time period

        Args:
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            Analysis results with recommendations
        """
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=self.analysis_window_days)
            if not end_date:
                end_date = datetime.now()

            self.logger.info(
                f"Analyzing query patterns from {start_date} to {end_date}"
            )

            # Step 1: Collect query metrics
            relevant_metrics = [
                metric
                for metric in self.query_metrics
                if start_date <= metric.timestamp <= end_date
            ]

            # Step 2: Identify common patterns
            pattern_analysis = self._analyze_patterns(relevant_metrics)

            # Step 3: Identify slow queries
            slow_queries = self._identify_slow_queries(relevant_metrics)

            # Step 4: Generate index recommendations
            recommendations = await self._generate_index_recommendations(
                pattern_analysis, slow_queries
            )

            # Step 5: Analyze current index usage
            index_usage = await self._analyze_current_index_usage()

            analysis_results = {
                "analysis_period": {
                    "start": start_date,
                    "end": end_date,
                    "total_queries": len(relevant_metrics),
                },
                "pattern_analysis": pattern_analysis,
                "slow_queries": slow_queries,
                "index_recommendations": recommendations,
                "current_index_usage": index_usage,
                "performance_summary": self._create_performance_summary(
                    relevant_metrics
                ),
            }

            self.logger.info(
                f"Query pattern analysis completed: {len(recommendations)} recommendations"
            )
            return analysis_results

        except Exception as e:
            self.logger.error(f"Query pattern analysis failed: {e}")
            raise

    def record_query_metrics(
        self,
        collection_name: str,
        filters: Dict[str, Any],
        sort_fields: List[str],
        execution_time_ms: float,
        result_count: int,
    ):
        """
        Record metrics for a query execution

        Args:
            collection_name: Name of the collection queried
            filters: Filters applied to the query
            sort_fields: Fields used for sorting
            execution_time_ms: Query execution time
            result_count: Number of results returned
        """
        try:
            # Create query signature for pattern recognition
            query_signature = self._create_query_signature(
                collection_name, filters, sort_fields
            )

            # Record metrics
            metrics = QueryMetrics(
                query_signature=query_signature,
                execution_time_ms=execution_time_ms,
                result_count=result_count,
                filters_used=list(filters.keys()),
                sort_fields=sort_fields,
                timestamp=datetime.now(),
                collection_name=collection_name,
            )

            self.query_metrics.append(metrics)

            # Update or create query pattern
            if query_signature in self.query_patterns:
                pattern = self.query_patterns[query_signature]
                pattern.frequency += 1
                pattern.avg_execution_time_ms = (
                    pattern.avg_execution_time_ms * (pattern.frequency - 1)
                    + execution_time_ms
                ) / pattern.frequency
                pattern.last_seen = datetime.now()
            else:
                pattern = QueryPattern(
                    query_signature=query_signature,
                    frequency=1,
                    avg_execution_time_ms=execution_time_ms,
                    filter_columns=list(filters.keys()),
                    sort_columns=sort_fields,
                )
                self.query_patterns[query_signature] = pattern

            # Keep only recent metrics to prevent memory bloat
            cutoff_date = datetime.now() - timedelta(days=self.analysis_window_days * 2)
            self.query_metrics = [
                metric
                for metric in self.query_metrics
                if metric.timestamp > cutoff_date
            ]

        except Exception as e:
            self.logger.error(f"Failed to record query metrics: {e}")

    def _create_query_signature(
        self, collection_name: str, filters: Dict[str, Any], sort_fields: List[str]
    ) -> str:
        """Create a normalized signature for query pattern recognition"""
        # Sort keys for consistent signatures
        filter_keys = sorted(filters.keys())
        sort_keys = sorted(sort_fields)

        signature_parts = [collection_name, "|".join(filter_keys), "|".join(sort_keys)]

        signature = "::".join(signature_parts)
        return hashlib.md5(signature.encode()).hexdigest()[:16]

    def _analyze_patterns(self, metrics: List[QueryMetrics]) -> Dict[str, Any]:
        """Analyze query patterns to identify optimization opportunities"""
        pattern_stats = defaultdict(
            lambda: {
                "count": 0,
                "total_time_ms": 0.0,
                "collections": set(),
                "common_filters": Counter(),
                "common_sorts": Counter(),
            }
        )

        for metric in metrics:
            pattern = pattern_stats[metric.query_signature]
            pattern["count"] += 1
            pattern["total_time_ms"] += metric.execution_time_ms
            pattern["collections"].add(metric.collection_name)
            pattern["common_filters"].update(metric.filters_used)
            pattern["common_sorts"].update(metric.sort_fields)

        # Convert to analyzable format
        analyzed_patterns = {}
        for signature, stats in pattern_stats.items():
            if stats["count"] >= self.min_query_frequency:
                analyzed_patterns[signature] = {
                    "frequency": stats["count"],
                    "avg_execution_time_ms": stats["total_time_ms"] / stats["count"],
                    "collections": list(stats["collections"]),
                    "most_common_filters": dict(stats["common_filters"].most_common(5)),
                    "most_common_sorts": dict(stats["common_sorts"].most_common(3)),
                }

        return analyzed_patterns

    def _identify_slow_queries(
        self, metrics: List[QueryMetrics]
    ) -> List[Dict[str, Any]]:
        """Identify queries that are consistently slow"""
        slow_queries = []

        for metric in metrics:
            if metric.execution_time_ms > self.slow_query_threshold_ms:
                slow_queries.append(
                    {
                        "signature": metric.query_signature,
                        "collection": metric.collection_name,
                        "execution_time_ms": metric.execution_time_ms,
                        "filters_used": metric.filters_used,
                        "sort_fields": metric.sort_fields,
                        "timestamp": metric.timestamp,
                        "result_count": metric.result_count,
                    }
                )

        # Sort by execution time descending
        slow_queries.sort(key=lambda x: x["execution_time_ms"], reverse=True)
        return slow_queries[:50]  # Top 50 slowest queries

    async def _generate_index_recommendations(
        self, pattern_analysis: Dict[str, Any], slow_queries: List[Dict[str, Any]]
    ) -> List[IndexRecommendation]:
        """Generate index recommendations based on analysis"""
        recommendations = []

        # Analyze patterns for composite index opportunities
        for signature, pattern in pattern_analysis.items():
            if pattern["avg_execution_time_ms"] > self.index_benefit_threshold_ms:
                collection = pattern["collections"][0]  # Primary collection

                # Get most common filter combinations
                common_filters = list(pattern["most_common_filters"].keys())
                common_sorts = list(pattern["most_common_sorts"].keys())

                if len(common_filters) > 1:
                    # Composite index recommendation
                    rec = IndexRecommendation(
                        table_name=collection,
                        columns=common_filters[:3],  # Limit to 3 columns for efficiency
                        index_type="btree",
                        priority=self._calculate_priority(pattern),
                        estimated_improvement_ms=pattern["avg_execution_time_ms"] * 0.6,
                        reasoning=f"Frequent pattern with {pattern['frequency']} occurrences, "
                        f"avg time {pattern['avg_execution_time_ms']:.1f}ms",
                        query_patterns_benefited=[signature],
                    )
                    recommendations.append(rec)

                if common_sorts:
                    # Sort index recommendation
                    sort_columns = common_filters + common_sorts
                    rec = IndexRecommendation(
                        table_name=collection,
                        columns=sort_columns[:3],
                        index_type="btree",
                        priority=self._calculate_priority(pattern) + 1,
                        estimated_improvement_ms=pattern["avg_execution_time_ms"] * 0.4,
                        reasoning=f"Sort optimization for pattern with {pattern['frequency']} occurrences",
                        query_patterns_benefited=[signature],
                    )
                    recommendations.append(rec)

        # Analyze slow queries for specific optimizations
        for slow_query in slow_queries[:20]:  # Top 20 slowest
            collection = slow_query["collection"]
            filters = slow_query["filters_used"]

            if filters:
                rec = IndexRecommendation(
                    table_name=collection,
                    columns=filters[:2],  # Limit complexity
                    index_type="btree",
                    priority=1,  # High priority for slow queries
                    estimated_improvement_ms=slow_query["execution_time_ms"] * 0.7,
                    reasoning=f"Slow query optimization - {slow_query['execution_time_ms']:.1f}ms execution time",
                    query_patterns_benefited=[slow_query["signature"]],
                )
                recommendations.append(rec)

        # Analyze partial index opportunities
        partial_recommendations = self._analyze_partial_index_opportunities(
            pattern_analysis
        )
        recommendations.extend(partial_recommendations)

        # Remove duplicates and prioritize
        recommendations = self._deduplicate_and_prioritize_recommendations(
            recommendations
        )

        return recommendations[:20]  # Return top 20 recommendations

    def _calculate_priority(self, pattern: Dict[str, Any]) -> int:
        """Calculate priority for index recommendation"""
        frequency = pattern["frequency"]
        avg_time = pattern["avg_execution_time_ms"]

        if avg_time > 2000 and frequency > 20:
            return 1  # High priority
        elif avg_time > 1000 and frequency > 10:
            return 2  # Medium priority
        else:
            return 3  # Low priority

    def _analyze_partial_index_opportunities(
        self, pattern_analysis: Dict[str, Any]
    ) -> List[IndexRecommendation]:
        """Identify opportunities for partial indexes"""
        recommendations = []

        # Look for patterns with consistent filter values
        for signature, pattern in pattern_analysis.items():
            common_filters = pattern["most_common_filters"]

            # Check for boolean or enum-like filters that could benefit from partial indexes
            for filter_name, frequency in common_filters.items():
                if frequency > pattern["frequency"] * 0.8:  # Used in 80% of queries
                    collection = pattern["collections"][0]

                    # Create partial index recommendation
                    rec = IndexRecommendation(
                        table_name=collection,
                        columns=[filter_name],
                        index_type="btree",
                        partial_condition=f"{filter_name} = true",  # Example condition
                        priority=2,
                        estimated_improvement_ms=pattern["avg_execution_time_ms"] * 0.3,
                        reasoning=f"Partial index for frequently filtered {filter_name}",
                        query_patterns_benefited=[signature],
                    )
                    recommendations.append(rec)

        return recommendations

    def _deduplicate_and_prioritize_recommendations(
        self, recommendations: List[IndexRecommendation]
    ) -> List[IndexRecommendation]:
        """Remove duplicate recommendations and prioritize by impact"""
        # Group by table and columns to find duplicates
        grouped = defaultdict(list)
        for rec in recommendations:
            key = f"{rec.table_name}::{','.join(sorted(rec.columns))}"
            grouped[key].append(rec)

        # Keep the best recommendation from each group
        deduplicated = []
        for group in grouped.values():
            # Sort by priority then by estimated improvement
            best_rec = min(
                group, key=lambda r: (r.priority, -r.estimated_improvement_ms)
            )

            # Combine reasoning from all recommendations in group
            all_reasoning = set(rec.reasoning for rec in group)
            best_rec.reasoning = "; ".join(all_reasoning)

            # Combine benefited patterns
            all_patterns = set()
            for rec in group:
                all_patterns.update(rec.query_patterns_benefited)
            best_rec.query_patterns_benefited = list(all_patterns)

            deduplicated.append(best_rec)

        # Sort by priority and impact
        deduplicated.sort(key=lambda r: (r.priority, -r.estimated_improvement_ms))
        return deduplicated

    async def _analyze_current_index_usage(self) -> Dict[str, Any]:
        """Analyze current index usage and identify unused indexes"""
        try:
            # Get information about current indexes
            # This would need to be implemented based on Qdrant's capabilities
            current_indexes = await self._get_current_indexes()

            usage_analysis = {
                "total_indexes": len(current_indexes),
                "used_indexes": [],
                "unused_indexes": [],
                "low_usage_indexes": [],
                "recommended_deletions": [],
            }

            for index_name, index_info in current_indexes.items():
                if index_name in self.index_performance:
                    perf = self.index_performance[index_name]
                    if perf.hit_count == 0:
                        usage_analysis["unused_indexes"].append(index_name)
                    elif perf.hit_count < 10:  # Arbitrary threshold
                        usage_analysis["low_usage_indexes"].append(index_name)
                    else:
                        usage_analysis["used_indexes"].append(index_name)

            return usage_analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze current index usage: {e}")
            return {}

    async def _get_current_indexes(self) -> Dict[str, Any]:
        """Get information about current indexes"""
        # This would need to be implemented based on Qdrant's index capabilities
        # For now, return empty dict
        return {}

    def _create_performance_summary(
        self, metrics: List[QueryMetrics]
    ) -> Dict[str, Any]:
        """Create a performance summary from metrics"""
        if not metrics:
            return {}

        execution_times = [m.execution_time_ms for m in metrics]
        result_counts = [m.result_count for m in metrics]

        return {
            "total_queries": len(metrics),
            "avg_execution_time_ms": sum(execution_times) / len(execution_times),
            "median_execution_time_ms": sorted(execution_times)[
                len(execution_times) // 2
            ],
            "slowest_query_ms": max(execution_times),
            "fastest_query_ms": min(execution_times),
            "avg_result_count": sum(result_counts) / len(result_counts),
            "slow_query_percentage": len(
                [t for t in execution_times if t > self.slow_query_threshold_ms]
            )
            / len(execution_times)
            * 100,
            "collections_queried": len(set(m.collection_name for m in metrics)),
        }

    async def apply_index_recommendation(
        self, recommendation: IndexRecommendation
    ) -> bool:
        """
        Apply an index recommendation to the database

        Args:
            recommendation: Index recommendation to apply

        Returns:
            True if successful, False otherwise
        """
        try:
            index_name = (
                f"idx_{recommendation.table_name}_{'_'.join(recommendation.columns)}"
            )

            # Create index strategy record
            strategy = IndexStrategy(
                table_name=recommendation.table_name,
                index_name=index_name,
                columns=recommendation.columns,
                index_type=recommendation.index_type,
                partial_condition=recommendation.partial_condition,
            )

            # Apply the index using Qdrant's payload indexing
            for column in recommendation.columns:
                self.qdrant_store.create_payload_index(
                    collection_name=recommendation.table_name, field_name=column
                )

            # Record index performance tracking
            self.index_performance[index_name] = IndexPerformance(
                index_name=index_name,
                table_name=recommendation.table_name,
                size_mb=recommendation.estimated_size_mb,
                estimated_benefit_ms=recommendation.estimated_improvement_ms,
            )

            self.logger.info(f"Applied index recommendation: {index_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to apply index recommendation: {e}")
            return False

    async def monitor_index_performance(self) -> Dict[str, Any]:
        """Monitor the performance impact of indexes"""
        try:
            monitoring_results = {
                "total_indexes": len(self.index_performance),
                "performance_improvements": [],
                "underperforming_indexes": [],
                "index_statistics": {},
            }

            for index_name, performance in self.index_performance.items():
                stats = {
                    "hit_count": performance.hit_count,
                    "last_used": performance.last_used,
                    "estimated_benefit_ms": performance.estimated_benefit_ms,
                    "maintenance_cost": performance.maintenance_cost,
                    "age_days": (datetime.now() - performance.creation_time).days,
                }

                monitoring_results["index_statistics"][index_name] = stats

                # Identify performance improvements
                if (
                    performance.hit_count > 100
                    and performance.estimated_benefit_ms > 50
                ):
                    monitoring_results["performance_improvements"].append(
                        {
                            "index_name": index_name,
                            "benefit_ms": performance.estimated_benefit_ms,
                            "usage_count": performance.hit_count,
                        }
                    )

                # Identify underperforming indexes
                if performance.hit_count < 10 and stats["age_days"] > 7:
                    monitoring_results["underperforming_indexes"].append(
                        {
                            "index_name": index_name,
                            "hit_count": performance.hit_count,
                            "age_days": stats["age_days"],
                        }
                    )

            return monitoring_results

        except Exception as e:
            self.logger.error(f"Index performance monitoring failed: {e}")
            return {}

    def get_query_statistics(self) -> Dict[str, Any]:
        """Get comprehensive query statistics"""
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_metrics = [m for m in self.query_metrics if m.timestamp > recent_cutoff]

        return {
            "total_patterns": len(self.query_patterns),
            "recent_queries_24h": len(recent_metrics),
            "top_patterns": sorted(
                [
                    (p.query_signature, p.frequency, p.avg_execution_time_ms)
                    for p in self.query_patterns.values()
                ],
                key=lambda x: x[1],
                reverse=True,
            )[:10],
            "slowest_patterns": sorted(
                [
                    (p.query_signature, p.avg_execution_time_ms, p.frequency)
                    for p in self.query_patterns.values()
                ],
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        }
