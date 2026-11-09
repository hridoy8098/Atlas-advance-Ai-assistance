# backend/core/context_engine.py — Atlas 6.0 Context Engine
# Proactive suggestions + Context awareness + Situation understanding

import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

import config
from backend.core.memory import memory_manager
from backend.core.language import language_detector, get_lang


class ContextEngine:
    """
    Atlas 6.0 Context Engine
    - সময় বুঝে proactive suggestions
    - User behavior pattern recognition
    - Situation awareness
    - Auto-actions based on context
    """
    
    def __init__(self):
        # Current context
        self.current_context = {
            "time_of_day": None,
            "day_of_week": None,
            "user_activity": None,
            "location": None,  # From weather
            "weather": None,
            "system_state": None,
            "last_user_action": None,
            "last_user_action_time": None,
            "idle_time": 0,
        }
        
        # Context history
        self.context_history = []
        self.max_history = 50
        
        # Suggestion engine
        self.suggestions_enabled = True
        self.last_suggestion_time = None
        self.suggestion_cooldown = 300  # 5 minutes between suggestions
        
        # Pattern tracking
        self.user_patterns = {
            "active_hours": [],      # কোন সময় user active থাকে
            "frequent_tasks": {},    # কোন কাজ বারবার করে
            "frequent_apps": {},     # কোন apps বেশি use করে
            "break_time": None,      # কখন break নেয়
            "study_time": None,      # কখন পড়াশোনা করে
            "sleep_time": None,      # কখন ঘুমায় (approx)
        }
        
        # Proactive triggers
        self.triggers = self._load_triggers()
        
        # Background monitoring
        self.monitoring = False
        self.monitor_thread = None
        self.monitor_interval = 60  # Check every 60 seconds
        
        # Update context
        self._update_time_context()
        
        print(f"🧠 Context Engine initialized")
        print(f"   Time: {self.current_context['time_of_day']}")
        print(f"   Day: {self.current_context['day_of_week']}")
    
    # ===== TIME CONTEXT =====
    
    def _update_time_context(self):
        """Time-based context update করো"""
        now = datetime.now()
        hour = now.hour
        day = now.strftime("%A")
        
        # Time of day
        if 5 <= hour < 8:
            self.current_context["time_of_day"] = "early_morning"
        elif 8 <= hour < 12:
            self.current_context["time_of_day"] = "morning"
        elif 12 <= hour < 14:
            self.current_context["time_of_day"] = "noon"
        elif 14 <= hour < 17:
            self.current_context["time_of_day"] = "afternoon"
        elif 17 <= hour < 19:
            self.current_context["time_of_day"] = "evening"
        elif 19 <= hour < 22:
            self.current_context["time_of_day"] = "night"
        else:
            self.current_context["time_of_day"] = "late_night"
        
        self.current_context["day_of_week"] = day
        self.current_context["is_weekend"] = day in ["Friday", "Saturday"]
        self.current_context["hour"] = hour
    
    # ===== CONTEXT UPDATE =====
    
    def update_context(self, key: str, value: Any):
        """Context update করো"""
        self.current_context[key] = value
        
        # Track history
        self.context_history.append({
            "timestamp": datetime.now().isoformat(),
            "key": key,
            "value": value
        })
        
        # Keep history limited
        if len(self.context_history) > self.max_history:
            self.context_history = self.context_history[-self.max_history:]
    
    def get_context(self, key: str = None) -> Any:
        """Context retrieve করো"""
        if key:
            return self.current_context.get(key)
        return self.current_context.copy()
    
    def get_full_context(self) -> Dict:
        """AI prompt এর জন্য full context"""
        return {
            **self.current_context,
            "recent_actions": self.context_history[-5:],
            "patterns": self.user_patterns
        }
    
    # ===== PROACTIVE SUGGESTIONS =====
    
    def get_suggestion(self) -> Optional[str]:
        """
        Current context analyze করে suggestion return করো
        """
        if not self.suggestions_enabled:
            return None
        
        # Check cooldown
        if self.last_suggestion_time:
            elapsed = time.time() - self.last_suggestion_time
            if elapsed < self.suggestion_cooldown:
                return None
        
        self._update_time_context()
        
        suggestions = []
        time_of_day = self.current_context["time_of_day"]
        day = self.current_context["day_of_week"]
        hour = self.current_context["hour"]
        
        # ===== TIME-BASED SUGGESTIONS =====
        
        # Early morning (5-8 AM)
        if time_of_day == "early_morning":
            suggestions.extend([
                "শুভ সকাল! আজকের weather দেখবেন? ☀️",
                "Good morning! Ready to start the day?",
                "সকালের নামাজের সময় হয়ে গেছে।",
                "আজকের জন্য calendar check করবেন?",
            ])
        
        # Morning (8-12 AM) - Productivity peak
        elif time_of_day == "morning":
            suggestions.extend([
                "Morning! Ready to be productive? Let me optimize your system.",
                "সকালের শুরুতেই important tasks শেষ করে ফেলুন!",
                "আজকের email check করবেন?",
                "Focus time! গান বন্ধ করে কাজ শুরু করি?",
            ])
        
        # Noon (12-2 PM)
        elif time_of_day == "noon":
            suggestions.extend([
                "Lunch time! 🍱 20-20-20 rule: চোখের rest নিন।",
                "দুপুরের খাবার সময়! 30 min break নিন।",
                "Posture check! সোজা হয়ে বসুন।",
                "জোহরের নামাজের সময় হয়ে গেছে।",
            ])
        
        # Afternoon (2-5 PM)
        elif time_of_day == "afternoon":
            suggestions.extend([
                "Afternoon slump? এক কাপ চা খান ☕",
                "Productivity dropping? Try Pomodoro technique!",
                "চলুন দেখি আজ কতটুকু কাজ শেষ হলো।",
                "Study break নিন। Spaced repetition করে নিন।",
            ])
        
        # Evening (5-7 PM)
        elif time_of_day == "evening":
            suggestions.extend([
                "আসরের নামাজের সময়।",
                "Evening walk নিন 🚶 10 minutes refresh হবে।",
                "দিনের summary দেখবেন?",
                "আগামীকালের plan করে ফেলুন।",
            ])
        
        # Night (7-10 PM)
        elif time_of_day == "night":
            suggestions.extend([
                "এশার নামাজের সময়।",
                "Screen brightness কমিয়ে নিন (night mode)।",
                "Night study session? Flashcards review করবেন?",
                "Relax time! Music play করি? 🎵",
            ])
        
        # Late Night (10 PM - 5 AM)
        elif time_of_day == "late_night":
            suggestions.extend([
                "দেরি হয়ে গেছে! ঘুমাতে যান 🌙",
                "কাল সকালে important কাজ আছে। Rest নিন।",
                "Blue light filter on করি? চোখের জন্য ভালো।",
                "Late night coding? Coffee খান কিন্তু ঘুম ভুলবেন না! ☕",
            ])
        
        # ===== DAY-SPECIFIC =====
        
        if day == "Friday":
            suggestions.append("জুমার নামাজের প্রস্তুতি নিন।")
            suggestions.append("It's Friday! Weekend planning?")
        
        elif day == "Saturday":
            suggestions.append("Weekend! Learning mode? নতুন কিছু শিখি?")
        
        elif day == "Sunday":
            suggestions.append("কাল সোমবার! আগামী সপ্তাহের plan করে ফেলুন।")
        
        # ===== SYSTEM-BASED =====
        
        system_state = self.current_context.get("system_state", {})
        if system_state:
            cpu = system_state.get("cpu", 0)
            ram = system_state.get("ram_percent", 0)
            disk = system_state.get("disk_percent", 0)
            
            if cpu > 80:
                suggestions.append("⚠️ CPU usage high (80%+)! Heavy apps close করি?")
            if ram > 85:
                suggestions.append("⚠️ RAM almost full! Clean করি?")
            if disk > 90:
                suggestions.append("⚠️ Disk space low! Junk files clean করি?")
        
        # ===== WEATHER-BASED =====
        
        weather = self.current_context.get("weather", "")
        if "rain" in str(weather).lower():
            suggestions.append("বৃষ্টি হচ্ছে! ☔ ছাতা নিতে ভুলবেন না।")
        
        # ===== IDLE TIME =====
        
        idle_time = self.current_context.get("idle_time", 0)
        if idle_time > 600:  # 10 minutes
            suggestions.append(f"You were idle for {idle_time//60} minutes. Lock screen করবো?")
        
        # ===== PATTERN-BASED =====
        
        # Study time pattern
        if self.user_patterns.get("study_time"):
            study_hour = self.user_patterns["study_time"]
            if hour == study_hour:
                suggestions.append("📚 Study time! Flashcards ready?")
        
        # Frequent tasks
        if self.user_patterns.get("frequent_tasks"):
            top_task = max(self.user_patterns["frequent_tasks"], 
                          key=self.user_patterns["frequent_tasks"].get)
            suggestions.append(f"You often {top_task} around this time. Continue?")
        
        # ===== SELECT SUGGESTION =====
        
        if suggestions:
            import random
            suggestion = random.choice(suggestions)
            self.last_suggestion_time = time.time()
            return suggestion
        
        return None
    
    # ===== TRIGGERS =====
    
    def _load_triggers(self) -> Dict:
        """Auto-action triggers"""
        return {
            # Time triggers
            "morning_start": {
                "condition": lambda: self.current_context["time_of_day"] == "morning" and 
                                     self.current_context["hour"] == 8,
                "action": "system_agent.optimize",
                "message": "Good morning! System optimized for the day."
            },
            "prayer_fajr": {
                "condition": lambda: self.current_context["time_of_day"] == "early_morning",
                "action": "info.prayer",
                "message": "ফজরের নামাজের সময়।"
            },
            "prayer_dhuhr": {
                "condition": lambda: self.current_context["time_of_day"] == "noon",
                "action": "info.prayer",
                "message": "জোহরের নামাজের সময়।"
            },
            "prayer_asr": {
                "condition": lambda: self.current_context["time_of_day"] == "evening" and
                                    self.current_context["hour"] < 17,
                "action": "info.prayer",
                "message": "আসরের নামাজের সময়।"
            },
            "prayer_maghrib": {
                "condition": lambda: self.current_context["time_of_day"] == "evening" and
                                    18 <= self.current_context["hour"] < 19,
                "action": "info.prayer",
                "message": "মাগরিবের নামাজের সময়।"
            },
            "prayer_isha": {
                "condition": lambda: self.current_context["time_of_day"] == "night",
                "action": "info.prayer",
                "message": "এশার নামাজের সময়।"
            },
            
            # System triggers
            "high_cpu": {
                "condition": lambda: (self.current_context.get("system_state") or {}).get("cpu", 0) > 90,
                "action": "system_agent.optimize",
                "message": "⚠️ CPU critically high! Optimizing..."
            },
            "low_battery": {
                "condition": lambda: (self.current_context.get("system_state") or {}).get("battery", 100) < 15,
                "action": "system_agent.battery_saver",
                "message": "🔋 Battery low! Power saving mode on."
            },
            
            # Idle triggers
            "idle_warning": {
                "condition": lambda: self.current_context.get("idle_time", 0) > 900,
                "action": "security.lock",
                "message": "15 minutes idle. Locking for security."
            },
            
            # Eye rest (20-20-20 rule)
            "eye_rest": {
                "condition": lambda: self.current_context.get("screen_time", 0) > 1200,
                "action": "life.eye_rest",
                "message": "👁️ 20-20-20: চোখকে rest দিন। 20 feet দূরে 20 seconds তাকান।"
            },
        }
    
    def check_triggers(self) -> List[Dict]:
        """সব triggers check করে match করলে action return করো"""
        triggered = []
        
        for trigger_name, trigger_data in self.triggers.items():
            try:
                if trigger_data["condition"]():
                    triggered.append({
                        "trigger": trigger_name,
                        "action": trigger_data["action"],
                        "message": trigger_data["message"]
                    })
            except Exception as e:
                print(f"⚠️ Trigger check error [{trigger_name}]: {e}")
        
        return triggered
    
    # ===== PATTERN LEARNING =====
    
    def track_user_action(self, action: str, metadata: Dict = None):
        """User action track করে pattern learn করো"""
        now = datetime.now()
        hour = now.hour
        
        # Track active hours
        if hour not in self.user_patterns["active_hours"]:
            self.user_patterns["active_hours"].append(hour)
        
        # Track frequent tasks
        if action in self.user_patterns["frequent_tasks"]:
            self.user_patterns["frequent_tasks"][action] += 1
        else:
            self.user_patterns["frequent_tasks"][action] = 1
        
        # Update last action
        self.current_context["last_user_action"] = action
        self.current_context["last_user_action_time"] = now.isoformat()
        self.current_context["idle_time"] = 0
        
        # Learn patterns
        if "study" in action.lower() or "flashcard" in action.lower() or "exam" in action.lower():
            if not self.user_patterns["study_time"]:
                self.user_patterns["study_time"] = hour
        
        # Save to memory
        memory_manager.add_fact(
            fact=f"User performed action: {action} at {now.strftime('%H:%M')}",
            category="behavior",
            source="context_engine"
        )
    
    def update_idle_time(self):
        """Idle time update করো"""
        last_action = self.current_context.get("last_user_action_time")
        if last_action:
            try:
                last_time = datetime.fromisoformat(last_action)
                idle_seconds = (datetime.now() - last_time).total_seconds()
                self.current_context["idle_time"] = idle_seconds
            except:
                pass
    
    # ===== SYSTEM STATE TRACKING =====
    
    def update_system_state(self, cpu: float = None, ram: float = None, 
                            disk: float = None, battery: float = None):
        """System metrics update করো"""
        state = self.current_context.get("system_state", {})
        
        if cpu is not None:
            state["cpu"] = cpu
        if ram is not None:
            state["ram_percent"] = ram
        if disk is not None:
            state["disk_percent"] = disk
        if battery is not None:
            state["battery"] = battery
        
        self.current_context["system_state"] = state
    
    def update_weather(self, weather_data: Dict):
        """Weather data update করো"""
        if weather_data:
            self.current_context["weather"] = weather_data.get("description", "")
            self.current_context["temperature"] = weather_data.get("temp", 0)
    
    # ===== BACKGROUND MONITORING =====
    
    def start_monitoring(self):
        """Background monitoring start করো"""
        if self.monitoring:
            return
        
        self.monitoring = True
        
        def monitor_loop():
            print("👁️ Context monitoring started")
            while self.monitoring:
                try:
                    # Update time context
                    self._update_time_context()
                    
                    # Update idle time
                    self.update_idle_time()
                    
                    # Check triggers
                    triggers = self.check_triggers()
                    for trigger in triggers:
                        print(f"⚡ Trigger: {trigger['trigger']} → {trigger['message']}")
                        
                        # Send to UI if possible
                        try:
                            import eel
                            eel.showNotification("Atlas", trigger["message"], "info")()
                        except:
                            pass
                    
                    # Get suggestion
                    suggestion = self.get_suggestion()
                    if suggestion:
                        print(f"💡 Suggestion: {suggestion}")
                        try:
                            import eel
                            eel.showNotification("Atlas Suggests", suggestion, "info")()
                        except:
                            pass
                    
                except Exception as e:
                    print(f"⚠️ Monitor error: {e}")
                
                time.sleep(self.monitor_interval)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Background monitoring বন্ধ করো"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("👁️ Context monitoring stopped")
    
    # ===== CONTEXT-AWARE RESPONSE =====
    
    def get_system_prompt_context(self) -> str:
        """AI system prompt এর জন্য context information"""
        self._update_time_context()
        
        ctx = self.current_context
        
        context_str = f"""
Current Context:
- Time: {ctx['time_of_day'].replace('_', ' ').title()}
- Day: {ctx['day_of_week']} ({'Weekend' if ctx.get('is_weekend') else 'Weekday'})
- Hour: {ctx.get('hour', 'N/A')}
"""
        
        if ctx.get("weather"):
            context_str += f"- Weather: {ctx['weather']}, {ctx.get('temperature', 'N/A')}°C\n"
        
        if ctx.get("system_state"):
            state = ctx["system_state"]
            context_str += f"- CPU: {state.get('cpu', 'N/A')}%, RAM: {state.get('ram_percent', 'N/A')}%\n"
        
        if self.user_patterns.get("frequent_tasks"):
            top_tasks = sorted(self.user_patterns["frequent_tasks"].items(), 
                             key=lambda x: x[1], reverse=True)[:3]
            tasks_str = ", ".join(f"{t[0]}({t[1]}x)" for t in top_tasks)
            context_str += f"- Frequent tasks: {tasks_str}\n"
        
        return context_str
    
    # ===== STATS =====
    
    def get_context_summary(self) -> Dict:
        """Current context summary"""
        self._update_time_context()
        
        return {
            "time": self.current_context["time_of_day"],
            "day": self.current_context["day_of_week"],
            "is_weekend": self.current_context.get("is_weekend", False),
            "weather": self.current_context.get("weather", "Unknown"),
            "idle_time": self.current_context.get("idle_time", 0),
            "patterns_learned": len(self.user_patterns["frequent_tasks"]),
            "active_hours": self.user_patterns["active_hours"],
            "top_tasks": sorted(self.user_patterns["frequent_tasks"].items(), 
                              key=lambda x: x[1], reverse=True)[:5],
        }
    
    # ===== CLEANUP =====
    
    def cleanup(self):
        """Resources clean করো"""
        self.stop_monitoring()
        print("🧠 Context engine cleaned up")
    
    def __del__(self):
        self.cleanup()


# ===== Singleton =====
context_engine = ContextEngine()


# ===== EEL EXPOSED FUNCTIONS =====
def setup_context_engine_eel():
    """Frontend থেকে call করার জন্য eel functions"""
    try:
        import eel
        
        @eel.expose
        def get_context():
            """Current context return করো"""
            return context_engine.get_context_summary()
        
        @eel.expose
        def get_suggestion():
            """Proactive suggestion"""
            return context_engine.get_suggestion()
        
        @eel.expose
        def start_context_monitoring():
            """Background monitoring start"""
            context_engine.start_monitoring()
            return True
        
        @eel.expose
        def stop_context_monitoring():
            """Background monitoring stop"""
            context_engine.stop_monitoring()
            return True
        
        print("✅ Context engine eel functions registered")
        
    except ImportError:
        print("⚠️ Eel not available")
    except Exception as e:
        print(f"⚠️ Context engine eel setup error: {e}")


# ===== Auto-start monitoring =====
if __name__ != "__main__":
    # Auto-start in background
    context_engine.start_monitoring()
