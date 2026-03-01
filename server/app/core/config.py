from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://agentops:agentops@localhost:5432/agentops"
    sync_database_url: str = "postgresql://agentops:agentops@localhost:5432/agentops"

    class Config:
        env_file = ".env"


settings = Settings()
