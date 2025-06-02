"""
Test function calling and tool schemas.
"""

import pytest
import json
from unittest.mock import Mock, patch
from talk_dnd_to_me.game.tools import GameToolHandler
from talk_dnd_to_me.game.dice import DiceRoller
from talk_dnd_to_me.game.character_manager import CharacterManager


@pytest.fixture
def game_tool_handler():
    """Create a GameToolHandler for testing."""
    dice_roller = Mock(spec=DiceRoller)
    character_manager = Mock(spec=CharacterManager) 
    session_manager = Mock()
    return GameToolHandler(dice_roller, character_manager, session_manager)


@pytest.mark.unit
class TestToolSchemas:
    """Test tool schema definitions."""
    
    def test_all_tools_have_required_fields(self, game_tool_handler):
        """Test that all tool schemas have required fields."""
        tools = game_tool_handler.get_tool_definitions()
        
        assert len(tools) > 0, "No tools found"
        
        for tool in tools:
            # Check top-level fields
            assert 'type' in tool, f"Tool missing 'type' field: {tool}"
            assert 'function' in tool, f"Tool missing 'function' field: {tool}"
            assert tool['type'] == 'function', f"Tool type should be 'function': {tool['type']}"
            
            # Check function fields
            func = tool['function']
            assert 'name' in func, f"Function missing 'name': {func}"
            assert 'description' in func, f"Function missing 'description': {func}"
            assert 'parameters' in func, f"Function missing 'parameters': {func}"
    
    def test_required_tools_exist(self, game_tool_handler):
        """Test that required tools are defined."""
        tools = game_tool_handler.get_tool_definitions()
        tool_names = [tool['function']['name'] for tool in tools]
        
        required_tools = ['roll_dice', 'update_character', 'get_character_info']
        
        for required_tool in required_tools:
            assert required_tool in tool_names, f"Required tool '{required_tool}' not found"
    
    def test_roll_dice_schema(self, game_tool_handler):
        """Test roll_dice tool schema specifics."""
        tools = game_tool_handler.get_tool_definitions()
        roll_dice_tool = next(tool for tool in tools if tool['function']['name'] == 'roll_dice')
        
        assert roll_dice_tool['function']['name'] == 'roll_dice'
        
        params = roll_dice_tool['function']['parameters']
        assert 'properties' in params
        assert 'number_of_dice' in params['properties']
        assert 'dice_type' in params['properties']
    
    def test_update_character_schema(self, game_tool_handler):
        """Test update_character tool schema."""
        tools = game_tool_handler.get_tool_definitions()
        update_tool = next(tool for tool in tools if tool['function']['name'] == 'update_character')
        
        assert update_tool['function']['name'] == 'update_character'
        
        params = update_tool['function']['parameters']
        assert 'properties' in params
        assert 'character_name' in params['properties']
        assert 'update_type' in params['properties']
    
    def test_get_character_info_schema(self, game_tool_handler):
        """Test get_character_info tool schema."""
        tools = game_tool_handler.get_tool_definitions()
        info_tool = next(tool for tool in tools if tool['function']['name'] == 'get_character_info')
        
        assert info_tool['function']['name'] == 'get_character_info'
        
        params = info_tool['function']['parameters']
        assert 'properties' in params
        assert 'character_name' in params['properties']


@pytest.mark.unit
class TestFunctionCalling:
    """Test function calling mechanisms."""
    
    def test_dice_roller_integration(self, game_tool_handler):
        """Test that dice roller is called correctly."""
        # Mock the dice roller response
        game_tool_handler.dice_roller.roll_dice.return_value = {
            "success": True,
            "message": "Rolled 1d20+5: 15 (rolled 10, +5 modifier)",
            "expression": "1d20+5",
            "rolls": [10],
            "modifier": 5,
            "total": 15
        }
        
        # Create mock tool call
        mock_tool_call = Mock()
        mock_tool_call.function.name = "roll_dice"
        mock_tool_call.function.arguments = json.dumps({
            "number_of_dice": 1,
            "dice_type": 20,
            "modification_int": 5
        })
        mock_tool_call.id = "test_id"
        
        # Execute tool call
        results = game_tool_handler.handle_tool_calls([mock_tool_call])
        
        assert len(results) == 1
        result = results[0]
        assert result["tool_call_id"] == "test_id"
        assert result["role"] == "tool"
        assert "Rolled 1d20+5" in result["content"]
    
    def test_character_update_integration(self, game_tool_handler):
        """Test character update function calling."""
        # Mock the character manager response
        game_tool_handler.character_manager.update_character.return_value = "HP updated: 25 → 20"
        
        # Create mock tool call
        mock_tool_call = Mock()
        mock_tool_call.function.name = "update_character"
        mock_tool_call.function.arguments = json.dumps({
            "character_name": "Rose",
            "update_type": "hp",
            "update_data": {"current_hp": 25, "change": -5}
        })
        mock_tool_call.id = "test_id"
        
        # Execute tool call
        results = game_tool_handler.handle_tool_calls([mock_tool_call])
        
        assert len(results) == 1
        result = results[0]
        assert result["content"] == "HP updated: 25 → 20"
    
    def test_character_info_retrieval(self, game_tool_handler):
        """Test character info retrieval."""
        # Mock the character manager response
        game_tool_handler.character_manager.get_character_info.return_value = "Rose: Level 3 Elf Bard"
        
        # Create mock tool call
        mock_tool_call = Mock()
        mock_tool_call.function.name = "get_character_info"
        mock_tool_call.function.arguments = json.dumps({
            "character_name": "Rose"
        })
        mock_tool_call.id = "test_id"
        
        # Execute tool call
        results = game_tool_handler.handle_tool_calls([mock_tool_call])
        
        assert len(results) == 1
        result = results[0]
        assert result["content"] == "Rose: Level 3 Elf Bard"
    
    def test_unknown_function_handling(self, game_tool_handler):
        """Test handling of unknown functions."""
        # Create mock tool call with unknown function
        mock_tool_call = Mock()
        mock_tool_call.function.name = "unknown_function"
        mock_tool_call.function.arguments = json.dumps({})
        mock_tool_call.id = "test_id"
        
        # Execute tool call
        results = game_tool_handler.handle_tool_calls([mock_tool_call])
        
        assert len(results) == 1
        result = results[0]
        assert "Unknown function" in result["content"]


@pytest.mark.unit  
class TestMockFunctionCalls:
    """Test function calling with mocks."""
    
    def test_mock_openai_function_call(self):
        """Test processing mock OpenAI function call responses."""
        # Mock OpenAI response with function call (new format uses tool_calls)
        mock_response = {
            'choices': [{
                'message': {
                    'role': 'assistant',
                    'content': None,
                    'tool_calls': [{
                        'id': 'call_123',
                        'type': 'function',
                        'function': {
                            'name': 'roll_dice',
                            'arguments': json.dumps({
                                'number_of_dice': 1,
                                'dice_type': 20,
                                'modification_int': 5
                            })
                        }
                    }]
                }
            }]
        }
        
        # Extract function call
        choice = mock_response['choices'][0]
        assert 'tool_calls' in choice['message']
        
        tool_call = choice['message']['tool_calls'][0]
        assert tool_call['function']['name'] == 'roll_dice'
        
        args = json.loads(tool_call['function']['arguments'])
        assert args['number_of_dice'] == 1
        assert args['dice_type'] == 20
        assert args['modification_int'] == 5
    
    def test_multiple_function_calls(self, game_tool_handler):
        """Test handling multiple function calls."""
        # Mock responses
        game_tool_handler.dice_roller.roll_dice.return_value = {
            "success": True, "message": "Rolled dice", "expression": "1d20", "rolls": [15], "modifier": 0, "total": 15
        }
        game_tool_handler.character_manager.update_character.return_value = "Character updated"
        
        # Create multiple mock tool calls
        mock_tool_calls = []
        for i, (func_name, args) in enumerate([
            ('roll_dice', {'number_of_dice': 1, 'dice_type': 20}),
            ('roll_dice', {'number_of_dice': 1, 'dice_type': 8, 'modification_int': 3}),
            ('update_character', {'character_name': 'Rose', 'update_type': 'hp', 'update_data': {'change': -8}})
        ]):
            mock_call = Mock()
            mock_call.function.name = func_name
            mock_call.function.arguments = json.dumps(args)
            mock_call.id = f"test_id_{i}"
            mock_tool_calls.append(mock_call)
        
        # Execute all calls
        results = game_tool_handler.handle_tool_calls(mock_tool_calls)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)
            assert 'content' in result
            assert len(result['content']) > 0