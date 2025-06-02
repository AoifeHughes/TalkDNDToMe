# -*- coding: utf-8 -*-
"""
Test session management functionality.
"""

import pytest
from talk_dnd_to_me.core.session_manager import SessionManager


@pytest.mark.integration
class TestSessionManager:
    """Test session management functionality."""

    def test_session_manager_initialization(self, chroma_client):
        """Test session manager initialization."""
        session_manager = SessionManager(chroma_client)
        assert session_manager is not None
        assert session_manager.current_session_id is None

    def test_new_session_creation(self, chroma_client):
        """Test creating a new session."""
        session_manager = SessionManager(chroma_client)

        # Start a new session
        session_id = session_manager.start_session()

        # Should get a valid session ID
        assert session_id is not None
        assert session_id.startswith("session_")
        assert session_manager.get_current_session_id() == session_id

    def test_session_id_generation(self, chroma_client):
        """Test that session IDs are generated properly."""
        session_manager = SessionManager(chroma_client)

        # Generate a few session IDs
        session_id1 = session_manager.start_session()
        session_manager2 = SessionManager(chroma_client)  # New instance
        session_id2 = session_manager2.start_session()

        # Should be different
        assert session_id1 != session_id2

        # Should follow expected format (session_YYYYMMDD_HHMMSS_XXXXXXXX)
        assert session_id1.startswith("session_")
        assert len(session_id1) == len("session_20250101_123456_12345678")

        # Should be valid session ID format
        import re

        pattern = r"session_\d{8}_\d{6}_[a-f0-9]{8}"
        assert re.match(
            pattern, session_id1
        ), f"Invalid session ID format: {session_id1}"


@pytest.mark.unit
class TestSessionUtilities:
    """Test session utility functions."""

    def test_session_id_format(self, chroma_client):
        """Test session ID format validation."""
        session_manager = SessionManager(chroma_client)
        session_id = session_manager.start_session()

        # Validate format
        parts = session_id.split("_")
        assert len(parts) == 4, f"Session ID should have 4 parts: {session_id}"
        assert parts[0] == "session", f"Should start with 'session': {session_id}"

        # Date part should be 8 digits
        assert len(parts[1]) == 8, f"Date part should be 8 digits: {parts[1]}"
        assert parts[1].isdigit(), f"Date part should be numeric: {parts[1]}"

        # Time part should be 6 digits
        assert len(parts[2]) == 6, f"Time part should be 6 digits: {parts[2]}"
        assert parts[2].isdigit(), f"Time part should be numeric: {parts[2]}"

        # UUID part should be 8 hex characters
        assert len(parts[3]) == 8, f"UUID part should be 8 characters: {parts[3]}"
        assert all(
            c in "0123456789abcdef" for c in parts[3]
        ), f"UUID part should be hex: {parts[3]}"
