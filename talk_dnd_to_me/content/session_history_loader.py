# -*- coding: utf-8 -*-
"""Session history loader for embedding session summaries."""

import os
import re
from typing import List, Dict, Any

from ..database.chroma_client import ChromaClient
from ..content.embeddings import EmbeddingManager


class SessionHistoryLoader:
    """Loads and embeds session history markdown files."""

    def __init__(
        self, chroma_client: ChromaClient, embedding_manager: EmbeddingManager
    ):
        """Initialize session history loader.

        Args:
            chroma_client: ChromaDB client instance
            embedding_manager: Embedding manager instance
        """
        self.chroma_client = chroma_client
        self.embedding_manager = embedding_manager
        self.sessions_dir = "Sessions"

    def load_and_embed_sessions(self) -> bool:
        """Load all session markdown files and embed them.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.sessions_dir):
                print("✓ No Sessions directory found - no session history to load")
                return True

            session_files = self._get_session_files()
            if not session_files:
                print("✓ No session files found - no session history to load")
                return True

            print(f"📚 Loading {len(session_files)} session files...")

            # Check which files need to be processed
            files_to_process = self._get_files_to_process(session_files)

            if not files_to_process:
                print("✓ All session files already embedded")
                return True

            print(
                f"📝 Processing {len(files_to_process)} new/modified session files..."
            )

            # Process each file
            for file_path in files_to_process:
                try:
                    self._process_session_file(file_path)
                    print(f"  ✓ Processed {file_path}")
                except Exception as e:
                    print(f"  ⚠ Warning: Failed to process {file_path}: {e}")

            print("✓ Session history loading complete")
            return True

        except Exception as e:
            print(f"✗ Error loading session history: {e}")
            return False

    def embed_new_session(self, session_file_path: str) -> bool:
        """Embed a newly created session file.

        Args:
            session_file_path: Path to the session markdown file

        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(session_file_path):
                print(f"⚠ Warning: Session file not found: {session_file_path}")
                return False

            print(f"📝 Embedding new session file: {session_file_path}")
            self._process_session_file(session_file_path)
            print(f"✓ Successfully embedded {session_file_path}")
            return True

        except Exception as e:
            print(f"✗ Error embedding session file {session_file_path}: {e}")
            return False

    def _get_session_files(self) -> List[str]:
        """Get list of session markdown files.

        Returns:
            List of session file paths
        """
        session_files = []
        for filename in os.listdir(self.sessions_dir):
            if filename.startswith("session_") and filename.endswith(".md"):
                session_files.append(os.path.join(self.sessions_dir, filename))

        # Sort by session number
        session_files.sort(key=lambda x: self._extract_session_number(x))
        return session_files

    def _extract_session_number(self, file_path: str) -> int:
        """Extract session number from filename.

        Args:
            file_path: Path to session file

        Returns:
            Session number
        """
        filename = os.path.basename(file_path)
        match = re.search(r"session_(\d+)\.md", filename)
        return int(match.group(1)) if match else 0

    def _get_files_to_process(self, session_files: List[str]) -> List[str]:
        """Get list of files that need to be processed.

        Args:
            session_files: List of all session files

        Returns:
            List of files that need processing
        """
        files_to_process = []

        for file_path in session_files:
            # Check if file is already embedded by looking for it in the collection
            session_number = self._extract_session_number(file_path)
            doc_id = f"session_{session_number:03d}"

            try:
                collection = self.chroma_client.get_collection("session_history")
                existing = collection.get(ids=[doc_id])

                if not existing["ids"]:
                    # File not embedded yet
                    files_to_process.append(file_path)
                else:
                    # Check if file was modified since last embedding
                    file_mtime = os.path.getmtime(file_path)
                    embedded_time = existing["metadatas"][0].get("file_mtime", 0)

                    if file_mtime > embedded_time:
                        files_to_process.append(file_path)

            except Exception:
                # If there's any error checking, just process the file
                files_to_process.append(file_path)

        return files_to_process

    def _process_session_file(self, file_path: str):
        """Process a single session file and embed it.

        Args:
            file_path: Path to the session markdown file
        """
        # Read the file
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract metadata from the file
        metadata = self._extract_session_metadata(file_path, content)

        # Create chunks from the session content
        chunks = self._create_session_chunks(content, metadata)

        # Generate embeddings for chunks
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_manager.embed_documents(chunk_texts)

        # Prepare data for ChromaDB
        documents = chunk_texts
        metadatas = [chunk["metadata"] for chunk in chunks]
        ids = [chunk["id"] for chunk in chunks]

        # Add to session_history collection
        self.chroma_client.add_documents(
            "session_history",
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings,
        )

    def _extract_session_metadata(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract metadata from session file.

        Args:
            file_path: Path to the session file
            content: File content

        Returns:
            Metadata dictionary
        """
        session_number = self._extract_session_number(file_path)
        file_mtime = os.path.getmtime(file_path)

        # Extract basic info from content
        metadata = {
            "content_type": "session_history",
            "session_number": session_number,
            "file_path": file_path,
            "file_mtime": file_mtime,
            "session_id": f"session_{session_number:03d}",
        }

        # Extract date from content
        date_match = re.search(r"\*\*Date\*\*:\s*([^\n]+)", content)
        if date_match:
            metadata["date"] = date_match.group(1).strip()

        # Extract duration
        duration_match = re.search(r"\*\*Duration\*\*:\s*([^\n]+)", content)
        if duration_match:
            metadata["duration"] = duration_match.group(1).strip()

        # Extract total interactions
        interactions_match = re.search(r"\*\*Total Interactions\*\*:\s*(\d+)", content)
        if interactions_match:
            metadata["total_interactions"] = int(interactions_match.group(1))

        # Extract dice rolls
        dice_match = re.search(r"\*\*Dice Rolls\*\*:\s*(\d+)", content)
        if dice_match:
            metadata["dice_rolls_count"] = int(dice_match.group(1))

        # Extract character names (simple approach - look for common D&D names)
        characters = self._extract_character_names(content)
        if characters:
            metadata["characters_mentioned"] = ", ".join(
                characters
            )  # Convert list to string

        # Extract locations
        locations = self._extract_locations(content)
        if locations:
            metadata["locations_mentioned"] = ", ".join(
                locations
            )  # Convert list to string

        return metadata

    def _extract_character_names(self, content: str) -> List[str]:
        """Extract character names from content.

        Args:
            content: Session content

        Returns:
            List of character names found
        """
        # Common character names from the existing sessions
        known_characters = [
            "Rose",
            "Luvash",
            "Arabelle",
            "Meda",
            "Duras",
            "Strahd",
            "Ireena",
            "Ismark",
        ]

        found_characters = []
        for character in known_characters:
            if character in content:
                found_characters.append(character)

        return found_characters

    def _extract_locations(self, content: str) -> List[str]:
        """Extract location names from content.

        Args:
            content: Session content

        Returns:
            List of locations found
        """
        # Common locations from Curse of Strahd
        known_locations = [
            "Barovia",
            "Vallaki",
            "Krezk",
            "Ravenloft",
            "Castle Ravenloft",
            "Death House",
            "Village of Barovia",
            "Tser Pool",
            "Old Bonegrinder",
            "Wizard of Wines",
            "Yester Hill",
            "Amber Temple",
            "tavern",
            "church",
        ]

        found_locations = []
        for location in known_locations:
            if location.lower() in content.lower():
                found_locations.append(location)

        return found_locations

    def _create_session_chunks(
        self, content: str, base_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create chunks from session content.

        Args:
            content: Session markdown content
            base_metadata: Base metadata for the session

        Returns:
            List of chunk dictionaries
        """
        chunks = []
        session_number = base_metadata["session_number"]

        # Split content into sections
        sections = self._split_into_sections(content)

        for i, section in enumerate(sections):
            if not section["content"].strip():
                continue

            chunk_metadata = base_metadata.copy()
            chunk_metadata.update(
                {
                    "section_type": section["type"],
                    "section_title": section["title"],
                    "chunk_index": i,
                    "priority_level": self._determine_priority_level(section["type"]),
                }
            )

            chunk_id = f"session_{session_number:03d}_chunk_{i:02d}"

            chunks.append(
                {"id": chunk_id, "text": section["content"], "metadata": chunk_metadata}
            )

        return chunks

    def _split_into_sections(self, content: str) -> List[Dict[str, str]]:
        """Split markdown content into logical sections.

        Args:
            content: Markdown content

        Returns:
            List of section dictionaries
        """
        sections = []

        # Split by headers
        lines = content.split("\n")
        current_section = {
            "type": "overview",
            "title": "Session Summary",
            "content": "",
        }

        for line in lines:
            if line.startswith("## "):
                # Save previous section
                if current_section["content"].strip():
                    sections.append(current_section)

                # Start new section
                title = line[3:].strip()
                section_type = self._classify_section_type(title)
                current_section = {
                    "type": section_type,
                    "title": title,
                    "content": line + "\n",
                }
            else:
                current_section["content"] += line + "\n"

        # Add final section
        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def _classify_section_type(self, title: str) -> str:
        """Classify section type based on title.

        Args:
            title: Section title

        Returns:
            Section type
        """
        title_lower = title.lower()

        if "overview" in title_lower:
            return "overview"
        elif "key events" in title_lower or "events" in title_lower:
            return "key_events"
        elif "character" in title_lower and "action" in title_lower:
            return "character_actions"
        elif "story" in title_lower and "progression" in title_lower:
            return "story_progression"
        elif "dice" in title_lower or "roll" in title_lower:
            return "dice_rolls"
        elif "highlight" in title_lower:
            return "highlights"
        elif "next session" in title_lower or "setup" in title_lower:
            return "next_session"
        else:
            return "general"

    def _determine_priority_level(self, section_type: str) -> str:
        """Determine priority level for a section type.

        Args:
            section_type: Type of section

        Returns:
            Priority level (high/medium/low)
        """
        high_priority = ["key_events", "character_actions", "story_progression"]
        medium_priority = ["highlights", "next_session", "overview"]

        if section_type in high_priority:
            return "high"
        elif section_type in medium_priority:
            return "medium"
        else:
            return "low"
