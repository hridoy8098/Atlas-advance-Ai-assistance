from typing import Dict, List
from datetime import datetime
import config
from .base_agent import BaseAgent


class ProductivityAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Productivity Agent",
            description="Manages tasks, calendar, reminders, Pomodoro, and productivity tracking"
        )

    def get_capabilities(self) -> List[str]:
        return ["add_task", "show_tasks", "add_reminder", "pomodoro", "show_calendar"]

    def add_task(self, task: str) -> Dict:
        # এখানে database এ save করতে পারবেন পরে
        return {
            "success": True,
            "message": f"Task added: {task}",
            "task": task
        }

    def start_pomodoro(self, minutes: int = 25) -> Dict:
        return {
            "success": True,
            "message": f"Pomodoro timer started for {minutes} minutes",
            "duration": minutes
        }

    def handle(self, intent: str, entities: Dict) -> Dict:
        task = entities.get("task") or entities.get("title", "")

        if intent in ["add_task", "new_task"]:
            return self.add_task(task)
        
        elif intent == "pomodoro" or intent == "focus_mode":
            mins = int(entities.get("minutes", 25))
            return self.start_pomodoro(mins)
        
        elif intent in ["show_tasks", "todo"]:
            return {
                "success": True,
                "message": "Here are your current tasks (demo)",
                "tasks": ["Complete Atlas Agent integration", "Study for exam"]
            }

        return {"success": False, "message": "ProductivityAgent: Command not supported"}