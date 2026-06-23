from typing import Any

from knowledge_engine.embeddings.base import EmbeddingProvider
from knowledge_engine.embeddings.factory import EmbeddingProviderConfig
from knowledge_engine.embeddings.schemas import EmbeddingVector
from knowledge_engine.embeddings.schemas import hash_embedding_text

try:
    import requests
except ImportError:  # pragma: no cover - exercised only in stripped runtimes
    requests = None


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        config: EmbeddingProviderConfig | None = None,
        session: Any | None = None,
    ) -> None:
        self.config = config or EmbeddingProviderConfig()
        self.session = session or self._build_session()

    def embed_text(self, text: str) -> EmbeddingVector:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[EmbeddingVector]:
        if not texts:
            return []

        for text in texts:
            if not isinstance(text, str):
                raise TypeError("Embedding text must be a string")

        model = self.config.model_name
        if not model:
            raise ValueError(
                "EMBEDDING_MODEL_NAME is required for openai_compatible provider"
            )

        response = self.session.post(
            self._embeddings_url(),
            json=self._payload(texts, model),
            headers=self._headers(),
            timeout=self.config.timeout_seconds,
        )
        if getattr(response, "status_code", 200) >= 400:
            raise RuntimeError(
                "OpenAI-compatible embedding request failed with "
                f"status {response.status_code}"
            )

        data = self._response_json(response)
        embeddings = self._embeddings_from_response(data, len(texts))
        return [
            EmbeddingVector(
                text_hash=hash_embedding_text(text),
                vector=vector,
                dimension=len(vector),
                provider="openai_compatible",
                model=str(data.get("model") or model),
                metadata={
                    "usage": (
                        data.get("usage")
                        if isinstance(data.get("usage"), dict)
                        else {}
                    ),
                    "index": index,
                    "configured_dimension": self.config.dimension,
                },
            )
            for index, (text, vector) in enumerate(zip(texts, embeddings, strict=True))
        ]

    def _payload(self, texts: list[str], model: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "input": texts,
        }
        if self.config.dimension > 0:
            payload["dimensions"] = self.config.dimension
        return payload

    def _embeddings_url(self) -> str:
        base_url = self.config.base_url.strip().rstrip("/")
        if not base_url:
            raise ValueError(
                "EMBEDDING_BASE_URL is required for openai_compatible provider"
            )
        if base_url.endswith("/embeddings"):
            return base_url
        return f"{base_url}/embeddings"

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
            raise RuntimeError(
                "OpenAI-compatible embedding response was not valid JSON"
            ) from exc
        if not isinstance(data, dict):
            raise RuntimeError("OpenAI-compatible embedding response must be a JSON object")
        return data

    @staticmethod
    def _embeddings_from_response(
        data: dict[str, Any],
        expected_count: int,
    ) -> list[list[float]]:
        raw_items = data.get("data")
        if not isinstance(raw_items, list):
            raise RuntimeError("OpenAI-compatible embedding response had no data list")
        if len(raw_items) != expected_count:
            raise RuntimeError(
                "OpenAI-compatible embedding response count did not match request"
            )

        ordered_items = sorted(
            enumerate(raw_items),
            key=lambda item: (
                item[1].get("index")
                if isinstance(item[1], dict) and isinstance(item[1].get("index"), int)
                else item[0]
            ),
        )

        vectors: list[list[float]] = []
        for _, item in ordered_items:
            if not isinstance(item, dict):
                raise RuntimeError("OpenAI-compatible embedding item was not an object")
            embedding = item.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                raise RuntimeError("OpenAI-compatible embedding item had no vector")
            vectors.append([float(value) for value in embedding])
        return vectors
