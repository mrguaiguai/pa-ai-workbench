from dataclasses import dataclass
from dataclasses import field


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    title: str
    description: str
    supported_task_types: list[str]
    required_tools: list[str] = field(default_factory=list)
    document_path: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class SkillRegistry:
    def __init__(self, skills: list[SkillDefinition] | None = None) -> None:
        self._skills: dict[str, SkillDefinition] = {}
        for skill in skills or []:
            self.register(skill)

    def register(self, skill: SkillDefinition) -> None:
        if skill.name in self._skills:
            raise ValueError(f"Skill already registered: {skill.name}")
        self._skills[skill.name] = skill

    def get(self, name: str) -> SkillDefinition | None:
        return self._skills.get(name)

    def require(self, name: str) -> SkillDefinition:
        skill = self.get(name)
        if skill is None:
            raise KeyError(f"Skill not found: {name}")
        return skill

    def list_skills(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def find_by_task_type(self, task_type: str) -> list[SkillDefinition]:
        return [
            skill
            for skill in self._skills.values()
            if task_type in skill.supported_task_types
        ]


def create_builtin_skill_registry() -> SkillRegistry:
    from agent.skills.builtin import BUILTIN_SKILLS

    return SkillRegistry(list(BUILTIN_SKILLS))

