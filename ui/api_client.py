"""FastAPI 백엔드 HTTP 클라이언트 -- T068"""

import json
import os
from typing import Generator

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
TIMEOUT = httpx.Timeout(timeout=60.0, connect=10.0)


class ApiClient:
    """FastAPI 백엔드와의 모든 HTTP 통신을 캡슐화한다."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self._client = httpx.Client(base_url=base_url, timeout=TIMEOUT)

    def health_check(self) -> dict:
        """GET /health -- 시스템 상태 확인."""
        try:
            resp = self._client.get("/health")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return {"status": "unreachable", "components": {}}

    def list_models(self) -> list[dict]:
        """GET /models -- 지원 기종 목록."""
        try:
            resp = self._client.get("/models")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return []

    def chat(self, message: str, thread_id: str) -> dict:
        """POST /chat -- 동기 폴백 요청."""
        resp = self._client.post(
            "/chat",
            json={"message": message, "thread_id": thread_id},
        )
        resp.raise_for_status()
        return resp.json()

    def chat_stream(
        self, message: str, thread_id: str
    ) -> Generator[dict, None, None]:
        """POST /chat/stream -- SSE 스트리밍 수신 제너레이터."""
        with self._client.stream(
            "POST",
            "/chat/stream",
            json={"message": message, "thread_id": thread_id},
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        yield json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

    def delete_session(self, thread_id: str) -> bool:
        """DELETE /sessions/{thread_id} -- 세션 초기화."""
        try:
            resp = self._client.delete(f"/sessions/{thread_id}")
            return resp.status_code == 204
        except httpx.HTTPError:
            return False


_client: ApiClient | None = None


def get_client() -> ApiClient:
    """싱글톤 ApiClient를 반환한다."""
    global _client
    if _client is None:
        _client = ApiClient()
    return _client
