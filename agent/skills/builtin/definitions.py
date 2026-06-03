from agent.skills.registry import SkillDefinition

BUILTIN_SKILLS = [
    SkillDefinition(
        name="knowledge_qa",
        title="Knowledge QA",
        description="Answer user questions with grounded evidence and concise citations.",
        supported_task_types=["knowledge_qa"],
        required_tools=["retriever", "citation_checker"],
        document_path="agent/skills/builtin/knowledge_qa.md",
    ),
    SkillDefinition(
        name="policy_analysis",
        title="Policy Analysis",
        description="Analyze policy material into structured findings, risks, and actions.",
        supported_task_types=["policy_analysis"],
        required_tools=["retriever", "citation_checker"],
        document_path="agent/skills/builtin/policy_analysis.md",
    ),
    SkillDefinition(
        name="case_review",
        title="Case Review",
        description="Review case material and produce a lightweight evidence-based summary.",
        supported_task_types=["case_review"],
        required_tools=["retriever", "citation_checker"],
        document_path="agent/skills/builtin/case_review.md",
    ),
]

