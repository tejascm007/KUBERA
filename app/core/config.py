"""
Application Configuration
Environment variables and settings - Supabase Compatible
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # ==================== APP ====================
    APP_NAME: str = "KUBERA"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    
    # ==================== DATABASE (SUPABASE) ====================

    SUPABASE_URL : str
    SUPABASE_ANON_KEY : str

    POSTGRES_HOST: str
    POSTGRES_PORT: int = 6543  # Supabase Transaction Pooler port
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "postgres"
    POSTGRES_MIN_POOL_SIZE: int = 2
    POSTGRES_MAX_POOL_SIZE: int = 10

    
    # ==================== JWT ====================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
      
    # ==================== EMAIL ====================
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = Field(..., env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(..., env="SMTP_PASSWORD")
    SMTP_FROM_EMAIL: Optional[str] = Field(..., env="SMTP_FROM_EMAIL")
    SMTP_FROM_NAME: str = "KUBERA"

    # ========== LLM CONFIGURATION (OPENROUTER) ==========
    OPENROUTER_API_KEY: str = Field(..., env="OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL: str = Field(
        default="https://openrouter.ai/api/v1",
        env="OPENROUTER_BASE_URL"
    )
    # OpenRouter models - you can use any model from https://openrouter.ai/models
    # Popular options:
    # - anthropic/claude-3.5-sonnet (best for complex reasoning)
    # - openai/gpt-4-turbo (powerful)
    # - meta-llama/llama-3.1-70b-instruct (open source, fast)
    # - google/gemini-pro (good balance)
    # - mistralai/mixtral-8x7b-instruct (efficient)
    OPENROUTER_MODEL: str = Field(
        default="meta-llama/llama-3.3-70b-instruct",
        env="OPENROUTER_MODEL"
    )
    # Optional: Your site URL and app name for OpenRouter rankings
    OPENROUTER_SITE_URL: str = Field(default="http://localhost:8000", env="OPENROUTER_SITE_URL")
    OPENROUTER_APP_NAME: str = Field(default="KUBERA", env="OPENROUTER_APP_NAME")
    
    MAX_TOKENS: int = Field(default=4096, env="MAX_TOKENS")
    TEMPERATURE: float = Field(default=0.7, env="TEMPERATURE")
    # ==================== OTP ====================
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 3
    OTP_LENGTH: int = 6
    
    # ==================== RATE LIMITING ====================
    RATE_LIMIT_BURST: int = 10
    RATE_LIMIT_PER_CHAT: int = 50
    RATE_LIMIT_PER_HOUR: int = 150
    RATE_LIMIT_PER_DAY: int = 1000
    
    # ==================== STOCK DATA APIs (For MCP Servers) ====================
    # All optional - yfinance works without any key
    ALPHA_VANTAGE_API_KEY: Optional[str] = Field(..., env="ALPHA_VANTAGE_API_KEY")
    FINNHUB_API_KEY: Optional[str] = Field(..., env="FINNHUB_API_KEY")
    MARKETAUX_API_KEY: Optional[str] = Field(..., env="MARKETAUX_API_KEY")
    NEWSAPI_KEY: Optional[str] = Field(..., env="NEWSAPI_KEY")
    INDIAN_API_KEY: Optional[str] = Field(..., env="INDIAN_API_KEY")
    
    # ==================== BACKGROUND JOBS ====================
    PORTFOLIO_UPDATE_FREQUENCY: int = 30
    PORTFOLIO_REPORT_FREQUENCY: str = "disabled"
    PORTFOLIO_REPORT_SEND_TIME: str = "09:00"
    PORTFOLIO_REPORT_DAY_WEEKLY: int = 1
    PORTFOLIO_REPORT_DAY_MONTHLY: int = 1

    # ========================================================================
    # PASSWORD VALIDATION SETTINGS
    # ========================================================================
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    
    # ==================== MISC ====================
    TIMEZONE: str = "Asia/Kolkata"
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/kubera.log"
    PYTHON_EXECUTABLE: str = "python"
    
    # ==================== HELPER PROPERTIES ====================
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def database_url(self) -> str:
        """Construct database URL"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def is_email_configured(self) -> bool:
        """Check if email is properly configured"""
        return all([self.SMTP_USER, self.SMTP_PASSWORD, self.SMTP_FROM_EMAIL])
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()
