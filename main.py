"""Main entry point for the D&D DM system."""

import sys
from talk_dnd_to_me.core.dm_engine import DMEngine
from talk_dnd_to_me.config.settings import DMConfig


def main():
    """Main entry point that launches the DM chat interface."""
    # Check for reset command line argument
    if len(sys.argv) > 1 and sys.argv[1].lower() in ['--reset', '-r', 'reset']:
        print("🔄 Campaign Reset Mode")
        print("This will reset all campaign progress while preserving content.")
        
        # Create configuration and engine for reset
        config = DMConfig.default()
        dm_engine = DMEngine(config)
        
        # Initialize just enough to perform reset
        if dm_engine.chroma_client.initialize():
            dm_engine.initialized = True  # Mark as initialized for reset
            dm_engine.reset_campaign_progress()
        else:
            print("❌ Failed to initialize database for reset")
            sys.exit(1)
        return
    
    # Create default configuration (can be customized here)
    config = DMConfig.default()
    
    # Example of how to customize configuration:
    # config.update_content_directory("path/to/your/content")
    # config.update_ai_settings(base_url="http://localhost:11434/v1", temperature=0.8)
    
    # Initialize DM engine
    dm_engine = DMEngine(config)
    
    # Initialize all subsystems
    if not dm_engine.initialize():
        print("❌ Failed to initialize DM system")
        sys.exit(1)
    
    # Start the interactive chat
    print("\n✓ Starting enhanced DM session...")
    dm_engine.chat_with_dm()


if __name__ == "__main__":
    main()
