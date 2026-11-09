from typing import Dict, List
import config
from .base_agent import BaseAgent


class MediaAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Media Agent",
            description="Handles YouTube, image generation, subtitles, memes, and media processing"
        )

    def get_capabilities(self) -> List[str]:
        return ["youtube_download", "generate_image", "generate_meme", 
                "create_subtitle", "play_music", "download_video"]

    def youtube_search(self, query: str) -> Dict:
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        return {
            "success": True,
            "message": f"Searching YouTube: {query}",
            "url": url
        }

    def generate_image(self, prompt: str) -> Dict:
        try:
            # ai_engine এ generate_image ফাংশন থাকলে ব্যবহার করবে
            result = self.ai.generate_image(prompt) if hasattr(self.ai, 'generate_image') else None
            return {
                "success": True,
                "prompt": prompt,
                "message": "Image generated successfully (demo)",
            }
        except:
            return {"success": False, "message": "Image generation failed"}

    def generate_meme(self, top_text: str, bottom_text: str) -> Dict:
        return {
            "success": True,
            "message": f"Meme created: Top='{top_text}' | Bottom='{bottom_text}'",
            "top": top_text,
            "bottom": bottom_text
        }

    def handle(self, intent: str, entities: Dict) -> Dict:
        query = entities.get("query") or entities.get("prompt", "")

        if intent in ["youtube", "play_youtube", "youtube_search"]:
            return self.youtube_search(query)
        
        elif intent == "generate_image":
            return self.generate_image(query)
        
        elif intent == "generate_meme":
            return self.generate_meme(
                entities.get("top_text", "Top Text"), 
                entities.get("bottom_text", "Bottom Text")
            )
        
        return {"success": False, "message": "MediaAgent: Command not supported yet"}