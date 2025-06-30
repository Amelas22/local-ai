"""
Enhanced Document Chunker for Normalized Database Schema

This module provides optimized chunking functionality that works with the normalized
database schema. It creates intelligent chunks with rich metadata and efficient
document linking for enhanced search and retrieval performance.

Key Features:
1. Semantic-aware chunking
2. Enhanced chunk metadata
3. Efficient document-chunk relationships
4. Vector embedding optimization
5. Context-aware chunk boundaries
6. Performance-optimized storage
"""

import hashlib
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models.normalized_document_models import ChunkMetadata, DocumentCore
from ..vector_storage.embeddings import EmbeddingGenerator
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ChunkType(str, Enum):
    """Types of document chunks for semantic processing"""
    PARAGRAPH = "paragraph"
    HEADER = "header"
    LIST_ITEM = "list_item"
    TABLE = "table"
    FOOTNOTE = "footnote"
    CAPTION = "caption"
    QUOTE = "quote"
    CODE = "code"
    LEGAL_CITATION = "legal_citation"
    FACT_STATEMENT = "fact_statement"
    ARGUMENT = "argument"
    CONCLUSION = "conclusion"
    PROCEDURAL = "procedural"
    UNKNOWN = "unknown"


class ChunkQuality(str, Enum):
    """Quality assessment of chunk content"""
    HIGH = "high"        # Clear, complete content
    MEDIUM = "medium"    # Acceptable content with minor issues
    LOW = "low"          # Poor quality, fragmented content
    FRAGMENT = "fragment" # Incomplete or corrupted content


@dataclass
class ChunkBoundary:
    """Information about chunk boundaries"""
    start_char: int
    end_char: int
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    boundary_type: str = "natural"  # natural, forced, semantic
    confidence: float = 1.0


@dataclass
class ChunkContext:
    """Contextual information for a chunk"""
    preceding_context: str = ""
    following_context: str = ""
    section_title: Optional[str] = None
    document_section: Optional[str] = None
    parent_element: Optional[str] = None


class EnhancedChunker:
    """
    Advanced document chunker with semantic awareness and optimized storage
    """
    
    def __init__(self, 
                 embedding_generator: EmbeddingGenerator,
                 chunk_size: int = 1200,
                 chunk_overlap: int = 200,
                 min_chunk_size: int = 100,
                 max_chunk_size: int = 2000):
        """
        Initialize the enhanced chunker
        
        Args:
            embedding_generator: Generator for vector embeddings
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks in characters
            min_chunk_size: Minimum acceptable chunk size
            max_chunk_size: Maximum acceptable chunk size
        """
        self.embedding_generator = embedding_generator
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.logger = logger
        
        # Patterns for semantic chunking
        self.patterns = {
            'header': re.compile(r'^#+\s+.*$|^[A-Z][A-Z\s]+$', re.MULTILINE),
            'legal_citation': re.compile(r'\b\d+\s+\w+\.?\s+\d+|\b\w+\s+v\.\s+\w+|\b\d+\s+F\.\s*\d*d?\s+\d+'),
            'list_item': re.compile(r'^\s*[\d\w]\.\s+|^\s*[•\-\*]\s+', re.MULTILINE),
            'paragraph_break': re.compile(r'\n\s*\n'),
            'sentence_end': re.compile(r'[.!?]+\s+'),
            'quote': re.compile(r'"[^"]*"'),
            'footnote': re.compile(r'\[\d+\]|\(\d+\)'),
            'page_break': re.compile(r'\f|\[Page \d+\]'),
            'table_start': re.compile(r'\|\s*\w+\s*\||\+-+\+'),
            'procedural': re.compile(r'\bWHEREAS\b|\bWHEREFORE\b|\bORDERED\b|\bADJUDGED\b', re.IGNORECASE)
        }
    
    async def create_chunks(self, 
                          document_core: DocumentCore,
                          document_text: str,
                          page_boundaries: Optional[List[int]] = None) -> List[ChunkMetadata]:
        """
        Create optimized chunks from document text
        
        Args:
            document_core: Core document information
            document_text: Full document text
            page_boundaries: Character positions of page breaks
            
        Returns:
            List of enhanced chunk metadata objects
        """
        try:
            start_time = datetime.now()
            
            # Step 1: Analyze document structure
            structure_analysis = self._analyze_document_structure(document_text)
            
            # Step 2: Create semantic chunks
            raw_chunks = self._create_semantic_chunks(document_text, structure_analysis)
            
            # Step 3: Optimize chunk boundaries
            optimized_chunks = self._optimize_chunk_boundaries(raw_chunks, document_text)
            
            # Step 4: Generate chunk metadata
            chunk_metadata_list = []
            for i, chunk_info in enumerate(optimized_chunks):
                chunk_metadata = await self._create_chunk_metadata(
                    document_core=document_core,
                    chunk_info=chunk_info,
                    chunk_index=i,
                    page_boundaries=page_boundaries
                )
                chunk_metadata_list.append(chunk_metadata)
            
            # Step 5: Generate embeddings in batch
            await self._generate_embeddings_batch(chunk_metadata_list)
            
            # Step 6: Calculate quality scores
            self._calculate_quality_scores(chunk_metadata_list)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(
                f"Created {len(chunk_metadata_list)} chunks for document {document_core.id} "
                f"in {processing_time:.2f}s"
            )
            
            return chunk_metadata_list
            
        except Exception as e:
            self.logger.error(f"Failed to create chunks for document {document_core.id}: {e}")
            raise
    
    def _analyze_document_structure(self, text: str) -> Dict[str, Any]:
        """Analyze document structure for better chunking"""
        structure = {
            'headers': [],
            'paragraphs': [],
            'lists': [],
            'citations': [],
            'tables': [],
            'footnotes': [],
            'total_length': len(text),
            'estimated_pages': len(text) // 2000  # Rough estimate
        }
        
        # Find headers
        for match in self.patterns['header'].finditer(text):
            structure['headers'].append({
                'text': match.group().strip(),
                'start': match.start(),
                'end': match.end()
            })
        
        # Find legal citations
        for match in self.patterns['legal_citation'].finditer(text):
            structure['citations'].append({
                'text': match.group().strip(),
                'start': match.start(),
                'end': match.end()
            })
        
        # Find list items
        for match in self.patterns['list_item'].finditer(text):
            structure['lists'].append({
                'text': match.group().strip(),
                'start': match.start(),
                'end': match.end()
            })
        
        # Find paragraphs
        paragraphs = self.patterns['paragraph_break'].split(text)
        current_pos = 0
        for para in paragraphs:
            if para.strip():
                structure['paragraphs'].append({
                    'text': para.strip(),
                    'start': current_pos,
                    'end': current_pos + len(para),
                    'length': len(para.strip())
                })
            current_pos += len(para) + 2  # Account for paragraph break
        
        return structure
    
    def _create_semantic_chunks(self, text: str, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create chunks with semantic awareness"""
        chunks = []
        current_pos = 0
        
        # Sort structural elements by position
        all_elements = []
        for element_type, elements in structure.items():
            if element_type in ['headers', 'paragraphs', 'lists', 'citations']:
                for element in elements:
                    element['type'] = element_type
                    all_elements.append(element)
        
        all_elements.sort(key=lambda x: x['start'])
        
        # Create chunks respecting semantic boundaries
        current_chunk = ""
        chunk_start = 0
        
        for element in all_elements:
            element_text = element['text']
            
            # Check if adding this element would exceed chunk size
            if len(current_chunk) + len(element_text) > self.chunk_size and current_chunk:
                # Create chunk
                chunks.append({
                    'text': current_chunk.strip(),
                    'start_char': chunk_start,
                    'end_char': current_pos,
                    'type': self._determine_chunk_type(current_chunk),
                    'elements': []
                })
                
                # Start new chunk with overlap
                overlap_start = max(0, current_pos - self.chunk_overlap)
                current_chunk = text[overlap_start:current_pos] + element_text
                chunk_start = overlap_start
            else:
                current_chunk += element_text + " "
            
            current_pos = element['end']
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'start_char': chunk_start,
                'end_char': current_pos,
                'type': self._determine_chunk_type(current_chunk),
                'elements': []
            })
        
        return chunks
    
    def _determine_chunk_type(self, chunk_text: str) -> ChunkType:
        """Determine the semantic type of a chunk"""
        text_lower = chunk_text.lower()
        
        # Check for specific legal patterns
        if self.patterns['legal_citation'].search(chunk_text):
            return ChunkType.LEGAL_CITATION
        
        if self.patterns['procedural'].search(chunk_text):
            return ChunkType.PROCEDURAL
        
        if self.patterns['header'].match(chunk_text):
            return ChunkType.HEADER
        
        if self.patterns['list_item'].search(chunk_text):
            return ChunkType.LIST_ITEM
        
        if self.patterns['table_start'].search(chunk_text):
            return ChunkType.TABLE
        
        if self.patterns['quote'].search(chunk_text):
            return ChunkType.QUOTE
        
        if self.patterns['footnote'].search(chunk_text):
            return ChunkType.FOOTNOTE
        
        # Legal document patterns
        if any(word in text_lower for word in ['therefore', 'whereas', 'plaintiff', 'defendant']):
            if any(word in text_lower for word in ['facts', 'evidence', 'testified']):
                return ChunkType.FACT_STATEMENT
            elif any(word in text_lower for word in ['argue', 'contend', 'assert']):
                return ChunkType.ARGUMENT
            elif any(word in text_lower for word in ['conclusion', 'ruling', 'finding']):
                return ChunkType.CONCLUSION
        
        return ChunkType.PARAGRAPH
    
    def _optimize_chunk_boundaries(self, chunks: List[Dict[str, Any]], full_text: str) -> List[Dict[str, Any]]:
        """Optimize chunk boundaries for better semantic coherence"""
        optimized = []
        
        for chunk in chunks:
            # Check if chunk is too small and can be merged
            if len(chunk['text']) < self.min_chunk_size and optimized:
                # Try to merge with previous chunk
                prev_chunk = optimized[-1]
                if len(prev_chunk['text']) + len(chunk['text']) <= self.max_chunk_size:
                    prev_chunk['text'] += " " + chunk['text']
                    prev_chunk['end_char'] = chunk['end_char']
                    continue
            
            # Check if chunk is too large and needs splitting
            if len(chunk['text']) > self.max_chunk_size:
                split_chunks = self._split_large_chunk(chunk, full_text)
                optimized.extend(split_chunks)
            else:
                optimized.append(chunk)
        
        return optimized
    
    def _split_large_chunk(self, chunk: Dict[str, Any], full_text: str) -> List[Dict[str, Any]]:
        """Split a chunk that's too large into smaller chunks"""
        text = chunk['text']
        start_char = chunk['start_char']
        
        # Try to split at sentence boundaries first
        sentences = self.patterns['sentence_end'].split(text)
        
        split_chunks = []
        current_text = ""
        current_start = start_char
        
        for sentence in sentences:
            if len(current_text) + len(sentence) > self.chunk_size and current_text:
                # Create chunk
                split_chunks.append({
                    'text': current_text.strip(),
                    'start_char': current_start,
                    'end_char': current_start + len(current_text),
                    'type': chunk['type'],
                    'elements': []
                })
                
                # Start new chunk
                current_start += len(current_text) - self.chunk_overlap
                current_text = sentence
            else:
                current_text += sentence
        
        # Add final chunk
        if current_text.strip():
            split_chunks.append({
                'text': current_text.strip(),
                'start_char': current_start,
                'end_char': current_start + len(current_text),
                'type': chunk['type'],
                'elements': []
            })
        
        return split_chunks
    
    async def _create_chunk_metadata(self,
                                   document_core: DocumentCore,
                                   chunk_info: Dict[str, Any],
                                   chunk_index: int,
                                   page_boundaries: Optional[List[int]] = None) -> ChunkMetadata:
        """Create enhanced metadata for a chunk"""
        
        # Calculate chunk hash for deduplication
        chunk_hash = hashlib.sha256(chunk_info['text'].encode()).hexdigest()
        
        # Determine page boundaries
        start_page, end_page = self._calculate_page_boundaries(
            chunk_info['start_char'], 
            chunk_info['end_char'], 
            page_boundaries
        )
        
        # Generate context summary
        context_summary = self._generate_context_summary(chunk_info['text'])
        
        # Create chunk metadata
        chunk_metadata = ChunkMetadata(
            document_id=document_core.id,
            chunk_text=chunk_info['text'],
            chunk_index=chunk_index,
            chunk_hash=chunk_hash,
            start_page=start_page,
            end_page=end_page,
            start_char=chunk_info['start_char'],
            end_char=chunk_info['end_char'],
            semantic_type=chunk_info['type'].value,
            context_summary=context_summary,
            text_quality_score=1.0,  # Will be calculated later
            extraction_confidence=1.0
        )
        
        return chunk_metadata
    
    def _calculate_page_boundaries(self, 
                                 start_char: int, 
                                 end_char: int,
                                 page_boundaries: Optional[List[int]]) -> Tuple[Optional[int], Optional[int]]:
        """Calculate which pages a chunk spans"""
        if not page_boundaries:
            return None, None
        
        start_page = None
        end_page = None
        
        for i, boundary in enumerate(page_boundaries):
            if start_char <= boundary and start_page is None:
                start_page = i + 1
            if end_char <= boundary:
                end_page = i + 1
                break
        
        # If we didn't find an end page, it's on the last page
        if end_page is None:
            end_page = len(page_boundaries)
        
        return start_page, end_page
    
    def _generate_context_summary(self, chunk_text: str) -> str:
        """Generate a brief context summary for the chunk"""
        # Extract key terms and concepts
        words = chunk_text.split()
        
        # Simple extractive summary - take first and last sentences
        sentences = self.patterns['sentence_end'].split(chunk_text)
        if len(sentences) >= 2:
            return f"{sentences[0].strip()}... {sentences[-1].strip()}"
        elif sentences:
            return sentences[0].strip()
        else:
            return chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text
    
    async def _generate_embeddings_batch(self, chunk_metadata_list: List[ChunkMetadata]):
        """Generate embeddings for all chunks in batch for efficiency"""
        try:
            # Extract texts for batch processing
            texts = [chunk.chunk_text for chunk in chunk_metadata_list]
            
            # Generate embeddings in batch
            embeddings = await self.embedding_generator.generate_embeddings_batch(texts)
            
            # Assign embeddings to chunks
            for chunk, embedding in zip(chunk_metadata_list, embeddings):
                chunk.dense_vector = embedding
                chunk.embedding_model = self.embedding_generator.model_name
            
            self.logger.info(f"Generated embeddings for {len(chunk_metadata_list)} chunks")
            
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings batch: {e}")
            # Fall back to individual generation
            for chunk in chunk_metadata_list:
                try:
                    embedding = await self.embedding_generator.generate_embedding(chunk.chunk_text)
                    chunk.dense_vector = embedding
                    chunk.embedding_model = self.embedding_generator.model_name
                except Exception as individual_error:
                    self.logger.error(f"Failed to generate embedding for chunk: {individual_error}")
    
    def _calculate_quality_scores(self, chunk_metadata_list: List[ChunkMetadata]):
        """Calculate quality scores for chunks"""
        for chunk in chunk_metadata_list:
            score = 1.0
            text = chunk.chunk_text
            
            # Penalize very short chunks
            if len(text) < self.min_chunk_size:
                score *= 0.7
            
            # Penalize chunks with lots of whitespace or special characters
            if len(text.strip()) / len(text) < 0.8:
                score *= 0.8
            
            # Reward chunks with complete sentences
            sentence_count = len(self.patterns['sentence_end'].findall(text))
            if sentence_count > 0:
                score *= min(1.2, 1.0 + (sentence_count * 0.1))
            
            # Penalize chunks that appear to be fragmented
            if text.count('\n') > len(text) / 50:  # Too many line breaks
                score *= 0.9
            
            chunk.text_quality_score = max(0.1, min(1.0, score))
    
    def get_chunk_statistics(self, chunk_metadata_list: List[ChunkMetadata]) -> Dict[str, Any]:
        """Get comprehensive statistics about the chunks"""
        if not chunk_metadata_list:
            return {}
        
        total_chunks = len(chunk_metadata_list)
        total_chars = sum(len(chunk.chunk_text) for chunk in chunk_metadata_list)
        
        # Type distribution
        type_distribution = {}
        for chunk in chunk_metadata_list:
            chunk_type = chunk.semantic_type or 'unknown'
            type_distribution[chunk_type] = type_distribution.get(chunk_type, 0) + 1
        
        # Quality distribution
        quality_scores = [chunk.text_quality_score for chunk in chunk_metadata_list]
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        # Size distribution
        chunk_sizes = [len(chunk.chunk_text) for chunk in chunk_metadata_list]
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        
        return {
            'total_chunks': total_chunks,
            'total_characters': total_chars,
            'average_chunk_size': avg_size,
            'average_quality_score': avg_quality,
            'type_distribution': type_distribution,
            'size_distribution': {
                'min': min(chunk_sizes),
                'max': max(chunk_sizes),
                'median': sorted(chunk_sizes)[len(chunk_sizes) // 2]
            },
            'quality_distribution': {
                'min': min(quality_scores),
                'max': max(quality_scores),
                'high_quality_count': sum(1 for score in quality_scores if score > 0.8),
                'low_quality_count': sum(1 for score in quality_scores if score < 0.5)
            }
        }