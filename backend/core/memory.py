# backend/core/memory.py — Atlas 6.0 Memory System
# Short-term + Long-term memory + Vector DB (ChromaDB)

import os
import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    print("⚠️ pip install chromadb (optional, vector search এর জন্য)")
    CHROMADB_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    print("⚠️ pip install numpy (optional)")
    NUMPY_AVAILABLE = False

import config


class MemoryManager:
    """
    Atlas 6.0 Memory System
    - Short-term memory (recent conversations)
    - Long-term memory (SQLite)
    - Vector memory (ChromaDB - semantic search)
    - Memory types: conversation, fact, preference, event
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(config.DB_MEMORY)
        
        # Short-term memory (in RAM)
        self.short_term = []  # Recent conversations
        self.max_short_term = config.SHORT_TERM_MEMORY_SIZE
        
        # Working memory (current context)
        self.working_memory = {
            "current_topic": None,
            "current_task": None,
            "user_mood": None,
            "last_action": None,
            "context_stack": [],  # Nested contexts
        }
        
        # Long-term memory (SQLite)
        self.conn = None
        self._init_database()
        
        # Vector memory (ChromaDB)
        self.chroma_client = None
        self.chroma_collection = None
        self._init_vector_db()
        
        # Memory stats
        self.stats = {
            "total_conversations": 0,
            "total_facts": 0,
            "total_preferences": 0,
            "total_events": 0,
            "last_cleanup": time.time(),
        }
        
        # Load stats
        self._load_stats()
        
        print(f"🧠 Memory Manager initialized")
        print(f"   Short-term: {self.max_short_term} items")
        print(f"   Long-term: SQLite ({self.db_path})")
        print(f"   Vector DB: {'✅ ChromaDB' if self.chroma_collection else '❌ Disabled'}")
    
    # ===== DATABASE INIT =====
    
    def _init_database(self):
        """SQLite database initialize করো"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            
            cursor = self.conn.cursor()
            
            # Conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL,           -- "user" or "assistant"
                    content TEXT NOT NULL,
                    language TEXT DEFAULT 'en',
                    topic TEXT,
                    sentiment TEXT,
                    importance INTEGER DEFAULT 1, -- 1-10
                    embedding_id TEXT,            -- ChromaDB reference
                    metadata TEXT                 -- JSON extra data
                )
            ''')
            
            # Facts table (learned facts about user)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL,
                    category TEXT,                -- "personal", "preference", "knowledge"
                    confidence REAL DEFAULT 1.0,   -- 0-1
                    source TEXT,                  -- where learned from
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT
                )
            ''')
            
            # Preferences table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # Events table (calendar, reminders)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    event_type TEXT,              -- "meeting", "reminder", "deadline"
                    start_time TEXT,
                    end_time TEXT,
                    is_completed INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # Memory index (for fast lookup)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    memory_type TEXT NOT NULL,    -- "conversation", "fact", "event"
                    memory_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_topic ON conversations(topic)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_prefs_key ON preferences(key)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_time ON events(start_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_keyword ON memory_index(keyword)')
            
            self.conn.commit()
            print("   SQLite tables ready")
            
        except Exception as e:
            print(f"❌ Database init error: {e}")
            self.conn = None
    
    def _init_vector_db(self):
        """ChromaDB vector database initialize করো"""
        if not CHROMADB_AVAILABLE or not config.LONG_TERM_MEMORY_ENABLED:
            return
        
        try:
            chroma_path = str(config.DATA_DIR / "chromadb")
            
            # Support both old and new chromadb API
            try:
                # New API (chromadb >= 0.4.0)
                self.chroma_client = chromadb.PersistentClient(path=chroma_path)
            except AttributeError:
                # Old API fallback
                self.chroma_client = chromadb.Client(Settings(
                    persist_directory=chroma_path,
                    anonymized_telemetry=False
                ))
            
            # Get or create collection
            try:
                self.chroma_collection = self.chroma_client.get_collection("atlas_memory")
            except Exception:
                self.chroma_collection = self.chroma_client.create_collection(
                    name="atlas_memory",
                    metadata={"description": "Atlas 6.0 long-term memory"}
                )
            
            print(f"   ChromaDB collection: {self.chroma_collection.count()} documents")
            
        except Exception as e:
            print(f"⚠️ ChromaDB init error: {e}")
            self.chroma_client = None
            self.chroma_collection = None
    
    # ===== SHORT-TERM MEMORY =====
    
    def add_to_short_term(self, role: str, content: str, metadata: Dict = None):
        """Short-term memory তে যোগ করো"""
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.short_term.append(entry)
        
        # Keep only last N items
        if len(self.short_term) > self.max_short_term:
            # Move oldest to long-term before removing
            oldest = self.short_term.pop(0)
            self._archive_to_long_term(oldest)
    
    def get_short_term(self, limit: int = None) -> List[Dict]:
        """Short-term memory return করো"""
        limit = limit or self.max_short_term
        return self.short_term[-limit:]
    
    def get_recent_conversation(self, n: int = 10) -> List[Dict]:
        """Recent conversation for AI context"""
        return [
            {"role": entry["role"], "content": entry["content"]}
            for entry in self.short_term[-n:]
        ]
    
    def clear_short_term(self):
        """Short-term memory clear করো"""
        # Archive to long-term first
        for entry in self.short_term:
            self._archive_to_long_term(entry)
        self.short_term = []
        print("🗑️ Short-term memory cleared")
    
    # ===== LONG-TERM MEMORY =====
    
    def add_conversation(self, role: str, content: str, 
                         language: str = "en", topic: str = None,
                         importance: int = 1) -> int:
        """Conversation long-term memory তে save করো"""
        if self.conn is None:
            return -1
        
        try:
            cursor = self.conn.cursor()
            
            timestamp = datetime.now().isoformat()
            sentiment = self._analyze_sentiment(content)
            
            cursor.execute('''
                INSERT INTO conversations (timestamp, role, content, language, topic, sentiment, importance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, role, content, language, topic, sentiment, importance))
            
            conv_id = cursor.lastrowid
            
            # Add to memory index
            keywords = self._extract_keywords(content)
            for keyword in keywords:
                cursor.execute('''
                    INSERT INTO memory_index (keyword, memory_type, memory_id, timestamp)
                    VALUES (?, 'conversation', ?, ?)
                ''', (keyword, conv_id, timestamp))
            
            self.conn.commit()
            self.stats["total_conversations"] += 1
            
            # Also add to vector DB
            if self.chroma_collection:
                self._add_to_vector_db(
                    doc_id=f"conv_{conv_id}",
                    text=content,
                    metadata={"role": role, "topic": topic, "timestamp": timestamp}
                )
            
            return conv_id
            
        except Exception as e:
            print(f"❌ Add conversation error: {e}")
            return -1
    
    def add_fact(self, fact: str, category: str = "general", 
                 confidence: float = 1.0, source: str = "conversation") -> int:
        """Learned fact save করো"""
        if self.conn is None:
            return -1
        
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()
            
            # Check if fact already exists
            cursor.execute('SELECT id FROM facts WHERE fact = ?', (fact,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute('''
                    UPDATE facts SET confidence = ?, updated_at = ?, access_count = access_count + 1
                    WHERE id = ?
                ''', (confidence, now, existing["id"]))
                self.conn.commit()
                return existing["id"]
            
            # Insert new
            cursor.execute('''
                INSERT INTO facts (fact, category, confidence, source, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (fact, category, confidence, source, now))
            
            fact_id = cursor.lastrowid
            
            # Add to memory index
            keywords = self._extract_keywords(fact)
            for keyword in keywords:
                cursor.execute('''
                    INSERT INTO memory_index (keyword, memory_type, memory_id, timestamp)
                    VALUES (?, 'fact', ?, ?)
                ''', (keyword, fact_id, now))
            
            self.conn.commit()
            self.stats["total_facts"] += 1
            
            return fact_id
            
        except Exception as e:
            print(f"❌ Add fact error: {e}")
            return -1
    
    def set_preference(self, key: str, value: str, category: str = "general"):
        """User preference save করো"""
        if self.conn is None:
            return
        
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO preferences (key, value, category, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (key, str(value), category, now))
            
            self.conn.commit()
            self.stats["total_preferences"] += 1
            
        except Exception as e:
            print(f"❌ Set preference error: {e}")
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """User preference retrieve করো"""
        if self.conn is None:
            return default
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT value FROM preferences WHERE key = ?', (key,))
            row = cursor.fetchone()
            
            return row["value"] if row else default
            
        except Exception as e:
            return default
    
    # ===== MEMORY RETRIEVAL =====
    
    def search_memory(self, query: str, memory_type: str = None, limit: int = 10) -> List[Dict]:
        """Memory search - keyword based"""
        if self.conn is None:
            return []
        
        try:
            cursor = self.conn.cursor()
            keywords = self._extract_keywords(query)
            
            if not keywords:
                return []
            
            # Build query
            placeholders = ','.join(['?' for _ in keywords])
            sql = f'''
                SELECT DISTINCT m.memory_type, m.memory_id, m.timestamp
                FROM memory_index m
                WHERE m.keyword IN ({placeholders})
            '''
            
            if memory_type:
                sql += ' AND m.memory_type = ?'
                params = keywords + [memory_type]
            else:
                params = keywords
            
            sql += ' ORDER BY m.timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                memory = self._get_memory_by_id(row["memory_type"], row["memory_id"])
                if memory:
                    memory["memory_type"] = row["memory_type"]
                    memory["relevance"] = 1.0  # Simple relevance
                    results.append(memory)
            
            return results
            
        except Exception as e:
            print(f"❌ Memory search error: {e}")
            return []
    
    def semantic_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Vector similarity search (ChromaDB)"""
        if not self.chroma_collection:
            return []
        
        try:
            results = self.chroma_collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            formatted = []
            if results and results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    formatted.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0,
                        "id": results['ids'][0][i] if results['ids'] else None
                    })
            
            return formatted
            
        except Exception as e:
            print(f"❌ Semantic search error: {e}")
            return []
    
    def get_conversation_context(self, query: str = None, limit: int = 5) -> str:
        """AI context এর জন্য formatted memory string"""
        # Get recent conversations
        recent = self.get_short_term(limit)
        
        # Get relevant facts if query provided
        facts = []
        if query:
            facts = self.search_memory(query, "fact", 3)
        
        # Format context
        context_parts = []
        
        if facts:
            context_parts.append("**Relevant facts:**")
            for fact in facts:
                context_parts.append(f"- {fact.get('fact', fact.get('content', ''))}")
        
        if recent:
            context_parts.append("\n**Recent conversation:**")
            for entry in recent:
                role = "User" if entry["role"] == "user" else "Atlas"
                context_parts.append(f"{role}: {entry['content'][:200]}")
        
        return "\n".join(context_parts)
    
    # ===== WORKING MEMORY =====
    
    def set_context(self, key: str, value: Any):
        """Working memory update করো"""
        self.working_memory[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Working memory retrieve করো"""
        return self.working_memory.get(key, default)
    
    def push_context(self, context_name: str):
        """Context stack এ push করো (nested conversations)"""
        self.working_memory["context_stack"].append({
            "name": context_name,
            "previous_topic": self.working_memory.get("current_topic"),
            "timestamp": datetime.now().isoformat()
        })
    
    def pop_context(self) -> Optional[Dict]:
        """Context stack থেকে pop করো"""
        if self.working_memory["context_stack"]:
            return self.working_memory["context_stack"].pop()
        return None
    
    # ===== HELPER FUNCTIONS =====
    
    def _archive_to_long_term(self, entry: Dict):
        """Short-term → Long-term archive"""
        if entry["role"] in ["user", "assistant"]:
            self.add_conversation(
                role=entry["role"],
                content=entry["content"],
                language=entry.get("metadata", {}).get("language", "en")
            )
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Simple keyword extraction"""
        if not text:
            return []
        
        # Remove punctuation
        import string
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Split and filter
        words = text.lower().split()
        
        # Filter stop words (basic English)
        stop_words = {'the', 'is', 'are', 'was', 'were', 'a', 'an', 'in', 'on', 'at', 
                      'to', 'for', 'of', 'and', 'or', 'but', 'it', 'i', 'you', 'he', 
                      'she', 'we', 'they', 'my', 'your', 'this', 'that', 'with', 'from'}
        
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        
        # Return unique keywords
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)
                if len(unique) >= max_keywords:
                    break
        
        return unique
    
    def _analyze_sentiment(self, text: str) -> Optional[str]:
        """Basic sentiment analysis"""
        if not text:
            return None
        
        text_lower = text.lower()
        
        positive_words = ['ভালো', 'সুন্দর', 'দারুণ', 'চমৎকার', 'অসাধারণ', 'খুশি',
                         'good', 'great', 'nice', 'excellent', 'awesome', 'happy', 'love']
        negative_words = ['খারাপ', 'বাজে', 'কষ্ট', 'দুঃখ', 'রাগ', 'ঘৃণা',
                         'bad', 'terrible', 'awful', 'sad', 'angry', 'hate', 'worst']
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"
    
    def _get_memory_by_id(self, memory_type: str, memory_id: int) -> Optional[Dict]:
        """ID দিয়ে memory retrieve করো"""
        if self.conn is None:
            return None
        
        try:
            cursor = self.conn.cursor()
            
            if memory_type == "conversation":
                cursor.execute('SELECT * FROM conversations WHERE id = ?', (memory_id,))
            elif memory_type == "fact":
                cursor.execute('SELECT * FROM facts WHERE id = ?', (memory_id,))
            else:
                return None
            
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except Exception:
            return None
    
    def _add_to_vector_db(self, doc_id: str, text: str, metadata: Dict):
        """ChromaDB তে document add করো"""
        if not self.chroma_collection:
            return
        
        try:
            self.chroma_collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[doc_id]
            )
        except Exception as e:
            print(f"⚠️ Vector DB add error: {e}")
    
    # ===== STATS & MAINTENANCE =====
    
    def _load_stats(self):
        """Database stats load করো"""
        if self.conn is None:
            return
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM conversations')
            self.stats["total_conversations"] = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM facts')
            self.stats["total_facts"] = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM preferences')
            self.stats["total_preferences"] = cursor.fetchone()[0]
        except:
            pass
    
    def get_stats(self) -> Dict:
        """Memory statistics return করো"""
        stats = self.stats.copy()
        stats["short_term_count"] = len(self.short_term)
        
        if self.chroma_collection:
            stats["vector_count"] = self.chroma_collection.count()
        
        return stats
    
    def cleanup_old_memories(self, days: int = 30):
        """পুরনো memories clean করো"""
        if self.conn is None:
            return
        
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            cursor = self.conn.cursor()
            
            # Delete old conversations
            cursor.execute('DELETE FROM conversations WHERE timestamp < ? AND importance < 5', (cutoff,))
            deleted_conv = cursor.rowcount
            
            # Delete orphaned index entries
            cursor.execute('''
                DELETE FROM memory_index 
                WHERE memory_type = 'conversation' 
                AND memory_id NOT IN (SELECT id FROM conversations)
            ''')
            
            self.conn.commit()
            
            print(f"🧹 Cleaned {deleted_conv} old conversations")
            self.stats["last_cleanup"] = time.time()
            
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
    
    def export_memories(self, filepath: str = None) -> str:
        """সব memories JSON এ export করো"""
        if self.conn is None:
            return ""
        
        filepath = filepath or str(config.BACKUPS_DIR / f"memory_export_{datetime.now():%Y%m%d_%H%M%S}.json")
        
        try:
            cursor = self.conn.cursor()
            
            # Export conversations
            cursor.execute('SELECT * FROM conversations ORDER BY timestamp DESC LIMIT 1000')
            conversations = [dict(row) for row in cursor.fetchall()]
            
            # Export facts
            cursor.execute('SELECT * FROM facts')
            facts = [dict(row) for row in cursor.fetchall()]
            
            # Export preferences
            cursor.execute('SELECT * FROM preferences')
            preferences = [dict(row) for row in cursor.fetchall()]
            
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "conversations": conversations,
                "facts": facts,
                "preferences": preferences,
                "stats": self.get_stats()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Memories exported to: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Export error: {e}")
            return ""
    
    # ===== CLEANUP =====
    
    def cleanup(self):
        """Resources clean করো"""
        if self.conn:
            self.conn.close()
        print("🧠 Memory cleaned up")
    
    def __del__(self):
        self.cleanup()


# ===== Singleton =====
memory_manager = MemoryManager()


# ===== EEL EXPOSED FUNCTIONS =====
def setup_memory_eel():
    """Frontend থেকে call করার জন্য eel functions"""
    try:
        import eel
        
        @eel.expose
        def remember_this(key, value):
            """Quick memory save"""
            memory_manager.set_preference(key, value)
            return True
        
        @eel.expose
        def recall_this(key):
            """Quick memory recall"""
            return memory_manager.get_preference(key)
        
        @eel.expose
        def search_my_memory(query):
            """Memory search"""
            results = memory_manager.search_memory(query)
            return [{"type": r.get("memory_type"), "content": r.get("content", r.get("fact", ""))} 
                    for r in results[:5]]
        
        @eel.expose
        def get_memory_stats():
            """Memory statistics"""
            return memory_manager.get_stats()
        
        @eel.expose
        def clear_chat_history():
            """Chat history clear"""
            memory_manager.clear_short_term()
            try:
                from backend.core.ai_engine import ai_engine
                ai_engine.clear_history()
            except Exception:
                pass
            return True
        
        print("✅ Memory eel functions registered")
        
    except ImportError:
        print("⚠️ Eel not available")
    except Exception as e:
        print(f"⚠️ Memory eel setup error: {e}")
