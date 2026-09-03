"""
Long-term memory — persists conversations to SQLite, extracts facts into ChromaDB.
"""

import json
import sqlite3
import uuid
from datetime import datetime

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_chroma import Chroma

from llm_provider import build_embeddings, load_llm_config
from text_utils import message_text


FACT_EXTRACTION_PROMPT = """Extract the key facts, decisions, and action items from this conversation.
Return each fact on its own line. Focus on:
- Vehicle IDs and ECU configurations discussed
- Problems identified and their root causes
- Decisions made and their rationale
- Action items and their status
- Any metrics or thresholds mentioned

Conversation:
{conversation}

Key facts (one per line):"""


class LongTermMemory:
    def __init__(
        self,
        db_path: str = "data/memory.db",
        chroma_dir: str = "data/chroma",
        collection_name: str = "conversation_memory",
        embeddings: Embeddings | None = None,
        top_k: int = 3,
    ):
        self.db_path = db_path
        self.top_k = top_k
        self.conn = sqlite3.connect(db_path, check_same_thread=False)

        if embeddings is None:
            embeddings = build_embeddings(load_llm_config())

        self.vectorstore = Chroma(
            collection_name=collection_name,
            persist_directory=chroma_dir,
            embedding_function=embeddings,
        )

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

    async def extract_and_store_facts(
        self, conversation_id: str, messages: list[dict], llm: BaseChatModel
    ):
        conversation_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )
        response = await llm.ainvoke(
            [HumanMessage(content=FACT_EXTRACTION_PROMPT.format(conversation=conversation_text))]
        )

        facts = [
            line.strip().lstrip("- ")
            for line in message_text(response.content).strip().split("\n")
            if line.strip() and not line.strip().startswith("Key facts")
        ]

        if not facts:
            return

        now = datetime.utcnow().isoformat()
        documents = []
        for fact in facts:
            fact_id = str(uuid.uuid4())
            self.conn.execute(
                "INSERT INTO memory_facts (fact_id, conversation_id, fact_text, created_at) VALUES (?, ?, ?, ?)",
                (fact_id, conversation_id, fact, now),
            )
            documents.append(Document(
                page_content=fact,
                metadata={
                    "fact_id": fact_id,
                    "conversation_id": conversation_id,
                    "timestamp": now,
                },
            ))

        self.conn.commit()
        self.vectorstore.add_documents(documents)

    def retrieve_relevant(self, query: str) -> list[str]:
        try:
            results = self.vectorstore.similarity_search(query, k=self.top_k)
        except Exception:
            return []
        return [doc.page_content for doc in results]

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
