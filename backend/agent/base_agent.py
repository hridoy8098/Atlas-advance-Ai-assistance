from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import config
from backend.core.ai_engine import ai_engine


class BaseAgent(ABC):
    """সব Agent-এর Base Class"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.ai = ai_engine

    async def think(self, task: str, context: Dict = None) -> str:
        """AI দিয়ে intelligent decision নেয়"""
        prompt = f"""You are the {self.name} Agent of Atlas 7.0.
Your job: {self.description}

Task: {task}
Context: {context or 'No additional context'}

Return only the best action in clear, concise format."""
        
        try:
            response = self.ai.chat(prompt)
            return response
        except:
            return "I am thinking..."

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        pass

    def handle(self, intent: str, entities: Dict) -> Dict:
        """Default handler"""
        return {"success": False, "message": f"{self.name} cannot handle this intent yet."}