"""Embedding generation and management."""

import os
from typing import List, Optional
from langchain_community.embeddings import HuggingFaceEmbeddings

from ..config.settings import AIConfig


class EmbeddingManager:
    """Manages embedding generation for documents and queries."""
    
    def __init__(self, config: AIConfig):
        """Initialize embedding manager.
        
        Args:
            config: AI configuration
        """
        self.config = config
        self.embedding_model: Optional[HuggingFaceEmbeddings] = None
        
        # Suppress tokenizers parallelism warning
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
    
    def initialize(self) -> bool:
        """Initialize the embedding model.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.embedding_model = HuggingFaceEmbeddings(
                model_name=self.config.embedding_model_name
            )
            print(f"✓ Embedding model loaded successfully ({self.config.embedding_model_name})")
            return True
        except Exception as e:
            print(f"✗ Error loading embedding model: {e}")
            print("Try installing: pip install sentence-transformers")
            return False
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of documents.
        
        Args:
            texts: List of document texts
            
        Returns:
            List of embedding vectors
        """
        if not self.embedding_model:
            raise RuntimeError("Embedding model not initialized")
        
        return self.embedding_model.embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query.
        
        Args:
            text: Query text
            
        Returns:
            Embedding vector
        """
        if not self.embedding_model:
            raise RuntimeError("Embedding model not initialized")
        
        return self.embedding_model.embed_query(text)
