"""Main DM engine that orchestrates all subsystems."""

import sys
from typing import List, Dict, Any, Optional

from ..config.settings import DMConfig
from ..database.chroma_client import ChromaClient
from ..database.cache_manager import CacheManager
from ..content.embeddings import EmbeddingManager
from ..content.content_loader import ContentLoader
from ..content.player_loader import PlayerCharacterLoader
from ..game.dice import DiceRoller
from ..game.character_manager import CharacterManager
from ..game.tools import GameToolHandler
from ..ai.llm_client import LLMClient
from ..ai.context_retriever import ContextRetriever
from .session_manager import SessionManager


class DMEngine:
    """Main DM engine that coordinates all subsystems."""
    
    def __init__(self, config: Optional[DMConfig] = None):
        """Initialize DM engine.
        
        Args:
            config: DM configuration (uses default if None)
        """
        self.config = config or DMConfig.default()
        
        # Initialize all subsystems
        self.chroma_client = ChromaClient(self.config.database)
        self.cache_manager = CacheManager(self.chroma_client)
        self.embedding_manager = EmbeddingManager(self.config.ai)
        self.content_loader = ContentLoader(
            self.config.content, self.chroma_client, 
            self.cache_manager, self.embedding_manager
        )
        self.player_loader = PlayerCharacterLoader(self.config.content)
        self.dice_roller = DiceRoller(self.config.game)
        self.character_manager = CharacterManager(self.chroma_client)
        self.session_manager = SessionManager(self.chroma_client)
        self.llm_client = LLMClient(self.config.ai)
        self.context_retriever = ContextRetriever(
            self.chroma_client, self.embedding_manager, self.config.content
        )
        self.game_tool_handler = GameToolHandler(
            self.dice_roller, self.character_manager, self.session_manager
        )
        
        # System state
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize all subsystems.
        
        Returns:
            True if all systems initialized successfully
        """
        print("🎲 Enhanced Curse of Strahd DM System Starting...")
        
        # Initialize embedding model
        print("\nInitializing embedding model...")
        if not self.embedding_manager.initialize():
            return False
        
        # Setup ChromaDB collections
        print("\nSetting up ChromaDB collections...")
        if not self.chroma_client.initialize():
            return False
        
        # Initialize LLM client
        print("\nInitializing LLM client...")
        if not self.llm_client.initialize():
            return False
        
        # Load and process documents with smart caching
        print("\nLoading Curse of Strahd content...")
        try:
            documents, files_to_process = self.content_loader.load_curse_of_strahd_content()
            if documents:
                self.content_loader.process_documents(documents, files_to_process)
            print(f"✓ Content loading complete")
        except Exception as e:
            print(f"✗ Error loading content: {e}")
            return False
        
        # Load player character if available
        print("\nLoading player character...")
        try:
            player_info = self.player_loader.load_player_character()
            if player_info:
                print(f"✓ Player character loaded: {self.player_loader.get_player_summary()}")
            else:
                print("⚠ No player character found (optional)")
        except Exception as e:
            print(f"⚠ Warning: Error loading player character: {e}")
        
        # Test retrieval
        print("\nTesting enhanced system...")
        if not self.context_retriever.test_retrieval():
            print("⚠ Warning: Context retrieval may not be working properly")
        
        print("\n✓ All systems ready!")
        self.initialized = True
        return True
    
    def reset_campaign_progress(self) -> bool:
        """Reset all campaign progress while keeping content.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.initialized:
            print("❌ DM engine not initialized. Call initialize() first.")
            return False
        
        print("\n🔄 Resetting campaign progress...")
        print("This will clear all session history, character data, and cached files.")
        print("Campaign content will be preserved.")
        
        confirm = input("\nAre you sure you want to reset? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("Reset cancelled.")
            return False
        
        return self.chroma_client.reset_progress_data()
    
    def chat_with_dm(self):
        """Interactive chat loop with the enhanced DM."""
        if not self.initialized:
            print("❌ DM engine not initialized. Call initialize() first.")
            return
        
        # Start new session
        session_id = self.session_manager.start_session()
        self.character_manager.set_session_id(session_id)
        
        print("\n" + "="*60)
        print("🎲 ENHANCED CURSE OF STRAHD - DUNGEON MASTER 🎲")
        print("="*60)
        print("Welcome to Barovia! I'm your enhanced AI Dungeon Master.")
        print("I can roll dice, track characters, and remember everything!")
        print(f"\nSession ID: {session_id}")
        print("\nCommands:")
        print("- Type 'quit', 'exit', or 'END SESSION' to end")
        print("- I can roll dice automatically when needed")
        print("- I'll track character stats and story progress")
        print("-" * 60)
        
        # Load player character information for the DM
        player_name = self.player_loader.get_player_name()
        player_summary = ""
        if self.player_loader.get_player_info():
            player_summary = f"\n\nPlayer Character Information:\n{self.player_loader.get_player_summary()}"
        
        # Initialize conversation history
        conversation_history = [{
            "role": "system",
            "content": f"""You are an expert Dungeon Master running Curse of Strahd: Reloaded with enhanced capabilities. You have access to tools for dice rolling, character management, and session tracking.

Your enhanced abilities:
- Roll dice using the roll_dice function when players need checks, saves, attacks, or damage
- Update character information using update_character when stats change
- Look up character details using get_character_info when needed
- End sessions properly using end_session when requested

Your role:
- Act as an engaging, atmospheric DM who brings Barovia to life
- Use dice rolls naturally in gameplay (ability checks, combat, etc.)
- Track character changes (HP, inventory, relationships, location)
- Reference past events and character details from memory
- Create tension and atmosphere appropriate to the horror setting
- Guide players through the story while letting them make meaningful choices
- Address the player by their character name ({player_name}) when appropriate

Always be immersive and interactive. Use your tools to enhance the gameplay experience.{player_summary}"""
        }]
        
        while True:
            try:
                # Get user input
                user_input = input("\n🎭 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q', 'end session']:
                    print("\n🌙 Ending session...")
                    end_result = self.session_manager.end_session()
                    print(end_result)
                    print("The mists of Barovia fade as you step back into reality...")
                    print("Thanks for playing! May you find your way out of the darkness.")
                    break
                
                if not user_input:
                    continue
                
                # Log player input
                self.session_manager.log_player_input(user_input)
                
                # Get relevant context from the knowledge base
                context = self.context_retriever.get_relevant_context(user_input, max_chunks=3)
                
                # Prepare the prompt with context
                context_prompt = ""
                if context:
                    context_prompt = f"\n\nRelevant information:\n{context}"
                
                # Add user message to conversation
                conversation_history.append({
                    "role": "user",
                    "content": user_input + context_prompt
                })
                
                # Keep conversation history manageable
                if len(conversation_history) > self.config.game.conversation_history_limit + 1:
                    conversation_history = [conversation_history[0]] + conversation_history[-(self.config.game.conversation_history_limit):]
                
                print("\n🎲 DM: ", end="", flush=True)
                
                # Generate DM response with tool calling
                response = self.llm_client.chat_completion(
                    messages=conversation_history,
                    tools=self.game_tool_handler.get_tool_definitions(),
                    tool_choice="auto"
                )
                
                response_message = response.choices[0].message
                
                # Handle tool calls if present
                if response_message.tool_calls:
                    # Add the assistant's message with tool calls to conversation
                    conversation_history.append({
                        "role": "assistant",
                        "content": response_message.content,
                        "tool_calls": [{
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in response_message.tool_calls]
                    })
                    
                    # Execute tool calls
                    tool_results = self.game_tool_handler.handle_tool_calls(response_message.tool_calls)
                    
                    # Display tool results to user
                    for result in tool_results:
                        print(result["content"])
                    
                    # Add tool results to conversation
                    conversation_history.extend(tool_results)
                    
                    # Get final response after tool execution
                    final_response = self.llm_client.chat_completion(
                        messages=conversation_history
                    )
                    
                    dm_response = final_response.choices[0].message.content
                    print(dm_response)
                    
                    # Log DM response
                    self.session_manager.log_dm_response(dm_response)
                    
                    # Add final DM response to conversation history
                    conversation_history.append({
                        "role": "assistant",
                        "content": dm_response
                    })
                    
                else:
                    # No tool calls, just regular response
                    dm_response = response_message.content
                    print(dm_response)
                    
                    # Log DM response
                    self.session_manager.log_dm_response(dm_response)
                    
                    # Add DM response to conversation history
                    conversation_history.append({
                        "role": "assistant",
                        "content": dm_response
                    })
                
            except KeyboardInterrupt:
                print("\n\n🌙 Session interrupted. The mists swirl around you...")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("The mists seem to interfere with our connection. Try again...")
