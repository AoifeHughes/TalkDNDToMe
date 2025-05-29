"""Player character loading and processing."""

import os
import json
from typing import Optional, Dict, Any

from ..config.settings import ContentConfig


class PlayerCharacterLoader:
    """Loads and processes player character information from JSON files."""

    def __init__(self, config: ContentConfig):
        self.config = config
        self.player_directory = "player_character"
        self.player_info: Optional[Dict[str, Any]] = None

    def load_player_character(self) -> Optional[Dict[str, Any]]:
        """Load player character information from player.json file.
        
        Returns:
            Dictionary containing player character information or None if not found
        """
        player_file = os.path.join(self.player_directory, "player.json")
        
        if not os.path.exists(player_file):
            print(f"⚠ Player character file '{player_file}' not found")
            return None

        print(f"📋 Loading player character from: {os.path.basename(player_file)}")

        try:
            with open(player_file, 'r', encoding='utf-8') as file:
                player_data = json.load(file)
                
            player_info = self._process_player_data(player_data)
            self.player_info = player_info
            print(f"✓ Player character loaded: {player_info.get('name', 'Unknown')}")
            return player_info
            
        except json.JSONDecodeError as e:
            print(f"✗ Error parsing JSON file: {e}")
            return None
        except Exception as e:
            print(f"✗ Error loading player character: {e}")
            return None

    def _process_player_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw JSON data into standardized player info format.
        
        Args:
            data: Raw JSON data from player.json
            
        Returns:
            Processed player information dictionary
        """
        # Create standardized player info structure
        player_info = {
            "name": data.get("name", "Unknown"),
            "class": data.get("class", "Unknown"),
            "race": data.get("race", "Unknown"),
            "level": data.get("level", 1),
            "gender": data.get("gender", "Unknown"),
            "background": data.get("background", "Unknown"),
            "armor_class": data.get("armor_class", 10),
            "initiative": data.get("initiative", 0),
            "speed": data.get("speed", "30 ft."),
            "hit_points": data.get("hit_points", {"current": 1, "max": 1, "temp": None}),
            "proficiency_bonus": data.get("proficiency_bonus", 2),
            "abilities": data.get("abilities", {}),
            "saving_throws": data.get("saving_throws", {}),
            "skills": data.get("skills", {}),
            "passive_skills": data.get("passive_skills", {}),
            "senses": data.get("senses", {}),
            "languages": data.get("languages", []),
            "armor_proficiencies": data.get("armor_proficiencies", []),
            "weapon_proficiencies": data.get("weapon_proficiencies", []),
            "tool_proficiencies": data.get("tool_proficiencies", []),
            "defenses": data.get("defenses", []),
            "stats": {},  # Legacy compatibility
            "equipment": data.get("equipment", []),
            "spells": data.get("spells", []),
            "backstory": data.get("backstory", ""),
            "raw_content": json.dumps(data, indent=2)
        }
        
        # Map abilities to legacy stats format for backward compatibility
        if player_info["abilities"]:
            player_info["stats"] = {
                "STR": player_info["abilities"].get("strength", 10),
                "DEX": player_info["abilities"].get("dexterity", 10),
                "CON": player_info["abilities"].get("constitution", 10),
                "INT": player_info["abilities"].get("intelligence", 10),
                "WIS": player_info["abilities"].get("wisdom", 10),
                "CHA": player_info["abilities"].get("charisma", 10)
            }
        
        return player_info

    def get_player_info(self) -> Optional[Dict[str, Any]]:
        """Get the loaded player character information.
        
        Returns:
            Player character information or None if not loaded
        """
        return self.player_info

    def get_player_name(self) -> str:
        """Get the player character's name.
        
        Returns:
            Player character name or 'Adventurer' if not available
        """
        return self.player_info['name'] if self.player_info and self.player_info.get('name') != 'Unknown' else 'Adventurer'

    def get_player_summary(self) -> str:
        """Get a formatted summary of the player character.
        
        Returns:
            Formatted player character summary
        """
        if not self.player_info:
            return "No player character information available."

        info = self.player_info
        summary = f"**{info['name']}** - Level {info['level']} {info['race']} {info['class']}"

        if info.get('gender') and info['gender'] != 'Unknown':
            summary += f" ({info['gender']})"

        if info.get('background') and info['background'] != 'Unknown':
            summary += f"\nBackground: {info['background']}"

        # Add combat stats
        hp = info.get('hit_points', {})
        if hp:
            summary += f"\nHP: {hp.get('current', '?')}/{hp.get('max', '?')} | AC: {info.get('armor_class', '?')} | Speed: {info.get('speed', '?')}"

        # Add ability scores
        if info.get('abilities'):
            abilities = info['abilities']
            summary += f"\nAbilities: STR {abilities.get('strength', '?')}, DEX {abilities.get('dexterity', '?')}, CON {abilities.get('constitution', '?')}, INT {abilities.get('intelligence', '?')}, WIS {abilities.get('wisdom', '?')}, CHA {abilities.get('charisma', '?')}"

        # Add key skills
        if info.get('skills'):
            key_skills = []
            skills = info['skills']
            for skill, value in skills.items():
                if value >= 5:  # Show skills with good bonuses
                    key_skills.append(f"{skill.replace('_', ' ').title()}: +{value}")
            if key_skills:
                summary += f"\nKey Skills: {', '.join(key_skills[:5])}"  # Limit to top 5

        # Add languages and senses
        if info.get('languages'):
            summary += f"\nLanguages: {', '.join(info['languages'])}"
            
        if info.get('senses'):
            senses_list = [f"{k}: {v}" for k, v in info['senses'].items()]
            if senses_list:
                summary += f"\nSenses: {', '.join(senses_list)}"

        if info.get('backstory'):
            summary += f"\nBackstory: {info['backstory'][:200]}..."

        return summary

    def get_ability_modifier(self, ability_name: str) -> int:
        """Get the modifier for a specific ability score.
        
        Args:
            ability_name: Name of the ability (strength, dexterity, etc.)
            
        Returns:
            Ability modifier
        """
        if not self.player_info or 'abilities' not in self.player_info:
            return 0
            
        ability_score = self.player_info['abilities'].get(ability_name.lower(), 10)
        return (ability_score - 10) // 2

    def get_skill_bonus(self, skill_name: str) -> int:
        """Get the bonus for a specific skill.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Skill bonus
        """
        if not self.player_info or 'skills' not in self.player_info:
            return 0
            
        return self.player_info['skills'].get(skill_name.lower().replace(' ', '_'), 0)
