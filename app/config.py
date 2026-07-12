from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    base_url: str = "http://127.0.0.1:8000"
    rate_limit_storage_uri: str = "memory://"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    trusted_proxy_hops: int = 0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()  # type: ignore[call-arg]
