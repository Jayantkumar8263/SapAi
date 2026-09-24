"""
API Security
============
API-key authentication for protected FastAPI endpoints.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader


# ---------------------------------------------------------
# Project root
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ENV_FILE = PROJECT_ROOT / ".env"


# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

load_dotenv(ENV_FILE)


# ---------------------------------------------------------
# API key from .env
# ---------------------------------------------------------

API_KEY = os.getenv("SAPAI_API_KEY")


# ---------------------------------------------------------
# FastAPI API-key security scheme
# ---------------------------------------------------------

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


# ---------------------------------------------------------
# Authentication dependency
# ---------------------------------------------------------

def verify_api_key(
    x_api_key: str | None = Security(api_key_header),
) -> None:

    # Server configuration
    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "SAPAI_API_KEY is not configured on the server. "
                f"Expected it in: {ENV_FILE}"
            ),
        )

    # Missing key
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header.",
        )

    # Invalid key
    if not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )