"""ChromaDB client wrapper."""

import chromadb
from typing import Optional, List, Dict, Any
import sys
import os
import shutil

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
            # Use the project root directory for ChromaDB persistence
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            db_path = os.path.join(project_root, "chroma_db")
            
            # Ensure the directory exists
            os.makedirs(db_path, exist_ok=True)
            
            # Initialize ChromaDB with the specified persistence directory
            self.client = chromadb.PersistentClient(path=db_path)
            print(f"✓ ChromaDB initialized with persistence at: {db_path}")
            
            # Initialize all standardized collections
            collection_names = [
                self.config.campaign_reference_collection,
                self.config.session_history_collection,
                self.config.current_session_collection,
                self.config.character_collection,
                self.config.world_state_collection,
                self.config.cache_collection
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
            'campaign_reference': self.config.campaign_reference_collection,
            'session_history': self.config.session_history_collection,
            'current_session': self.config.current_session_collection,
            'character_data': self.config.character_collection,
            'world_state': self.config.world_state_collection,
            'file_cache': self.config.cache_collection
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
        """Reset all progress data (history, characters, cache, world state) while keeping content.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            print("🔄 Resetting campaign progress...")
            
            # Collections to clear (progress data, not campaign content)
            collections_to_clear = [
                ('current_session', 'current session data'),
                ('session_history', 'session history summaries'),
                ('character_data', 'character data'),
                ('world_state', 'world state'),
                ('file_cache', 'file cache')
            ]
            
            cleared_collections = []
            
            for collection_type, description in collections_to_clear:
                try:
                    collection = self.get_collection(collection_type)
                    if collection:
                        all_docs = collection.get()
                        if all_docs['ids']:
                            collection.delete(ids=all_docs['ids'])
                            cleared_collections.append(description)
                            print(f"✓ Cleared {description}")
                        else:
                            print(f"✓ {description} was already empty")
                except Exception as e:
                    print(f"⚠ Warning: Could not clear {description}: {e}")
            
            # Clear Sessions folder
            try:
                sessions_dir = "Sessions"
                if os.path.exists(sessions_dir):
                    shutil.rmtree(sessions_dir)
                    print("✓ Cleared session summaries folder")
                    cleared_collections.append("session summary files")
                else:
                    print("✓ No session summaries folder to clear")
            except Exception as e:
                print(f"⚠ Warning: Could not clear Sessions folder: {e}")
            
            print("\n✅ Campaign progress reset complete!")
            print("   Collections cleared:")
            for item in cleared_collections:
                print(f"   - {item}")
            print("   - Campaign content preserved (campaign_reference collection)")
            print("   - Content will be reprocessed on next startup")
            
            return True
            
        except Exception as e:
            print(f"❌ Error resetting progress: {e}")
            return False
