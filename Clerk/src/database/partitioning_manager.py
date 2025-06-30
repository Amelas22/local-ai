"""
Database Partitioning Manager for Scalable Document Storage

This module provides intelligent partitioning strategies for the normalized database
schema to support large-scale document management. It implements multiple partitioning
strategies to optimize query performance and manage storage efficiently.

Key Features:
1. Time-based partitioning for temporal queries
2. Size-based partitioning for storage optimization
3. Access-pattern partitioning for hot/warm/cold data
4. Automatic partition management and maintenance
5. Cross-partition query optimization
6. Partition pruning for improved performance
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import math

from ..models.normalized_document_models import DocumentCore, ChunkMetadata
from ..vector_storage.qdrant_store import QdrantVectorStore
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class PartitionStrategy(str, Enum):
    """Partitioning strategies"""
    TIME_BASED = "time_based"
    SIZE_BASED = "size_based"
    ACCESS_PATTERN = "access_pattern"
    HASH_BASED = "hash_based"
    CASE_BASED = "case_based"
    HYBRID = "hybrid"


class DataTemperature(str, Enum):
    """Data access temperature for tiered storage"""
    HOT = "hot"      # Frequently accessed (last 30 days)
    WARM = "warm"    # Moderately accessed (30-180 days)
    COLD = "cold"    # Rarely accessed (180+ days)
    FROZEN = "frozen" # Archive storage (1+ years)


@dataclass
class PartitionConfig:
    """Configuration for a partition"""
    partition_id: str
    collection_name: str
    strategy: PartitionStrategy
    criteria: Dict[str, Any]
    max_size_mb: Optional[int] = None
    max_documents: Optional[int] = None
    temperature: DataTemperature = DataTemperature.HOT
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None
    document_count: int = 0
    size_mb: float = 0.0
    
    @property
    def is_full(self) -> bool:
        """Check if partition is full based on criteria"""
        if self.max_documents and self.document_count >= self.max_documents:
            return True
        if self.max_size_mb and self.size_mb >= self.max_size_mb:
            return True
        return False
    
    @property
    def partition_name(self) -> str:
        """Generate partition name"""
        return f"{self.collection_name}_{self.partition_id}"


@dataclass
class PartitionPlan:
    """Plan for partitioning a collection"""
    collection_name: str
    strategy: PartitionStrategy
    estimated_partitions: int
    partition_size_mb: float
    time_range_days: Optional[int] = None
    access_pattern_threshold: Optional[float] = None
    benefits: List[str] = field(default_factory=list)
    estimated_performance_improvement: float = 0.0


@dataclass
class PartitionMaintenance:
    """Maintenance task for partitions"""
    task_id: str
    partition_id: str
    task_type: str  # merge, split, archive, delete
    priority: int  # 1=high, 2=medium, 3=low
    estimated_duration_minutes: int
    benefits: List[str] = field(default_factory=list)
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PartitioningManager:
    """
    Manages database partitioning strategies for optimal performance
    """
    
    def __init__(self, qdrant_store: QdrantVectorStore):
        """
        Initialize the partitioning manager
        
        Args:
            qdrant_store: Vector database store
        """
        self.qdrant_store = qdrant_store
        self.logger = logger
        
        # Partition tracking
        self.partitions: Dict[str, PartitionConfig] = {}
        self.partition_mappings: Dict[str, List[str]] = {}  # collection -> partition_ids
        self.maintenance_tasks: List[PartitionMaintenance] = []
        
        # Configuration
        self.default_partition_size_mb = 1000  # 1GB per partition
        self.default_partition_documents = 100000  # 100k documents per partition
        self.time_partition_interval_days = 30  # Monthly time partitions
        self.hot_data_threshold_days = 30
        self.warm_data_threshold_days = 180
        self.cold_data_threshold_days = 365
        
        # Performance thresholds
        self.slow_query_threshold_ms = 1000
        self.partition_split_threshold = 0.8  # Split when 80% full
        self.partition_merge_threshold = 0.3  # Merge when < 30% full
    
    async def analyze_partitioning_needs(self, 
                                       collection_name: str) -> PartitionPlan:
        """
        Analyze a collection to determine optimal partitioning strategy
        
        Args:
            collection_name: Collection to analyze
            
        Returns:
            Partitioning plan with recommendations
        """
        try:
            # Step 1: Get collection statistics
            stats = await self._get_collection_statistics(collection_name)
            
            # Step 2: Analyze access patterns
            access_patterns = await self._analyze_access_patterns(collection_name)
            
            # Step 3: Determine optimal strategy
            strategy = self._determine_optimal_strategy(stats, access_patterns)
            
            # Step 4: Create partitioning plan
            plan = await self._create_partitioning_plan(
                collection_name, strategy, stats, access_patterns
            )
            
            self.logger.info(
                f"Partitioning analysis for {collection_name}: "
                f"{strategy} strategy with {plan.estimated_partitions} partitions"
            )
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Partitioning analysis failed for {collection_name}: {e}")
            raise
    
    async def _get_collection_statistics(self, collection_name: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a collection"""
        try:
            # Get basic collection info
            collection_info = await self.qdrant_store.get_collection_info(collection_name)
            
            # Estimate storage size (simplified)
            estimated_size_mb = collection_info.get('points_count', 0) * 0.01  # Rough estimate
            
            # Get temporal distribution if possible
            temporal_distribution = await self._analyze_temporal_distribution(collection_name)
            
            stats = {
                'document_count': collection_info.get('points_count', 0),
                'estimated_size_mb': estimated_size_mb,
                'temporal_distribution': temporal_distribution,
                'avg_document_size_kb': estimated_size_mb * 1024 / max(1, collection_info.get('points_count', 1)),
                'creation_date_range': temporal_distribution.get('date_range', {}),
                'growth_rate_documents_per_day': temporal_distribution.get('growth_rate', 0)
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get collection statistics: {e}")
            return {}
    
    async def _analyze_temporal_distribution(self, collection_name: str) -> Dict[str, Any]:
        """Analyze temporal distribution of documents"""
        try:
            # Sample some documents to analyze temporal patterns
            sample_results = self.qdrant_store.scroll_points(
                collection_name=collection_name,
                limit=1000
            )
            
            if not sample_results or not sample_results[0]:
                return {}
            
            dates = []
            for point in sample_results[0]:
                # Extract date fields from payload
                payload = point.payload
                for field in ['created_at', 'first_ingested_at', 'document_date']:
                    if field in payload and payload[field]:
                        try:
                            if isinstance(payload[field], str):
                                date = datetime.fromisoformat(payload[field])
                            else:
                                date = payload[field]
                            dates.append(date)
                            break
                        except:
                            continue
            
            if not dates:
                return {}
            
            dates.sort()
            date_range = {
                'earliest': dates[0],
                'latest': dates[-1],
                'span_days': (dates[-1] - dates[0]).days
            }
            
            # Calculate growth rate
            growth_rate = len(dates) / max(1, date_range['span_days'])
            
            return {
                'date_range': date_range,
                'growth_rate': growth_rate,
                'sample_size': len(dates)
            }
            
        except Exception as e:
            self.logger.error(f"Temporal distribution analysis failed: {e}")
            return {}
    
    async def _analyze_access_patterns(self, collection_name: str) -> Dict[str, Any]:
        """Analyze access patterns for the collection"""
        try:
            # This would integrate with the query optimizer to get access patterns
            # For now, provide estimated patterns
            
            access_patterns = {
                'hot_data_percentage': 0.2,  # 20% of data is frequently accessed
                'warm_data_percentage': 0.3,  # 30% is moderately accessed
                'cold_data_percentage': 0.5,  # 50% is rarely accessed
                'access_temporal_bias': 0.8,  # 80% bias toward recent data
                'query_selectivity': 0.1,  # Average query returns 10% of results
                'common_filters': ['case_id', 'document_type', 'document_date'],
                'frequent_sorts': ['document_date', 'created_at']
            }
            
            return access_patterns
            
        except Exception as e:
            self.logger.error(f"Access pattern analysis failed: {e}")
            return {}
    
    def _determine_optimal_strategy(self, 
                                  stats: Dict[str, Any], 
                                  access_patterns: Dict[str, Any]) -> PartitionStrategy:
        """Determine the optimal partitioning strategy"""
        document_count = stats.get('document_count', 0)
        size_mb = stats.get('estimated_size_mb', 0)
        temporal_span_days = stats.get('temporal_distribution', {}).get('date_range', {}).get('span_days', 0)
        
        # Decision logic
        if document_count < 50000 and size_mb < 500:
            return PartitionStrategy.CASE_BASED  # Small collections by case
        
        elif temporal_span_days > 365 and access_patterns.get('access_temporal_bias', 0) > 0.7:
            return PartitionStrategy.TIME_BASED  # Time-based for temporal bias
        
        elif size_mb > 5000:  # Large collections
            return PartitionStrategy.HYBRID  # Combine time and size
        
        elif access_patterns.get('hot_data_percentage', 0) < 0.3:
            return PartitionStrategy.ACCESS_PATTERN  # Access pattern for cold data
        
        else:
            return PartitionStrategy.SIZE_BASED  # Default size-based
    
    async def _create_partitioning_plan(self,
                                      collection_name: str,
                                      strategy: PartitionStrategy,
                                      stats: Dict[str, Any],
                                      access_patterns: Dict[str, Any]) -> PartitionPlan:
        """Create a detailed partitioning plan"""
        document_count = stats.get('document_count', 0)
        size_mb = stats.get('estimated_size_mb', 0)
        
        if strategy == PartitionStrategy.TIME_BASED:
            # Monthly partitions
            temporal_span_days = stats.get('temporal_distribution', {}).get('date_range', {}).get('span_days', 365)
            estimated_partitions = max(1, temporal_span_days // self.time_partition_interval_days)
            partition_size_mb = size_mb / estimated_partitions
            benefits = [
                "Efficient temporal queries",
                "Easy archival of old data",
                "Improved query pruning"
            ]
            
        elif strategy == PartitionStrategy.SIZE_BASED:
            # Size-based partitions
            estimated_partitions = max(1, math.ceil(size_mb / self.default_partition_size_mb))
            partition_size_mb = self.default_partition_size_mb
            benefits = [
                "Controlled partition sizes",
                "Predictable performance",
                "Easy maintenance"
            ]
            
        elif strategy == PartitionStrategy.ACCESS_PATTERN:
            # Hot/warm/cold partitions
            estimated_partitions = 3  # Hot, warm, cold
            partition_size_mb = size_mb / 3
            benefits = [
                "Optimized for access patterns",
                "Tiered storage capabilities",
                "Reduced I/O for cold data"
            ]
            
        elif strategy == PartitionStrategy.CASE_BASED:
            # One partition per major case grouping
            estimated_partitions = max(1, document_count // 10000)  # 10k docs per partition
            partition_size_mb = size_mb / estimated_partitions
            benefits = [
                "Perfect case isolation",
                "Easy case-specific operations",
                "Simplified access control"
            ]
            
        elif strategy == PartitionStrategy.HYBRID:
            # Combine time and size
            time_partitions = max(1, stats.get('temporal_distribution', {}).get('date_range', {}).get('span_days', 365) // 90)  # Quarterly
            size_partitions = max(1, math.ceil(size_mb / (self.default_partition_size_mb * 2)))  # Larger partitions
            estimated_partitions = min(time_partitions, size_partitions)
            partition_size_mb = size_mb / estimated_partitions
            benefits = [
                "Balanced time and size optimization",
                "Flexible query patterns",
                "Scalable architecture"
            ]
            
        else:
            # Default fallback
            estimated_partitions = max(1, math.ceil(document_count / self.default_partition_documents))
            partition_size_mb = size_mb / estimated_partitions
            benefits = ["Balanced partitioning"]
        
        # Estimate performance improvement
        improvement = min(50.0, estimated_partitions * 5.0)  # Up to 50% improvement
        
        return PartitionPlan(
            collection_name=collection_name,
            strategy=strategy,
            estimated_partitions=estimated_partitions,
            partition_size_mb=partition_size_mb,
            benefits=benefits,
            estimated_performance_improvement=improvement
        )
    
    async def implement_partitioning_plan(self, plan: PartitionPlan) -> Dict[str, Any]:
        """
        Implement a partitioning plan
        
        Args:
            plan: Partitioning plan to implement
            
        Returns:
            Implementation results
        """
        try:
            self.logger.info(f"Implementing {plan.strategy} partitioning for {plan.collection_name}")
            
            # Step 1: Create partition configurations
            partition_configs = await self._create_partition_configs(plan)
            
            # Step 2: Create physical partitions
            created_partitions = []
            for config in partition_configs:
                success = await self._create_physical_partition(config)
                if success:
                    created_partitions.append(config.partition_id)
                    self.partitions[config.partition_id] = config
            
            # Step 3: Migrate data to partitions
            migration_results = await self._migrate_data_to_partitions(
                plan.collection_name, partition_configs
            )
            
            # Step 4: Update partition mappings
            if plan.collection_name not in self.partition_mappings:
                self.partition_mappings[plan.collection_name] = []
            self.partition_mappings[plan.collection_name].extend(created_partitions)
            
            # Step 5: Create indexes on partitions
            await self._create_partition_indexes(partition_configs)
            
            implementation_results = {
                'status': 'completed',
                'partitions_created': len(created_partitions),
                'partition_ids': created_partitions,
                'migration_results': migration_results,
                'strategy_applied': plan.strategy.value,
                'estimated_improvement': plan.estimated_performance_improvement
            }
            
            self.logger.info(
                f"Partitioning implementation completed: {len(created_partitions)} partitions created"
            )
            
            return implementation_results
            
        except Exception as e:
            self.logger.error(f"Partitioning implementation failed: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    async def _create_partition_configs(self, plan: PartitionPlan) -> List[PartitionConfig]:
        """Create partition configurations based on plan"""
        configs = []
        
        if plan.strategy == PartitionStrategy.TIME_BASED:
            # Create monthly partitions
            start_date = datetime.now() - timedelta(days=365)  # Start from 1 year ago
            for i in range(plan.estimated_partitions):
                partition_date = start_date + timedelta(days=i * self.time_partition_interval_days)
                partition_id = f"time_{partition_date.strftime('%Y%m')}"
                
                config = PartitionConfig(
                    partition_id=partition_id,
                    collection_name=plan.collection_name,
                    strategy=plan.strategy,
                    criteria={
                        'start_date': partition_date,
                        'end_date': partition_date + timedelta(days=self.time_partition_interval_days)
                    },
                    max_size_mb=int(plan.partition_size_mb * 1.2),  # 20% buffer
                    temperature=self._calculate_data_temperature(partition_date)
                )
                configs.append(config)
        
        elif plan.strategy == PartitionStrategy.SIZE_BASED:
            # Create size-based partitions
            for i in range(plan.estimated_partitions):
                partition_id = f"size_{i:03d}"
                
                config = PartitionConfig(
                    partition_id=partition_id,
                    collection_name=plan.collection_name,
                    strategy=plan.strategy,
                    criteria={'partition_index': i},
                    max_size_mb=int(plan.partition_size_mb),
                    max_documents=self.default_partition_documents
                )
                configs.append(config)
        
        elif plan.strategy == PartitionStrategy.ACCESS_PATTERN:
            # Create hot/warm/cold partitions
            temperatures = [DataTemperature.HOT, DataTemperature.WARM, DataTemperature.COLD]
            
            for i, temp in enumerate(temperatures):
                partition_id = f"access_{temp.value}"
                
                config = PartitionConfig(
                    partition_id=partition_id,
                    collection_name=plan.collection_name,
                    strategy=plan.strategy,
                    criteria={'temperature': temp.value},
                    max_size_mb=int(plan.partition_size_mb),
                    temperature=temp
                )
                configs.append(config)
        
        elif plan.strategy == PartitionStrategy.CASE_BASED:
            # Create case-based partitions (would need case analysis)
            for i in range(plan.estimated_partitions):
                partition_id = f"case_{i:03d}"
                
                config = PartitionConfig(
                    partition_id=partition_id,
                    collection_name=plan.collection_name,
                    strategy=plan.strategy,
                    criteria={'case_group': i},
                    max_documents=10000  # 10k documents per case group
                )
                configs.append(config)
        
        else:  # HYBRID or other strategies
            # Create hybrid partitions
            for i in range(plan.estimated_partitions):
                partition_id = f"hybrid_{i:03d}"
                
                config = PartitionConfig(
                    partition_id=partition_id,
                    collection_name=plan.collection_name,
                    strategy=plan.strategy,
                    criteria={'partition_index': i},
                    max_size_mb=int(plan.partition_size_mb)
                )
                configs.append(config)
        
        return configs
    
    def _calculate_data_temperature(self, date: datetime) -> DataTemperature:
        """Calculate data temperature based on date"""
        age_days = (datetime.now() - date).days
        
        if age_days <= self.hot_data_threshold_days:
            return DataTemperature.HOT
        elif age_days <= self.warm_data_threshold_days:
            return DataTemperature.WARM
        elif age_days <= self.cold_data_threshold_days:
            return DataTemperature.COLD
        else:
            return DataTemperature.FROZEN
    
    async def _create_physical_partition(self, config: PartitionConfig) -> bool:
        """Create a physical partition in the database"""
        try:
            partition_name = config.partition_name
            
            # Create the Qdrant collection for this partition
            self.qdrant_store.create_collection_if_not_exists(
                collection_name=partition_name,
                vector_size=1536,  # Standard embedding size
                distance='Cosine'
            )
            
            self.logger.info(f"Created physical partition: {partition_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create physical partition {config.partition_id}: {e}")
            return False
    
    async def _migrate_data_to_partitions(self,
                                        collection_name: str,
                                        partition_configs: List[PartitionConfig]) -> Dict[str, Any]:
        """Migrate data from main collection to partitions"""
        try:
            migration_results = {
                'documents_migrated': 0,
                'partitions_populated': 0,
                'errors': []
            }
            
            # Get all documents from source collection
            all_points = []
            scroll_result = self.qdrant_store.scroll_points(
                collection_name=collection_name,
                limit=1000
            )
            
            while scroll_result and scroll_result[0]:
                all_points.extend(scroll_result[0])
                if scroll_result[1]:  # Has next offset
                    scroll_result = self.qdrant_store.scroll_points(
                        collection_name=collection_name,
                        limit=1000,
                        offset=scroll_result[1]
                    )
                else:
                    break
            
            # Distribute points to partitions based on strategy
            partition_assignments = self._assign_points_to_partitions(
                all_points, partition_configs
            )
            
            # Migrate points to their assigned partitions
            for config in partition_configs:
                points_for_partition = partition_assignments.get(config.partition_id, [])
                if points_for_partition:
                    try:
                        self.qdrant_store.upsert_points(
                            collection_name=config.partition_name,
                            points=points_for_partition
                        )
                        
                        # Update partition statistics
                        config.document_count = len(points_for_partition)
                        config.size_mb = len(points_for_partition) * 0.01  # Rough estimate
                        
                        migration_results['documents_migrated'] += len(points_for_partition)
                        migration_results['partitions_populated'] += 1
                        
                    except Exception as e:
                        error_msg = f"Failed to migrate to partition {config.partition_id}: {e}"
                        migration_results['errors'].append(error_msg)
                        self.logger.error(error_msg)
            
            return migration_results
            
        except Exception as e:
            self.logger.error(f"Data migration failed: {e}")
            return {'error': str(e)}
    
    def _assign_points_to_partitions(self,
                                   points: List[Any],
                                   partition_configs: List[PartitionConfig]) -> Dict[str, List[Any]]:
        """Assign points to partitions based on partitioning strategy"""
        assignments = {config.partition_id: [] for config in partition_configs}
        
        for point in points:
            assigned_partition = self._determine_point_partition(point, partition_configs)
            if assigned_partition:
                assignments[assigned_partition].append(point)
        
        return assignments
    
    def _determine_point_partition(self, point: Any, partition_configs: List[PartitionConfig]) -> Optional[str]:
        """Determine which partition a point should be assigned to"""
        payload = point.payload
        
        for config in partition_configs:
            if self._point_matches_partition_criteria(payload, config):
                return config.partition_id
        
        # Default to first partition if no match
        return partition_configs[0].partition_id if partition_configs else None
    
    def _point_matches_partition_criteria(self, payload: Dict[str, Any], config: PartitionConfig) -> bool:
        """Check if a point matches partition criteria"""
        criteria = config.criteria
        
        if config.strategy == PartitionStrategy.TIME_BASED:
            # Check date ranges
            point_date = self._extract_date_from_payload(payload)
            if point_date:
                return criteria['start_date'] <= point_date < criteria['end_date']
        
        elif config.strategy == PartitionStrategy.ACCESS_PATTERN:
            # Check access temperature
            point_temp = self._calculate_point_temperature(payload)
            return point_temp.value == criteria['temperature']
        
        elif config.strategy == PartitionStrategy.CASE_BASED:
            # Check case grouping (simplified)
            case_id = payload.get('case_id', '')
            case_hash = hashlib.md5(case_id.encode()).hexdigest()
            case_group = int(case_hash[:8], 16) % len(criteria)  # Simple hash distribution
            return case_group == criteria['case_group']
        
        # Default: round-robin assignment for size-based or other strategies
        return True
    
    def _extract_date_from_payload(self, payload: Dict[str, Any]) -> Optional[datetime]:
        """Extract date from payload for time-based partitioning"""
        for field in ['created_at', 'first_ingested_at', 'document_date']:
            if field in payload and payload[field]:
                try:
                    if isinstance(payload[field], str):
                        return datetime.fromisoformat(payload[field])
                    else:
                        return payload[field]
                except:
                    continue
        return None
    
    def _calculate_point_temperature(self, payload: Dict[str, Any]) -> DataTemperature:
        """Calculate temperature for a data point"""
        last_accessed = payload.get('last_accessed')
        if last_accessed:
            try:
                if isinstance(last_accessed, str):
                    access_date = datetime.fromisoformat(last_accessed)
                else:
                    access_date = last_accessed
                
                return self._calculate_data_temperature(access_date)
            except:
                pass
        
        # Fallback to creation date
        creation_date = self._extract_date_from_payload(payload)
        if creation_date:
            return self._calculate_data_temperature(creation_date)
        
        return DataTemperature.COLD  # Default
    
    async def _create_partition_indexes(self, partition_configs: List[PartitionConfig]):
        """Create indexes on partitions"""
        try:
            for config in partition_configs:
                # Create standard indexes based on collection type
                if 'document' in config.collection_name:
                    index_fields = ['document_id', 'case_id', 'document_type']
                elif 'chunk' in config.collection_name:
                    index_fields = ['document_id', 'chunk_index']
                else:
                    index_fields = ['id']
                
                for field in index_fields:
                    try:
                        self.qdrant_store.create_payload_index(
                            collection_name=config.partition_name,
                            field_name=field
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to create index {field} on {config.partition_name}: {e}")
                
                self.logger.info(f"Created indexes for partition: {config.partition_name}")
                
        except Exception as e:
            self.logger.error(f"Partition index creation failed: {e}")
    
    async def query_across_partitions(self,
                                    collection_name: str,
                                    query_vector: List[float],
                                    filters: Optional[Dict[str, Any]] = None,
                                    limit: int = 10) -> List[Any]:
        """
        Query across all partitions of a collection
        
        Args:
            collection_name: Base collection name
            query_vector: Query vector
            filters: Query filters
            limit: Maximum results
            
        Returns:
            Combined results from all partitions
        """
        try:
            partition_ids = self.partition_mappings.get(collection_name, [])
            if not partition_ids:
                # No partitions, query original collection
                return self.qdrant_store.search_points(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    query_filter=filters,
                    limit=limit
                )
            
            # Query all partitions
            all_results = []
            for partition_id in partition_ids:
                config = self.partitions[partition_id]
                
                # Partition pruning: skip partitions that don't match filters
                if self._can_prune_partition(config, filters):
                    continue
                
                try:
                    results = self.qdrant_store.search_points(
                        collection_name=config.partition_name,
                        query_vector=query_vector,
                        query_filter=filters,
                        limit=limit * 2  # Get more results per partition
                    )
                    all_results.extend(results)
                    
                except Exception as e:
                    self.logger.warning(f"Query failed on partition {partition_id}: {e}")
            
            # Sort and limit results
            all_results.sort(key=lambda x: x.score, reverse=True)
            return all_results[:limit]
            
        except Exception as e:
            self.logger.error(f"Cross-partition query failed: {e}")
            return []
    
    def _can_prune_partition(self, config: PartitionConfig, filters: Optional[Dict[str, Any]]) -> bool:
        """Determine if a partition can be pruned from the query"""
        if not filters:
            return False
        
        # Time-based pruning
        if config.strategy == PartitionStrategy.TIME_BASED and 'document_date' in filters:
            filter_date = filters['document_date']
            if isinstance(filter_date, dict):
                # Range query
                if 'gte' in filter_date and filter_date['gte'] > config.criteria['end_date']:
                    return True
                if 'lte' in filter_date and filter_date['lte'] < config.criteria['start_date']:
                    return True
            elif isinstance(filter_date, datetime):
                # Exact date query
                if not (config.criteria['start_date'] <= filter_date < config.criteria['end_date']):
                    return True
        
        # Case-based pruning
        if config.strategy == PartitionStrategy.CASE_BASED and 'case_id' in filters:
            case_id = filters['case_id']
            expected_partition = self._determine_case_partition(case_id)
            if expected_partition != config.partition_id:
                return True
        
        return False
    
    def _determine_case_partition(self, case_id: str) -> str:
        """Determine which partition a case should be in"""
        case_hash = hashlib.md5(case_id.encode()).hexdigest()
        # This would need to match the logic used during partitioning
        return f"case_{int(case_hash[:8], 16) % 10:03d}"
    
    async def get_partitioning_status(self) -> Dict[str, Any]:
        """Get comprehensive partitioning status"""
        try:
            status = {
                'total_partitions': len(self.partitions),
                'partitioned_collections': len(self.partition_mappings),
                'partition_strategies': {},
                'storage_distribution': {},
                'maintenance_tasks': len(self.maintenance_tasks),
                'partition_details': []
            }
            
            # Analyze strategies
            for config in self.partitions.values():
                strategy = config.strategy.value
                status['partition_strategies'][strategy] = status['partition_strategies'].get(strategy, 0) + 1
            
            # Analyze storage distribution
            total_size = 0
            for config in self.partitions.values():
                total_size += config.size_mb
                temp = config.temperature.value
                status['storage_distribution'][temp] = status['storage_distribution'].get(temp, 0) + config.size_mb
            
            # Partition details
            for config in self.partitions.values():
                status['partition_details'].append({
                    'partition_id': config.partition_id,
                    'collection': config.collection_name,
                    'strategy': config.strategy.value,
                    'document_count': config.document_count,
                    'size_mb': config.size_mb,
                    'temperature': config.temperature.value,
                    'utilization': config.size_mb / config.max_size_mb if config.max_size_mb else 0,
                    'is_full': config.is_full
                })
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get partitioning status: {e}")
            return {'error': str(e)}