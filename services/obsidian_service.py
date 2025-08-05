"""
Obsidian Service for Discord Habit Bot.

Handles synchronization with Obsidian vault via REST API for habit tracking notes.
Supports full vault integration including daily notes, habits, and task management.
"""

import logging
import os
import aiohttp
import json
from datetime import date, datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import yaml
from database import DatabaseManager

logger = logging.getLogger(__name__)


class ObsidianService:
    """Service for syncing habit data with Obsidian vault via REST API."""
    
    def __init__(self):
        self.vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
        self.api_url = os.getenv("OBSIDIAN_API_URL", "http://localhost:3001")
        self.api_key = os.getenv("OBSIDIAN_API_KEY")
        
        # Enable if we have vault path (for file-based) OR API credentials (for REST)
        self.enabled = bool(
            (self.vault_path and os.path.exists(self.vault_path)) or 
            (self.api_url and self.api_key)
        )
        
        self.use_api = bool(self.api_url and self.api_key)
        
        if self.enabled:
            mode = "REST API" if self.use_api else "file-based"
            logger.info(f"Obsidian sync enabled ({mode}): {self.api_url if self.use_api else self.vault_path}")
        else:
            logger.info("Obsidian sync disabled (no valid vault path or API credentials)")
    
    async def _make_api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to Obsidian REST API."""
        if not self.use_api:
            return None
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.api_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, json=data) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        return None
                    else:
                        logger.error(f"API request failed: {response.status} - {await response.text()}")
                        return None
        except Exception as e:
            logger.error(f"API request error: {e}")
            return None
    
    async def get_daily_note(self, target_date: date = None) -> Optional[Dict]:
        """Get daily note content for specified date."""
        if target_date is None:
            target_date = date.today()
        
        date_str = target_date.strftime("%Y-%m-%d")
        
        if self.use_api:
            return await self._make_api_request("GET", f"/api/daily/{date_str}")
        else:
            # File-based implementation
            note_path = Path(self.vault_path) / "1_life" / "13_journal" / f"{date_str}.md"
            if note_path.exists():
                return {"content": note_path.read_text(), "path": str(note_path)}
            return None
    
    async def create_daily_note(self, target_date: date = None, template_data: Dict = None) -> bool:
        """Create daily note with template."""
        if target_date is None:
            target_date = date.today()
        
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Generate daily note template
        template = self._generate_daily_note_template(target_date, template_data)
        
        if self.use_api:
            result = await self._make_api_request("POST", f"/api/daily/{date_str}", {"content": template})
            return result is not None
        else:
            # File-based implementation
            note_path = Path(self.vault_path) / "1_life" / "13_journal" / f"{date_str}.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(template)
            return True
    
    async def add_task_to_daily_note(self, task_description: str, target_date: date = None) -> bool:
        """Add task to daily note."""
        if target_date is None:
            target_date = date.today()
        
        date_str = target_date.strftime("%Y-%m-%d")
        
        if self.use_api:
            data = {"task": task_description}
            result = await self._make_api_request("POST", f"/api/daily/{date_str}/task", data)
            return result is not None
        else:
            # File-based implementation
            note_path = Path(self.vault_path) / "1_life" / "13_journal" / f"{date_str}.md"
            if note_path.exists():
                content = note_path.read_text()
                content += f"\n- [ ] {task_description}"
                note_path.write_text(content)
                return True
            return False
    
    async def sync_daily_habits(self, user_id: int, habit_logs: List[Dict], target_date: date = None) -> bool:
        """Sync daily habit completions to Obsidian vault."""
        if not self.enabled:
            return False
        
        if target_date is None:
            target_date = date.today()
        
        # Ensure daily note exists
        daily_note = await self.get_daily_note(target_date)
        if not daily_note:
            await self.create_daily_note(target_date)
        
        # Generate habit tracking section
        habit_section = self._generate_habit_section(habit_logs, target_date)
        
        if self.use_api:
            date_str = target_date.strftime("%Y-%m-%d")
            data = {"section": "habits", "content": habit_section}
            result = await self._make_api_request("PATCH", f"/api/daily/{date_str}/section", data)
            return result is not None
        else:
            # File-based implementation
            note_path = Path(self.vault_path) / "Daily Notes" / f"{target_date.strftime('%Y-%m-%d')}.md"
            if note_path.exists():
                content = note_path.read_text()
                # Simple append for now - could be more sophisticated
                content += f"\n\n## Habits\n{habit_section}"
                note_path.write_text(content)
                return True
            return False
    
    async def create_habit_note(self, habit_name: str, completion_data: Dict[str, Any]) -> bool:
        """Create or update a habit note in Obsidian."""
        if not self.enabled:
            return False
        
        habit_slug = habit_name.lower().replace(" ", "-")
        
        if self.use_api:
            note_path = f"Habits/{habit_slug}.md"
            content = self._generate_habit_note_content(habit_name, completion_data)
            result = await self._make_api_request("POST", f"/api/notes/{note_path}", {"content": content})
            return result is not None
        else:
            # File-based implementation
            note_path = Path(self.vault_path) / "Habits" / f"{habit_slug}.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            content = self._generate_habit_note_content(habit_name, completion_data)
            note_path.write_text(content)
            return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of Obsidian integration."""
        if not self.enabled:
            return {"status": "disabled", "reason": "No vault path or API credentials"}
        
        if self.use_api:
            result = await self._make_api_request("GET", "/api/health")
            if result:
                return {"status": "healthy", "mode": "api", "vault": result.get("vault")}
            else:
                return {"status": "unhealthy", "mode": "api", "reason": "API not responding"}
        else:
            vault_exists = os.path.exists(self.vault_path)
            return {
                "status": "healthy" if vault_exists else "unhealthy",
                "mode": "file",
                "vault": self.vault_path,
                "reason": None if vault_exists else "Vault path not found"
            }
    
    def _generate_daily_note_template(self, target_date: date, template_data: Dict = None) -> str:
        """Generate daily note template content."""
        date_str = target_date.strftime("%Y-%m-%d")
        day_name = target_date.strftime("%A")
        
        template = f"""# {date_str} - {day_name}

## Habits
<!-- Habit tracking will be populated here -->

## Tasks
- [ ] 

## Notes


## Reflection
- **What went well today?**
- **What could be improved?**
- **What am I grateful for?**

---
*Generated by Discord Habit Bot*
"""
        
        if template_data:
            template = template.format(**template_data)
        
        return template
    
    def _generate_habit_section(self, habit_logs: List[Dict], target_date: date) -> str:
        """Generate habit tracking section for daily note."""
        if not habit_logs:
            return "No habits logged today."
        
        lines = []
        for log in habit_logs:
            status = "✅" if log.get('completed', False) else "❌"
            habit_name = log.get('habit_name', 'Unknown Habit')
            xp_gained = log.get('xp_gained', 0)
            notes = log.get('notes', '')
            
            line = f"- {status} **{habit_name}** (+{xp_gained} XP)"
            if notes:
                line += f" - {notes}"
            lines.append(line)
        
        return "\n".join(lines)
    
    def _generate_habit_note_content(self, habit_name: str, completion_data: Dict) -> str:
        """Generate habit note content with tracking data."""
        total_completions = completion_data.get('total_completions', 0)
        current_streak = completion_data.get('current_streak', 0)
        best_streak = completion_data.get('best_streak', 0)
        total_xp = completion_data.get('total_xp', 0)
        
        content = f"""# {habit_name}

## Statistics
- **Total Completions:** {total_completions}
- **Current Streak:** {current_streak} days
- **Best Streak:** {best_streak} days
- **Total XP Earned:** {total_xp}

## Recent Activity
<!-- Recent completions will be tracked here -->

## Notes
<!-- Add your notes about this habit here -->

---
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
        return content