from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    POSTGRES_HOST: str = Field(..., description="Database host")
    POSTGRES_DB: str = Field(..., description="Database name")
    POSTGRES_USER: str = Field(..., description="Database username")
    POSTGRES_PASSWORD: str = Field(..., description="Database password")
    POSTGRES_PORT: int = Field(..., description="Database port")

    GEMINI_API_KEY: str = Field(..., description="Gemini API key")

    class Config:
        env_file = ".env"  
        env_file_encoding = "utf-8"

settings = Settings() # type: ignore