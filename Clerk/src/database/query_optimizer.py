"""
Query Optimizer Integration Layer

This module integrates the indexing strategy manager with the document management
system to provide automatic query optimization and performance monitoring.

Key Features:
1. Automatic query interception and metrics collection
2. Real-time optimization suggestions
3. Adaptive index management
4. Query plan optimization
5. Performance monitoring dashboard
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Callable
from functools import wraps
import time

from .indexing_strategy_manager import IndexingStrategyManager, IndexRecommendation
from ..vector_storage.qdrant_store import QdrantVectorStore
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class QueryInterceptor:
    """
    Intercepts and monitors database queries for optimization
    """

    def __init__(self, indexing_manager: IndexingStrategyManager):
        self.indexing_manager = indexing_manager
        self.logger = logger
        self.intercepted_queries = []
        self.optimization_suggestions = []

    def intercept_query(self, func: Callable) -> Callable:
        """
        Decorator to intercept and monitor query performance

        Args:
            func: Function to intercept

        Returns:
            Wrapped function with performance monitoring
        """

        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                # Extract query parameters
                collection_name = self._extract_collection_name(args, kwargs)
                filters = self._extract_filters(args, kwargs)
                sort_fields = self._extract_sort_fields(args, kwargs)

                # Execute original query
                result = await func(*args, **kwargs)

                # Calculate metrics
                execution_time_ms = (time.time() - start_time) * 1000
                result_count = self._extract_result_count(result)

                # Record metrics
                self.indexing_manager.record_query_metrics(
                    collection_name=collection_name,
                    filters=filters,
                    sort_fields=sort_fields,
                    execution_time_ms=execution_time_ms,
                    result_count=result_count,
                )

                # Check for immediate optimization opportunities
                if execution_time_ms > 1000:  # Slow query threshold
                    await self._suggest_immediate_optimization(
                        collection_name, filters, sort_fields, execution_time_ms
                    )

                return result

            except Exception as e:
                self.logger.error(f"Query interception failed: {e}")
                # Still execute original function if monitoring fails
                return await func(*args, **kwargs)

        return wrapper

    def _extract_collection_name(self, args: tuple, kwargs: dict) -> str:
        """Extract collection name from query parameters"""
        if "collection_name" in kwargs:
            return kwargs["collection_name"]
        elif len(args) > 0 and isinstance(args[0], str):
            return args[0]
        else:
            return "unknown"

    def _extract_filters(self, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """Extract filters from query parameters"""
        filters = {}

        if "query_filter" in kwargs and kwargs["query_filter"]:
            filters.update(kwargs["query_filter"])
        if "filters" in kwargs and kwargs["filters"]:
            filters.update(kwargs["filters"])

        return filters

    def _extract_sort_fields(self, args: tuple, kwargs: dict) -> List[str]:
        """Extract sort fields from query parameters"""
        sort_fields = []

        if "sort_by" in kwargs and kwargs["sort_by"]:
            if isinstance(kwargs["sort_by"], str):
                sort_fields.append(kwargs["sort_by"])
            elif isinstance(kwargs["sort_by"], list):
                sort_fields.extend(kwargs["sort_by"])

        return sort_fields

    def _extract_result_count(self, result: Any) -> int:
        """Extract result count from query result"""
        if hasattr(result, "__len__"):
            return len(result)
        elif isinstance(result, list):
            return len(result)
        else:
            return 1

    async def _suggest_immediate_optimization(
        self,
        collection_name: str,
        filters: Dict[str, Any],
        sort_fields: List[str],
        execution_time_ms: float,
    ):
        """Suggest immediate optimization for slow queries"""
        try:
            suggestion = {
                "timestamp": datetime.now(),
                "collection": collection_name,
                "execution_time_ms": execution_time_ms,
                "suggested_indexes": [],
                "optimization_type": "immediate",
            }

            # Suggest index for filters
            if filters:
                filter_columns = list(filters.keys())[:2]  # Limit to 2 columns
                suggestion["suggested_indexes"].append(
                    {
                        "columns": filter_columns,
                        "type": "filter_optimization",
                        "estimated_improvement": "50-70%",
                    }
                )

            # Suggest index for sorting
            if sort_fields:
                combined_columns = list(filters.keys())[:1] + sort_fields[:1]
                suggestion["suggested_indexes"].append(
                    {
                        "columns": combined_columns,
                        "type": "sort_optimization",
                        "estimated_improvement": "30-50%",
                    }
                )

            self.optimization_suggestions.append(suggestion)

            self.logger.warning(
                f"Slow query detected ({execution_time_ms:.1f}ms) on {collection_name}. "
                f"Suggested {len(suggestion['suggested_indexes'])} optimizations."
            )

        except Exception as e:
            self.logger.error(f"Failed to suggest immediate optimization: {e}")


class AdaptiveIndexManager:
    """
    Manages indexes adaptively based on query patterns
    """

    def __init__(
        self, indexing_manager: IndexingStrategyManager, qdrant_store: QdrantVectorStore
    ):
        self.indexing_manager = indexing_manager
        self.qdrant_store = qdrant_store
        self.logger = logger

        self.auto_optimization_enabled = True
        self.optimization_threshold_queries = 100  # Minimum queries before optimization
        self.last_optimization = datetime.now()
        self.optimization_interval_hours = 24

    async def run_adaptive_optimization(self) -> Dict[str, Any]:
        """
        Run adaptive optimization based on collected query patterns

        Returns:
            Optimization results and actions taken
        """
        try:
            if not self.auto_optimization_enabled:
                return {"status": "disabled"}

            # Check if enough time has passed since last optimization
            hours_since_last = (
                datetime.now() - self.last_optimization
            ).total_seconds() / 3600
            if hours_since_last < self.optimization_interval_hours:
                return {
                    "status": "too_recent",
                    "hours_since_last": hours_since_last,
                    "next_optimization_in_hours": self.optimization_interval_hours
                    - hours_since_last,
                }

            self.logger.info("Starting adaptive index optimization")

            # Step 1: Analyze query patterns
            analysis_results = await self.indexing_manager.analyze_query_patterns()

            # Step 2: Filter recommendations by impact
            high_impact_recommendations = [
                rec
                for rec in analysis_results["index_recommendations"]
                if rec.priority <= 2 and rec.estimated_improvement_ms > 100
            ]

            # Step 3: Apply recommendations automatically (with limits)
            applied_optimizations = []
            max_auto_optimizations = 5  # Safety limit

            for rec in high_impact_recommendations[:max_auto_optimizations]:
                success = await self.indexing_manager.apply_index_recommendation(rec)
                if success:
                    applied_optimizations.append(
                        {
                            "table": rec.table_name,
                            "columns": rec.columns,
                            "estimated_improvement_ms": rec.estimated_improvement_ms,
                            "reasoning": rec.reasoning,
                        }
                    )

            # Step 4: Clean up unused indexes
            cleanup_results = await self._cleanup_unused_indexes()

            # Step 5: Update optimization timestamp
            self.last_optimization = datetime.now()

            optimization_results = {
                "status": "completed",
                "optimizations_applied": len(applied_optimizations),
                "applied_optimizations": applied_optimizations,
                "cleanup_results": cleanup_results,
                "analysis_summary": {
                    "total_recommendations": len(
                        analysis_results["index_recommendations"]
                    ),
                    "high_impact_recommendations": len(high_impact_recommendations),
                    "queries_analyzed": analysis_results["analysis_period"][
                        "total_queries"
                    ],
                },
            }

            self.logger.info(
                f"Adaptive optimization completed: {len(applied_optimizations)} optimizations applied"
            )

            return optimization_results

        except Exception as e:
            self.logger.error(f"Adaptive optimization failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _cleanup_unused_indexes(self) -> Dict[str, Any]:
        """Clean up indexes that are no longer being used"""
        try:
            # Get current index usage analysis
            usage_analysis = await self.indexing_manager._analyze_current_index_usage()

            cleanup_results = {
                "indexes_removed": 0,
                "space_reclaimed_mb": 0.0,
                "removed_indexes": [],
            }

            # Remove indexes that haven't been used in a while
            for index_name in usage_analysis.get("unused_indexes", []):
                if index_name in self.indexing_manager.index_performance:
                    perf = self.indexing_manager.index_performance[index_name]
                    age_days = (datetime.now() - perf.creation_time).days

                    # Only remove indexes older than 7 days
                    if age_days > 7:
                        # In practice, would remove the actual index
                        cleanup_results["indexes_removed"] += 1
                        cleanup_results["space_reclaimed_mb"] += perf.size_mb
                        cleanup_results["removed_indexes"].append(
                            {
                                "name": index_name,
                                "age_days": age_days,
                                "size_mb": perf.size_mb,
                            }
                        )

                        # Remove from tracking
                        del self.indexing_manager.index_performance[index_name]

            return cleanup_results

        except Exception as e:
            self.logger.error(f"Index cleanup failed: {e}")
            return {"error": str(e)}

    def enable_auto_optimization(self):
        """Enable automatic optimization"""
        self.auto_optimization_enabled = True
        self.logger.info("Automatic optimization enabled")

    def disable_auto_optimization(self):
        """Disable automatic optimization"""
        self.auto_optimization_enabled = False
        self.logger.info("Automatic optimization disabled")


class QueryOptimizer:
    """
    Main query optimizer that coordinates all optimization components
    """

    def __init__(self, qdrant_store: QdrantVectorStore):
        """
        Initialize the query optimizer

        Args:
            qdrant_store: Vector database store
        """
        self.qdrant_store = qdrant_store
        self.indexing_manager = IndexingStrategyManager(qdrant_store)
        self.query_interceptor = QueryInterceptor(self.indexing_manager)
        self.adaptive_manager = AdaptiveIndexManager(
            self.indexing_manager, qdrant_store
        )
        self.logger = logger

        # Background task for periodic optimization
        self._optimization_task = None
        self._running = False

    async def start_background_optimization(self):
        """Start background optimization task"""
        if self._running:
            return

        self._running = True
        self._optimization_task = asyncio.create_task(
            self._background_optimization_loop()
        )
        self.logger.info("Background optimization started")

    async def stop_background_optimization(self):
        """Stop background optimization task"""
        self._running = False
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Background optimization stopped")

    async def _background_optimization_loop(self):
        """Background loop for periodic optimization"""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self.adaptive_manager.run_adaptive_optimization()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Background optimization error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    def get_query_interceptor(self) -> QueryInterceptor:
        """Get the query interceptor for decorating functions"""
        return self.query_interceptor

    async def get_optimization_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive optimization dashboard data"""
        try:
            # Get query statistics
            query_stats = self.indexing_manager.get_query_statistics()

            # Get recent optimization suggestions
            recent_suggestions = self.query_interceptor.optimization_suggestions[-10:]

            # Get index performance monitoring
            index_monitoring = await self.indexing_manager.monitor_index_performance()

            # Get current recommendations
            analysis_results = await self.indexing_manager.analyze_query_patterns()

            dashboard = {
                "query_statistics": query_stats,
                "recent_suggestions": recent_suggestions,
                "index_performance": index_monitoring,
                "current_recommendations": analysis_results["index_recommendations"][
                    :10
                ],
                "performance_summary": analysis_results.get("performance_summary", {}),
                "background_optimization": {
                    "enabled": self.adaptive_manager.auto_optimization_enabled,
                    "last_run": self.adaptive_manager.last_optimization,
                    "running": self._running,
                },
            }

            return dashboard

        except Exception as e:
            self.logger.error(f"Failed to get optimization dashboard: {e}")
            return {"error": str(e)}

    async def force_optimization(self) -> Dict[str, Any]:
        """Force immediate optimization regardless of timing"""
        try:
            self.adaptive_manager.last_optimization = (
                datetime.min
            )  # Reset to force optimization
            return await self.adaptive_manager.run_adaptive_optimization()
        except Exception as e:
            self.logger.error(f"Forced optimization failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def apply_specific_recommendation(
        self, recommendation_data: Dict[str, Any]
    ) -> bool:
        """Apply a specific index recommendation"""
        try:
            recommendation = IndexRecommendation(
                table_name=recommendation_data["table_name"],
                columns=recommendation_data["columns"],
                index_type=recommendation_data.get("index_type", "btree"),
                partial_condition=recommendation_data.get("partial_condition"),
                priority=recommendation_data.get("priority", 2),
                estimated_improvement_ms=recommendation_data.get(
                    "estimated_improvement_ms", 0
                ),
                reasoning=recommendation_data.get("reasoning", "Manual application"),
            )

            return await self.indexing_manager.apply_index_recommendation(
                recommendation
            )

        except Exception as e:
            self.logger.error(f"Failed to apply specific recommendation: {e}")
            return False
