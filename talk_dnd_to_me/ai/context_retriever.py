"""Context retrieval for RAG (Retrieval-Augmented Generation)."""

import json
from typing import List, Optional, Dict, Any, Tuple

from ..database.chroma_client import ChromaClient
from ..content.embeddings import EmbeddingManager
from ..config.settings import ContentConfig


class ContextRetriever:
    """Retrieves relevant context from knowledge base and session history."""
    
    def __init__(self, chroma_client: ChromaClient, embedding_manager: EmbeddingManager,
                 config: ContentConfig):
        """Initialize context retriever.
        
        Args:
            chroma_client: ChromaDB client instance
            embedding_manager: Embedding manager instance
            config: Content configuration
        """
        self.chroma_client = chroma_client
        self.embedding_manager = embedding_manager
        self.config = config
    
    def get_relevant_context(self, query: str, max_chunks: Optional[int] = None, 
                           current_session_id: Optional[str] = None) -> str:
        """Retrieve relevant context using three-tier prioritization system.
        
        Args:
            query: Query text to find relevant context for
            max_chunks: Maximum number of chunks to retrieve
            current_session_id: Current session ID for prioritizing current session data
            
        Returns:
            Formatted context string
        """
        if max_chunks is None:
            max_chunks = self.config.max_context_chunks
        
        try:
            # Analyze query intent for smart prioritization
            query_intent = self._analyze_query_intent(query)
            
            # Adjust retrieval strategy based on session recall intent
            is_session_recall = query_intent.get('session_recall', 0) > 0
            
            if is_session_recall:
                # For session recall queries, prioritize session history heavily
                tier1_context = self._get_current_session_context(query, current_session_id, max_results=2)
                remaining_slots = max_chunks - len(tier1_context)
                
                # Give most slots to session history
                tier2_context = self._get_session_history_context(query, query_intent, max_results=min(6, remaining_slots))
                remaining_slots = max_chunks - len(tier1_context) - len(tier2_context)
                
                # Minimal campaign content for session recall queries
                tier3_context = self._get_campaign_context(query, max_results=min(2, remaining_slots))
            else:
                # Normal three-tier retrieval
                tier1_context = self._get_current_session_context(query, current_session_id, max_results=2)
                remaining_slots = max_chunks - len(tier1_context)
                
                tier2_context = self._get_session_history_context(query, query_intent, max_results=min(4, remaining_slots))
                remaining_slots = max_chunks - len(tier1_context) - len(tier2_context)
                
                tier3_context = self._get_campaign_context(query, max_results=remaining_slots)
            
            # Combine all context with priority ordering
            all_context = tier1_context + tier2_context + tier3_context
            
            # Format context for output
            return self._format_context_output(all_context)
            
        except Exception as e:
            print(f"Warning: Error retrieving context: {e}")
            return ""
    
    def test_retrieval(self, test_query: str = "What is Death House?") -> bool:
        """Test context retrieval functionality.
        
        Args:
            test_query: Query to test with
            
        Returns:
            True if retrieval works, False otherwise
        """
        try:
            # Check if content collection has any documents
            content_collection = self.chroma_client.get_collection('content')
            content_count = content_collection.count() if content_collection else 0
            
            # Check if history collection exists
            history_collection = self.chroma_client.get_collection('history')
            history_count = history_collection.count() if history_collection else 0
            
            if content_count == 0:
                print("⚠ Warning: No content loaded in database yet (this is normal on first run)")
                return True  # Don't treat this as an error
            
            # Test actual retrieval
            context = self.get_relevant_context(test_query)
            if context:
                print(f"✓ Context retrieval working ({content_count} content docs, {history_count} history docs)")
                return True
            else:
                print(f"⚠ Warning: Context retrieval returned empty results ({content_count} content docs available)")
                return False
                
        except Exception as e:
            print(f"✗ Error testing context retrieval: {e}")
            return False
    
    def _analyze_query_intent(self, query: str) -> Dict[str, int]:
        """Analyze query to determine intent and prioritization needs.
        
        Args:
            query: User query text
            
        Returns:
            Dictionary of intent scores
        """
        patterns = {
            'session_recall': [
                'last time', 'previous', 'before', 'remember', 'what happened', 'earlier',
                'last session', 'previously', 'we did', 'we were', 'i was', 'where we left off',
                'recap', 'summary', 'catch up', 'remind me', 'what was happening'
            ],
            'character_focus': ['Rose', 'Luvash', 'Arabelle', 'Meda', 'Duras', 'Strahd', 'Ireena', 'Ismark'],
            'location_focus': ['Vallaki', 'Barovia', 'tavern', 'church', 'Ravenloft', 'Death House'],
            'story_continuation': ['continue', 'next', 'where we left off', 'what now', 'proceed']
        }
        
        intent_scores = {}
        query_lower = query.lower()
        
        for intent, keywords in patterns.items():
            score = sum(1 for keyword in keywords if keyword.lower() in query_lower)
            intent_scores[intent] = score
        
        return intent_scores
    
    def _get_current_session_context(self, query: str, current_session_id: Optional[str], 
                                   max_results: int) -> List[Dict[str, Any]]:
        """Get context from current session (Tier 1 - Highest Priority).
        
        Args:
            query: User query
            current_session_id: Current session ID
            max_results: Maximum results to return
            
        Returns:
            List of context items
        """
        if not current_session_id:
            return []
        
        try:
            query_embedding = self.embedding_manager.embed_query(query)
            
            # Query current session data from history collection
            results = self.chroma_client.query_collection(
                'history',
                query_embeddings=[query_embedding],
                where={'session_id': current_session_id},
                n_results=max_results,
                include=["documents", "metadatas", "distances"]
            )
            
            context_items = []
            if results['documents'] and results['documents'][0]:
                for doc, metadata, distance in zip(
                    results['documents'][0], 
                    results['metadatas'][0], 
                    results['distances'][0]
                ):
                    try:
                        entry = json.loads(doc)
                        if entry.get('entry_type') in ['player_input', 'dm_response']:
                            context_items.append({
                                'text': entry.get('content', ''),
                                'source': 'current_session',
                                'priority': 'highest',
                                'metadata': metadata,
                                'distance': distance * 0.5  # Boost current session
                            })
                    except json.JSONDecodeError:
                        continue
            
            return context_items
            
        except Exception as e:
            print(f"Warning: Error retrieving current session context: {e}")
            return []
    
    def _get_session_history_context(self, query: str, query_intent: Dict[str, int], 
                                   max_results: int) -> List[Dict[str, Any]]:
        """Get context from session history summaries (Tier 2 - High Priority).
        
        Args:
            query: User query
            query_intent: Query intent analysis
            max_results: Maximum results to return
            
        Returns:
            List of context items
        """
        try:
            query_embedding = self.embedding_manager.embed_query(query)
            
            # Query session history collection
            results = self.chroma_client.query_collection(
                'session_history',
                query_embeddings=[query_embedding],
                n_results=max_results,
                include=["documents", "metadatas", "distances"]
            )
            
            context_items = []
            if results['documents'] and results['documents'][0]:
                for doc, metadata, distance in zip(
                    results['documents'][0], 
                    results['metadatas'][0], 
                    results['distances'][0]
                ):
                    # Calculate priority boost based on query intent and session recency
                    priority_boost = self._calculate_session_priority_boost(
                        metadata, query_intent
                    )
                    
                    context_items.append({
                        'text': doc,
                        'source': 'session_history',
                        'priority': 'high',
                        'metadata': metadata,
                        'distance': distance * (0.7 - priority_boost)  # Apply boost
                    })
            
            # Sort by adjusted distance (lower = more relevant)
            context_items.sort(key=lambda x: x['distance'])
            
            return context_items
            
        except Exception as e:
            print(f"Warning: Error retrieving session history context: {e}")
            return []
    
    def _get_campaign_context(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Get context from campaign content (Tier 3 - Normal Priority).
        
        Args:
            query: User query
            max_results: Maximum results to return
            
        Returns:
            List of context items
        """
        try:
            query_embedding = self.embedding_manager.embed_query(query)
            
            # Query campaign content collection
            results = self.chroma_client.query_collection(
                'content',
                query_embeddings=[query_embedding],
                n_results=max_results,
                include=["documents", "metadatas", "distances"]
            )
            
            context_items = []
            if results['documents'] and results['documents'][0]:
                for doc, metadata, distance in zip(
                    results['documents'][0], 
                    results['metadatas'][0], 
                    results['distances'][0]
                ):
                    context_items.append({
                        'text': doc,
                        'source': 'campaign_content',
                        'priority': 'normal',
                        'metadata': metadata,
                        'distance': distance  # No boost for campaign content
                    })
            
            return context_items
            
        except Exception as e:
            print(f"Warning: Error retrieving campaign context: {e}")
            return []
    
    def _calculate_session_priority_boost(self, metadata: Dict[str, Any], 
                                        query_intent: Dict[str, int]) -> float:
        """Calculate priority boost for session history based on recency and relevance.
        
        Args:
            metadata: Session metadata
            query_intent: Query intent scores
            
        Returns:
            Priority boost value (0.0 to 0.3)
        """
        boost = 0.0
        
        # Recency boost (more recent sessions get higher priority)
        session_number = metadata.get('session_number', 0)
        if session_number > 0:
            # Assume max 10 sessions for now, adjust as needed
            recency_boost = min(session_number / 10.0, 1.0) * 0.2
            boost += recency_boost
        
        # Intent-based boost
        if query_intent.get('session_recall', 0) > 0:
            boost += 0.1  # Boost for session recall queries
        
        # Character/location relevance boost
        characters_mentioned = metadata.get('characters_mentioned', '')
        locations_mentioned = metadata.get('locations_mentioned', '')
        
        if query_intent.get('character_focus', 0) > 0 and characters_mentioned:
            boost += 0.05
        
        if query_intent.get('location_focus', 0) > 0 and locations_mentioned:
            boost += 0.05
        
        return min(boost, 0.3)  # Cap at 0.3
    
    def _format_context_output(self, context_items: List[Dict[str, Any]]) -> str:
        """Format context items for output to the LLM.
        
        Args:
            context_items: List of context items
            
        Returns:
            Formatted context string
        """
        if not context_items:
            return ""
        
        # Sort by priority and distance
        priority_order = {'highest': 0, 'high': 1, 'normal': 2}
        context_items.sort(key=lambda x: (priority_order.get(x['priority'], 3), x['distance']))
        
        context_parts = []
        
        for item in context_items:
            source = item['source']
            text = item['text']
            metadata = item.get('metadata', {})
            
            if source == 'current_session':
                context_parts.append(f"[Current Session] {text}")
            elif source == 'session_history':
                session_num = metadata.get('session_number', 'Unknown')
                section_type = metadata.get('section_type', 'general')
                context_parts.append(f"[Session {session_num} - {section_type.title()}] {text}")
            elif source == 'campaign_content':
                content_type = metadata.get('content_type', 'Unknown')
                context_parts.append(f"[Campaign Content - {content_type}] {text}")
        
        return "\n\n".join(context_parts)
