from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://krishivoice:krishivoice_dev@localhost:5432/krishivoice"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    data_dir: str = "../data/processed"
    ml_models_dir: str = "../ml/models"
    use_openmeteo: bool = True
    openmeteo_cache_dir: str = ".cache/openmeteo"
    openmeteo_cache_seconds: int = 3600

    openrouter_api_key: str = ""
    openrouter_enabled: bool = True
    openrouter_vl_model: str = "nvidia/nemotron-nano-12b-v2-vl:free"
    openrouter_llm_model: str = "nvidia/nemotron-3-nano-30b-a3b:free"

    tavily_api_key: str = ""
    tavily_enabled: bool = True
    tavily_trusted_only: bool = True

    # data.gov.in — AGMARKNET daily mandi prices (free registration)
    data_gov_in_api_key: str = ""
    mandi_default_state: str = "Tamil Nadu"
    mandi_cache_seconds: int = 21600

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
