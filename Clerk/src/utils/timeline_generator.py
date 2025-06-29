"""
Timeline Generator for Case Facts
Creates chronological narratives from extracted facts with case isolation
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from src.models.fact_models import CaseFact, FactTimeline, DateReference
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.ai_agents.fact_extractor import FactExtractor

logger = logging.getLogger("clerk_api")


@dataclass
class TimelineEvent:
    """Represents a single event in the timeline"""
    date: datetime
    fact: CaseFact
    description: str
    significance: str  # Why this event matters
    related_events: List[str] = None  # IDs of related events


class TimelineGenerator:
    """
    Generates chronological timelines from case facts.
    Ensures all operations are case-isolated.
    """
    
    def __init__(self, case_name: str):
        """Initialize timeline generator for specific case"""
        self.case_name = case_name
        self.vector_store = QdrantVectorStore()
        self.facts_collection = f"{case_name}_facts"
        self.timeline_collection = f"{case_name}_timeline"
        
        logger.info(f"TimelineGenerator initialized for case: {case_name}")
    
    async def generate_timeline(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_uncertain: bool = True
    ) -> FactTimeline:
        """Generate a timeline from all facts in the case"""
        logger.info(f"Generating timeline for case: {self.case_name}")
        
        # Retrieve all facts with dates
        facts_with_dates = await self._get_facts_with_dates(start_date, end_date)
        
        # Create timeline
        timeline = FactTimeline(
            case_name=self.case_name,
            timeline_events=[],
            date_ranges=[],
            key_dates={}
        )
        
        # Process facts
        for fact in facts_with_dates:
            if fact.date_references:
                for date_ref in fact.date_references:
                    if date_ref.start_date:
                        # Skip uncertain dates if not included
                        if not include_uncertain and date_ref.is_approximate:
                            continue
                            
                        timeline.timeline_events.append((date_ref.start_date, fact))
                        
                        # Track date ranges
                        if date_ref.is_range and date_ref.end_date:
                            timeline.date_ranges.append(
                                (date_ref.start_date, date_ref.end_date, fact.content[:100])
                            )
        
        # Sort events chronologically
        timeline.timeline_events.sort(key=lambda x: x[0])
        
        # Identify key dates
        timeline.key_dates = self._identify_key_dates(timeline)
        
        # Store timeline
        await self._store_timeline(timeline)
        
        return timeline
    
    async def _get_facts_with_dates(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[CaseFact]:
        """Retrieve facts that have date references"""
        # Build filter
        must_conditions = [
            {"key": "case_name", "match": {"value": self.case_name}},
            {"key": "has_dates", "match": {"value": True}}
        ]
        
        if start_date and end_date:
            must_conditions.append({
                "key": "primary_date",
                "range": {
                    "gte": start_date.isoformat(),
                    "lte": end_date.isoformat()
                }
            })
        
        # Search for facts with dates
        results = self.vector_store.client.scroll(
            collection_name=self.facts_collection,
            scroll_filter={"must": must_conditions},
            limit=1000,  # Get all facts with dates
            with_payload=True,
            with_vectors=False
        )
        
        # Convert to fact objects (simplified - in production would deserialize full facts)
        facts = []
        for point in results[0]:
            # Here we would normally deserialize the full fact
            # For now, creating a minimal fact object
            fact = CaseFact(
                id=point.payload["fact_id"],
                case_name=self.case_name,
                content=point.payload.get("content", ""),
                category=point.payload["category"],
                source_document=point.payload["source_document"],
                page_references=[],
                extraction_timestamp=datetime.fromisoformat(point.payload["extraction_timestamp"]),
                confidence_score=point.payload["confidence_score"],
                date_references=[DateReference(
                    date_text="",
                    start_date=datetime.fromisoformat(point.payload["primary_date"])
                )] if "primary_date" in point.payload else []
            )
            facts.append(fact)
        
        return facts
    
    def _identify_key_dates(self, timeline: FactTimeline) -> Dict[str, datetime]:
        """Identify key dates in the timeline"""
        key_dates = {}
        
        if not timeline.timeline_events:
            return key_dates
        
        # First and last events
        key_dates["case_start"] = timeline.timeline_events[0][0]
        key_dates["case_end"] = timeline.timeline_events[-1][0]
        
        # Look for specific event types
        for date, fact in timeline.timeline_events:
            content_lower = fact.content.lower()
            
            # Incident date
            if any(word in content_lower for word in ["incident", "accident", "crash", "injury"]):
                if "incident_date" not in key_dates:
                    key_dates["incident_date"] = date
            
            # Filing date
            if any(word in content_lower for word in ["filed", "filing", "complaint"]):
                if "filing_date" not in key_dates:
                    key_dates["filing_date"] = date
            
            # Discovery dates
            if "deposition" in content_lower:
                depo_key = f"deposition_{date.strftime('%Y%m%d')}"
                key_dates[depo_key] = date
        
        return key_dates
    
    async def _store_timeline(self, timeline: FactTimeline):
        """Store timeline in case-specific collection"""
        # Create timeline entries for vector storage
        points = []
        
        for i, (date, fact) in enumerate(timeline.timeline_events):
            # Create a narrative description
            narrative = f"On {date.strftime('%B %d, %Y')}: {fact.content}"
            
            # Generate embedding for the narrative
            from src.vector_storage.embeddings import EmbeddingGenerator
            embedding_gen = EmbeddingGenerator()
            embedding, _ = await embedding_gen.generate_embedding_async(narrative)
            
            metadata = {
                "case_name": self.case_name,
                "event_date": date.isoformat(),
                "fact_id": fact.id,
                "event_index": i,
                "category": fact.category,
                "source_document": fact.source_document,
                "narrative": narrative
            }
            
            points.append({
                "id": f"{self.case_name}_timeline_{i}",
                "vector": embedding,
                "payload": metadata
            })
        
        # Store in timeline collection
        if points:
            self.vector_store.client.upsert(
                collection_name=self.timeline_collection,
                points=points
            )
            logger.info(f"Stored {len(points)} timeline events in {self.timeline_collection}")
    
    def generate_narrative_timeline(
        self,
        timeline: FactTimeline,
        format: str = "markdown"
    ) -> str:
        """Generate a human-readable timeline narrative"""
        if format == "markdown":
            return self._generate_markdown_timeline(timeline)
        elif format == "text":
            return self._generate_text_timeline(timeline)
        elif format == "json":
            return self._generate_json_timeline(timeline)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def _generate_markdown_timeline(self, timeline: FactTimeline) -> str:
        """Generate markdown-formatted timeline"""
        lines = [
            f"# Case Timeline: {self.case_name}",
            "",
            f"**Timeline Period**: {timeline.key_dates.get('case_start', 'Unknown')} to {timeline.key_dates.get('case_end', 'Unknown')}",
            ""
        ]
        
        # Key dates section
        if timeline.key_dates:
            lines.extend([
                "## Key Dates",
                ""
            ])
            for event_name, date in timeline.key_dates.items():
                formatted_name = event_name.replace('_', ' ').title()
                lines.append(f"- **{formatted_name}**: {date.strftime('%B %d, %Y')}")
            lines.append("")
        
        # Chronological events
        lines.extend([
            "## Chronological Events",
            ""
        ])
        
        current_year = None
        for date, fact in timeline.timeline_events:
            # Add year header if changed
            if date.year != current_year:
                current_year = date.year
                lines.extend([
                    f"### {current_year}",
                    ""
                ])
            
            # Add event
            lines.append(f"**{date.strftime('%B %d')}**: {fact.content}")
            
            # Add metadata
            metadata = []
            if fact.source_document:
                metadata.append(f"Source: {fact.source_document}")
            if fact.confidence_score < 0.8:
                metadata.append(f"Confidence: {fact.confidence_score:.0%}")
            
            if metadata:
                lines.append(f"  *{' | '.join(metadata)}*")
            
            lines.append("")
        
        # Date ranges section
        if timeline.date_ranges:
            lines.extend([
                "## Time Periods",
                ""
            ])
            for start, end, description in timeline.date_ranges:
                duration = (end - start).days
                lines.append(
                    f"- **{start.strftime('%B %d, %Y')} to {end.strftime('%B %d, %Y')}** "
                    f"({duration} days): {description}"
                )
        
        return "\n".join(lines)
    
    def _generate_text_timeline(self, timeline: FactTimeline) -> str:
        """Generate plain text timeline"""
        lines = [
            f"CASE TIMELINE: {self.case_name}",
            "=" * 50,
            ""
        ]
        
        for date, fact in timeline.timeline_events:
            lines.append(f"{date.strftime('%Y-%m-%d')}: {fact.content}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_json_timeline(self, timeline: FactTimeline) -> str:
        """Generate JSON timeline"""
        data = {
            "case_name": self.case_name,
            "timeline_period": {
                "start": timeline.key_dates.get("case_start", datetime.now()).isoformat(),
                "end": timeline.key_dates.get("case_end", datetime.now()).isoformat()
            },
            "key_dates": {
                name: date.isoformat() 
                for name, date in timeline.key_dates.items()
            },
            "events": [
                {
                    "date": date.isoformat(),
                    "fact_id": fact.id,
                    "content": fact.content,
                    "category": fact.category,
                    "source": fact.source_document,
                    "confidence": fact.confidence_score
                }
                for date, fact in timeline.timeline_events
            ],
            "date_ranges": [
                {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "description": desc,
                    "duration_days": (end - start).days
                }
                for start, end, desc in timeline.date_ranges
            ]
        }
        
        return json.dumps(data, indent=2)
    
    async def find_events_near_date(
        self,
        target_date: datetime,
        days_before: int = 30,
        days_after: int = 30
    ) -> List[Tuple[datetime, CaseFact]]:
        """Find events within a date range"""
        start_date = target_date - timedelta(days=days_before)
        end_date = target_date + timedelta(days=days_after)
        
        # Get facts within date range
        facts = await self._get_facts_with_dates(start_date, end_date)
        
        # Convert to timeline events
        events = []
        for fact in facts:
            if fact.date_references:
                for date_ref in fact.date_references:
                    if date_ref.start_date:
                        events.append((date_ref.start_date, fact))
        
        # Sort by date
        events.sort(key=lambda x: x[0])
        
        return events
    
    def calculate_timeline_statistics(self, timeline: FactTimeline) -> Dict[str, Any]:
        """Calculate statistics about the timeline"""
        if not timeline.timeline_events:
            return {
                "total_events": 0,
                "date_range_days": 0,
                "events_by_category": {},
                "events_by_month": {}
            }
        
        # Basic statistics
        first_date = timeline.timeline_events[0][0]
        last_date = timeline.timeline_events[-1][0]
        date_range_days = (last_date - first_date).days
        
        # Events by category
        events_by_category = {}
        for _, fact in timeline.timeline_events:
            category = fact.category
            events_by_category[category] = events_by_category.get(category, 0) + 1
        
        # Events by month
        events_by_month = {}
        for date, _ in timeline.timeline_events:
            month_key = date.strftime("%Y-%m")
            events_by_month[month_key] = events_by_month.get(month_key, 0) + 1
        
        return {
            "total_events": len(timeline.timeline_events),
            "date_range_days": date_range_days,
            "first_event": first_date.isoformat(),
            "last_event": last_date.isoformat(),
            "events_by_category": events_by_category,
            "events_by_month": events_by_month,
            "date_ranges": len(timeline.date_ranges),
            "key_dates_identified": len(timeline.key_dates)
        }