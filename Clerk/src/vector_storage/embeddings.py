"""
Embeddings generation module.
Creates vector embeddings using OpenAI's text-embedding-3-small model.
"""

import logging
from typing import List, Dict, Any, Tuple
import numpy as np
import asyncio

import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tenacity.asyncio import AsyncRetrying

from config.settings import settings

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """Generates vector embeddings for text chunks"""
    
    def __init__(self):
        """Initialize embedding generator with OpenAI client"""
        self.client = openai.OpenAI(api_key=settings.openai.api_key)
        self.async_client = openai.AsyncOpenAI(api_key=settings.openai.api_key)
        self.model = settings.ai.embedding_model
        self.dimensions = settings.ai.embedding_dimensions
        
        # Batch settings
        self.max_batch_size = 100  # OpenAI limit
        self.max_tokens_per_request = 8000  # Conservative limit
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate_embedding(self, text: str) -> Tuple[List[float], int]:
        """Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            Tuple of (embedding vector, token count)
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            token_count = response.usage.total_tokens
            
            # Validate embedding dimensions
            if len(embedding) != self.dimensions:
                raise ValueError(
                    f"Expected {self.dimensions} dimensions, got {len(embedding)}"
                )
            
            return embedding, token_count
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str]) -> Tuple[List[List[float]], int]:
        """Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Tuple of (list of embedding vectors, total token count)
        """
        if not texts:
            return [], 0
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        all_embeddings = []
        total_tokens = 0
        
        # Process in batches
        for i in range(0, len(texts), self.max_batch_size):
            batch = texts[i:i + self.max_batch_size]
            
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    encoding_format="float"
                )
                
                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                total_tokens += response.usage.total_tokens
                
                logger.debug(f"Processed batch {i//self.max_batch_size + 1}")
                
            except Exception as e:
                logger.error(f"Error in batch {i//self.max_batch_size + 1}: {str(e)}")
                # Try individual processing for failed batch
                for text in batch:
                    try:
                        embedding, tokens = self.generate_embedding(text)
                        all_embeddings.append(embedding)
                        total_tokens += tokens
                    except:
                        # Use zero vector as fallback
                        all_embeddings.append([0.0] * self.dimensions)
        
        logger.info(f"Generated {len(all_embeddings)} embeddings using {total_tokens} tokens")
        return all_embeddings, total_tokens
    
    def prepare_chunk_for_embedding(self, chunk_content: str, metadata: Dict[str, Any]) -> Tuple[Dict, int]:
        """Prepare a chunk with metadata for storage
        
        Args:
            chunk_content: The chunk text (with or without context)
            metadata: Metadata for the chunk
            
        Returns:
            Tuple of (dictionary ready for vector storage, token count)
        """
        # Generate embedding
        embedding, tokens = self.generate_embedding(chunk_content)
        
        # Prepare storage format
        return {
            "content": chunk_content,
            "embedding": embedding,
            "metadata": {
                **metadata,
                "embedding_model": self.model,
                "content_length": len(chunk_content)
            }
        }, tokens
    
    def calculate_similarity(self, embedding1: List[float], 
                           embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # Ensure result is in [0, 1] range
        return max(0.0, min(1.0, similarity))
    
    async def generate_embedding_async(self, text: str) -> Tuple[List[float], int]:
        """Generate embedding for a single text asynchronously
        
        Args:
            text: Text to embed
            
        Returns:
            Tuple of (embedding vector, token count)
        """
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError))
        ):
            with attempt:
                try:
                    response = await self.async_client.embeddings.create(
                        model=self.model,
                        input=text,
                        encoding_format="float"
                    )
                    
                    embedding = response.data[0].embedding
                    token_count = response.usage.total_tokens
                    
                    # Validate embedding dimensions
                    if len(embedding) != self.dimensions:
                        raise ValueError(
                            f"Expected {self.dimensions} dimensions, got {len(embedding)}"
                        )
                    
                    return embedding, token_count
                    
                except Exception as e:
                    logger.error(f"Error generating embedding async: {str(e)}")
                    raise
    
    async def generate_embeddings_batch_async(self, texts: List[str]) -> Tuple[List[List[float]], int]:
        """Generate embeddings for multiple texts asynchronously
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Tuple of (list of embedding vectors, total token count)
        """
        if not texts:
            return [], 0
        
        logger.info(f"Generating embeddings async for {len(texts)} texts")
        
        all_embeddings = []
        total_tokens = 0
        
        # Process in batches
        for i in range(0, len(texts), self.max_batch_size):
            batch = texts[i:i + self.max_batch_size]
            
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=4, max=10),
                retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError))
            ):
                with attempt:
                    try:
                        response = await self.async_client.embeddings.create(
                            model=self.model,
                            input=batch,
                            encoding_format="float"
                        )
                        
                        # Extract embeddings in order
                        batch_embeddings = [item.embedding for item in response.data]
                        all_embeddings.extend(batch_embeddings)
                        total_tokens += response.usage.total_tokens
                        
                        logger.debug(f"Processed async batch {i//self.max_batch_size + 1}")
                        break
                        
                    except Exception as e:
                        logger.error(f"Error in async batch {i//self.max_batch_size + 1}: {str(e)}")
                        # Try individual processing for failed batch
                        for text in batch:
                            try:
                                embedding, tokens = await self.generate_embedding_async(text)
                                all_embeddings.append(embedding)
                                total_tokens += tokens
                            except:
                                # Use zero vector as fallback
                                all_embeddings.append([0.0] * self.dimensions)
                        break
        
        logger.info(f"Generated {len(all_embeddings)} embeddings async using {total_tokens} tokens")
        return all_embeddings, total_tokens
    
    async def generate_embeddings_concurrent(self, texts: List[str], max_concurrent: int = 5) -> Tuple[List[List[float]], int]:
        """Generate embeddings for multiple texts with controlled concurrency
        
        Args:
            texts: List of texts to embed
            max_concurrent: Maximum number of concurrent requests
            
        Returns:
            Tuple of (list of embedding vectors, total token count)
        """
        if not texts:
            return [], 0
        
        logger.info(f"Generating {len(texts)} embeddings with max {max_concurrent} concurrent requests")
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def embed_with_semaphore(text: str) -> Tuple[List[float], int]:
            async with semaphore:
                return await self.generate_embedding_async(text)
        
        # Execute all embedding requests concurrently
        tasks = [embed_with_semaphore(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        embeddings = []
        total_tokens = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to generate embedding for text {i}: {result}")
                # Use zero vector as fallback
                embeddings.append([0.0] * self.dimensions)
            else:
                embedding, tokens = result
                embeddings.append(embedding)
                total_tokens += tokens
        
        logger.info(f"Generated {len(embeddings)} embeddings concurrently using {total_tokens} tokens")
        return embeddings, total_tokens
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """Validate an embedding vector
        
        Args:
            embedding: Embedding vector to validate
            
        Returns:
            True if embedding is valid
        """
        if not embedding or len(embedding) != self.dimensions:
            return False
        
        # Check for all zeros (failed embedding)
        if all(x == 0 for x in embedding):
            return False
        
        # Check for NaN or infinite values
        if any(np.isnan(x) or np.isinf(x) for x in embedding):
            return False
        
        return True