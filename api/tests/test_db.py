import os
import importlib
import sys


def test_db_is_none_when_no_env():
    # Clear any cached module
    if "api.db" in sys.modules:
        del sys.modules["api.db"]
    os.environ.pop("SUPABASE_URL", None)
    os.environ.pop("SUPABASE_KEY", None)
    os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
    import api.db as db_module
    assert db_module.db is None


def test_db_init_skipped_without_credentials():
    if "api.db" in sys.modules:
        del sys.modules["api.db"]
    os.environ["SUPABASE_URL"] = ""
    import api.db as db_module
    assert db_module.db is None
