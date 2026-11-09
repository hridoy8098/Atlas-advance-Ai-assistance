from typing import Dict, List
import subprocess
import webbrowser
import config
from .base_agent import BaseAgent


class AppAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="App Agent",
            description="Opens desktop and web applications"
        )

    def get_capabilities(self) -> List[str]:
        return ["open_app", "open_youtube", "open_chrome", "open_vscode"]

    def open_app(self, app_name: str) -> Dict:
        name = app_name.lower().strip()

        # Web Apps
        web_map = {
            "youtube": "https://youtube.com",
            "yt": "https://youtube.com",
            "chrome": "https://google.com",
            "google": "https://google.com",
            "gmail": "https://mail.google.com",
            "github": "https://github.com",
            "vscode": "https://vscode.dev",
            "chatgpt": "https://chat.openai.com",
            "facebook": "https://facebook.com",
            "whatsapp": "https://web.whatsapp.com"
        }

        if name in web_map:
            webbrowser.open(web_map[name])
            return {"success": True, "message": f"✅ Opened {app_name}"}

        # Try desktop app
        try:
            subprocess.Popen(name, shell=True)
            return {"success": True, "message": f"✅ Trying to open {app_name}..."}
        except:
            webbrowser.open(f"https://{name}.com")
            return {"success": True, "message": f"✅ Opened {app_name} in browser"}

    def handle(self, intent: str, entities: Dict) -> Dict:
        app = entities.get("app_name") or entities.get("app") or entities.get("query", "")
        if app:
            return self.open_app(app)
        return {"success": False, "message": "কোন অ্যাপ খুলতে চান?"}