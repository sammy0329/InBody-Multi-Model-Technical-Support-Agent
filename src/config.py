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

    # 시멘틱 캐시
    enable_semantic_cache: bool = True
    cache_similarity_threshold: float = 0.92
    cache_max_entries: int = 10000
    cache_ttl_troubleshoot: int = 604800  # 7일 (초)
    cache_ttl_install: int = 2592000  # 30일
    cache_ttl_connect: int = 1209600  # 14일
    cache_ttl_clinical: int = 7776000  # 90일
    cache_ttl_general: int = 2592000  # 30일

    # 로깅
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
