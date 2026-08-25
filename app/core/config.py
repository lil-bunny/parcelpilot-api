import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_model: str = "openai:gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    openai_api_key: str = ""
    database_url: str = ""
    # Comma-separated origins for MVP-UI (Render static site, local dev, etc.)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Override for Render persistent disk, e.g. /var/data/chroma
    chroma_dir: str = ""

    @property
    def llm_api_key(self) -> str:
        return self.openai_api_key.strip()

    def apply_env(self) -> None:
        # ponytail: pydantic-settings loads .env into this object, not os.environ
        key = self.llm_api_key
        if key:
            os.environ.setdefault("OPENAI_API_KEY", key)

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
settings.apply_env()
