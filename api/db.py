import os
from supabase import create_client, Client

_url = os.environ.get("SUPABASE_URL", "")
_key = (
    os.environ.get("SUPABASE_KEY", "")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
)
db: Client | None = create_client(_url, _key) if (_url and _key) else None
