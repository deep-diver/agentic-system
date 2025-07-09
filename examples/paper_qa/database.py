import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

DATABASE_PATH = "chat_history.db"

class ChatDatabase:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create chat_sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    preview TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create chat_messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('user', 'bot', 'error')),
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_id 
                ON chat_messages (session_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_updated_at 
                ON chat_sessions (updated_at DESC)
            """)
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def create_or_update_session(self, session_id: str, title: str, preview: str) -> None:
        """Create a new session or update existing one"""
        current_time = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if session exists
            cursor.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # Update existing session
                cursor.execute("""
                    UPDATE chat_sessions 
                    SET title = ?, preview = ?, updated_at = ?
                    WHERE id = ?
                """, (title, preview, current_time, session_id))
            else:
                # Create new session
                cursor.execute("""
                    INSERT INTO chat_sessions (id, title, preview, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (session_id, title, preview, current_time, current_time))
            
            conn.commit()
    
    def add_message(self, session_id: str, content: str, message_type: str, progresses: List[str] = None) -> None:
        """Add a message to a session"""
        current_time = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Add progresses column if it doesn't exist
            cursor.execute("PRAGMA table_info(chat_messages)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'progresses' not in columns:
                cursor.execute("ALTER TABLE chat_messages ADD COLUMN progresses TEXT")
            
            # Serialize progress data as JSON
            progress_json = json.dumps(progresses) if progresses else None
            
            # Insert message
            cursor.execute("""
                INSERT INTO chat_messages (session_id, content, type, timestamp, progresses)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, content, message_type, current_time, progress_json))
            
            # Update session's updated_at timestamp
            cursor.execute("""
                UPDATE chat_sessions 
                SET updated_at = ?
                WHERE id = ?
            """, (current_time, session_id))
            
            conn.commit()
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a complete session with all messages"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get session info
            cursor.execute("""
                SELECT id, title, preview, created_at, updated_at
                FROM chat_sessions 
                WHERE id = ?
            """, (session_id,))
            
            session_row = cursor.fetchone()
            if not session_row:
                return None
            
            # Get messages for this session
            cursor.execute("""
                SELECT content, type, timestamp, progresses
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,))
            
            messages = []
            for msg_row in cursor.fetchall():
                message_data = {
                    "content": msg_row["content"],
                    "type": msg_row["type"],
                    "timestamp": msg_row["timestamp"]
                }
                
                # Parse progress data if available
                if msg_row["progresses"]:
                    try:
                        message_data["progresses"] = json.loads(msg_row["progresses"])
                    except (json.JSONDecodeError, TypeError):
                        message_data["progresses"] = []
                
                messages.append(message_data)
            
            return {
                "id": session_row["id"],
                "title": session_row["title"],
                "preview": session_row["preview"],
                "created_at": session_row["created_at"],
                "updated_at": session_row["updated_at"],
                "messages": messages
            }
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all sessions metadata (without messages)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    s.id, s.title, s.preview, s.created_at, s.updated_at,
                    COUNT(m.id) as message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.id = m.session_id
                GROUP BY s.id, s.title, s.preview, s.created_at, s.updated_at
                ORDER BY s.updated_at DESC
            """)
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    "id": row["id"],
                    "title": row["title"],
                    "preview": row["preview"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "message_count": row["message_count"]
                })
            
            return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete session (messages will be deleted automatically due to CASCADE)
            cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            deleted = cursor.rowcount > 0
            
            conn.commit()
            return deleted
    
    def migrate_from_json(self, json_directory: str = "chat_history") -> int:
        """Migrate existing JSON files to SQLite database"""
        migrated_count = 0
        
        if not os.path.exists(json_directory):
            return migrated_count
        
        for filename in os.listdir(json_directory):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(json_directory, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                # Create session
                self.create_or_update_session(
                    session_id=data["id"],
                    title=data["title"],
                    preview=data["preview"]
                )
                
                # Add messages
                for message in data.get("messages", []):
                    # Check if message has progress data
                    progresses = message.get("progresses", []) if isinstance(message, dict) else []
                    self.add_message(
                        session_id=data["id"],
                        content=message["content"],
                        message_type=message["type"],
                        progresses=progresses
                    )
                
                migrated_count += 1
                print(f"Migrated session: {data['id']}")
                
            except Exception as e:
                print(f"Error migrating {filename}: {e}")
        
        return migrated_count

# Global database instance
db = ChatDatabase()