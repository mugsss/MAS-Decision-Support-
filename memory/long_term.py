"""
Long-term memory — persists conversations to SQLite and retrieves recent history.
"""

import json
import sqlite3
from datetime import datetime


class LongTermMemory:
    def __init__(self, db_path: str = "data/memory.db", max_history: int = 5):
        self.db_path = db_path
        self.max_history = max_history
        self.conn = sqlite3.connect(db_path, check_same_thread=False)

    def save_conversation(self, conversation_id: str, messages: list[dict]):
        now = datetime.utcnow().isoformat()
        messages_json = json.dumps(messages, default=str)

        self.conn.execute(
            """INSERT INTO conversations (conversation_id, messages_json, created_at, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(conversation_id) DO UPDATE SET
                 messages_json = excluded.messages_json,
                 updated_at = excluded.updated_at""",
            (conversation_id, messages_json, now, now),
        )
        self.conn.commit()

    def get_recent_conversations(self) -> list[dict]:
        cur = self.conn.execute(
            "SELECT messages_json FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (self.max_history,),
        )
        results = []
        for row in cur.fetchall():
            results.extend(json.loads(row[0]))
        return results

    def get_conversation(self, conversation_id: str) -> list[dict] | None:
        cur = self.conn.execute(
            "SELECT messages_json FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        )
        row = cur.fetchone()
        if row:
            return json.loads(row[0])
        return None

    def close(self):
        self.conn.close()
