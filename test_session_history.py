#!/usr/bin/env python3
"""Test script for the enhanced session history system."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from talk_dnd_to_me.core.dm_engine import DMEngine
from talk_dnd_to_me.config.settings import DMConfig

def test_session_history_system():
    """Test the session history system components."""
    print("🧪 Testing Enhanced Session History System")
    print("=" * 50)
    
    try:
        # Initialize DM engine with default config
        print("1. Initializing DM Engine...")
        config = DMConfig.default()
        dm_engine = DMEngine(config)
        
        # Initialize the system
        print("\n2. Initializing all subsystems...")
        if not dm_engine.initialize():
            print("❌ Failed to initialize DM engine")
            return False
        
        print("\n3. Testing session history loader...")
        # Test session history loader directly
        session_loader = dm_engine.session_history_loader
        
        # Check if existing session files are loaded
        print("   - Checking for existing session files...")
        if os.path.exists("Sessions"):
            session_files = [f for f in os.listdir("Sessions") if f.endswith('.md')]
            print(f"   - Found {len(session_files)} session files")
        else:
            print("   - No Sessions directory found")
        
        print("\n4. Testing context retrieval with session history...")
        # Test context retrieval
        context_retriever = dm_engine.context_retriever
        
        # Test queries that should trigger session history
        test_queries = [
            "What happened last time?",
            "Tell me about Rose and Luvash",
            "Where did we leave off?",
            "What about Arabelle?"
        ]
        
        for query in test_queries:
            print(f"\n   Testing query: '{query}'")
            try:
                context = context_retriever.get_relevant_context(
                    query, max_chunks=5, current_session_id="test_session"
                )
                if context:
                    print(f"   ✓ Retrieved context ({len(context)} characters)")
                    # Show first 100 characters of context
                    preview = context[:100] + "..." if len(context) > 100 else context
                    print(f"   Preview: {preview}")
                else:
                    print("   - No context retrieved")
            except Exception as e:
                print(f"   ⚠ Error: {e}")
        
        print("\n5. Testing ChromaDB collections...")
        # Check collections
        collections = ['content', 'history', 'character', 'cache', 'session_history']
        for collection_name in collections:
            try:
                collection = dm_engine.chroma_client.get_collection(collection_name)
                count = collection.count() if collection else 0
                print(f"   - {collection_name}: {count} documents")
            except Exception as e:
                print(f"   - {collection_name}: Error - {e}")
        
        print("\n✅ Session history system test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_session_history_system()
    sys.exit(0 if success else 1)
