from knowledge_engine.errors import KnowledgeEngineError


class DocumentParseError(KnowledgeEngineError):
    """Raised when a document cannot be parsed into text."""


class UnsupportedDocumentFormatError(DocumentParseError):
    """Raised when the parser does not support the document format."""


class ParserDependencyError(DocumentParseError):
    """Raised when an optional parser dependency is missing."""
