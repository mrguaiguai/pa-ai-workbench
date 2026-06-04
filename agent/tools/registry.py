from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    tool: Any
    metadata: dict[str, str] | None = None


class ToolRegistry:
    def __init__(self, tools: list[ToolDefinition] | None = None) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"Tool already registered: {definition.name}")
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def require(self, name: str) -> ToolDefinition:
        definition = self.get(name)
        if definition is None:
            raise KeyError(f"Tool not found: {name}")
        return definition

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())


def create_builtin_tool_registry() -> ToolRegistry:
    from agent.tools.citation_checker import CitationChecker
    from agent.tools.real_retriever import RealRetrieverTool

    real_retriever = RealRetrieverTool()

    return ToolRegistry(
        [
            ToolDefinition(
                name="retriever",
                description="Retrieve grounded evidence from the Knowledge Engine.",
                tool=real_retriever,
                metadata={"implementation": "real_retriever"},
            ),
            ToolDefinition(
                name="real_retriever",
                description="Retrieve real document and Wiki evidence from the Knowledge Engine.",
                tool=real_retriever,
                metadata={"implementation": "real_retriever"},
            ),
            ToolDefinition(
                name="citation_checker",
                description="Validate citations before an AgentResult is returned.",
                tool=CitationChecker(),
            ),
        ]
    )
