"""Content loading and processing for D&D campaign materials."""

import os
import sys
from typing import List, Tuple, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from ..config.settings import ContentConfig
from ..database.chroma_client import ChromaClient
from ..database.cache_manager import CacheManager
from ..content.embeddings import EmbeddingManager
from ..utils.file_utils import find_markdown_files, get_file_hash, get_md5_hash


class ContentLoader:
    """Loads and processes campaign content with smart caching."""
    
    def __init__(self, config: ContentConfig, chroma_client: ChromaClient, 
                 cache_manager: CacheManager, embedding_manager: EmbeddingManager):
        """Initialize content loader.
        
        Args:
            config: Content configuration
            chroma_client: ChromaDB client
            cache_manager: Cache manager
            embedding_manager: Embedding manager
        """
        self.config = config
        self.chroma_client = chroma_client
        self.cache_manager = cache_manager
        self.embedding_manager = embedding_manager
    
    def load_curse_of_strahd_content(self) -> Tuple[List[Document], List[str]]:
        """Load all markdown files from Curse of Strahd with smart caching.
        
        Returns:
            Tuple of (documents to process, files that need processing)
        """
        base_path = self.config.content_directory
        
        if not os.path.exists(base_path):
            print(f"✗ Error: Path '{base_path}' does not exist")
            sys.exit(1)
        
        md_files = find_markdown_files(base_path)
        
        if not md_files:
            print(f"✗ No markdown files found in '{base_path}'")
            sys.exit(1)
        
        print(f"Found {len(md_files)} markdown files")
        
        documents = []
        files_to_process = []
        cached_chunks = []
        
        # Check which files need processing
        for file_path in md_files:
            if self.cache_manager.check_file_cache(file_path):
                print(f"✓ Using cached version of {os.path.basename(file_path)}")
                cached_chunks.extend(self.cache_manager.get_cached_chunks(file_path))
            else:
                files_to_process.append(file_path)
        
        print(f"Processing {len(files_to_process)} new/changed files, using {len(cached_chunks)} cached chunks")
        
        # Process new/changed files
        for file_path in files_to_process:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract metadata from path
                rel_path = os.path.relpath(file_path, base_path)
                path_parts = rel_path.split(os.sep)
                
                filename = os.path.basename(file_path)
                filename_no_ext = os.path.splitext(filename)[0]
                
                # Determine act and content type from path
                act = "Unknown"
                act_number = "0"
                if len(path_parts) > 0 and "Act" in path_parts[0]:
                    act = path_parts[0]
                    act_number = act.split()[1] if len(act.split()) > 1 else "0"
                
                # Create document with enhanced metadata
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": file_path,
                        "filename": filename,
                        "act": act,
                        "act_number": act_number,
                        "document_type": "curse_of_strahd",
                        "content_type": filename_no_ext,
                        "relative_path": rel_path
                    }
                )
                
                # Prepend context to content for better embedding
                enhanced_content = f"[{act}] {filename_no_ext}\n\n{content}"
                doc.page_content = enhanced_content
                
                documents.append(doc)
                print(f"✓ Loaded {filename} ({len(content)} characters)")
                
            except Exception as e:
                print(f"✗ Error loading {file_path}: {e}")
                continue
        
        return documents, files_to_process
    
    def process_documents(self, documents: List[Document], files_to_process: List[str]):
        """Process and embed new documents.
        
        Args:
            documents: List of documents to process
            files_to_process: List of file paths being processed
        """
        if not documents:
            print("No new documents to process")
            return
        
        print(f"\nSplitting {len(documents)} documents into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )

        # Split documents while preserving metadata
        all_chunks = []
        file_chunk_mapping = {}
        
        for doc in documents:
            chunks = text_splitter.split_documents([doc])
            file_path = doc.metadata['source']
            chunk_ids = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"chunk_{get_md5_hash(file_path + str(i))}"
                chunk.metadata['chunk_id'] = chunk_id
                chunk_ids.append(chunk_id)
                all_chunks.append(chunk)
            
            file_chunk_mapping[file_path] = chunk_ids

        print(f"✓ Created {len(all_chunks)} chunks from {len(documents)} documents")

        if len(all_chunks) == 0:
            print("✗ No chunks were created")
            return

        print("Generating embeddings...")
        try:
            chunk_texts = [chunk.page_content for chunk in all_chunks]
            embeddings = self.embedding_manager.embed_documents(chunk_texts)
            print(f"✓ Generated {len(embeddings)} embeddings")
        except Exception as e:
            print(f"✗ Error generating embeddings: {e}")
            return

        print("Storing chunks in ChromaDB...")
        try:
            # Prepare metadata for ChromaDB
            metadatas = []
            chunk_ids = []
            
            for chunk in all_chunks:
                metadata = {
                    "source": chunk.metadata.get("source", ""),
                    "filename": chunk.metadata.get("filename", ""),
                    "act": chunk.metadata.get("act", ""),
                    "act_number": chunk.metadata.get("act_number", ""),
                    "document_type": chunk.metadata.get("document_type", ""),
                    "content_type": chunk.metadata.get("content_type", ""),
                    "chunk_id": chunk.metadata.get("chunk_id", "")
                }
                metadatas.append(metadata)
                chunk_ids.append(chunk.metadata.get("chunk_id", ""))
            
            # Remove existing chunks for updated files
            for file_path in files_to_process:
                try:
                    self.chroma_client.delete_from_collection('content', where={"source": file_path})
                except:
                    pass
            
            # Add new chunks
            self.chroma_client.add_documents(
                'content',
                documents=chunk_texts,
                metadatas=metadatas,
                ids=chunk_ids,
                embeddings=embeddings
            )
            print(f"✓ Stored {len(all_chunks)} chunks in database")
            
            # Update file cache
            for file_path in files_to_process:
                file_hash = get_file_hash(file_path)
                if file_hash and file_path in file_chunk_mapping:
                    # Find the document metadata for this file
                    doc_metadata = next((doc.metadata for doc in documents if doc.metadata['source'] == file_path), {})
                    self.cache_manager.update_file_cache(file_path, file_hash, file_chunk_mapping[file_path], doc_metadata)
            
        except Exception as e:
            print(f"✗ Error storing in ChromaDB: {e}")
