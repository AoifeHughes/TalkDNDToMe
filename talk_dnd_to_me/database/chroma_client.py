"""ChromaDB client wrapper."""

import chromadb
from typing import Optional, List, Dict, Any
import sys

from ..config.settings import DatabaseConfig


class ChromaClient:
    """Wrapper around ChromaDB operations."""
    
    def __init__(self, config: DatabaseConfig):
        """Initialize ChromaDB client.
        
        Args:
            config: Database configuration
        """
        self.config = config
        self.client: Optional[chromadb.Client] = None
        self.collections: Dict[str, Any] = {}
        
    def initialize(self) -> bool:
        """Initialize ChromaDB client and collections.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client = chromadb.Client()
            
            # Initialize all collections
            collection_names = [
                self.config.content_collection_name,
                self.config.history_collection_name,
                self.config.character_collection_name,
                self.config.cache_collection_name
            ]
            
            for name in collection_names:
                try:
                    collection = self.client.get_collection(name)
                    print(f"✓ Using existing {name} collection")
                except:
                    collection = self.client.create_collection(name)
                    print(f"✓ Created {name} collection")
                
                self.collections[name] = collection
            
            return True
            
        except Exception as e:
            print(f"✗ Error setting up ChromaDB: {e}")
            return False
    
    def get_collection(self, collection_type: str):
        """Get a collection by type.
        
        Args:
            collection_type: Type of collection (content, history, character, cache)
            
        Returns:
            ChromaDB collection object
        """
        collection_map = {
            'content': self.config.content_collection_name,
            'history': self.config.history_collection_name,
            'character': self.config.character_collection_name,
            'cache': self.config.cache_collection_name
        }
        
        collection_name = collection_map.get(collection_type)
        if not collection_name:
            raise ValueError(f"Unknown collection type: {collection_type}")
        
        return self.collections.get(collection_name)
    
    def add_documents(self, collection_type: str, documents: List[str], 
                     metadatas: List[Dict], ids: List[str], 
                     embeddings: Optional[List[List[float]]] = None):
        """Add documents to a collection.
        
        Args:
            collection_type: Type of collection
            documents: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of document IDs
            embeddings: Optional list of embeddings
        """
        collection = self.get_collection(collection_type)
        
        if embeddings:
            collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        else:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
    
    def query_collection(self, collection_type: str, query_embeddings: Optional[List[List[float]]] = None,
                        where: Optional[Dict] = None, n_results: int = 5,
                        include: Optional[List[str]] = None):
        """Query a collection.
        
        Args:
            collection_type: Type of collection
            query_embeddings: Query embeddings
            where: Where clause for filtering
            n_results: Number of results to return
            include: What to include in results
            
        Returns:
            Query results
        """
        collection = self.get_collection(collection_type)
        
        return collection.query(
            query_embeddings=query_embeddings,
            where=where,
            n_results=n_results,
            include=include or ["documents", "metadatas"]
        )
    
    def delete_from_collection(self, collection_type: str, where: Optional[Dict] = None,
                              ids: Optional[List[str]] = None):
        """Delete documents from a collection.
        
        Args:
            collection_type: Type of collection
            where: Where clause for filtering
            ids: Specific IDs to delete
        """
        collection = self.get_collection(collection_type)
        
        if ids:
            collection.delete(ids=ids)
        elif where:
            collection.delete(where=where)
    
    def get_documents(self, collection_type: str, ids: List[str]):
        """Get specific documents by ID.
        
        Args:
            collection_type: Type of collection
            ids: List of document IDs
            
        Returns:
            Document results
        """
        collection = self.get_collection(collection_type)
        return collection.get(ids=ids)
    
    def reset_progress_data(self) -> bool:
        """Reset all progress data (history, characters, cache) while keeping content.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            print("🔄 Resetting campaign progress...")
            
            # Clear history collection
            try:
                history_collection = self.get_collection('history')
                # Get all documents and delete them
                all_docs = history_collection.get()
                if all_docs['ids']:
                    history_collection.delete(ids=all_docs['ids'])
                print("✓ Cleared session history")
            except Exception as e:
                print(f"⚠ Warning: Could not clear history: {e}")
            
            # Clear character collection
            try:
                character_collection = self.get_collection('character')
                all_docs = character_collection.get()
                if all_docs['ids']:
                    character_collection.delete(ids=all_docs['ids'])
                print("✓ Cleared character data")
            except Exception as e:
                print(f"⚠ Warning: Could not clear characters: {e}")
            
            # Clear cache collection (this will force content to be reprocessed)
            try:
                cache_collection = self.get_collection('cache')
                all_docs = cache_collection.get()
                if all_docs['ids']:
                    cache_collection.delete(ids=all_docs['ids'])
                print("✓ Cleared file cache")
            except Exception as e:
                print(f"⚠ Warning: Could not clear cache: {e}")
            
            print("✅ Campaign progress reset complete!")
            print("   - All session history cleared")
            print("   - All character data cleared")
            print("   - File cache cleared (content will be reprocessed)")
            print("   - Campaign content preserved")
            
            return True
            
        except Exception as e:
            print(f"❌ Error resetting progress: {e}")
            return False
