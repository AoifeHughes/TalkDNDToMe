# -*- coding: utf-8 -*-
"""Session management for D&D campaigns."""

import json
import uuid
import os
from datetime import datetime
from typing import Dict, Any, Optional

from ..database.chroma_client import ChromaClient


class SessionManager:
    """Manages D&D session lifecycle and history tracking."""

    def __init__(self, chroma_client: ChromaClient):
        """Initialize session manager.

        Args:
            chroma_client: ChromaDB client instance
        """
        self.chroma_client = chroma_client
        self.current_session_id: Optional[str] = None

    def start_session(self) -> str:
        """Start a new D&D session.

        Returns:
            Session ID
        """
        self.current_session_id = (
            f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )

        # Log session start
        self.log_to_session(
            {
                "entry_type": "session_start",
                "content": f"Started new D&D session: {self.current_session_id}",
            }
        )

        return self.current_session_id

    def get_current_session_id(self) -> Optional[str]:
        """Get the current session ID.

        Returns:
            Current session ID or None if no session active
        """
        return self.current_session_id

    def log_to_session(self, entry_data: Dict[str, Any]):
        """Log an entry to the current session history.

        Args:
            entry_data: Entry data to log
        """
        if not self.current_session_id:
            return

        try:
            entry = {
                "session_id": self.current_session_id,
                "timestamp": datetime.now().isoformat(),
                "entry_id": str(uuid.uuid4()),
                **entry_data,
            }

            entry_id = f"entry_{entry['entry_id']}"

            self.chroma_client.add_documents(
                "current_session",
                documents=[json.dumps(entry)],
                metadatas=[
                    {
                        "session_id": self.current_session_id,
                        "entry_type": entry.get("entry_type", "unknown"),
                        "timestamp": entry["timestamp"],
                    }
                ],
                ids=[entry_id],
            )

        except Exception as e:
            print(f"Warning: Error logging to session: {e}")

    def end_session(self, llm_client=None) -> str:
        """End the current session and create a summary.

        Args:
            llm_client: Optional LLM client for generating markdown summary

        Returns:
            Session end message
        """
        if not self.current_session_id:
            return "❌ No active session to end"

        try:
            # Get all entries from current session
            collection = self.chroma_client.get_collection("current_session")
            results = collection.get(where={"session_id": self.current_session_id})

            session_entries = []
            if results["documents"]:
                session_entries = [json.loads(doc) for doc in results["documents"]]

            # Create session summary
            summary = {
                "session_id": self.current_session_id,
                "timestamp": datetime.now().isoformat(),
                "entry_type": "session_summary",
                "content": f"Session {self.current_session_id} ended",
                "session_data": {
                    "total_entries": len(session_entries),
                    "dice_rolls": [
                        entry
                        for entry in session_entries
                        if entry.get("entry_type") == "dice_roll"
                    ],
                    "key_events": [
                        entry
                        for entry in session_entries
                        if entry.get("entry_type") in ["player_input", "dm_response"]
                    ],
                },
            }

            # Save session summary to current_session collection
            summary_id = f"summary_{self.current_session_id}"
            self.chroma_client.add_documents(
                "current_session",
                documents=[json.dumps(summary)],
                metadatas=[
                    {
                        "session_id": self.current_session_id,
                        "entry_type": "session_summary",
                        "timestamp": summary["timestamp"],
                    }
                ],
                ids=[summary_id],
            )

            session_id = self.current_session_id

            # Generate and save markdown summary if LLM client is provided
            markdown_file = ""
            if llm_client:
                try:
                    print("\n📝 Generating session summary...")
                    markdown_content = self.generate_markdown_summary(
                        session_entries, llm_client
                    )
                    markdown_file = self.save_markdown_summary(
                        session_id, markdown_content
                    )
                    if markdown_file:
                        print(f"✓ Session summary saved to: {markdown_file}")
                        print(
                            "📝 Session summary ready for embedding on next system startup"
                        )
                    else:
                        print("⚠ Warning: Failed to save markdown summary file")
                except Exception as e:
                    print(f"⚠ Warning: Could not generate markdown summary: {e}")
                    import traceback

                    traceback.print_exc()
            else:
                print(
                    "⚠ Warning: No LLM client provided for markdown summary generation"
                )

            self.current_session_id = None  # Clear current session

            result_msg = f"✓ Session {session_id} ended. Summary saved with {len(session_entries)} entries."
            if markdown_file:
                result_msg += f"\n📄 Detailed summary: {markdown_file}"

            return result_msg

        except Exception as e:
            return f"❌ Error ending session: {e}"

    def log_player_input(self, user_input: str):
        """Log player input to session history.

        Args:
            user_input: Player's input text
        """
        self.log_to_session({"entry_type": "player_input", "content": user_input})

    def log_dm_response(self, dm_response: str):
        """Log DM response to session history.

        Args:
            dm_response: DM's response text
        """
        self.log_to_session({"entry_type": "dm_response", "content": dm_response})

    def get_previous_sessions_summary(self) -> Optional[str]:
        """Get a summary of previous sessions.

        Returns:
            Summary text of previous sessions or None if no previous sessions
        """
        try:
            # First check if there are any documents in the session_history collection
            collection = self.chroma_client.get_collection("session_history")
            if collection.count() == 0:
                return None

            # Get session summaries from session_history collection
            results = collection.get(where={"content_type": "session_history"})

            if not results["documents"]:
                return None

            session_summaries = []
            for doc in results["documents"]:
                try:
                    session_data = json.loads(doc)
                    session_id = session_data.get("session_id", "Unknown")
                    timestamp = session_data.get("timestamp", "Unknown time")
                    total_entries = session_data.get("session_data", {}).get(
                        "total_entries", 0
                    )

                    # Format timestamp for readability
                    try:
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        formatted_time = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        formatted_time = timestamp

                    session_summaries.append(
                        f"• {session_id} ({formatted_time}) - {total_entries} interactions"
                    )
                except Exception:
                    continue

            if not session_summaries:
                return None

            summary_text = "Previous Sessions:\n" + "\n".join(
                session_summaries[-5:]
            )  # Show last 5 sessions
            return summary_text

        except Exception as e:
            print(f"Warning: Error retrieving previous sessions: {e}")
            return None

    def get_last_session_events(self) -> Optional[str]:
        """Get key events from the most recent session.

        Returns:
            Summary of key events from last session or None if no previous sessions
        """
        try:
            # First check if there are any documents in the session_history collection
            collection = self.chroma_client.get_collection("session_history")
            if collection.count() == 0:
                return None

            # Get the most recent session summary
            results = collection.get(where={"content_type": "session_history"})

            if not results["documents"]:
                return None

            # Get the most recent session (last in the list)
            latest_session = json.loads(results["documents"][-1])
            session_id = latest_session.get("session_id")

            if not session_id:
                return None

            # Get the last few interactions from that session
            session_results = collection.get(
                where={"session_id": session_id, "entry_type": "dm_response"}
            )

            if not session_results["documents"]:
                return None

            events = []
            for doc in session_results["documents"][-3:]:
                try:
                    event_data = json.loads(doc)
                    content = event_data.get("content", "")
                    # Truncate long responses
                    if len(content) > 200:
                        content = content[:200] + "..."
                    events.append(content)
                except Exception:
                    continue

            if events:
                return "\n\nKey events from your last session:\n" + "\n\n".join(
                    reversed(events[-2:])
                )  # Show last 2 events

            return None

        except Exception as e:
            print(f"Warning: Error retrieving last session events: {e}")
            return None

    def generate_markdown_summary(self, session_entries: list, llm_client) -> str:
        """Generate a markdown summary of the session using the LLM.

        Args:
            session_entries: List of session entries
            llm_client: LLM client for generating summary

        Returns:
            Markdown formatted session summary
        """
        try:
            print("  - Validating LLM client...")
            # Validate LLM client is properly initialized
            if (
                not llm_client
                or not hasattr(llm_client, "client")
                or not llm_client.client
            ):
                raise ValueError("LLM client is not properly initialized")

            print("  - Processing session data...")
            # Prepare session data for the LLM
            player_inputs = [
                entry
                for entry in session_entries
                if entry.get("entry_type") == "player_input"
            ]
            dm_responses = [
                entry
                for entry in session_entries
                if entry.get("entry_type") == "dm_response"
            ]
            dice_rolls = [
                entry
                for entry in session_entries
                if entry.get("entry_type") == "dice_roll"
            ]

            print(
                f"  - Found {len(player_inputs)} player inputs, {len(dm_responses)} DM responses, {len(dice_rolls)} dice rolls"
            )

            # Create a conversation flow
            conversation_flow = []
            for entry in sorted(session_entries, key=lambda x: x.get("timestamp", "")):
                if entry.get("entry_type") in ["player_input", "dm_response"]:
                    conversation_flow.append(
                        {
                            "type": entry.get("entry_type"),
                            "content": entry.get("content", ""),
                            "timestamp": entry.get("timestamp", ""),
                        }
                    )

            print(
                f"  - Created conversation flow with {len(conversation_flow)} entries"
            )

            # Create prompt for LLM to generate summary
            prompt = f"""Please create a detailed markdown session summary for this D&D session. Use the following template and fill it out based on the session data provided:

# Session Summary

## Session Overview
- **Date**: [Extract from timestamps]
- **Duration**: [Estimate based on timestamps]
- **Total Interactions**: {len(conversation_flow)}
- **Dice Rolls**: {len(dice_rolls)}

## Key Events
[Summarize the main story beats and important moments from the session]

## Character Actions
[Highlight significant player actions and decisions]

## Story Progression
[Describe how the story advanced during this session]

## Notable Dice Rolls
[Mention any critical successes, failures, or important rolls]

## Session Highlights
[List 3-5 memorable moments from the session]

## Next Session Setup
[Brief note about where the story left off and what might happen next]

---

Session Data:

Conversation Flow:
{json.dumps(conversation_flow[:20], indent=2)}  # Limit to first 20 exchanges

Dice Rolls:
{json.dumps(dice_rolls, indent=2)}

Please generate a comprehensive but concise summary following the template above."""

            print("  - Generating summary with LLM (non-streaming mode)...")
            # Generate summary using LLM with explicit non-streaming mode
            messages = [{"role": "user", "content": prompt}]

            summary_content, response, was_streamed = (
                llm_client.chat_completion_with_streaming(
                    messages=messages,
                    use_streaming=False,  # Explicitly disable streaming for summary generation
                )
            )

            if not summary_content or summary_content.strip() == "":
                print("  - Warning: LLM returned empty content, using fallback")
                return self._create_fallback_summary(session_entries)

            print(
                f"  - Successfully generated summary ({len(summary_content)} characters)"
            )
            return summary_content

        except ValueError as e:
            print(f"  - Validation error: {e}")
            return self._create_fallback_summary(session_entries)
        except Exception as e:
            print(f"  - Error generating markdown summary: {e}")
            print(f"  - Error type: {type(e).__name__}")
            import traceback

            print(f"  - Full traceback: {traceback.format_exc()}")
            return self._create_fallback_summary(session_entries)

    def _create_fallback_summary(self, session_entries: list) -> str:
        """Create a basic fallback summary when LLM generation fails.

        Args:
            session_entries: List of session entries

        Returns:
            Basic markdown summary
        """
        try:
            # Extract basic statistics
            player_inputs = [
                entry
                for entry in session_entries
                if entry.get("entry_type") == "player_input"
            ]
            dm_responses = [
                entry
                for entry in session_entries
                if entry.get("entry_type") == "dm_response"
            ]
            dice_rolls = [
                entry
                for entry in session_entries
                if entry.get("entry_type") == "dice_roll"
            ]

            # Get session timing
            timestamps = [
                entry.get("timestamp", "")
                for entry in session_entries
                if entry.get("timestamp")
            ]
            start_time = min(timestamps) if timestamps else "Unknown"
            end_time = max(timestamps) if timestamps else "Unknown"

            # Format timestamps
            try:
                if start_time != "Unknown":
                    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    start_formatted = start_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    start_formatted = "Unknown"

                if end_time != "Unknown":
                    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    end_formatted = end_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    end_formatted = "Unknown"
            except Exception:
                start_formatted = start_time
                end_formatted = end_time

            # Create basic summary
            summary = f"""# Session Summary

## Session Overview
- **Start Time**: {start_formatted}
- **End Time**: {end_formatted}
- **Total Interactions**: {len(player_inputs) + len(dm_responses)}
- **Player Actions**: {len(player_inputs)}
- **DM Responses**: {len(dm_responses)}
- **Dice Rolls**: {len(dice_rolls)}

## Session Notes
This is an automatically generated summary. The detailed AI-generated summary could not be created.

## Key Statistics
- Total session entries: {len(session_entries)}
- Player engagement: {len(player_inputs)} actions taken
- Dice rolls performed: {len(dice_rolls)}

## Raw Session Data
*Note: This fallback summary contains basic statistics only. For detailed narrative summaries, ensure the LLM client is properly configured.*
"""

            # Add some recent player actions if available
            if player_inputs:
                summary += "\n## Recent Player Actions\n"
                recent_actions = player_inputs[-3:]  # Last 3 actions
                for i, action in enumerate(recent_actions, 1):
                    content = action.get("content", "")[:100]  # Truncate to 100 chars
                    if len(action.get("content", "")) > 100:
                        content += "..."
                    summary += f"{i}. {content}\n"

            return summary

        except Exception as e:
            return f"""# Session Summary

## Error
Unable to generate session summary due to error: {e}

## Basic Info
- Total entries: {len(session_entries) if session_entries else 0}
- Summary generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    def save_markdown_summary(self, session_id: str, markdown_content: str) -> str:
        """Save markdown summary to Sessions folder with sequential numbering.

        Args:
            session_id: Session ID
            markdown_content: Markdown content to save

        Returns:
            Path to saved file
        """
        try:
            print("  - Creating Sessions directory...")
            # Create Sessions directory if it doesn't exist
            sessions_dir = "Sessions"
            os.makedirs(sessions_dir, exist_ok=True)

            print("  - Finding next session number...")
            # Find the next sequential number
            existing_files = [
                f
                for f in os.listdir(sessions_dir)
                if f.startswith("session_") and f.endswith(".md")
            ]
            session_numbers = []

            for filename in existing_files:
                try:
                    # Extract number from filename like "session_001.md"
                    number_part = filename.replace("session_", "").replace(".md", "")
                    session_numbers.append(int(number_part))
                except ValueError:
                    continue

            # Get next number
            next_number = max(session_numbers, default=0) + 1
            print(f"  - Using session number: {next_number:03d}")

            # Create filename with zero-padded number
            filename = f"session_{next_number:03d}.md"
            filepath = os.path.join(sessions_dir, filename)

            print(f"  - Writing summary to: {filepath}")
            # Validate markdown content
            if not markdown_content or markdown_content.strip() == "":
                print("  - Warning: Empty markdown content, creating minimal summary")
                markdown_content = f"# Session Summary\n\nSession {session_id} completed but no detailed summary was generated.\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            # Write the markdown file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            print(
                f"  - Successfully saved {len(markdown_content)} characters to {filepath}"
            )
            return filepath

        except PermissionError as e:
            print(f"  - Permission error saving markdown summary: {e}")
            print(f"  - Check write permissions for directory: {os.getcwd()}")
            return ""
        except OSError as e:
            print(f"  - File system error saving markdown summary: {e}")
            return ""
        except Exception as e:
            print(f"  - Unexpected error saving markdown summary: {e}")
            print(f"  - Error type: {type(e).__name__}")
            import traceback

            print(f"  - Full traceback: {traceback.format_exc()}")
            return ""
