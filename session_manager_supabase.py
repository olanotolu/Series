import os
import json
from datetime import datetime
from typing import List, Dict
from supabase import create_client, Client

class SessionManager:
    """
    Manages user session history using Supabase.
    Stores conversation context per user_id (phone number) in a 'sessions' table.
    """
    
    def __init__(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            print("⚠️  SUPABASE_URL or SUPABASE_KEY not set. Session persistence will fail.")
            self.supabase = None
            return

        try:
            self.supabase: Client = create_client(url, key)
            print("   ✅ Connected to Supabase")
        except Exception as e:
            print(f"   ❌ Supabase connection error: {e}")
            self.supabase = None

    def get_history(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Get conversation history for a user."""
        if not self.supabase:
            return []

        try:
            # Fetch row for user
            response = self.supabase.table("sessions").select("history").eq("user_id", user_id).execute()
            
            if response.data and len(response.data) > 0:
                row = response.data[0]
                history = row.get("history", [])
                if isinstance(history, str):
                     try:
                         history = json.loads(history)
                     except:
                         history = []
                
                # Return last 'limit' messages
                return history[-limit:]
            return []
        except Exception as e:
            print(f"   ⚠️  Supabase get_history error: {e}")
            return []

    def add_message(self, user_id: str, role: str, content: str):
        """Add a message to user history."""
        if not self.supabase:
            return

        try:
            # 1. Get existing history
            response = self.supabase.table("sessions").select("history").eq("user_id", user_id).execute()
            
            history = []
            if response.data and len(response.data) > 0:
                 raw_history = response.data[0].get("history", [])
                 if isinstance(raw_history, str):
                     try:
                         history = json.loads(raw_history)
                     except:
                         pass
                 elif isinstance(raw_history, list):
                     history = raw_history

            # 2. Append new message
            timestamp = datetime.now().isoformat()
            history.append({"role": role, "content": content, "timestamp": timestamp})
            
            # 3. Trim (keep last 50)
            if len(history) > 50:
                history = history[-50:]
            
            # 4. Upsert
            data = {
                "user_id": user_id,
                "history": history, # Supabase handles JSON automatically if column is jsonb
                "last_seen": timestamp
            }
            self.supabase.table("sessions").upsert(data).execute()
            
        except Exception as e:
            print(f"   ⚠️  Supabase add_message error: {e}")

    def clear_history(self, user_id: str):
        """Clear history for a user."""
        if not self.supabase:
            return

        try:
            self.supabase.table("sessions").delete().eq("user_id", user_id).execute()
        except Exception as e:
            print(f"   ⚠️  Supabase clear_history error: {e}")

    def analyze_behavior(self, user_id: str) -> str:
        """
        Analyze user behavior based on message history timings.
        Returns a context string describing the user's state.
        """
        if not self.supabase:
            return "User state: Unknown (No DB)."

        try:
            response = self.supabase.table("sessions").select("history").eq("user_id", user_id).execute()
            
            if not response.data or len(response.data) == 0:
                return "User state: New interaction. Be warm and welcoming."
            
            raw_history = response.data[0].get("history", [])
            if isinstance(raw_history, str):
                 history = json.loads(raw_history)
            else:
                 history = raw_history
                 
            if not history:
                 return "User state: New interaction."

            # Filter for user messages
            user_msgs = [m for m in history if m.get("role") == "user"]
            if not user_msgs:
                return "User state: Passive/Listening."
                
            last_msg = user_msgs[-1]
            last_ts_str = last_msg.get("timestamp")
            
            if not last_ts_str:
                return "User state: Normal flow."
                
            last_ts = datetime.fromisoformat(last_ts_str)
            now = datetime.now()
            time_since_last = (now - last_ts).total_seconds()
            
            behavior_notes = []
            
            # 1. Analyze Silence
            if time_since_last > 4 * 3600: # > 4 hours
                hours = int(time_since_last / 3600)
                behavior_notes.append(f"Long silence detected ({hours} hours since last text). User might be returning after a break.")
            elif time_since_last > 300: # > 5 mins
                behavior_notes.append("User returning after a short break.")
            else:
                behavior_notes.append("Live conversation happening now.")

            # 2. Analyze Bursts
            if len(user_msgs) >= 3:
                recent_msgs = user_msgs[-3:]
                try:
                    timestamps = [datetime.fromisoformat(m.get("timestamp", now.isoformat())) for m in recent_msgs]
                    duration = (timestamps[-1] - timestamps[0]).total_seconds()
                    
                    if duration < 60:
                        behavior_notes.append("High urgency/Excitement detected (messaging rapidly). Match this energy.")
                except:
                    pass
            
            return "User Behavioral Context: " + " ".join(behavior_notes)
            
        except Exception as e:
            print(f"Error analyzing behavior: {e}")
            return "User state: Normal."
