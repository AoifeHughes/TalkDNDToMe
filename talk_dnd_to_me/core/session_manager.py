"""Session management for D&D campaigns."""

import json
import uuid
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
        self.current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Log session start
        self.log_to_session({
            "entry_type": "session_start",
            "content": f"Started new D&D session: {self.current_session_id}"
        })
        
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
                **entry_data
            }
            
            entry_id = f"entry_{entry['entry_id']}"
            
            self.chroma_client.add_documents(
                'history',
                documents=[json.dumps(entry)],
                metadatas=[{
                    "session_id": self.current_session_id,
                    "entry_type": entry.get("entry_type", "unknown"),
                    "timestamp": entry["timestamp"]
                }],
                ids=[entry_id]
            )
            
        except Exception as e:
            print(f"Warning: Error logging to session: {e}")
    
    def end_session(self) -> str:
        """End the current session and create a summary.
        
        Returns:
            Session end message
        """
        if not self.current_session_id:
            return "❌ No active session to end"
        
        try:
            # Get all entries from current session
            results = self.chroma_client.query_collection(
                'history',
                where={"session_id": self.current_session_id},
                n_results=1000  # Get all entries
            )
            
            session_entries = []
            if results['documents'] and results['documents'][0]:
                session_entries = [json.loads(doc) for doc in results['documents'][0]]
            
            # Create session summary
            summary = {
                "session_id": self.current_session_id,
                "timestamp": datetime.now().isoformat(),
                "entry_type": "session_summary",
                "content": f"Session {self.current_session_id} ended",
                "session_data": {
                    "total_entries": len(session_entries),
                    "dice_rolls": [entry for entry in session_entries if entry.get("entry_type") == "dice_roll"],
                    "key_events": [entry for entry in session_entries if entry.get("entry_type") in ["player_input", "dm_response"]]
                }
            }
            
            # Save session summary
            summary_id = f"summary_{self.current_session_id}"
            self.chroma_client.add_documents(
                'history',
                documents=[json.dumps(summary)],
                metadatas=[{
                    "session_id": self.current_session_id,
                    "entry_type": "session_summary",
                    "timestamp": summary["timestamp"]
                }],
                ids=[summary_id]
            )
            
            session_id = self.current_session_id
            self.current_session_id = None  # Clear current session
            
            return f"✓ Session {session_id} ended. Summary saved with {len(session_entries)} entries."
            
        except Exception as e:
            return f"❌ Error ending session: {e}"
    
    def log_player_input(self, user_input: str):
        """Log player input to session history.
        
        Args:
            user_input: Player's input text
        """
        self.log_to_session({
            "entry_type": "player_input",
            "content": user_input
        })
    
    def log_dm_response(self, dm_response: str):
        """Log DM response to session history.
        
        Args:
            dm_response: DM's response text
        """
        self.log_to_session({
            "entry_type": "dm_response",
            "content": dm_response
        })
    
    def get_previous_sessions_summary(self) -> Optional[str]:
        """Get a summary of previous sessions.
        
        Returns:
            Summary text of previous sessions or None if no previous sessions
        """
        try:
            # First check if there are any documents in the collection
            collection = self.chroma_client.get_collection('history')
            if collection.count() == 0:
                return None
            
            # Query for session summaries
            results = self.chroma_client.query_collection(
                'history',
                where={"entry_type": "session_summary"},
                n_results=10  # Get last 10 sessions
            )
            
            if not results['documents'] or not results['documents'][0]:
                return None
            
            session_summaries = []
            for doc in results['documents'][0]:
                try:
                    session_data = json.loads(doc)
                    session_id = session_data.get('session_id', 'Unknown')
                    timestamp = session_data.get('timestamp', 'Unknown time')
                    total_entries = session_data.get('session_data', {}).get('total_entries', 0)
                    
                    # Format timestamp for readability
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        formatted_time = timestamp
                    
                    session_summaries.append(f"• {session_id} ({formatted_time}) - {total_entries} interactions")
                except Exception as e:
                    continue
            
            if not session_summaries:
                return None
            
            summary_text = "Previous Sessions:\n" + "\n".join(session_summaries[-5:])  # Show last 5 sessions
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
            # First check if there are any documents in the collection
            collection = self.chroma_client.get_collection('history')
            if collection.count() == 0:
                return None
            
            # Get the most recent session summary
            results = self.chroma_client.query_collection(
                'history',
                where={"entry_type": "session_summary"},
                n_results=1
            )
            
            if not results['documents'] or not results['documents'][0]:
                return None
            
            latest_session = json.loads(results['documents'][0][0])
            session_id = latest_session.get('session_id')
            
            if not session_id:
                return None
            
            # Get the last few interactions from that session
            session_results = self.chroma_client.query_collection(
                'history',
                where={
                    "session_id": session_id,
                    "entry_type": "dm_response"
                },
                n_results=3  # Get last 3 DM responses
            )
            
            if not session_results['documents'] or not session_results['documents'][0]:
                return None
            
            events = []
            for doc in session_results['documents'][0]:
                try:
                    event_data = json.loads(doc)
                    content = event_data.get('content', '')
                    # Truncate long responses
                    if len(content) > 200:
                        content = content[:200] + "..."
                    events.append(content)
                except:
                    continue
            
            if events:
                return "\n\nKey events from your last session:\n" + "\n\n".join(reversed(events[-2:]))  # Show last 2 events
            
            return None
            
        except Exception as e:
            print(f"Warning: Error retrieving last session events: {e}")
            return None
