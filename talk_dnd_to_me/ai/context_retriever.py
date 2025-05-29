"""Context retrieval for RAG (Retrieval-Augmented Generation)."""

import json
from typing import List, Optional

from ..database.chroma_client import ChromaClient
from ..content.embeddings import EmbeddingManager
from ..config.settings import ContentConfig


class ContextRetriever:
    """Retrieves relevant context from knowledge base and session history."""
    
    def __init__(self, chroma_client: ChromaClient, embedding_manager: EmbeddingManager,
                 config: ContentConfig):
        """Initialize context retriever.
        
        Args:
            chroma_client: ChromaDB client instance
            embedding_manager: Embedding manager instance
            config: Content configuration
        """
        self.chroma_client = chroma_client
        self.embedding_manager = embedding_manager
        self.config = config
    
    def get_relevant_context(self, query: str, max_chunks: Optional[int] = None) -> str:
        """Retrieve relevant context from knowledge base and session history.
        
        Args:
            query: Query text to find relevant context for
            max_chunks: Maximum number of chunks to retrieve
            
        Returns:
            Formatted context string
        """
        if max_chunks is None:
            max_chunks = self.config.max_context_chunks
        
        try:
            query_embedding = self.embedding_manager.embed_query(query)
            
            # Get context from campaign content
            content_results = self.chroma_client.query_collection(
                'content',
                query_embeddings=[query_embedding],
                n_results=min(max_chunks, 3),
                include=["documents", "metadatas"]
            )
            
            # Get context from session history
            history_results = self.chroma_client.query_collection(
                'history',
                query_embeddings=[query_embedding],
                n_results=min(max_chunks, 2),
                include=["documents", "metadatas"]
            )
            
            context_parts = []
            
            # Add campaign content
            if content_results['documents'] and content_results['documents'][0]:
                for doc, metadata in zip(content_results['documents'][0], content_results['metadatas'][0]):
                    context_parts.append(f"[Campaign Content - {metadata.get('content_type', 'Unknown')}] {doc}")
            
            # Add session history
            if history_results['documents'] and history_results['documents'][0]:
                for doc, metadata in zip(history_results['documents'][0], history_results['metadatas'][0]):
                    try:
                        entry = json.loads(doc)
                        if entry.get('entry_type') in ['player_input', 'dm_response', 'dice_roll']:
                            context_parts.append(f"[Session History] {entry.get('content', '')}")
                    except json.JSONDecodeError:
                        # Skip malformed entries
                        continue
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            print(f"Warning: Error retrieving context: {e}")
            return ""
    
    def test_retrieval(self, test_query: str = "What is Death House?") -> bool:
        """Test context retrieval functionality.
        
        Args:
            test_query: Query to test with
            
        Returns:
            True if retrieval works, False otherwise
        """
        try:
            # Check if content collection has any documents
            content_collection = self.chroma_client.get_collection('content')
            content_count = content_collection.count() if content_collection else 0
            
            # Check if history collection exists
            history_collection = self.chroma_client.get_collection('history')
            history_count = history_collection.count() if history_collection else 0
            
            if content_count == 0:
                print("⚠ Warning: No content loaded in database yet (this is normal on first run)")
                return True  # Don't treat this as an error
            
            # Test actual retrieval
            context = self.get_relevant_context(test_query)
            if context:
                print(f"✓ Context retrieval working ({content_count} content docs, {history_count} history docs)")
                return True
            else:
                print(f"⚠ Warning: Context retrieval returned empty results ({content_count} content docs available)")
                return False
                
        except Exception as e:
            print(f"✗ Error testing context retrieval: {e}")
            return False
