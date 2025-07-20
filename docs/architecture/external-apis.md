# External APIs Integration

## Overview

The Clerk Legal AI System integrates with several external APIs to provide document storage, AI capabilities, and enhanced search functionality. This document details all external API integrations, their configuration, usage patterns, and best practices.

## OpenAI API

### Purpose
- Generate embeddings for semantic search
- Power AI agents for motion drafting and analysis
- Extract facts and insights from legal documents

### Configuration
```python
# Environment Variables
OPENAI_API_KEY=sk-...
CONTEXT_LLM_MODEL=gpt-3.5-turbo
EMBEDDING_MODEL=text-embedding-ada-002
ANALYSIS_MODEL=gpt-4
```

### Integration Points

#### Embedding Generation
```python
class EmbeddingGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
    async def generate_embeddings(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        response = await self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=texts
        )
        return [e.embedding for e in response.data]
```

#### Motion Generation
```python
class MotionDrafter:
    async def generate_motion_content(
        self,
        outline: MotionOutline,
        context: str
    ) -> str:
        messages = [
            {"role": "system", "content": LEGAL_DRAFTER_PROMPT},
            {"role": "user", "content": f"Outline: {outline}\nContext: {context}"}
        ]
        
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.3,
            max_tokens=4000
        )
        return response.choices[0].message.content
```

#### Deficiency Analysis
```python
class DeficiencyAnalyzer:
    async def analyze_rtp_compliance(
        self,
        rtp_item: str,
        search_results: List[str]
    ) -> DeficiencyClassification:
        prompt = self._build_analysis_prompt(rtp_item, search_results)
        
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        return DeficiencyClassification.parse_raw(
            response.choices[0].message.content
        )
```

### Rate Limiting & Retry Strategy
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def call_openai_with_retry(self, **kwargs):
    try:
        return await self.client.chat.completions.create(**kwargs)
    except RateLimitError:
        await asyncio.sleep(60)  # Wait 1 minute on rate limit
        raise
```

### Cost Tracking
```python
class OpenAICostTracker:
    PRICING = {
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-4": {"input": 0.01, "output": 0.03},
        "text-embedding-ada-002": {"input": 0.0001}
    }
    
    async def track_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        operation: str,
        case_id: UUID
    ):
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        await self.save_cost_record(case_id, "openai", operation, cost)
```

## Cohere API

### Purpose
- Rerank search results for improved relevance
- Enhance hybrid search accuracy

### Configuration
```python
# Environment Variables
COHERE_API_KEY=co-...
COHERE_RERANK_MODEL=rerank-multilingual-v3.0
```

### Integration
```python
class CohereReranker:
    def __init__(self):
        self.client = cohere.Client(settings.COHERE_API_KEY)
        
    async def rerank_results(
        self,
        query: str,
        documents: List[str],
        top_k: int = 10
    ) -> List[RerankResult]:
        response = await self.client.rerank(
            model="rerank-multilingual-v3.0",
            query=query,
            documents=documents,
            top_n=top_k
        )
        
        return [
            RerankResult(
                index=r.index,
                score=r.relevance_score,
                document=documents[r.index]
            )
            for r in response.results
        ]
```

### Error Handling
```python
try:
    reranked = await self.reranker.rerank_results(query, docs)
except CohereAPIError as e:
    logger.error(f"Cohere reranking failed: {e}")
    # Fallback to original ranking
    return original_results
```

## Box API

### Purpose
- Secure document storage and retrieval
- Folder-based document organization
- Enterprise-grade file management

### Configuration
```python
# Environment Variables
BOX_CLIENT_ID=your_client_id
BOX_CLIENT_SECRET=your_client_secret
BOX_ENTERPRISE_ID=your_enterprise_id
BOX_JWT_KEY_ID=your_jwt_key_id
BOX_PRIVATE_KEY="-----BEGIN ENCRYPTED PRIVATE KEY-----..."
BOX_PASSPHRASE=your_passphrase
```

### Authentication
```python
class BoxClient:
    def __init__(self):
        self.config = JWTAuth(
            client_id=settings.BOX_CLIENT_ID,
            client_secret=settings.BOX_CLIENT_SECRET,
            enterprise_id=settings.BOX_ENTERPRISE_ID,
            jwt_key_id=settings.BOX_JWT_KEY_ID,
            rsa_private_key_data=settings.BOX_PRIVATE_KEY,
            rsa_private_key_passphrase=settings.BOX_PASSPHRASE
        )
        self.client = Client(self.config)
```

### File Operations
```python
class BoxDocumentManager:
    async def download_file(self, file_id: str) -> bytes:
        """Download file from Box"""
        try:
            file = self.client.file(file_id)
            return file.get().content()
        except BoxAPIException as e:
            raise DocumentRetrievalError(f"Failed to download: {e}")
    
    async def list_folder_items(
        self,
        folder_id: str,
        limit: int = 100
    ) -> List[BoxItem]:
        """List items in Box folder"""
        folder = self.client.folder(folder_id)
        items = []
        
        for item in folder.get_items(limit=limit):
            items.append(BoxItem(
                id=item.id,
                name=item.name,
                type=item.type,
                size=item.size
            ))
        
        return items
    
    async def upload_file(
        self,
        folder_id: str,
        file_name: str,
        file_content: bytes
    ) -> str:
        """Upload file to Box folder"""
        folder = self.client.folder(folder_id)
        
        file_stream = BytesIO(file_content)
        uploaded_file = folder.upload_stream(
            file_stream,
            file_name
        )
        
        return uploaded_file.id
```

### Webhook Integration (Future)
```python
class BoxWebhookManager:
    async def create_webhook(
        self,
        target_id: str,
        target_type: str,
        triggers: List[str]
    ) -> str:
        """Create Box webhook for file events"""
        webhook = self.client.create_webhook(
            target_id,
            target_type,
            triggers,
            f"{settings.API_BASE_URL}/webhooks/box"
        )
        return webhook.id
```

## Qdrant Vector Database

### Purpose
- Store and search document embeddings
- Provide semantic search capabilities
- Maintain case-isolated vector collections

### Configuration
```python
# Environment Variables
QDRANT_HOST=your_qdrant_host
QDRANT_PORT=6333
QDRANT_API_KEY=your_api_key
QDRANT_HTTPS=true
```

### Client Setup
```python
class QdrantVectorStore:
    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY,
            https=settings.QDRANT_HTTPS
        )
```

### Collection Management
```python
async def create_case_collection(self, case_name: str):
    """Create vector collection for a case"""
    await self.client.create_collection(
        collection_name=case_name,
        vectors_config=VectorParams(
            size=1536,  # OpenAI embedding dimension
            distance=Distance.COSINE
        )
    )
    
    # Create indexes for metadata filtering
    await self.client.create_payload_index(
        collection_name=case_name,
        field_name="document_type",
        field_schema=PayloadSchemaType.KEYWORD
    )
```

### Vector Operations
```python
async def store_embeddings(
    self,
    case_name: str,
    documents: List[Document]
) -> None:
    """Store document embeddings in Qdrant"""
    points = []
    
    for doc in documents:
        points.append(PointStruct(
            id=str(uuid4()),
            vector=doc.embedding,
            payload={
                "document_id": str(doc.id),
                "chunk_index": doc.chunk_index,
                "content": doc.content,
                "page_number": doc.page_number,
                "document_type": doc.document_type,
                "metadata": doc.metadata
            }
        ))
    
    # Batch upload for efficiency
    await self.client.upsert(
        collection_name=case_name,
        points=points,
        wait=True
    )
```

### Hybrid Search
```python
async def hybrid_search(
    self,
    case_name: str,
    query_vector: List[float],
    query_text: str,
    limit: int = 20
) -> List[SearchResult]:
    """Perform hybrid semantic + keyword search"""
    
    # Semantic search
    semantic_results = await self.client.search(
        collection_name=case_name,
        query_vector=query_vector,
        limit=limit * 2,  # Get more for reranking
        with_payload=True
    )
    
    # Keyword search using payload filtering
    keyword_filter = Filter(
        must=[
            FieldCondition(
                key="content",
                match=MatchText(text=query_text)
            )
        ]
    )
    
    keyword_results = await self.client.search(
        collection_name=case_name,
        query_vector=query_vector,
        query_filter=keyword_filter,
        limit=limit * 2,
        with_payload=True
    )
    
    # Merge and deduplicate results
    return self._merge_search_results(
        semantic_results,
        keyword_results,
        limit
    )
```

## External API Best Practices

### Authentication Management
```python
class APIKeyManager:
    """Centralized API key management"""
    
    def __init__(self):
        self._keys = {
            "openai": SecretStr(settings.OPENAI_API_KEY),
            "cohere": SecretStr(settings.COHERE_API_KEY),
            "box": self._load_box_config()
        }
    
    def get_key(self, service: str) -> SecretStr:
        if service not in self._keys:
            raise ValueError(f"Unknown service: {service}")
        return self._keys[service]
```

### Circuit Breaker Pattern
```python
class APICircuitBreaker:
    def __init__(self, failure_threshold: int = 5):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.last_failure_time = None
        self.circuit_open = False
    
    async def call(self, func, *args, **kwargs):
        if self.circuit_open:
            if self._should_retry():
                self.circuit_open = False
            else:
                raise CircuitOpenError("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.circuit_open = True
            
            raise e
```

### Request Pooling
```python
class APIRequestPool:
    """Pool API requests for efficiency"""
    
    def __init__(self, batch_size: int = 10, wait_time: float = 0.1):
        self.batch_size = batch_size
        self.wait_time = wait_time
        self.pending_requests = []
        self.processing = False
    
    async def add_request(self, request: APIRequest) -> Any:
        future = asyncio.Future()
        self.pending_requests.append((request, future))
        
        if not self.processing:
            asyncio.create_task(self._process_batch())
        
        return await future
```

### Monitoring and Alerting
```python
class APIMonitor:
    """Monitor external API health and performance"""
    
    async def track_api_call(
        self,
        service: str,
        endpoint: str,
        duration: float,
        success: bool,
        error: Optional[str] = None
    ):
        metric = APIMetric(
            service=service,
            endpoint=endpoint,
            duration=duration,
            success=success,
            error=error,
            timestamp=datetime.now()
        )
        
        await self.store_metric(metric)
        
        if not success:
            await self.check_alert_threshold(service)
```

## API Rate Limits & Quotas

### Service Limits
| Service | Rate Limit | Daily Quota | Burst Limit |
|---------|------------|-------------|-------------|
| OpenAI GPT-4 | 10,000 TPM | 100K requests | 100 req/min |
| OpenAI Embeddings | 1M TPM | No limit | 3000 req/min |
| Cohere Rerank | 100 req/min | 10K requests | 200 req/min |
| Box API | 15 req/sec | No limit | 20 req/sec |
| Qdrant | No limit | No limit | Hardware limited |

### Rate Limit Handling
```python
class RateLimitManager:
    def __init__(self):
        self.limiters = {
            "openai": TokenBucketLimiter(10000, 60),  # 10K per minute
            "cohere": TokenBucketLimiter(100, 60),    # 100 per minute
            "box": TokenBucketLimiter(15, 1)          # 15 per second
        }
    
    async def acquire(self, service: str, tokens: int = 1):
        limiter = self.limiters.get(service)
        if limiter:
            await limiter.acquire(tokens)
```

## Security Considerations

### API Key Storage
- Never commit API keys to version control
- Use environment variables or secure key management
- Rotate keys regularly (quarterly minimum)
- Implement key encryption at rest

### Request Signing
```python
class RequestSigner:
    """Sign API requests for additional security"""
    
    def sign_request(
        self,
        method: str,
        url: str,
        body: Optional[str] = None
    ) -> Dict[str, str]:
        timestamp = str(int(time.time()))
        message = f"{method}\n{url}\n{timestamp}\n{body or ''}"
        
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "X-Timestamp": timestamp,
            "X-Signature": signature
        }
```

### Data Privacy
- Minimize data sent to external APIs
- Anonymize sensitive information when possible
- Implement data retention policies
- Audit all external API calls

## Disaster Recovery

### Failover Strategy
```python
class APIFailover:
    """Handle API service failures"""
    
    def __init__(self):
        self.fallback_providers = {
            "embedding": ["openai", "cohere", "local"],
            "llm": ["gpt-4", "gpt-3.5-turbo", "claude"]
        }
    
    async def call_with_fallback(
        self,
        service_type: str,
        primary_func: Callable,
        *args,
        **kwargs
    ):
        providers = self.fallback_providers.get(service_type, [])
        
        for provider in providers:
            try:
                return await primary_func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Provider {provider} failed: {e}")
                continue
        
        raise AllProvidersFailedError()
```

### Backup Strategies
- Cache successful API responses
- Implement local fallbacks for critical features
- Store embeddings locally for offline search
- Queue failed requests for retry

## Performance Optimization

### Connection Pooling
```python
# Reuse HTTP connections
connector = aiohttp.TCPConnector(
    limit=100,
    limit_per_host=30,
    ttl_dns_cache=300
)

session = aiohttp.ClientSession(connector=connector)
```

### Response Caching
```python
class APIResponseCache:
    """Cache API responses for performance"""
    
    def __init__(self, ttl: int = 3600):
        self.cache = TTLCache(maxsize=1000, ttl=ttl)
    
    async def get_or_fetch(
        self,
        cache_key: str,
        fetch_func: Callable,
        *args,
        **kwargs
    ):
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        result = await fetch_func(*args, **kwargs)
        self.cache[cache_key] = result
        return result
```

### Batch Processing
```python
class BatchProcessor:
    """Batch API requests for efficiency"""
    
    async def process_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await self.generate_embeddings(batch)
            embeddings.extend(batch_embeddings)
        
        return embeddings
```