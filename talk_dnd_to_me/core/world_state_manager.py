"""World state management for tracking story progression and context."""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict

from ..database.chroma_client import ChromaClient
from ..content.embeddings import EmbeddingManager


@dataclass
class WorldState:
    """Represents the current state of the game world."""
    # Story progression
    current_act: str = "Act I"
    current_arc: str = "Arc A"
    current_location: str = "Unknown"
    last_significant_location: str = "Unknown"
    
    # Quest tracking
    active_quests: List[str] = None
    completed_quests: List[str] = None
    failed_quests: List[str] = None
    
    # Character relationships and reputation
    character_relationships: Dict[str, str] = None  # character_name -> relationship_status
    faction_reputation: Dict[str, int] = None       # faction_name -> reputation_score
    
    # Story flags and triggers
    story_flags: Dict[str, bool] = None             # flag_name -> is_active
    important_events: List[str] = None              # List of significant events that occurred
    
    # Session tracking
    current_session_number: int = 0
    total_sessions_played: int = 0
    last_updated: str = ""
    
    def __post_init__(self):
        """Initialize empty collections if None."""
        if self.active_quests is None:
            self.active_quests = []
        if self.completed_quests is None:
            self.completed_quests = []
        if self.failed_quests is None:
            self.failed_quests = []
        if self.character_relationships is None:
            self.character_relationships = {}
        if self.faction_reputation is None:
            self.faction_reputation = {}
        if self.story_flags is None:
            self.story_flags = {}
        if self.important_events is None:
            self.important_events = []
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()


class WorldStateManager:
    """Manages the current state of the game world and story progression."""
    
    def __init__(self, chroma_client: ChromaClient, embedding_manager: EmbeddingManager):
        """Initialize world state manager.
        
        Args:
            chroma_client: ChromaDB client instance
            embedding_manager: Embedding manager instance
        """
        self.chroma_client = chroma_client
        self.embedding_manager = embedding_manager
        self.current_state: Optional[WorldState] = None
        self._state_id = "current_world_state"
    
    def load_world_state(self) -> WorldState:
        """Load the current world state from the database.
        
        Returns:
            Current world state
        """
        try:
            collection = self.chroma_client.get_collection('world_state')
            results = collection.get(ids=[self._state_id])
            
            if results['documents'] and results['documents'][0]:
                state_data = json.loads(results['documents'][0])
                self.current_state = WorldState(**state_data)
                print(f"✓ Loaded world state: {self.current_state.current_location} ({self.current_state.current_act})")
            else:
                # Create new world state
                self.current_state = WorldState()
                self.save_world_state()
                print("✓ Created new world state")
                
        except Exception as e:
            print(f"Warning: Error loading world state, creating new: {e}")
            self.current_state = WorldState()
            self.save_world_state()
        
        return self.current_state
    
    def save_world_state(self):
        """Save the current world state to the database."""
        if not self.current_state:
            return
        
        try:
            self.current_state.last_updated = datetime.now().isoformat()
            state_json = json.dumps(asdict(self.current_state))
            
            # Create embedding for the world state (for semantic search)
            state_summary = self._create_state_summary()
            embedding = self.embedding_manager.embed_query(state_summary)
            
            # Save to database
            self.chroma_client.add_documents(
                'world_state',
                documents=[state_json],
                metadatas=[{
                    'state_id': self._state_id,
                    'current_act': self.current_state.current_act,
                    'current_location': self.current_state.current_location,
                    'session_number': self.current_state.current_session_number,
                    'last_updated': self.current_state.last_updated,
                    'content_type': 'world_state'
                }],
                ids=[self._state_id],
                embeddings=[embedding]
            )
            
        except Exception as e:
            print(f"Warning: Error saving world state: {e}")
    
    def update_location(self, new_location: str, is_significant: bool = True):
        """Update the current location.
        
        Args:
            new_location: New location name
            is_significant: Whether this is a significant location change
        """
        if not self.current_state:
            self.load_world_state()
        
        if is_significant and self.current_state.current_location != "Unknown":
            self.current_state.last_significant_location = self.current_state.current_location
        
        self.current_state.current_location = new_location
        self.save_world_state()
        print(f"📍 Location updated: {new_location}")
    
    def update_story_progression(self, act: str = None, arc: str = None):
        """Update story progression markers.
        
        Args:
            act: New act (e.g., "Act II")
            arc: New arc (e.g., "Arc D")
        """
        if not self.current_state:
            self.load_world_state()
        
        if act:
            self.current_state.current_act = act
        if arc:
            self.current_state.current_arc = arc
        
        self.save_world_state()
        print(f"📖 Story progression updated: {self.current_state.current_act}, {self.current_state.current_arc}")
    
    def add_quest(self, quest_name: str, quest_type: str = "active"):
        """Add a quest to tracking.
        
        Args:
            quest_name: Name of the quest
            quest_type: Type of quest (active, completed, failed)
        """
        if not self.current_state:
            self.load_world_state()
        
        # Remove from other lists if it exists
        for quest_list in [self.current_state.active_quests, 
                          self.current_state.completed_quests, 
                          self.current_state.failed_quests]:
            if quest_name in quest_list:
                quest_list.remove(quest_name)
        
        # Add to appropriate list
        if quest_type == "active":
            self.current_state.active_quests.append(quest_name)
        elif quest_type == "completed":
            self.current_state.completed_quests.append(quest_name)
        elif quest_type == "failed":
            self.current_state.failed_quests.append(quest_name)
        
        self.save_world_state()
        print(f"🎯 Quest {quest_type}: {quest_name}")
    
    def update_character_relationship(self, character_name: str, relationship_status: str):
        """Update relationship with a character.
        
        Args:
            character_name: Name of the character
            relationship_status: Relationship status (e.g., "friendly", "hostile", "neutral")
        """
        if not self.current_state:
            self.load_world_state()
        
        self.current_state.character_relationships[character_name] = relationship_status
        self.save_world_state()
        print(f"👥 Relationship updated: {character_name} -> {relationship_status}")
    
    def set_story_flag(self, flag_name: str, value: bool = True):
        """Set a story flag.
        
        Args:
            flag_name: Name of the flag
            value: Flag value
        """
        if not self.current_state:
            self.load_world_state()
        
        self.current_state.story_flags[flag_name] = value
        self.save_world_state()
        print(f"🚩 Story flag set: {flag_name} = {value}")
    
    def add_important_event(self, event_description: str):
        """Add an important event to the history.
        
        Args:
            event_description: Description of the event
        """
        if not self.current_state:
            self.load_world_state()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        event_with_timestamp = f"[{timestamp}] {event_description}"
        self.current_state.important_events.append(event_with_timestamp)
        
        # Keep only the last 20 events to prevent bloat
        if len(self.current_state.important_events) > 20:
            self.current_state.important_events = self.current_state.important_events[-20:]
        
        self.save_world_state()
        print(f"📝 Important event recorded: {event_description}")
    
    def start_new_session(self, session_number: int):
        """Start a new session and update session tracking.
        
        Args:
            session_number: Session number
        """
        if not self.current_state:
            self.load_world_state()
        
        self.current_state.current_session_number = session_number
        self.current_state.total_sessions_played = max(
            self.current_state.total_sessions_played, 
            session_number
        )
        self.save_world_state()
        print(f"🎲 Session {session_number} started")
    
    def get_current_context_summary(self) -> str:
        """Get a summary of the current world state for context.
        
        Returns:
            Formatted context summary
        """
        if not self.current_state:
            self.load_world_state()
        
        summary_parts = []
        
        # Story progression
        summary_parts.append(f"**Current Story Position**: {self.current_state.current_act}, {self.current_state.current_arc}")
        summary_parts.append(f"**Current Location**: {self.current_state.current_location}")
        
        # Active quests
        if self.current_state.active_quests:
            summary_parts.append(f"**Active Quests**: {', '.join(self.current_state.active_quests)}")
        
        # Recent events
        if self.current_state.important_events:
            recent_events = self.current_state.important_events[-3:]  # Last 3 events
            summary_parts.append("**Recent Important Events**:")
            for event in recent_events:
                summary_parts.append(f"  - {event}")
        
        # Key relationships
        if self.current_state.character_relationships:
            key_relationships = [(k, v) for k, v in self.current_state.character_relationships.items() 
                               if v in ['friendly', 'hostile', 'romantic', 'enemy']]
            if key_relationships:
                summary_parts.append("**Key Character Relationships**:")
                for char, status in key_relationships:
                    summary_parts.append(f"  - {char}: {status}")
        
        # Active story flags
        active_flags = [k for k, v in self.current_state.story_flags.items() if v]
        if active_flags:
            summary_parts.append(f"**Active Story Flags**: {', '.join(active_flags)}")
        
        return "\n".join(summary_parts)
    
    def _create_state_summary(self) -> str:
        """Create a text summary of the world state for embedding.
        
        Returns:
            Text summary for embedding
        """
        if not self.current_state:
            return ""
        
        summary_parts = [
            f"Current story: {self.current_state.current_act} {self.current_state.current_arc}",
            f"Location: {self.current_state.current_location}",
            f"Session: {self.current_state.current_session_number}"
        ]
        
        if self.current_state.active_quests:
            summary_parts.append(f"Active quests: {', '.join(self.current_state.active_quests)}")
        
        if self.current_state.important_events:
            recent_events = self.current_state.important_events[-2:]
            summary_parts.append(f"Recent events: {'; '.join(recent_events)}")
        
        return " | ".join(summary_parts)
    
    def get_story_relevance_context(self, query: str) -> Dict[str, Any]:
        """Get story relevance context for query processing.
        
        Args:
            query: User query
            
        Returns:
            Dictionary with story context for query processing
        """
        if not self.current_state:
            self.load_world_state()
        
        return {
            'current_act': self.current_state.current_act,
            'current_arc': self.current_state.current_arc,
            'current_location': self.current_state.current_location,
            'active_quests': self.current_state.active_quests,
            'story_flags': self.current_state.story_flags,
            'session_number': self.current_state.current_session_number,
            'character_relationships': self.current_state.character_relationships
        }
