"""
supabase_client.py
------------------
Initialises the Supabase client from environment variables.
If SUPABASE_URL is not set, logs a warning and falls back to SQLite
(the SQLAlchemy engine in database.py is used in that case).
"""

import logging
import os

logger = logging.getLogger(__name__)

# Lazy singleton — None means "not yet initialised"
_supabase_client = None
_supabase_available: bool = False


def get_supabase():
    """
    Returns the Supabase client singleton, or None if Supabase is not configured.
    Call this inside route handlers / services — do NOT call at module import time.
    """
    global _supabase_client, _supabase_available

    if _supabase_client is not None:
        return _supabase_client

    url = os.getenv("SUPABASE_URL", "").strip()
    # Prefer service-role key for server-side operations (bypasses RLS when needed)
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
    )

    if not url or not key:
        logger.warning(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set — "
            "falling back to local SQLite database."
        )
        _supabase_available = False
        return None

    try:
        from supabase import create_client, Client  # type: ignore

        _supabase_client: Client = create_client(url, key)
        _supabase_available = True
        logger.info("Supabase client initialised successfully (url=%s)", url)
        return _supabase_client
    except ImportError:
        logger.warning(
            "supabase-py package not installed — falling back to SQLite. "
            "Run: pip install supabase"
        )
        _supabase_available = False
        return None
    except Exception as exc:
        logger.error("Failed to initialise Supabase client: %s", exc)
        _supabase_available = False
        return None


def is_supabase_available() -> bool:
    """Returns True if Supabase is configured and the client was initialised."""
    get_supabase()  # trigger init
    return _supabase_available
