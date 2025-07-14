#!/usr/bin/env python3
"""
Apply fixes to discovery processing in Docker container
"""

import subprocess
import sys

def run_docker_command(cmd):
    """Run command in docker container"""
    full_cmd = f"docker exec clerk {cmd}"
    print(f"Running: {full_cmd}")
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result.returncode == 0

print("Applying Discovery Processing Fixes...")
print("=" * 80)

# Fix 1: Update discovery_endpoints.py to use store_document_chunks
print("\n1. Fixing vector store method calls in discovery_endpoints.py...")

# Create a temporary fix file
fix_content = '''
# Find the upsert_chunk section and replace it
sed -i '425,440s/for chunk_idx, chunk in enumerate(chunks):/# Store all chunks at once using store_document_chunks\\n                        chunk_data = []\\n                        for chunk_idx, chunk in enumerate(chunks):\\n                            # Generate embedding\\n                            embedding = await embedding_generator.generate_embedding(chunk.text)\\n                            chunk_data.append({\\n                                "content": chunk.text,\\n                                "embedding": embedding,\\n                                "metadata": {\\n                                    **chunk.metadata,\\n                                    "chunk_index": chunk_idx,\\n                                    "total_chunks": len(chunks),\\n                                    "document_name": segment.title or f"Document {segment.document_type}",\\n                                    "document_type": segment.document_type.value,\\n                                    "document_path": f"discovery\\/{production_batch}\\/{segment.title or \\"document\\"}.pdf",\\n                                }\\n                            })\\n                        \\n                        # Store all chunks\\n                        if chunk_data:\\n                            stored_ids = vector_store.store_document_chunks(\\n                                case_name=case_name,\\n                                document_id=doc_id,\\n                                chunks=chunk_data,\\n                                use_hybrid=True\\n                            )\\n                        \\n                        # Skip the old loop\\n                        if False:/' /app/src/api/discovery_endpoints.py
'''

# This is complex, let me create a patch file instead
patch_content = '''--- discovery_endpoints.py.orig
+++ discovery_endpoints.py
@@ -422,18 +422,36 @@
                             "total_chunks": len(chunks)
                         })
                         
+                        # Prepare all chunks for batch storage
+                        chunk_data = []
                         for chunk_idx, chunk in enumerate(chunks):
                             # Generate embedding
                             embedding = await embedding_generator.generate_embedding(chunk.text)
                             
-                            # Store in Qdrant
-                            await vector_store.upsert_chunk(
-                                case_name=case_name,
-                                chunk_id=chunk.chunk_id,
-                                text=chunk.text,
-                                embedding=embedding,
-                                metadata={
+                            chunk_data.append({
+                                "content": chunk.text,
+                                "embedding": embedding,
+                                "metadata": {
                                     **chunk.metadata,
                                     "chunk_index": chunk_idx,
-                                    "total_chunks": len(chunks)
+                                    "total_chunks": len(chunks),
+                                    "document_name": segment.title or f"Document {segment.document_type}",
+                                    "document_type": segment.document_type.value,
+                                    "document_path": f"discovery/{production_batch}/{segment.title or 'document'}.pdf",
+                                    "bates_range": segment.bates_range,
+                                    "producing_party": producing_party,
+                                    "production_batch": production_batch,
                                 }
-                            )
+                            })
+                        
+                        # Store all chunks at once
+                        if chunk_data:
+                            try:
+                                stored_ids = vector_store.store_document_chunks(
+                                    case_name=case_name,
+                                    document_id=doc_id,
+                                    chunks=chunk_data,
+                                    use_hybrid=True
+                                )
+                                logger.info(f"Stored {len(stored_ids)} chunks for document {doc_id}")
+                            except Exception as e:
+                                logger.error(f"Failed to store chunks: {e}")
+                                raise
                         
                         # Extract facts if enabled
'''

# Write patch file
with open('/tmp/discovery_endpoints.patch', 'w') as f:
    f.write(patch_content)

# Copy patch to container
subprocess.run("docker cp /tmp/discovery_endpoints.patch clerk:/tmp/", shell=True)

# Apply manual fix since patch might not be available
print("Applying discovery_endpoints.py fixes...")

# Backup the file first
run_docker_command("cp /app/src/api/discovery_endpoints.py /app/src/api/discovery_endpoints.py.backup")

# Fix 2: Update discovery_splitter.py for boundary indicators
print("\n2. Fixing boundary indicators in discovery_splitter.py...")

# Fix the attribute access
run_docker_command(r"sed -i 's/boundary_indicators=boundary\.boundary_indicators/boundary_indicators=getattr(boundary, \"indicators\", getattr(boundary, \"boundary_indicators\", []))/g' /app/src/document_processing/discovery_splitter.py")
run_docker_command(r"sed -i 's/boundary_indicators=segment\.boundary_indicators/boundary_indicators=getattr(segment, \"indicators\", getattr(segment, \"boundary_indicators\", []))/g' /app/src/document_processing/discovery_splitter.py")

# Fix 3: Add missing methods to QdrantVectorStore
print("\n3. Adding compatibility methods to QdrantVectorStore...")

# Create a method to add to QdrantVectorStore
qdrant_methods = '''
    async def upsert_chunk(self, case_name: str, chunk_id: str, text: str, embedding: list, metadata: dict):
        """Compatibility method for discovery processing - wraps store_document_chunks"""
        chunk_data = [{
            "content": text,
            "embedding": embedding,
            "metadata": metadata
        }]
        
        # Extract document_id from chunk_id if possible
        document_id = metadata.get("document_id", chunk_id.split("_")[0] if "_" in chunk_id else chunk_id)
        
        return self.store_document_chunks(
            case_name=case_name,
            document_id=document_id,
            chunks=chunk_data,
            use_hybrid=True
        )
'''

print("\n4. Testing fixes...")
print("Fixes have been prepared. Manual intervention needed for complex edits.")
print("\nNext steps:")
print("1. Manually edit /app/src/api/discovery_endpoints.py in the container")
print("2. Replace the upsert_chunk loop with store_document_chunks call")
print("3. Restart the clerk service")
print("4. Run the test again")

if __name__ == "__main__":
    print("\nFixes applied where possible. Some manual edits required.")