from typing import Dict, List
import config
from .base_agent import BaseAgent


class SecurityAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Security Agent",
            description="Handles privacy, password management, breach check, and system security"
        )

    def get_capabilities(self) -> List[str]:
        return ["check_breach", "password_strength", "privacy_mode", "lock_system"]

    def check_breach(self, email: str) -> Dict:
        return {
            "success": True,
            "email": email,
            "breached": False,
            "message": f"No breaches found for {email} (demo)"
        }

    def handle(self, intent: str, entities: Dict) -> Dict:
        if intent in ["privacy_mode", "enable_privacy"]:
            return {"success": True, "message": "Privacy mode activated"}
        
        elif intent in ["lock", "lock_system"]:
            return {"success": True, "message": "System locked successfully"}
        
        elif intent == "check_breach":
            email = entities.get("email", "")
            return self.check_breach(email)
        
        return {"success": False, "message": "SecurityAgent: Command not supported"}