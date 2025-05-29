"""Main DM engine that orchestrates all subsystems."""

import sys
from typing import List, Dict, Any, Optional

from ..config.settings import DMConfig
from ..database.chroma_client import ChromaClient
from ..database.cache_manager import CacheManager
from ..content.embeddings import EmbeddingManager
from ..content.content_loader import ContentLoader
from ..content.player_loader import PlayerCharacterLoader
from ..content.session_history_loader import SessionHistoryLoader
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
        self.session_history_loader = SessionHistoryLoader(
            self.chroma_client, self.embedding_manager
        )
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
        
        # Load and embed session history
        print("\nLoading session history...")
        try:
            if not self.session_history_loader.load_and_embed_sessions():
                print("⚠ Warning: Session history loading encountered issues")
        except Exception as e:
            print(f"⚠ Warning: Error loading session history: {e}")
        
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
    
    def generate_initial_session_response(self, previous_sessions: Optional[str], last_session_events: Optional[str]) -> str:
        """Generate initial DM response about session context.
        
        Args:
            previous_sessions: Summary of previous sessions
            last_session_events: Events from last session
            
        Returns:
            Initial DM response
        """
        # Load player character information for the DM
        player_name = self.player_loader.get_player_name()
        player_summary = ""
        if self.player_loader.get_player_info():
            player_summary = f"\n\nPlayer Character Information:\n{self.player_loader.get_player_summary()}"
        
        # Prepare session context prompt
        if previous_sessions:
            context_prompt = f"""You are an expert Dungeon Master for *Curse of Strahd: Reloaded*. This player ({player_name}) has returned for another session in Barovia. 

Previous Session Summary:
{previous_sessions}
{last_session_events or ""}

Please provide a brief, atmospheric summary of where they left off in their journey through Barovia and what has happened so far. Reference the previous session information to create continuity, then ask what they would like to do next. Keep this concise but engaging, maintaining the gothic horror atmosphere.

Player Character: {player_summary}"""
        else:
            context_prompt = f"""You are an expert Dungeon Master for *Curse of Strahd: Reloaded*. This is a new player ({player_name}) beginning their journey into Barovia for the first time. You are using the 5th edition Dungeons & Dragons ruleset, and you have access to tools for rolling dice, tracking character stats, and managing the session. Remember you are the DM and to keep the player in check, do not allow them to do anything that would break the game or try and trick you, such as lying about their character's abilities or stats.

Please provide an atmospheric introduction to Barovia, setting the scene for where their adventure starts. Create an engaging opening that draws them into the gothic horror atmosphere, then ask them what they would like to do first.

Player Character: {player_summary}"""
        
        # Generate initial response with streaming enabled
        try:
            initial_messages = [{"role": "user", "content": context_prompt}]
            
            print("\n🎲 DM: ", end="", flush=True)
            
            # Force streaming for initial response (no tools needed)
            dm_content, response, was_streamed = self.llm_client.chat_completion_with_streaming(
                messages=initial_messages,
                force_streaming=True
            )
            
            # If not streamed, print the content now
            if not was_streamed and dm_content:
                print(dm_content, end="", flush=True)
            
            print()  # Add newline after response
            return dm_content
            
        except Exception as e:
            error_msg = f"Welcome to Barovia! I'm your AI Dungeon Master, ready to guide you through this gothic horror adventure. What would you like to do first?"
            print(error_msg)
            print(f"\n⚠ Note: Error generating initial response: {e}")
            return error_msg
    
    def chat_with_dm(self):
        """Interactive chat loop with the enhanced DM."""
        if not self.initialized:
            print("❌ DM engine not initialized. Call initialize() first.")
            return
        
        # Check for previous sessions before starting new one
        previous_sessions = self.session_manager.get_previous_sessions_summary()
        last_session_events = self.session_manager.get_last_session_events()
        
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
        
        # Generate and display initial session context response
        initial_response = self.generate_initial_session_response(previous_sessions, last_session_events)
        
        # Log the initial DM response
        self.session_manager.log_dm_response(initial_response)
        
        # Load player character information for the DM
        player_name = self.player_loader.get_player_name()
        player_summary = ""
        if self.player_loader.get_player_info():
            player_summary = f"\n\nPlayer Character Information:\n{self.player_loader.get_player_summary()}"
        
        # Initialize conversation history with the initial response
        conversation_history = [{
            "role": "system",
            "content": f"""You are an expert Dungeon Master guiding a player through *Curse of Strahd: Reloaded*, a gothic horror Dungeons & Dragons adventure. You have access to special tools for dice rolling, character tracking, and session management to enhance the gameplay experience.

        ### Your Capabilities
        - **roll_dice**: Use this to resolve actions requiring randomness—skill checks, saving throws, attacks, or damage rolls.
        - **update_character**: Use this to track changes to the character’s state, such as HP, inventory, or abilities.
        - **get_character_info**: Use this to retrieve details about the player's character when needed.
        - **end_session**: Use this to conclude the session when the player requests it or when the narrative calls for a pause.

        ### Your Role
        You are the player’s guide through the eerie and oppressive land of Barovia. Your job is to:
        - **Narrate immersive scenes** full of suspense and dread appropriate to a horror setting.
        - **Facilitate gameplay** with fairness and fluidity, prompting dice rolls when needed.
        - **Track and recall** past events, character choices, and evolving story details.
        - **Encourage meaningful decisions** while gently guiding the story forward.
        - **Refer to the player by their character's name** ({player_name}) for immersion.
        - **Maintain tone and tension**, building atmosphere even during mundane tasks.
        - **Prompt rolls proactively**, offering the option to roll and clearly stating the type and DC (Difficulty Class).
        - **Begin each session appropriately** - either with a summary of previous events or an introduction for new players.

        ### General Guidance
        - Always be descriptive, using vivid imagery and emotional cues.
        - Stay interactive: ask questions, give choices, and invite player input.
        - Use your tools in the background to streamline gameplay.
        - Respect player agency—let them narrate actions and offer responses before resolving.
        - **IMPORTANT**: Start your first response by either summarizing previous sessions or providing an introduction for new players, then ask what the player wants to do.

        ---

        ### Example Interactions

        **1. Searching a room**
        - Player: "I want to check the room for traps."
        - DM: "The shadows flicker across the dusty floorboards. That sounds like an *Investigation* check—would you like to roll? The DC is 15."

        **2. Combat action**
        - Player: "I swing my longsword at the vampire!"
        - DM: "*The vampire snarls and raises its clawed hand in defense.* Roll for your attack—would you like me to roll it for you? The target AC is 12."

        **3. Failed check outcome**
        - (After a failed Stealth roll)
        - DM: "*Your foot slips on loose cobblestone with a sharp clack. From the far corridor, you hear a low growl—something has heard you.*"

        **4. Using a tool**
        - (Player rolls a d20 + 3 for a Perception check)
        - DM: (uses roll_dice tool) → result = 16  
        - DM: "*With a sharp eye, you spot a faint wire near the doorframe. A tripwire—just barely visible in the gloom.*"

        **5. Session ending**
        - Player: "Let's wrap up for tonight."
        - DM: "*The mists swirl and settle as your party finds a brief moment of calm. We'll pause here. Until next time, brave soul.*" (uses end_session)
        
        ---
        Player Information:
        {player_summary}
        """
        }, {
            "role": "assistant",
            "content": initial_response
        }]
        
        while True:
            try:
                # Get user input
                user_input = input("\n🎭 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q', 'end session']:
                    print("\n🌙 Ending session...")
                    end_result = self.session_manager.end_session(self.llm_client)
                    print(end_result)
                    print("The mists of Barovia fade as you step back into reality...")
                    print("Thanks for playing! May you find your way out of the darkness.")
                    break
                
                if not user_input:
                    continue
                
                # Log player input
                self.session_manager.log_player_input(user_input)
                
                # Get relevant context from the knowledge base with current session ID
                context = self.context_retriever.get_relevant_context(
                    user_input, max_chunks=10, current_session_id=session_id
                )
                
                # Prepare the prompt with context
                context_prompt = ""
                if context:
                    context_prompt = f"\n\nRelevant information:\n{context}"
                
                # Add user message to conversation with dice roll guidance
                conversation_history.append({
                    "role": "user",
                    "content": user_input + context_prompt + "\n\nConsider if the user has been asked to make a roll recently and if it would enhance their experience to ask them to make one now."
                })
                
                # Keep conversation history manageable
                if len(conversation_history) > self.config.game.conversation_history_limit + 1:
                    conversation_history = [conversation_history[0]] + conversation_history[-(self.config.game.conversation_history_limit):]
                
                print("\n🎲 DM: ", end="", flush=True)
                
                # Generate DM response with streaming support
                dm_content, response, was_streamed = self.llm_client.chat_completion_with_streaming(
                    messages=conversation_history,
                    tools=self.game_tool_handler.get_tool_definitions(),
                    tool_choice="auto"
                )
                
                # If not streamed, print the content now
                if not was_streamed and dm_content:
                    print(dm_content, end="", flush=True)
                
                response_message = response.choices[0].message if response else None
                
                # Handle tool calls if present
                if response_message and response_message.tool_calls:
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
                    
                    # Get final response after tool execution with streaming
                    print("\n")
                    final_content, final_response, final_was_streamed = self.llm_client.chat_completion_with_streaming(
                        messages=conversation_history,
                        tools=None,  # No tools for final response
                        force_streaming=True  # Force streaming for final response
                    )
                    
                    # If not streamed, print the content now
                    if not final_was_streamed and final_content:
                        print(final_content, end="", flush=True)
                    
                    dm_response = final_content
                    
                    # Log DM response
                    self.session_manager.log_dm_response(dm_response)
                    
                    # Add final DM response to conversation history
                    conversation_history.append({
                        "role": "assistant",
                        "content": dm_response
                    })
                    
                else:
                    # No tool calls, just regular response
                    dm_response = dm_content or (response_message.content if response_message else "")
                    
                    # Only print if not already streamed
                    if not was_streamed and dm_response:
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
