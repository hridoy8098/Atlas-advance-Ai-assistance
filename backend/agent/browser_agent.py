# backend/agent/browser_agent.py — Atlas 6.0 Browser Controller

import webbrowser
import subprocess
import platform
from typing import Optional


class BrowserAgent:
    """Browser control agent"""
    
    def __init__(self):
        self.system = platform.system()
        print(f"🌐 Browser Agent initialized")
    
    # ===== BROWSER =====
    
    def open_url(self, url: str) -> bool:
        """Open URL in browser"""
        if not url.startswith('http'):
            url = 'https://' + url
        
        try:
            webbrowser.open(url)
            print(f"🌐 Opened: {url}")
            return True
        except:
            return False
    
    def search(self, query: str, engine: str = "google") -> bool:
        """Search on web"""
        engines = {
            "google": "https://www.google.com/search?q=",
            "youtube": "https://www.youtube.com/results?search_query=",
            "wikipedia": "https://en.wikipedia.org/wiki/",
            "github": "https://github.com/search?q=",
            "amazon": "https://www.amazon.com/s?k=",
        }
        
        base = engines.get(engine.lower(), engines["google"])
        url = base + query.replace(' ', '+')
        return self.open_url(url)
    
    def open_youtube(self, query: str = "") -> bool:
        """Open YouTube"""
        if query:
            return self.search(query, "youtube")
        return self.open_url("https://youtube.com")
    
    def open_github(self, query: str = "") -> bool:
        """Open GitHub"""
        if query:
            return self.search(query, "github")
        return self.open_url("https://github.com")
    
    def open_gmail(self) -> bool:
        """Open Gmail"""
        return self.open_url("https://mail.google.com")
    
    def open_drive(self) -> bool:
        """Open Google Drive"""
        return self.open_url("https://drive.google.com")
    
    def open_maps(self, location: str = "") -> bool:
        """Open Google Maps"""
        if location:
            return self.open_url(f"https://www.google.com/maps/search/{location}")
        return self.open_url("https://maps.google.com")
    
    def open_social(self, platform: str) -> bool:
        """Open social media"""
        sites = {
            "facebook": "https://facebook.com",
            "twitter": "https://twitter.com",
            "instagram": "https://instagram.com",
            "linkedin": "https://linkedin.com",
            "reddit": "https://reddit.com",
        }
        url = sites.get(platform.lower())
        if url:
            return self.open_url(url)
        return False
    
    # ===== SHORTCUTS =====
    
    def quick_open(self, shortcut: str) -> bool:
        """Quick shortcuts"""
        shortcuts = {
            "mail": self.open_gmail,
            "gmail": self.open_gmail,
            "drive": self.open_drive,
            "maps": self.open_maps,
            "youtube": self.open_youtube,
            "github": self.open_github,
            "fb": lambda: self.open_social("facebook"),
            "facebook": lambda: self.open_social("facebook"),
        }
        
        func = shortcuts.get(shortcut.lower())
        if func:
            return func()
        return self.search(shortcut)


# Singleton
browser_agent = BrowserAgent()