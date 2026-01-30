"""환경 변수 및 설정 관리"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정 — .env 파일에서 자동 로드"""

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_mini_model: str = "gpt-4o-mini"

    # Vector DB (Chroma)
    chroma_persist_dir: str = "./data/chroma"

    # Structured DB (SQLite / PostgreSQL)
    structured_db_url: str = "sqlite+aiosqlite:///./data/inbody.db"

    # 로깅
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
