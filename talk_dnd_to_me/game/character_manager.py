# -*- coding: utf-8 -*-
"""Character management for tracking player and NPC information."""

import json
from datetime import datetime
from typing import Dict, Any, Optional

from ..database.chroma_client import ChromaClient


class CharacterManager:
    """Manages character information and updates."""

    def __init__(self, chroma_client: ChromaClient):
        """Initialize character manager.

        Args:
            chroma_client: ChromaDB client instance
        """
        self.chroma_client = chroma_client
        self.current_session_id: Optional[str] = None

    def set_session_id(self, session_id: str):
        """Set the current session ID.

        Args:
            session_id: Current session identifier
        """
        self.current_session_id = session_id

    def update_character(
        self, character_name: str, update_type: str, update_data: Dict[str, Any]
    ) -> str:
        """Update character information.

        Args:
            character_name: Name of the character to update
            update_type: Type of update (hp, inventory, status, relationship, location)
            update_data: Data to update

        Returns:
            Success or error message
        """
        try:
            character_id = f"char_{character_name.lower().replace(' ', '_')}"

            # Try to get existing character
            results = self.chroma_client.query_collection(
                "character", where={"character_id": character_id}, n_results=1
            )

            if results["documents"] and len(results["documents"][0]) > 0:
                character_data = json.loads(results["documents"][0][0])
            else:
                # Create new character
                character_data = {
                    "character_id": character_id,
                    "name": character_name,
                    "character_type": "unknown",
                    "last_updated": datetime.now().isoformat(),
                    "session_last_seen": self.current_session_id,
                    "attributes": {},
                    "inventory": {},
                    "personality": {},
                    "relationships": {},
                    "campaign_data": {},
                    "change_log": [],
                }

            # Apply update based on type
            if update_type == "hp":
                if "attributes" not in character_data:
                    character_data["attributes"] = {}
                if "hit_points" not in character_data["attributes"]:
                    character_data["attributes"]["hit_points"] = {
                        "current": 0,
                        "maximum": 0,
                    }

                if "current" in update_data:
                    character_data["attributes"]["hit_points"]["current"] = update_data[
                        "current"
                    ]
                if "maximum" in update_data:
                    character_data["attributes"]["hit_points"]["maximum"] = update_data[
                        "maximum"
                    ]

            elif update_type == "inventory":
                character_data["inventory"].update(update_data)

            elif update_type == "status":
                character_data["campaign_data"].update(update_data)

            elif update_type == "relationship":
                character_data["relationships"].update(update_data)

            elif update_type == "location":
                if "campaign_data" not in character_data:
                    character_data["campaign_data"] = {}
                character_data["campaign_data"]["current_location"] = update_data.get(
                    "location", ""
                )

            # Add to change log
            character_data["change_log"].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "change": f"Updated {update_type}: {update_data}",
                    "session": self.current_session_id,
                }
            )

            character_data["last_updated"] = datetime.now().isoformat()
            character_data["session_last_seen"] = self.current_session_id

            # Save updated character
            try:
                self.chroma_client.delete_from_collection(
                    "character", where={"character_id": character_id}
                )
            except Exception:
                pass

            self.chroma_client.add_documents(
                "character",
                documents=[json.dumps(character_data)],
                metadatas=[
                    {
                        "character_id": character_id,
                        "character_name": character_name,
                        "character_type": character_data.get(
                            "character_type", "unknown"
                        ),
                        "last_updated": character_data["last_updated"],
                    }
                ],
                ids=[character_id],
            )

            return f"✓ Updated {character_name}: {update_type} = {update_data}"

        except Exception as e:
            return f"❌ Error updating character {character_name}: {e}"

    def get_character_info(self, character_name: str) -> str:
        """Retrieve character information.

        Args:
            character_name: Name of the character to look up

        Returns:
            Formatted character information or error message
        """
        try:
            character_id = f"char_{character_name.lower().replace(' ', '_')}"

            results = self.chroma_client.query_collection(
                "character", where={"character_id": character_id}, n_results=1
            )

            if results["documents"] and len(results["documents"][0]) > 0:
                character_data = json.loads(results["documents"][0][0])

                # Format character info for display
                info = f"📋 **{character_data['name']}**\n"

                if "attributes" in character_data and character_data["attributes"]:
                    info += "**Stats:** "
                    attrs = character_data["attributes"]
                    if "hit_points" in attrs:
                        hp = attrs["hit_points"]
                        info += (
                            f"HP: {hp.get('current', '?')}/{hp.get('maximum', '?')} "
                        )
                    if "armor_class" in attrs:
                        info += f"AC: {attrs['armor_class']} "
                    if "level" in attrs:
                        info += f"Level: {attrs['level']} "
                    info += "\n"

                if (
                    "campaign_data" in character_data
                    and "current_location" in character_data["campaign_data"]
                ):
                    info += f"**Location:** {character_data['campaign_data']['current_location']}\n"

                if "inventory" in character_data and character_data["inventory"]:
                    info += f"**Inventory:** {character_data['inventory']}\n"

                return info
            else:
                return f"❌ Character '{character_name}' not found"

        except Exception as e:
            return f"❌ Error retrieving character {character_name}: {e}"
