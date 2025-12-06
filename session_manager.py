import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict

DB_PATH = "sessions.db"

class SessionManager:
    """
    Manages user session history using SQLite.
    Stores conversation context per user_id (phone number).
    """
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                user_id TEXT PRIMARY KEY,
                history TEXT,  -- JSON list of messages
                last_seen TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def get_history(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get conversation history for a user.
        
        Args:
            user_id: Unique identifier (phone number)
            limit: Max number of recent messages to return (default 10)
        
        Returns:
            List of message dicts [{"role": "user", "content": "..."}]
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT history FROM sessions WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        conn.close()
        
        if row and row[0]:
            try:
                history = json.loads(row[0])
                # Return last 'limit' messages
                return history[-limit:]
            except json.JSONDecodeError:
                return []
        return []

    def add_message(self, user_id: str, role: str, content: str):
        """
        Add a message to user history.
        
        Args:
            user_id: Unique identifier (phone number)
            role: "user" or "assistant" (or "system")
            content: The text content
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get existing history
        c.execute('SELECT history FROM sessions WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        
        if row and row[0]:
            try:
                history = json.loads(row[0])
            except json.JSONDecodeError:
                history = []
        else:
            history = []
        
        # Add new message with timestamp
        timestamp = datetime.now().isoformat()
        history.append({"role": role, "content": content, "timestamp": timestamp})
        
        # Trim if getting too huge (e.g. keep last 50 for storage, though we retrieve fewer)
        if len(history) > 50:
            history = history[-50:]
            
        # Update DB
        now = datetime.now().isoformat()
        c.execute('''
            INSERT OR REPLACE INTO sessions (user_id, history, last_seen)
            VALUES (?, ?, ?)
        ''', (user_id, json.dumps(history), now))
        
        conn.commit()
        conn.close()

    def clear_history(self, user_id: str):
        """Clear history for a user."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

    def analyze_behavior(self, user_id: str) -> str:
        """
        Analyze user behavior based on message history timings.
        Returns a context string describing the user's state.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT history, last_seen FROM sessions WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return "User state: New interaction. Be warm and welcoming."
            
        try:
            history = json.loads(row[0])
            if not history:
                return "User state: New interaction."
                
            # Filter for user messages only to analyze THEIR behavior
            user_msgs = [m for m in history if m.get("role") == "user"]
            if not user_msgs:
                return "User state: Passive/Listening."
                
            last_msg = user_msgs[-1]
            last_ts_str = last_msg.get("timestamp")
            
            # If historical messages don't have timestamps yet, skip analysis
            if not last_ts_str:
                return "User state: Normal flow."
                
            last_ts = datetime.fromisoformat(last_ts_str)
            now = datetime.now()
            time_since_last = (now - last_ts).total_seconds()
            
            behavior_notes = []
            
            # 1. Analyze Silence (Gap since last message)
            if time_since_last > 4 * 3600: # > 4 hours
                hours = int(time_since_last / 3600)
                behavior_notes.append(f"Long silence detected ({hours} hours since last text). User might be returning after a break.")
            elif time_since_last > 300: # > 5 mins (standard gap)
                behavior_notes.append("User returning after a short break.")
            else:
                behavior_notes.append("Live conversation happening now.")

            # 2. Analyze Bursts (Recent density)
            # Check last 3 user messages
            if len(user_msgs) >= 3:
                recent_msgs = user_msgs[-3:]
                try:
                    timestamps = [datetime.fromisoformat(m.get("timestamp", now.isoformat())) for m in recent_msgs]
                    duration = (timestamps[-1] - timestamps[0]).total_seconds()
                    
                    if duration < 60: # 3 messages in < 60 seconds
                        behavior_notes.append("High urgency/Excitement detected (messaging rapidly). Match this energy.")
                except:
                    pass
            
            return "User Behavioral Context: " + " ".join(behavior_notes)
            
        except Exception as e:
            print(f"Error analyzing behavior: {e}")
            return "User state: Normal."
