"""Game tool definitions and handlers for OpenAI function calling."""

import json
from typing import List, Dict, Any

from .dice import DiceRoller
from .character_manager import CharacterManager
from ..core.session_manager import SessionManager


class GameToolHandler:
    """Handles game tool execution for OpenAI function calling."""
    
    def __init__(self, dice_roller: DiceRoller, character_manager: CharacterManager, 
                 session_manager: SessionManager):
        """Initialize game tool handler.
        
        Args:
            dice_roller: Dice rolling instance
            character_manager: Character management instance
            session_manager: Session management instance
        """
        self.dice_roller = dice_roller
        self.character_manager = character_manager
        self.session_manager = session_manager
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI tool definitions.
        
        Returns:
            List of tool definitions for OpenAI
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "roll_dice",
                    "description": "Roll dice for D&D gameplay. Use this when players need to make ability checks, attack rolls, damage rolls, or any other dice-based mechanics.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "number_of_dice": {
                                "type": "integer",
                                "description": "Number of dice to roll (1-20)"
                            },
                            "dice_type": {
                                "type": "integer",
                                "description": "Type of dice (4, 6, 8, 10, 12, 20, 100)",
                                "enum": [4, 6, 8, 10, 12, 20, 100]
                            },
                            "modification_int": {
                                "type": "integer",
                                "description": "Modifier to add or subtract from the roll (default 0)",
                                "default": 0
                            }
                        },
                        "required": ["number_of_dice", "dice_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_character",
                    "description": "Update character stats, inventory, status, or other information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to update"
                            },
                            "update_type": {
                                "type": "string",
                                "description": "Type of update to perform",
                                "enum": ["hp", "inventory", "status", "relationship", "location"]
                            },
                            "update_data": {
                                "type": "object",
                                "description": "Data to update (structure depends on update_type)"
                            }
                        },
                        "required": ["character_name", "update_type", "update_data"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_character_info",
                    "description": "Retrieve current information about a character or NPC",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "character_name": {
                                "type": "string",
                                "description": "Name of the character to look up"
                            }
                        },
                        "required": ["character_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "end_session",
                    "description": "End the current D&D session and create a summary",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]
    
    def handle_tool_calls(self, tool_calls) -> List[Dict[str, Any]]:
        """Execute tool calls and return results.
        
        Args:
            tool_calls: List of tool calls from OpenAI
            
        Returns:
            List of tool call results
        """
        results = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            try:
                if function_name == "roll_dice":
                    roll_result = self.dice_roller.roll_dice(
                        arguments.get("number_of_dice"),
                        arguments.get("dice_type"),
                        arguments.get("modification_int", 0)
                    )
                    
                    # Log the roll to session history
                    if roll_result["success"]:
                        self.session_manager.log_to_session({
                            "entry_type": "dice_roll",
                            "content": roll_result["message"],
                            "dice_data": {
                                "expression": roll_result["expression"],
                                "rolls": roll_result["rolls"],
                                "modifier": roll_result["modifier"],
                                "total": roll_result["total"]
                            }
                        })
                    
                    result = roll_result["message"]
                    
                elif function_name == "update_character":
                    result = self.character_manager.update_character(
                        arguments.get("character_name"),
                        arguments.get("update_type"),
                        arguments.get("update_data")
                    )
                    
                elif function_name == "get_character_info":
                    result = self.character_manager.get_character_info(
                        arguments.get("character_name")
                    )
                    
                elif function_name == "end_session":
                    result = self.session_manager.end_session()
                    
                else:
                    result = f"❌ Unknown function: {function_name}"
                    
            except Exception as e:
                result = f"❌ Error executing {function_name}: {e}"
            
            results.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "content": result
            })
        
        return results
