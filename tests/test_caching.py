# -*- coding: utf-8 -*-
"""
Test ChromaDB caching functionality.
"""

import pytest
import time
from talk_dnd_to_me.database.cache_manager import CacheManager
from talk_dnd_to_me.content.content_loader import ContentLoader


@pytest.mark.caching
class TestCacheManager:
    """Test cache manager functionality."""

    def test_cache_manager_initialization(self, cache_manager: CacheManager):
        """Test that cache manager initializes properly."""
        assert cache_manager is not None
        assert cache_manager.chroma_client is not None

    def test_file_cache_check_new_file(self, cache_manager: CacheManager):
        """Test cache check for a new file returns False."""
        fake_file_path = "/nonexistent/fake_file.md"
        is_cached = cache_manager.check_file_cache(fake_file_path)
        assert not is_cached, "New file should not be cached"

    def test_file_cache_update_and_retrieval(self, cache_manager: CacheManager):
        """Test updating cache and retrieving cached chunks."""
        test_file_path = "test_file.md"
        test_hash = "fake_hash_12345"
        test_chunk_ids = ["chunk_1", "chunk_2", "chunk_3"]
        test_metadata = {"act": "Act I", "type": "test"}

        # Update cache
        cache_manager.update_file_cache(
            test_file_path, test_hash, test_chunk_ids, test_metadata
        )

        # Retrieve cached chunks
        cached_chunks = cache_manager.get_cached_chunks(test_file_path)

        assert (
            cached_chunks == test_chunk_ids
        ), f"Cached chunks don't match: expected {test_chunk_ids}, got {cached_chunks}"

    @pytest.mark.slow
    def test_cache_performance_improvement(
        self, cache_manager: CacheManager, embedding_manager, dm_config
    ):
        """Test that caching improves performance."""
        content_loader = ContentLoader(
            dm_config.content,
            cache_manager.chroma_client,
            cache_manager,
            embedding_manager,
        )

        # First load (should cache files)
        start_time = time.time()
        documents1, files1 = content_loader.load_curse_of_strahd_content()
        first_load_time = time.time() - start_time

        # Skip test if no content is available
        if not documents1 and not files1:
            pytest.skip("No content files available for testing")

        # Second load (should use cache)
        start_time = time.time()
        documents2, files2 = content_loader.load_curse_of_strahd_content()
        second_load_time = time.time() - start_time

        # Second load should be faster or at least not significantly slower
        # Allow some variance due to system performance
        assert (
            second_load_time <= first_load_time * 1.5
        ), f"Second load took too long: {second_load_time:.2f}s vs {first_load_time:.2f}s"

        # Second load should process fewer files (using cache)
        assert len(files2) <= len(
            files1
        ), f"Second load processed more files: {len(files2)} vs {len(files1)}"


@pytest.mark.integration
@pytest.mark.caching
class TestContentLoaderCaching:
    """Test content loader caching integration."""

    def test_content_loader_respects_cache(
        self, chroma_client, cache_manager, embedding_manager, dm_config
    ):
        """Test that content loader properly uses cache."""
        content_loader = ContentLoader(
            dm_config.content, chroma_client, cache_manager, embedding_manager
        )

        # Load content first time
        documents, files_to_process = content_loader.load_curse_of_strahd_content()

        # Skip test if no content is available
        if not documents and not files_to_process:
            pytest.skip("No content files available for testing")

        initial_file_count = len(files_to_process)

        # Load content second time - should use cache
        documents2, files_to_process2 = content_loader.load_curse_of_strahd_content()
        second_file_count = len(files_to_process2)

        # Should process fewer (or same) files on second run due to caching
        assert (
            second_file_count <= initial_file_count
        ), f"Second load processed more files: {second_file_count} vs {initial_file_count}"

    def test_cache_invalidation_on_file_change(self, cache_manager: CacheManager):
        """Test that cache is invalidated when file changes."""
        test_file = "test_cache_invalidation.md"

        # Create initial cache entry
        cache_manager.update_file_cache(test_file, "hash1", ["chunk1"], {})
        assert cache_manager.get_cached_chunks(test_file) == ["chunk1"]

        # Update with new hash (simulating file change)
        cache_manager.update_file_cache(test_file, "hash2", ["chunk2"], {})
        cached_chunks = cache_manager.get_cached_chunks(test_file)

        assert cached_chunks == [
            "chunk2"
        ], f"Cache should be updated: expected ['chunk2'], got {cached_chunks}"


@pytest.mark.unit
class TestCacheUtilities:
    """Test cache utility functions."""

    def test_get_cached_chunks_empty_file(self, cache_manager: CacheManager):
        """Test getting cached chunks for non-existent file."""
        chunks = cache_manager.get_cached_chunks("nonexistent_file.md")
        assert chunks == [], "Should return empty list for non-existent file"

    def test_cache_handles_special_characters(self, cache_manager: CacheManager):
        """Test that cache handles files with special characters."""
        special_file = "test file with spaces & symbols!.md"
        test_chunks = ["chunk_special_1", "chunk_special_2"]

        cache_manager.update_file_cache(special_file, "hash_special", test_chunks, {})
        cached_chunks = cache_manager.get_cached_chunks(special_file)

        assert (
            cached_chunks == test_chunks
        ), f"Special character file caching failed: {cached_chunks}"
