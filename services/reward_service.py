"""
Reward Service for Discord Habit Bot.

Handles RNG rewards, loot tables, and bonus rewards for habit completions.
"""

import logging
import random
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func
from models import Reward, User, InventoryItem
from database import DatabaseManager

logger = logging.getLogger(__name__)


class RewardService:
    """Service for managing RNG rewards and loot system."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
        # Loot table configuration
        # Format: (min_roll, max_roll, reward_type, value, description_template)
        self.loot_table = [
            # Common rewards (1-70)
            (1, 30, "encouragement", "", "received words of encouragement! 💪"),
            (31, 50, "xp", "5", "found a small XP crystal! +5 XP bonus! ✨"),
            (51, 70, "gold", "10", "discovered 10 gold coins! 💰"),
            
            # Uncommon rewards (71-90)
            (71, 80, "xp", "15", "stumbled upon a glowing XP orb! +15 XP bonus! 🔮"),
            (81, 85, "gold", "25", "found a small treasure chest! +25 gold! 📦"),
            (86, 90, "item", "Energy Potion", "brewed an Energy Potion! Drink for motivation! ⚗️"),
            
            # Rare rewards (91-98)
            (91, 94, "xp", "30", "activated an ancient XP rune! +30 XP bonus! 🏛️"),
            (95, 96, "gold", "50", "uncovered a buried treasure! +50 gold! 💎"),
            (97, 98, "item", "Lucky Charm", "crafted a Lucky Charm! Increases future luck! 🍀"),
            
            # Epic rewards (99-100)
            (99, 99, "xp", "50", "awakened the spirit of productivity! +50 XP! 👻"),
            (100, 100, "item", "Legendary Habit Crown", "forged the Legendary Habit Crown! You are truly dedicated! 👑"),
        ]
        
        # Special milestone rewards
        self.milestone_rewards = {
            7: ("item", "Week Warrior Badge", "earned the Week Warrior Badge for 7 days! 🏅"),
            30: ("gold", "100", "achieved 30-day mastery! +100 gold bonus! 🎖️"),
            100: ("item", "Centurion Medal", "reached 100 completions! Centurion Medal earned! 🥇"),
            365: ("item", "Annual Achievement Trophy", "completed a full year! Annual Achievement Trophy! 🏆"),
        }
        
        # Item descriptions for inventory
        self.item_descriptions = {
            "Energy Potion": "A magical elixir that boosts motivation. Reminds you of your inner strength!",
            "Lucky Charm": "A mystical charm that brings good fortune. Increases your chances of finding rewards!",
            "Week Warrior Badge": "A badge of honor for completing 7 consecutive days. Shows your dedication!",
            "Centurion Medal": "A prestigious medal for reaching 100 habit completions. Marks your commitment!",
            "Annual Achievement Trophy": "The ultimate trophy for year-long dedication. You are a true habit master!",
            "Legendary Habit Crown": "The rarest of all items. Only the most dedicated habit trackers possess this crown!",
        }
    
    async def roll_for_reward(self, user_id: int, source_type: str, source_id: int) -> Optional[Reward]:
        """Roll for a random reward based on habit completion.
        
        Args:
            user_id: Database user ID
            source_type: Source of the reward ("habit_log", "streak_milestone", etc.)
            source_id: ID of the source record
            
        Returns:
            Reward object if a reward was given, None otherwise
        """
        try:
            # Roll d100
            roll = random.randint(1, 100)
            
            # Check if user has lucky charm for bonus roll
            has_lucky_charm = await self._user_has_item(user_id, "Lucky Charm")
            if has_lucky_charm and roll < 90:  # Lucky charm gives second chance for rare rewards
                bonus_roll = random.randint(1, 100)
                if bonus_roll > roll:
                    roll = bonus_roll
                    logger.info(f"Lucky charm activated for user {user_id}: {roll}")
            
            # Find matching reward in loot table
            reward_data = None
            for min_roll, max_roll, reward_type, value, description in self.loot_table:
                if min_roll <= roll <= max_roll:
                    reward_data = (reward_type, value, description)
                    break
            
            if not reward_data:
                logger.warning(f"No reward found for roll {roll}")
                return None
            
            reward_type, reward_value, description_template = reward_data
            
            # Skip encouragement rewards (too spammy)
            if reward_type == "encouragement":
                return None
            
            # Create reward description
            description = f"🎲 Rolled {roll}! {description_template}"
            
            # Create and apply reward
            reward = await self._create_reward(
                user_id=user_id,
                reward_type=reward_type,
                reward_value=reward_value,
                description=description,
                source_type=source_type,
                source_id=source_id,
                roll_value=roll
            )
            
            # Apply the reward effects
            await self._apply_reward_effects(user_id, reward_type, reward_value)
            
            logger.info(f"Awarded reward to user {user_id}: {description}")
            return reward
            
        except Exception as e:
            logger.error(f"Error rolling for reward: {e}")
            return None
    
    async def award_milestone_reward(self, user_id: int, milestone: int, source_type: str, source_id: int) -> Optional[Reward]:
        """Award a special milestone reward.
        
        Args:
            user_id: Database user ID
            milestone: Milestone number (days, completions, etc.)
            source_type: Source type for tracking
            source_id: Source ID for tracking
            
        Returns:
            Reward object if milestone reward exists
        """
        if milestone not in self.milestone_rewards:
            return None
        
        try:
            reward_type, reward_value, description_template = self.milestone_rewards[milestone]
            
            description = f"🎯 Milestone reached! {description_template}"
            
            # Create reward
            reward = await self._create_reward(
                user_id=user_id,
                reward_type=reward_type,
                reward_value=reward_value,
                description=description,
                source_type=source_type,
                source_id=source_id,
                roll_value=None  # Milestone rewards don't use rolls
            )
            
            # Apply the reward effects
            await self._apply_reward_effects(user_id, reward_type, reward_value)
            
            logger.info(f"Awarded milestone reward to user {user_id}: {description}")
            return reward
            
        except Exception as e:
            logger.error(f"Error awarding milestone reward: {e}")
            return None
    
    async def _create_reward(self, user_id: int, reward_type: str, reward_value: str, 
                           description: str, source_type: str, source_id: int, 
                           roll_value: Optional[int]) -> Reward:
        """Create a reward record in the database."""
        async with self.db_manager.get_session() as session:
            reward = Reward(
                user_id=user_id,
                reward_type=reward_type,
                reward_value=reward_value,
                description=description,
                source_type=source_type,
                source_id=source_id,
                roll_value=roll_value
            )
            session.add(reward)
            await session.commit()
            await session.refresh(reward)
            return reward
    
    async def _apply_reward_effects(self, user_id: int, reward_type: str, reward_value: str) -> None:
        """Apply the actual effects of a reward (XP, gold, items)."""
        async with self.db_manager.get_session() as session:
            user = await session.get(User, user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            if reward_type == "xp":
                xp_amount = int(reward_value)
                old_level = user.level
                user.total_xp += xp_amount
                
                # Recalculate level
                user.level = max(1, int((user.total_xp / 100) ** 0.5) + 1)
                
                if user.level > old_level:
                    logger.info(f"User {user.username} leveled up from {old_level} to {user.level}!")
            
            elif reward_type == "gold":
                gold_amount = int(reward_value)
                user.gold += gold_amount
            
            elif reward_type == "item":
                await self._add_item_to_inventory(user_id, reward_value)
            
            await session.commit()
    
    async def _add_item_to_inventory(self, user_id: int, item_name: str) -> None:
        """Add an item to user's inventory."""
        async with self.db_manager.get_session() as session:
            # Check if user already has this item
            existing_stmt = select(InventoryItem).where(
                InventoryItem.user_id == user_id,
                InventoryItem.item_name == item_name
            )
            existing_result = await session.execute(existing_stmt)
            existing_item = existing_result.scalar_one_or_none()
            
            if existing_item:
                # Increase quantity for stackable items
                if item_name in ["Energy Potion"]:  # Consumable items stack
                    existing_item.quantity += 1
                # For unique items, we don't add duplicates
                await session.commit()
            else:
                # Create new inventory item
                item_type = self._get_item_type(item_name)
                description = self.item_descriptions.get(item_name, "A mysterious item...")
                
                inventory_item = InventoryItem(
                    user_id=user_id,
                    item_name=item_name,
                    item_type=item_type,
                    quantity=1,
                    description=description
                )
                session.add(inventory_item)
                await session.commit()
    
    def _get_item_type(self, item_name: str) -> str:
        """Determine item type based on item name."""
        consumables = ["Energy Potion"]
        equipment = ["Lucky Charm"]
        collectibles = ["Week Warrior Badge", "Centurion Medal", "Annual Achievement Trophy", "Legendary Habit Crown"]
        
        if item_name in consumables:
            return "consumable"
        elif item_name in equipment:
            return "equipment"
        elif item_name in collectibles:
            return "collectible"
        else:
            return "misc"
    
    async def _user_has_item(self, user_id: int, item_name: str) -> bool:
        """Check if user has a specific item in inventory."""
        async with self.db_manager.get_session() as session:
            stmt = select(InventoryItem).where(
                InventoryItem.user_id == user_id,
                InventoryItem.item_name == item_name,
                InventoryItem.quantity > 0
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
    
    async def get_user_rewards(self, user_id: int, limit: int = 20) -> List[Reward]:
        """Get recent rewards for a user."""
        async with self.db_manager.get_session() as session:
            stmt = select(Reward).where(
                Reward.user_id == user_id
            ).order_by(Reward.awarded_at.desc()).limit(limit)
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    async def get_user_inventory(self, user_id: int) -> List[InventoryItem]:
        """Get user's inventory items."""
        async with self.db_manager.get_session() as session:
            stmt = select(InventoryItem).where(
                InventoryItem.user_id == user_id,
                InventoryItem.quantity > 0
            ).order_by(InventoryItem.item_type, InventoryItem.item_name)
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
    
    async def use_consumable(self, user_id: int, item_name: str) -> bool:
        """Use a consumable item from inventory.
        
        Args:
            user_id: Database user ID
            item_name: Name of the consumable to use
            
        Returns:
            True if item was used successfully, False otherwise
        """
        async with self.db_manager.get_session() as session:
            # Find the item
            stmt = select(InventoryItem).where(
                InventoryItem.user_id == user_id,
                InventoryItem.item_name == item_name,
                InventoryItem.item_type == "consumable",
                InventoryItem.quantity > 0
            )
            result = await session.execute(stmt)
            item = result.scalar_one_or_none()
            
            if not item:
                return False
            
            # Decrease quantity
            item.quantity -= 1
            
            # Remove from inventory if quantity is 0
            if item.quantity <= 0:
                await session.delete(item)
            
            await session.commit()
            
            # Apply consumable effects (could be extended)
            if item_name == "Energy Potion":
                # Energy potion could give temporary XP bonus, but for now just acknowledgment
                pass
            
            logger.info(f"User {user_id} used {item_name}")
            return True
    
    async def get_reward_statistics(self) -> Dict[str, Any]:
        """Get global reward statistics."""
        async with self.db_manager.get_session() as session:
            # Total rewards given
            total_stmt = select(func.count(Reward.id))
            total_result = await session.execute(total_stmt)
            total_rewards = total_result.scalar()
            
            # Rewards by type
            type_stmt = select(Reward.reward_type, func.count(Reward.id)).group_by(Reward.reward_type)
            type_result = await session.execute(type_stmt)
            rewards_by_type = {row[0]: row[1] for row in type_result.all()}
            
            # Average roll value
            roll_stmt = select(func.avg(Reward.roll_value)).where(Reward.roll_value.isnot(None))
            roll_result = await session.execute(roll_stmt)
            avg_roll = roll_result.scalar() or 0
            
            return {
                "total_rewards": total_rewards,
                "rewards_by_type": rewards_by_type,
                "average_roll": round(avg_roll, 1),
                "legendary_items_awarded": rewards_by_type.get("item", 0)
            }