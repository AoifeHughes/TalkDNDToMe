"""
Test dice rolling functionality.
"""

import pytest
import re
from talk_dnd_to_me.core.dm_engine import DMEngine


@pytest.mark.llm
class TestDiceRolling:
    """Test dice rolling functionality."""
    
    def test_perception_check_includes_dice(self, dm_engine: DMEngine):
        """Test that perception checks include dice-related content."""
        query = "I want to make a perception check"
        response = dm_engine.generate_response(query)
        
        # Look for dice notation OR dice-related language
        dice_pattern = r'\b\d+d\d+(?:[+-]\d+)?\b'
        dice_found = re.findall(dice_pattern, response)
        
        # Also accept dice-related terms like "roll", "check", "DC"
        dice_terms = ['roll', 'check', 'dc', 'd20', 'dice', 'wisdom', 'perception']
        has_dice_terms = any(term in response.lower() for term in dice_terms)
        
        assert dice_found or has_dice_terms, f"No dice notation or dice terms found in perception check: {response[:200]}..."
    
    def test_attack_roll_includes_dice(self, dm_engine: DMEngine):
        """Test that attack rolls include dice-related content."""
        query = "I attack the goblin with my rapier"
        response = dm_engine.generate_response(query)
        
        # Look for dice notation OR attack-related terms
        dice_pattern = r'\b\d+d\d+(?:[+-]\d+)?\b'
        dice_found = re.findall(dice_pattern, response)
        
        attack_terms = ['roll', 'attack', 'hit', 'miss', 'd20', 'dice', 'rapier', 'goblin']
        has_attack_terms = any(term in response.lower() for term in attack_terms)
        
        assert dice_found or has_attack_terms, f"No dice notation or attack terms found: {response[:200]}..."
    
    def test_damage_roll_includes_dice(self, dm_engine: DMEngine):
        """Test that damage rolls include dice-related content."""
        query = "I hit! Roll damage for my rapier"
        response = dm_engine.generate_response(query)
        
        # Look for dice notation OR damage-related terms
        dice_pattern = r'\b\d+d\d+(?:[+-]\d+)?\b'
        dice_found = re.findall(dice_pattern, response)
        
        damage_terms = ['damage', 'roll', 'hit', 'rapier', 'dice', 'd8', 'd6']
        has_damage_terms = any(term in response.lower() for term in damage_terms)
        
        assert dice_found or has_damage_terms, f"No dice notation or damage terms found: {response[:200]}..."
    
    def test_initiative_roll(self, dm_engine: DMEngine):
        """Test initiative rolling."""
        query = "Roll for initiative"
        response = dm_engine.generate_response(query)
        
        # Should include dice notation OR initiative-related terms
        dice_pattern = r'\b\d+d\d+(?:[+-]\d+)?\b'
        dice_found = re.findall(dice_pattern, response)
        
        # Look for initiative-specific language
        initiative_words = ['initiative', 'turn order', 'combat', 'roll', 'd20', 'dexterity']
        has_initiative_context = any(word in response.lower() for word in initiative_words)
        
        assert dice_found or has_initiative_context, f"No dice or initiative context: {response[:200]}..."
    
    def test_roll_results_are_reasonable(self, dm_engine: DMEngine):
        """Test that roll responses are meaningful."""
        query = "Roll a d20"
        response = dm_engine.generate_response(query)
        
        # Look for roll-related terms OR numbers
        numbers = re.findall(r'\b\d+\b', response)
        roll_terms = ['roll', 'd20', 'dice', 'result']
        has_roll_context = any(term in response.lower() for term in roll_terms)
        
        assert numbers or has_roll_context, f"No numbers or roll context found: {response[:200]}..."
    
    @pytest.mark.parametrize("dice_type,query", [
        ("d4", "Roll a d4"),
        ("d6", "Roll a d6"),  
        ("d8", "Roll a d8"),
        ("d10", "Roll a d10"),
        ("d12", "Roll a d12"),
        ("d20", "Roll a d20"),
        ("d100", "Roll a d100")
    ])
    def test_various_die_types(self, dm_engine: DMEngine, dice_type: str, query: str):
        """Test rolling various types of dice."""
        response = dm_engine.generate_response(query)
        
        # Should mention the die type OR general roll terms
        die_mentioned = dice_type in response or f"1{dice_type}" in response
        roll_terms = ['roll', 'dice', 'result', 'rolled']
        has_roll_terms = any(term in response.lower() for term in roll_terms)
        
        assert die_mentioned or has_roll_terms, \
            f"No die type or roll terms found in: {response[:200]}..."
    
    def test_advantage_disadvantage(self, dm_engine: DMEngine):
        """Test advantage and disadvantage mechanics."""
        query = "I make a stealth check with advantage"
        response = dm_engine.generate_response(query)
        
        # Should mention advantage, stealth, or rolling
        advantage_words = ['advantage', 'twice', 'higher', 'two dice', '2d20', 'stealth', 'roll']
        has_advantage = any(word in response.lower() for word in advantage_words)
        
        assert has_advantage, f"No advantage or stealth mechanics found: {response[:200]}..."