"""Supabase client — initialized once at import time from env vars."""
from __future__ import annotations
import os
from supabase import create_client, Client

_url = os.environ.get("SUPABASE_URL", "")
_key = os.environ.get("SUPABASE_KEY", "")

db: Client | None = create_client(_url, _key) if (_url and _key) else None
