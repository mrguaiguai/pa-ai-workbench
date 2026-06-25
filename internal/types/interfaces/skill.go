package interfaces

import (
	"context"

	"github.com/Tencent/WeKnora/internal/agent/skills"
)

// SkillService defines the interface for skill business logic
type SkillService interface {
	// ListPreloadedSkills returns metadata for all preloaded skills
	ListPreloadedSkills(ctx context.Context) ([]*skills.SkillMetadata, error)

	// GetSkillByName retrieves a skill by its name
	GetSkillByName(ctx context.Context, name string) (*skills.Skill, error)

	// CreateSkill creates a managed SKILL.md under the preloaded skills directory.
	CreateSkill(ctx context.Context, input skills.SkillMutationInput) (*skills.Skill, error)

	// UpdateSkill updates a managed SKILL.md. Renaming is intentionally not supported.
	UpdateSkill(ctx context.Context, name string, input skills.SkillMutationInput) (*skills.Skill, error)

	// DeleteSkill deletes a managed skill directory by skill name.
	DeleteSkill(ctx context.Context, name string) error

	// TestSkill validates a skill without executing scripts.
	TestSkill(ctx context.Context, name string) (*skills.SkillTestResult, error)
}
