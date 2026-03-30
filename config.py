from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # AI Provider Configuration
    ai_provider: str = "anthropic"  # options: anthropic, openai, custom

    # Anthropic Configuration
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-6"

    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"

    # Custom API Configuration
    custom_api_url: str = ""
    custom_api_key: str = ""
    custom_model: str = "custom-model"

    # Common Configuration
    temperature: float = 0.7
    max_tokens: int = 2000

    # Image Generation Configuration
    image_api_url: str = "https://api.openai.com/v1"
    image_api_key: str = ""
    image_model: str = "dall-e-3"

    # Supabase Configuration (免费 PostgreSQL: supabase.com)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""  # 仅服务端使用，绕过 RLS

    class Config:
        env_file = ".env"

    @property
    def is_custom_provider(self):
        return self.ai_provider == "custom"

    @property
    def current_api_key(self):
        if self.ai_provider == "anthropic":
            return self.anthropic_api_key
        elif self.ai_provider == "openai":
            return self.openai_api_key
        elif self.ai_provider == "custom":
            return self.custom_api_key
        return ""

    @property
    def current_model(self):
        if self.ai_provider == "anthropic":
            return self.anthropic_model
        elif self.ai_provider == "openai":
            return self.openai_model
        elif self.ai_provider == "custom":
            return self.custom_model
        return ""

    @property
    def api_base_url(self):
        if self.ai_provider == "custom" and self.custom_api_url:
            return self.custom_api_url
        elif self.ai_provider == "openai":
            return "https://api.openai.com/v1"
        elif self.ai_provider == "anthropic":
            return "https://api.anthropic.com"
        return ""

    @property
    def supabase_enabled(self) -> bool:
        """是否配置了 Supabase"""
        return bool(self.supabase_url and self.supabase_anon_key)

@lru_cache()
def get_settings():
    return Settings()
