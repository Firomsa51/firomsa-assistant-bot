"""Basic sanity tests for config and utilities."""
import pytest


def test_admin_ids_list_empty():
    """admin_ids_list returns empty list when env var is not set."""
    import os
    from unittest.mock import patch

    # Patch env vars minimally
    env = {
        "TELEGRAM_BOT_TOKEN": "123:ABC",
        "GROQ_API_KEY": "gsk_test",
        "DATABASE_URL": "postgresql://u:p@localhost/db",
        "ADMIN_TELEGRAM_IDS": "",
    }
    with patch.dict(os.environ, env, clear=False):
        from importlib import import_module, reload
        import app.config as cfg
        # Force re-read
        settings_fresh = cfg.Settings()
        assert settings_fresh.admin_ids_list == []


def test_admin_ids_list_populated():
    """admin_ids_list correctly parses comma-separated IDs."""
    import os
    from unittest.mock import patch

    env = {
        "TELEGRAM_BOT_TOKEN": "123:ABC",
        "GROQ_API_KEY": "gsk_test",
        "DATABASE_URL": "postgresql://u:p@localhost/db",
        "ADMIN_TELEGRAM_IDS": "111,222,333",
    }
    with patch.dict(os.environ, env, clear=False):
        from app.config import Settings
        s = Settings()
        assert s.admin_ids_list == [111, 222, 333]


def test_async_database_url_conversion():
    """async_database_url converts postgresql:// to postgresql+asyncpg://."""
    import os
    from unittest.mock import patch

    env = {
        "TELEGRAM_BOT_TOKEN": "123:ABC",
        "GROQ_API_KEY": "gsk_test",
        "DATABASE_URL": "postgresql://u:p@localhost/db",
        "ADMIN_TELEGRAM_IDS": "",
    }
    with patch.dict(os.environ, env, clear=False):
        from app.config import Settings
        s = Settings()
        assert s.async_database_url.startswith("postgresql+asyncpg://")
