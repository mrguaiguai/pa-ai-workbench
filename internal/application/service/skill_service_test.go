package service

import (
	"context"
	"testing"

	"github.com/Tencent/WeKnora/internal/agent/skills"
)

func TestSkillServiceManagedLifecycle(t *testing.T) {
	t.Setenv("WEKNORA_SKILLS_DIR", t.TempDir())
	t.Setenv("WEKNORA_SANDBOX_MODE", "disabled")

	svc := NewSkillService()
	ctx := context.Background()

	created, err := svc.CreateSkill(ctx, skills.SkillMutationInput{
		Name:         "wnfc-skill",
		Description:  "WNFC managed skill lifecycle test.",
		Instructions: "Use this managed skill only for lifecycle validation.",
	})
	if err != nil {
		t.Fatalf("CreateSkill returned error: %v", err)
	}
	if created.Name != "wnfc-skill" {
		t.Fatalf("created skill name = %q, want wnfc-skill", created.Name)
	}

	list, err := svc.ListPreloadedSkills(ctx)
	if err != nil {
		t.Fatalf("ListPreloadedSkills returned error: %v", err)
	}
	if len(list) != 1 || list[0].Name != "wnfc-skill" {
		t.Fatalf("unexpected list result: %#v", list)
	}

	result, err := svc.TestSkill(ctx, "wnfc-skill")
	if err != nil {
		t.Fatalf("TestSkill returned error: %v", err)
	}
	if !result.Valid || result.ScriptCount != 0 || result.SandboxAvailable {
		t.Fatalf("unexpected test result: %#v", result)
	}

	updated, err := svc.UpdateSkill(ctx, "wnfc-skill", skills.SkillMutationInput{
		Name:         "wnfc-skill",
		Description:  "Updated WNFC managed skill.",
		Instructions: "Updated instructions.",
	})
	if err != nil {
		t.Fatalf("UpdateSkill returned error: %v", err)
	}
	if updated.Description != "Updated WNFC managed skill." {
		t.Fatalf("updated description = %q", updated.Description)
	}

	if _, err := svc.UpdateSkill(ctx, "wnfc-skill", skills.SkillMutationInput{
		Name:         "renamed-skill",
		Description:  "Rename attempt.",
		Instructions: "Rename should be rejected.",
	}); err == nil {
		t.Fatal("UpdateSkill rename unexpectedly succeeded")
	}

	if err := svc.DeleteSkill(ctx, "wnfc-skill"); err != nil {
		t.Fatalf("DeleteSkill returned error: %v", err)
	}
	if _, err := svc.GetSkillByName(ctx, "wnfc-skill"); err == nil {
		t.Fatal("GetSkillByName succeeded after delete")
	}
}
