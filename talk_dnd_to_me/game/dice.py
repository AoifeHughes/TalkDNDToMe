"""Dice rolling functionality for D&D gameplay."""

import random
from typing import Dict, Any

from ..config.settings import GameConfig


class DiceRoller:
    """Handles dice rolling mechanics for D&D gameplay."""
    
    def __init__(self, config: GameConfig):
        """Initialize dice roller.
        
        Args:
            config: Game configuration
        """
        self.config = config
    
    def roll_dice(self, number_of_dice: int, dice_type: int, modification_int: int = 0) -> Dict[str, Any]:
        """Roll dice and return formatted result.
        
        Args:
            number_of_dice: Number of dice to roll (1-20)
            dice_type: Type of dice (4, 6, 8, 10, 12, 20, 100)
            modification_int: Modifier to add or subtract from the roll
            
        Returns:
            Dictionary containing roll result and metadata
        """
        # Validate inputs
        if dice_type not in self.config.valid_dice_types:
            return {
                "success": False,
                "message": f"❌ Invalid dice type: d{dice_type}. Valid types: {', '.join(f'd{d}' for d in self.config.valid_dice_types)}",
                "total": 0,
                "rolls": [],
                "modifier": modification_int
            }
        
        if number_of_dice < 1 or number_of_dice > self.config.max_dice_count:
            return {
                "success": False,
                "message": f"❌ Invalid number of dice: {number_of_dice}. Must be between 1 and {self.config.max_dice_count}",
                "total": 0,
                "rolls": [],
                "modifier": modification_int
            }
        
        # Roll the dice
        rolls = [random.randint(1, dice_type) for _ in range(number_of_dice)]
        total = sum(rolls) + modification_int
        
        # Format the result message
        rolls_str = ", ".join(map(str, rolls))
        if number_of_dice == 1:
            if modification_int != 0:
                message = f"🎲 Rolling 1d{dice_type}{modification_int:+d}: [{rolls[0]}] {modification_int:+d} = {total}"
            else:
                message = f"🎲 Rolling 1d{dice_type}: [{rolls[0]}] = {total}"
        else:
            if modification_int != 0:
                message = f"🎲 Rolling {number_of_dice}d{dice_type}{modification_int:+d}: [{rolls_str}] {modification_int:+d} = {total}"
            else:
                message = f"🎲 Rolling {number_of_dice}d{dice_type}: [{rolls_str}] = {total}"
        
        return {
            "success": True,
            "message": message,
            "total": total,
            "rolls": rolls,
            "modifier": modification_int,
            "expression": f"{number_of_dice}d{dice_type}{modification_int:+d}" if modification_int != 0 else f"{number_of_dice}d{dice_type}"
        }
