"""File cache management for content loading."""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from .chroma_client import ChromaClient
from ..utils.file_utils import get_file_hash, get_md5_hash


class CacheManager:
    """Manages file caching for content loading."""
    
    def __init__(self, chroma_client: ChromaClient):
        """Initialize cache manager.
        
        Args:
            chroma_client: ChromaDB client instance
        """
        self.chroma_client = chroma_client
    
    def check_file_cache(self, file_path: str) -> bool:
        """Check if file is cached and unchanged.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file is cached and unchanged, False otherwise
        """
        try:
            current_hash = get_file_hash(file_path)
            if not current_hash:
                return False
            
            cache_id = f"cache_{get_md5_hash(file_path)}"
            results = self.chroma_client.get_documents('file_cache', [cache_id])
            
            if results['documents'] and len(results['documents']) > 0:
                cached_data = json.loads(results['documents'][0])
                return cached_data.get('file_hash') == current_hash
            return False
            
        except Exception as e:
            print(f"Error checking cache for {file_path}: {e}")
            return False
    
    def update_file_cache(self, file_path: str, file_hash: str, 
                         chunk_ids: List[str], metadata: Dict[str, Any]):
        """Update file cache with new hash and chunk references.
        
        Args:
            file_path: Path to the file
            file_hash: SHA256 hash of the file
            chunk_ids: List of chunk IDs for this file
            metadata: File metadata
        """
        try:
            cache_data = {
                "file_path": file_path,
                "file_hash": file_hash,
                "last_modified": datetime.now().isoformat(),
                "chunk_ids": chunk_ids,
                "metadata": metadata
            }
            
            # Remove existing cache entry
            try:
                self.chroma_client.delete_from_collection('file_cache', where={"file_path": file_path})
            except:
                pass
            
            # Add new cache entry
            cache_id = f"cache_{get_md5_hash(file_path)}"
            self.chroma_client.add_documents(
                'file_cache',
                documents=[json.dumps(cache_data)],
                metadatas=[{"file_path": file_path, "last_modified": cache_data["last_modified"]}],
                ids=[cache_id]
            )
            print(f"✓ Updated cache for {file_path.split('/')[-1]}")
            
        except Exception as e:
            print(f"Error updating cache for {file_path}: {e}")
    
    def get_cached_chunks(self, file_path: str) -> List[str]:
        """Get cached chunk IDs for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of cached chunk IDs
        """
        try:
            results = self.chroma_client.query_collection(
                'file_cache',
                where={"file_path": file_path},
                n_results=1
            )
            
            if results['documents'] and len(results['documents'][0]) > 0:
                cached_data = json.loads(results['documents'][0][0])
                return cached_data.get('chunk_ids', [])
            return []
            
        except Exception as e:
            print(f"Warning: Error loading cached chunks for {file_path}: {e}")
            return []
