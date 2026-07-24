"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Telegram ---
    telegram_bot_token: str
    telegram_webhook_secret: str = "firomsa-webhook-secret-change-me"
    webhook_url: Optional[str] = None  # e.g. https://firomsa-bot.onrender.com

    # --- Groq AI ---
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    max_tokens: int = 1024
    temperature: float = 0.7
    max_history_messages: int = 20  # per user conversation window

    # --- Database ---
    database_url: str

    # --- App ---
    app_name: str = "Firomsa Assistant Bot"
    debug: bool = False
    port: int = 8000

    # --- Admin ---
    # Comma-separated Telegram numeric user IDs that have admin access
    admin_telegram_ids: str = ""

    # --- Rate limiting ---
    rate_limit_per_minute: int = 10

    @property
    def admin_ids_list(self) -> list[int]:
        if not self.admin_telegram_ids:
            return []
        return [
            int(uid.strip())
            for uid in self.admin_telegram_ids.split(",")
            if uid.strip().isdigit()
        ]

    @property
    def async_database_url(self) -> str:
        """
        Convert postgresql:// → postgresql+asyncpg:// for SQLAlchemy async engine.
        Strips sslmode from query string — asyncpg handles SSL via connect_args.
        """
        import urllib.parse

        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql" + url[len("postgres"):]
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Remove sslmode from query params; asyncpg doesn't accept it via URL
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        qs.pop("sslmode", None)
        new_query = urllib.parse.urlencode(
            {k: v[0] for k, v in qs.items()}, quote_via=urllib.parse.quote
        )
        return urllib.parse.urlunparse(parsed._replace(query=new_query))

    @property
    def db_ssl_mode(self) -> str | None:
        """Extract sslmode from the original DATABASE_URL for use in connect_args."""
        import urllib.parse
        parsed = urllib.parse.urlparse(self.database_url)
        qs = urllib.parse.parse_qs(parsed.query)
        modes = qs.get("sslmode", [])
        return modes[0] if modes else None

    @property
    def webhook_endpoint(self) -> str:
        return f"{self.webhook_url}/telegram/webhook" if self.webhook_url else ""


settings = Settings()
