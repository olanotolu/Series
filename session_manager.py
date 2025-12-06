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
        
        # Add new message
        history.append({"role": role, "content": content})
        
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
