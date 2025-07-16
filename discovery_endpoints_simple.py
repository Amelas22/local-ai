# Simplified discovery processing section for _process_discovery_async
# This replaces the complex initialization with a simpler approach

    # Initialize processors
    vector_store = QdrantVectorStore()
    embedding_generator = EmbeddingGenerator()
    
    # Use the basic discovery processor without normalized services
    from src.document_processing.discovery_splitter import DiscoveryProductionProcessor
    discovery_processor = DiscoveryProductionProcessor(case_name=case_name)
    
    # Simple document manager for tracking
    document_manager = UnifiedDocumentManager(case_name, vector_store)
    fact_extractor = FactExtractor(case_name=case_name) if enable_fact_extraction else None
    chunker = EnhancedChunker(
        embedding_generator=embedding_generator,
        chunk_size=1400,
        chunk_overlap=200
    )
    
    # ... rest of the processing code remains the same but:
    
    # When processing, use the basic process_discovery_production method:
    try:
        # Create discovery request for the splitter
        discovery_metadata = {
            "production_batch": production_batch or f"batch_{idx}",
            "producing_party": producing_party or "Unknown",
            "production_date": production_date,
            "responsive_to_requests": responsive_to_requests or [],
            "confidentiality_designation": confidentiality_designation,
        }
        
        # Process with discovery splitter
        logger.info(f"Processing discovery production: {filename}")
        production_result = discovery_processor.process_discovery_production(
            pdf_path=temp_pdf_path,
            production_metadata=discovery_metadata
        )
        
        # Update total documents found
        processing_result["total_documents_found"] += len(production_result.segments_found)
        
        # Process each segment as a separate document
        for segment_idx, segment in enumerate(production_result.segments_found):
            # ... continue with existing segment processing