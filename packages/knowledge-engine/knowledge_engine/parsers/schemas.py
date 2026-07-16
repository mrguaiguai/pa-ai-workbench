from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field


@dataclass(frozen=True)
class ParsedSection:
    text: str
    title: str | None = None
    page_number: int | None = None
    section_path: list[str] = field(default_factory=list)
    start_char: int = 0
    end_char: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedDocument:
    source_path: str
    file_name: str
    file_type: str
    title: str
    text: str
    sections: list[ParsedSection]
    mime_type: str | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def section_count(self) -> int:
        return len(self.sections)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["char_count"] = self.char_count
        data["section_count"] = self.section_count
        return data
