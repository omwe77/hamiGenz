"""
hamigenz — User Feedback Store

Captures thumbs-up / thumbs-down ratings on AI answers so the system can
learn which answers users find helpful.  This is the standard production RAG
feedback pattern (thumbs up/down + optional comment), backed by SQLite.

Reference: ADT-RAG feedback mechanism; DeepLearning.AI RAG evaluation guide
(thumbs up/down as the cheapest meaningful quality signal); PatchRAG (2026)
— feedback adaptation as a measurable RAG dimension.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class FeedbackStore:
    """Persist user ratings on AI-generated answers."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _init_table(self) -> None:
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS feedback (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id      TEXT,
                question    TEXT NOT NULL,
                rating      INTEGER NOT NULL CHECK (rating IN (-1, 1)),
                comment     TEXT,
                created_at  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_feedback_doc
                ON feedback(doc_id);
            CREATE INDEX IF NOT EXISTS idx_feedback_created
                ON feedback(created_at);
        """)
        conn.commit()
        conn.close()

    def add(
        self,
        doc_id: Optional[str],
        question: str,
        rating: int,           # -1 (thumbs down) or 1 (thumbs up)
        comment: Optional[str] = None,
    ) -> int:
        """Record a feedback entry.  Returns the new row id."""
        conn = sqlite3.connect(str(self.db_path))
        row_id = conn.execute(
            """INSERT INTO feedback (doc_id, question, rating, comment, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                doc_id,
                question.strip(),
                rating,
                comment.strip() if comment else None,
                datetime.now(timezone.utc).isoformat(),
            ),
        ).lastrowid
        conn.commit()
        conn.close()
        return row_id

    def for_question(self, question: str) -> list[dict]:
        """Return all feedback rows for an exact question match."""
        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute(
            "SELECT id, doc_id, question, rating, comment, created_at FROM feedback WHERE question = ? ORDER BY created_at DESC",
            (question.strip(),),
        ).fetchall()
        conn.close()
        return [
            {
                "id": r[0], "doc_id": r[1], "question": r[2],
                "rating": r[3], "comment": r[4], "created_at": r[5],
            }
            for r in rows
        ]

    def aggregate(self, doc_id: Optional[str] = None, limit: int = 100) -> dict:
        """Return aggregate satisfaction stats, optionally scoped to a doc."""
        conn = sqlite3.connect(str(self.db_path))
        if doc_id:
            rows = conn.execute(
                """SELECT rating, COUNT(*) as cnt
                   FROM feedback WHERE doc_id = ? GROUP BY rating
                   ORDER BY created_at DESC LIMIT ?""",
                (doc_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT rating, COUNT(*) as cnt
                   FROM feedback GROUP BY rating
                   ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        conn.close()
        total = sum(r[1] for r in rows)
        up = sum(r[1] for r in rows if r[0] == 1)
        down = sum(r[1] for r in rows if r[0] == -1)
        return {
            "total": total,
            "up": up,
            "down": down,
            "up_rate": round(up / total, 3) if total else None,
        }
