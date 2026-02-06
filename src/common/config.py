from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Supabase
    supabase_url: str
    supabase_key: str

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    # OpenAI
    openai_api_key: str

    # Application
    worker_id: str = "worker-1"
    log_level: str = "INFO"

    # Queue settings
    queue_name: str = "ticket_processing"
    dlx_name: str = "ticket_processing_dlx"
    max_retries: int = 3
    prefetch_count: int = 1

    # Worker settings
    heartbeat_interval_seconds: int = 30
    stale_processing_threshold_seconds: int = 300  # 5 minutes

    # LLM settings
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2

    # Agent settings
    use_agent_workflow: bool = True  # Set to False to use legacy fixed pipeline

    # Email settings
    email_provider: str = "mock"  # "sendgrid", "mailgun", or "mock"
    email_from_address: str = "support@example.com"
    email_from_name: str = "Support Team"
    email_domain: str = "example.com"

    # SendGrid
    sendgrid_api_key: str | None = None

    # Mailgun
    mailgun_api_key: str | None = None
    mailgun_domain: str | None = None
    mailgun_webhook_key: str | None = None

    # GitHub Integration (for bug reports)
    github_token: str | None = None
    github_repo: str | None = None  # Format: "owner/repo"


@lru_cache
def get_settings() -> Settings:
    return Settings()
