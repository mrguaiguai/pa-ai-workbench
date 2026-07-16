from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
import hashlib


@dataclass(frozen=True)
class ChunkingConfig:
    max_chars: int = 1200
    overlap_chars: int = 150
    min_chars: int = 120

    def __post_init__(self) -> None:
        if self.max_chars <= 0:
            raise ValueError("CHUNK_MAX_CHARS must be positive")
        if self.overlap_chars < 0:
            raise ValueError("CHUNK_OVERLAP_CHARS cannot be negative")
        if self.min_chars < 0:
            raise ValueError("CHUNK_MIN_CHARS cannot be negative")
        if self.overlap_chars >= self.max_chars:
            raise ValueError("CHUNK_OVERLAP_CHARS must be smaller than CHUNK_MAX_CHARS")


@dataclass(frozen=True)
class DocumentChunkCandidate:
    chunk_index: int
    title: str
    content: str
    content_hash: str
    token_count: int
    char_count: int
    start_char: int
    end_char: int
    page_number: int | None = None
    section_path: list[str] = field(default_factory=list)
    paragraph_start_index: int | None = None
    paragraph_end_index: int | None = None
    source_path: str | None = None
    file_name: str | None = None
    file_type: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def estimate_token_count(content: str) -> int:
    if not content:
        return 0
    return max(1, len(content) // 4)
