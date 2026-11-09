import webbrowser
import requests
from urllib.parse import quote
from typing import Dict, List
import config
from .base_agent import BaseAgent


class WebAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Web Agent",
            description="Advanced web browsing, research, summarization and online tools"
        )

    def get_capabilities(self) -> List[str]:
        return ["open_url", "search_web", "research", "summarize_url", "wikipedia_search"]

    def open_url(self, url: str) -> Dict:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return {"success": True, "url": url, "message": f"Opened {url}"}

    def search_web(self, query: str) -> Dict:
        search_url = f"https://www.google.com/search?q={quote(query)}"
        webbrowser.open(search_url)
        return {"success": True, "query": query, "url": search_url}

    def research(self, topic: str) -> Dict:
        try:
            prompt = f"""Provide a concise, well-organized research summary about: {topic}
Include: definition, key facts, current status, and important sources."""
            summary = self.ai.chat(prompt)
            
            self.open_url(f"https://www.google.com/search?q={quote(topic)}")
            
            return {
                "success": True,
                "topic": topic,
                "summary": summary[:700],
                "action_taken": "Google search opened"
            }
        except:
            return {"success": False, "message": "Research failed"}

    def handle(self, intent: str, entities: Dict) -> Dict:
        query = entities.get("query") or entities.get("topic") or ""
        url = entities.get("url") or query

        if intent in ["open_url", "open_website"]:
            return self.open_url(url)
        elif intent in ["search", "search_web", "google"]:
            return self.search_web(query)
        elif intent in ["research", "research_topic"]:
            return self.research(query)
        
        return {"success": False, "message": "WebAgent: Command not supported"}