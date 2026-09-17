"""Admin panel endpoints for hamiGenZ.

Provides document management (list/delete) and system stats.
These endpoints are for the admin UI at /admin.
"""

import os
import time
import psutil
from fastapi import APIRouter, HTTPException

from .vector_store import get_pipeline
from .document_processor import _session_dirs

router = APIRouter()


# ─── List documents ───────────────────────────────────────

@router.get("/admin/documents")
async def admin_list_documents() -> list[dict]:
    """List all uploaded documents from the vector store."""
    pipeline = get_pipeline()
...[truncated]