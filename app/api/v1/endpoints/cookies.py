# ============================================================================
# FILE: app/api/v1/endpoints/cookies.py
# Endpoint to upload and persist logged cookies for fallback streaming
# ============================================================================
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class LoggedCookiesRequest(BaseModel):
    cookies: str

@router.post("/logged")
async def upload_logged_cookies(payload: LoggedCookiesRequest):
    """Accept pasted logged cookies and write them verbatim to production file(s)."""
    content = payload.cookies
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Cookies content is empty")

    written_paths = []
    errors = []
    candidates = []

    # Resolve project root and target file path
    try:
        base_dir = os.path.dirname(__file__)
        project_root = os.path.abspath(os.path.join(base_dir, "../../../.."))
        candidates.append(os.path.join(project_root, "logged_cookies.txt"))
    except Exception as e:
        errors.append(f"Root path resolution failed: {str(e)[:80]}")

    # Docker/Cloud Run path
    candidates.append("/app/logged_cookies.txt")

    for path in candidates:
        try:
            parent = os.path.dirname(path)
            if parent and not os.path.exists(parent):
                # Do not create parents outside project; attempt write only if parent exists
                if parent.startswith("/app"):
                    # On some platforms /app may not exist in local dev
                    continue
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            written_paths.append(path)
        except Exception as e:
            errors.append(f"Failed to write {path}: {str(e)[:120]}")

    if not written_paths:
        logger.error(f"Logged cookies write failed: {errors[0] if errors else 'unknown error'}")
        raise HTTPException(status_code=500, detail="Failed to write logged cookies file")

    # Minimal logging, never log cookie contents
    logger.info(f"Logged cookies updated ({len(content)} chars) -> {', '.join(written_paths)}")
    return {"message": "Logged cookies saved", "paths": written_paths}