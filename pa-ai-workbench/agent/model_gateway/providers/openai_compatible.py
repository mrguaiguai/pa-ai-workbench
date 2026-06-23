from typing import Any

from agent.model_gateway.base import ModelGateway
from agent.model_gateway.factory import ModelGatewayConfig
from agent.model_gateway.schemas import ChatRequest
from agent.model_gateway.schemas import ChatResponse

try:
    import requests
except ImportError:  # pragma: no cover - exercised only in stripped runtimes
    requests = None


class OpenAICompatibleChatProvider(ModelGateway):
    def __init__(
        self,
        config: ModelGatewayConfig | None = None,
        session: Any | None = None,
    ) -> None:
        self.config = config or ModelGatewayConfig()
        self.session = session or self._build_session()

    def generate(self, request: ChatRequest) -> ChatResponse:
        model = request.model or self.config.model_name
        if not model:
            raise ValueError(
                "CHAT_MODEL_NAME is required for openai_compatible provider"
            )

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in request.messages
            ],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        response = self.session.post(
            self._chat_completions_url(),
            json=payload,
            headers=self._headers(),
            timeout=self.config.timeout_seconds,
        )
        if getattr(response, "status_code", 200) >= 400:
            raise RuntimeError(
                "OpenAI-compatible chat request failed with "
                f"status {response.status_code}"
            )

        data = self._response_json(response)
        content = self._content_from_response(data)
        return ChatResponse(
            content=content,
            model=str(data.get("model") or model),
            provider="openai_compatible",
            usage=data.get("usage") if isinstance(data.get("usage"), dict) else {},
            raw_metadata={
                "id": data.get("id"),
                "object": data.get("object"),
                "created": data.get("created"),
                "choice_count": len(data.get("choices") or []),
                "finish_reason": self._finish_reason(data),
            },
        )

    def _chat_completions_url(self) -> str:
        base_url = self.config.base_url.strip().rstrip("/")
        if not base_url:
            raise ValueError(
                "CHAT_MODEL_BASE_URL is required for openai_compatible provider"
            )
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    @staticmethod
    def _build_session() -> Any:
        if requests is None:
            raise RuntimeError("requests is required for openai_compatible provider")
        return requests.Session()

    @staticmethod
    def _response_json(response: Any) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("OpenAI-compatible chat response was not valid JSON") from exc
        if not isinstance(data, dict):
            raise RuntimeError("OpenAI-compatible chat response must be a JSON object")
        return data

    @staticmethod
    def _content_from_response(data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("OpenAI-compatible chat response had no choices")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise RuntimeError("OpenAI-compatible chat choice was not an object")

        message = first_choice.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
        if isinstance(first_choice.get("text"), str):
            return first_choice["text"]
        raise RuntimeError("OpenAI-compatible chat response had no text content")

    @staticmethod
    def _finish_reason(data: dict[str, Any]) -> str | None:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return None
        finish_reason = first_choice.get("finish_reason")
        return str(finish_reason) if finish_reason is not None else None
