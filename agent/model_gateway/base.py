from abc import ABC
from abc import abstractmethod

from agent.model_gateway.schemas import ChatRequest
from agent.model_gateway.schemas import ChatResponse


class ModelGateway(ABC):
    """Unified boundary for all chat model calls."""

    @abstractmethod
    def generate(self, request: ChatRequest) -> ChatResponse:
        """Generate a chat response through the configured provider."""
