# -*- coding: utf-8 -*-
"""Main entry point for the D&D DM system."""

import sys
from talk_dnd_to_me.core.dm_engine import DMEngine
from talk_dnd_to_me.config.settings import DMConfig


def main():
    """Main entry point that launches the DM chat interface."""
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1].lower() in ["--reset", "-r", "reset"]:
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
        elif sys.argv[1].lower() in ["--no-streaming", "--disable-streaming"]:
            print("🔧 Streaming disabled via command line")
        elif sys.argv[1].lower() in ["--help", "-h"]:
            print("🎲 Enhanced Curse of Strahd DM System")
            print("\nUsage: python main.py [options]")
            print("\nOptions:")
            print("  --reset, -r              Reset campaign progress")
            print("  --no-streaming           Disable text streaming")
            print("  --disable-streaming      Disable text streaming")
            print("  --help, -h               Show this help message")
            return

    # Create default configuration (can be customized here)
    config = DMConfig.default()

    # Handle streaming configuration from command line
    if len(sys.argv) > 1 and sys.argv[1].lower() in [
        "--no-streaming",
        "--disable-streaming",
    ]:
        config.ai.enable_streaming = False

    # Example of how to customize configuration:
    # config.update_content_directory("path/to/your/content")
    # config.update_ai_settings(base_url="http://localhost:11434/v1", temperature=0.8)
    # config.ai.enable_streaming = False  # Disable streaming
    # config.ai.streaming_fallback_on_tools = False  # Allow streaming even with tools

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
