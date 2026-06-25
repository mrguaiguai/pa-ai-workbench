package service

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"

	"github.com/Tencent/WeKnora/internal/agent/skills"
	apperrors "github.com/Tencent/WeKnora/internal/errors"
	"github.com/Tencent/WeKnora/internal/logger"
	"github.com/Tencent/WeKnora/internal/types/interfaces"
	"gopkg.in/yaml.v3"
)

// DefaultPreloadedSkillsDir is the default directory for preloaded skills
const DefaultPreloadedSkillsDir = "skills/preloaded"

const maxManagedSkillInstructionsChars = 65536

// skillService implements SkillService interface
type skillService struct {
	loader       *skills.Loader
	preloadedDir string
	mu           sync.RWMutex
	initialized  bool
}

// NewSkillService creates a new skill service
func NewSkillService() interfaces.SkillService {
	// Determine the preloaded skills directory
	preloadedDir := getPreloadedSkillsDir()

	return &skillService{
		preloadedDir: preloadedDir,
		initialized:  false,
	}
}

// getPreloadedSkillsDir returns the path to the preloaded skills directory
func getPreloadedSkillsDir() string {
	// Check if SKILLS_DIR environment variable is set
	if dir := os.Getenv("WEKNORA_SKILLS_DIR"); dir != "" {
		return dir
	}

	// Try to find the skills directory relative to the executable
	execPath, err := os.Executable()
	if err == nil {
		execDir := filepath.Dir(execPath)
		skillsDir := filepath.Join(execDir, DefaultPreloadedSkillsDir)
		if _, err := os.Stat(skillsDir); err == nil {
			return skillsDir
		}
	}

	// Try current working directory
	cwd, err := os.Getwd()
	if err == nil {
		skillsDir := filepath.Join(cwd, DefaultPreloadedSkillsDir)
		if _, err := os.Stat(skillsDir); err == nil {
			return skillsDir
		}
	}

	// Default to relative path (will be created if needed)
	return DefaultPreloadedSkillsDir
}

// ensureInitialized initializes the loader if not already done
func (s *skillService) ensureInitialized(ctx context.Context) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.initialized {
		return nil
	}

	// Check if preloaded directory exists
	if _, err := os.Stat(s.preloadedDir); os.IsNotExist(err) {
		logger.Warnf(ctx, "Preloaded skills directory does not exist: %s", s.preloadedDir)
		// Create the directory to avoid repeated warnings
		if err := os.MkdirAll(s.preloadedDir, 0755); err != nil {
			logger.Warnf(ctx, "Failed to create preloaded skills directory: %v", err)
		}
	}

	// Create loader with preloaded directory
	s.loader = skills.NewLoader([]string{s.preloadedDir})
	s.initialized = true

	logger.Infof(ctx, "Skill service initialized with preloaded directory: %s", s.preloadedDir)

	return nil
}

// ListPreloadedSkills returns metadata for all preloaded skills
func (s *skillService) ListPreloadedSkills(ctx context.Context) ([]*skills.SkillMetadata, error) {
	if err := s.ensureInitialized(ctx); err != nil {
		return nil, fmt.Errorf("failed to initialize skill service: %w", err)
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	metadata, err := s.loader.DiscoverSkills()
	if err != nil {
		logger.Errorf(ctx, "Failed to discover preloaded skills: %v", err)
		return nil, fmt.Errorf("failed to discover skills: %w", err)
	}

	logger.Infof(ctx, "Discovered %d preloaded skills", len(metadata))

	return metadata, nil
}

// GetSkillByName retrieves a skill by its name
func (s *skillService) GetSkillByName(ctx context.Context, name string) (*skills.Skill, error) {
	if err := s.ensureInitialized(ctx); err != nil {
		return nil, fmt.Errorf("failed to initialize skill service: %w", err)
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	skill, err := s.loader.LoadSkillInstructions(name)
	if err != nil {
		logger.Errorf(ctx, "Failed to load skill %s: %v", name, err)
		return nil, fmt.Errorf("failed to load skill: %w", err)
	}

	return skill, nil
}

// CreateSkill creates a managed SKILL.md under the preloaded skills directory.
func (s *skillService) CreateSkill(ctx context.Context, input skills.SkillMutationInput) (*skills.Skill, error) {
	if err := s.ensureInitialized(ctx); err != nil {
		return nil, fmt.Errorf("failed to initialize skill service: %w", err)
	}

	normalized, content, err := buildManagedSkillFile(input)
	if err != nil {
		return nil, err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if _, err := s.loader.LoadSkillInstructions(normalized.Name); err == nil {
		return nil, apperrors.NewConflictError("skill already exists")
	}

	skillDir, err := s.safeSkillDir(normalized.Name)
	if err != nil {
		return nil, err
	}
	if _, err := os.Stat(skillDir); err == nil {
		return nil, apperrors.NewConflictError("skill directory already exists")
	} else if !os.IsNotExist(err) {
		return nil, fmt.Errorf("failed to check skill directory: %w", err)
	}

	if err := os.MkdirAll(skillDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create skill directory: %w", err)
	}
	if err := os.WriteFile(filepath.Join(skillDir, skills.SkillFileName), []byte(content), 0644); err != nil {
		return nil, fmt.Errorf("failed to write skill file: %w", err)
	}

	skill, err := s.loader.LoadSkillInstructions(normalized.Name)
	if err != nil {
		return nil, fmt.Errorf("failed to reload created skill: %w", err)
	}
	return skill, nil
}

// UpdateSkill updates the SKILL.md for an existing managed skill.
func (s *skillService) UpdateSkill(ctx context.Context, name string, input skills.SkillMutationInput) (*skills.Skill, error) {
	if err := s.ensureInitialized(ctx); err != nil {
		return nil, fmt.Errorf("failed to initialize skill service: %w", err)
	}
	name = strings.TrimSpace(name)
	if name == "" {
		return nil, apperrors.NewBadRequestError("skill name is required")
	}
	if strings.TrimSpace(input.Name) == "" {
		input.Name = name
	}
	if input.Name != name {
		return nil, apperrors.NewBadRequestError("skill rename is not supported")
	}

	normalized, content, err := buildManagedSkillFile(input)
	if err != nil {
		return nil, err
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	existing, err := s.loader.LoadSkillInstructions(name)
	if err != nil {
		return nil, apperrors.NewNotFoundError("skill not found")
	}
	if !s.pathInsidePreloadedDir(existing.BasePath) {
		return nil, apperrors.NewBadRequestError("skill path is outside the managed skills directory")
	}
	if err := os.WriteFile(existing.FilePath, []byte(content), 0644); err != nil {
		return nil, fmt.Errorf("failed to write skill file: %w", err)
	}
	if _, err := s.loader.Reload(); err != nil {
		return nil, fmt.Errorf("failed to reload skills: %w", err)
	}

	updated, err := s.loader.LoadSkillInstructions(normalized.Name)
	if err != nil {
		return nil, fmt.Errorf("failed to reload updated skill: %w", err)
	}
	return updated, nil
}

// DeleteSkill deletes a managed skill directory by name.
func (s *skillService) DeleteSkill(ctx context.Context, name string) error {
	if err := s.ensureInitialized(ctx); err != nil {
		return fmt.Errorf("failed to initialize skill service: %w", err)
	}
	name = strings.TrimSpace(name)
	if name == "" {
		return apperrors.NewBadRequestError("skill name is required")
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	existing, err := s.loader.LoadSkillInstructions(name)
	if err != nil {
		return apperrors.NewNotFoundError("skill not found")
	}
	if !s.pathInsidePreloadedDir(existing.BasePath) {
		return apperrors.NewBadRequestError("skill path is outside the managed skills directory")
	}
	if err := os.RemoveAll(existing.BasePath); err != nil {
		return fmt.Errorf("failed to delete skill directory: %w", err)
	}
	_, err = s.loader.Reload()
	if err != nil {
		return fmt.Errorf("failed to reload skills: %w", err)
	}
	return nil
}

// TestSkill validates a skill without executing any script.
func (s *skillService) TestSkill(ctx context.Context, name string) (*skills.SkillTestResult, error) {
	if err := s.ensureInitialized(ctx); err != nil {
		return nil, fmt.Errorf("failed to initialize skill service: %w", err)
	}
	name = strings.TrimSpace(name)
	if name == "" {
		return nil, apperrors.NewBadRequestError("skill name is required")
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	skill, err := s.loader.LoadSkillInstructions(name)
	if err != nil {
		return nil, apperrors.NewNotFoundError("skill not found")
	}
	files, err := s.loader.ListSkillFiles(name)
	if err != nil {
		return nil, fmt.Errorf("failed to list skill files: %w", err)
	}
	sort.Strings(files)

	fileSummaries := make([]skills.SkillFileSummary, 0, len(files))
	scriptCount := 0
	for _, file := range files {
		isScript := skills.IsScript(file)
		if isScript {
			scriptCount++
		}
		fileSummaries = append(fileSummaries, skills.SkillFileSummary{
			Name:     file,
			IsScript: isScript,
		})
	}

	sandboxMode := os.Getenv("WEKNORA_SANDBOX_MODE")
	return &skills.SkillTestResult{
		Name:                  skill.Name,
		Description:           skill.Description,
		Valid:                 true,
		InstructionsPresent:   strings.TrimSpace(skill.Instructions) != "",
		InstructionsCharCount: len([]rune(skill.Instructions)),
		FileCount:             len(files),
		ScriptCount:           scriptCount,
		SandboxMode:           sandboxMode,
		SandboxAvailable:      sandboxMode != "" && sandboxMode != "disabled",
		Files:                 fileSummaries,
	}, nil
}

// GetPreloadedDir returns the configured preloaded skills directory
func (s *skillService) GetPreloadedDir() string {
	return s.preloadedDir
}

func buildManagedSkillFile(input skills.SkillMutationInput) (skills.SkillMutationInput, string, error) {
	normalized := skills.SkillMutationInput{
		Name:         strings.TrimSpace(input.Name),
		Description:  strings.TrimSpace(input.Description),
		Instructions: strings.TrimSpace(input.Instructions),
	}
	if normalized.Name == "" {
		return normalized, "", apperrors.NewBadRequestError("skill name is required")
	}
	if normalized.Description == "" {
		return normalized, "", apperrors.NewBadRequestError("skill description is required")
	}
	if normalized.Instructions == "" {
		return normalized, "", apperrors.NewBadRequestError("skill instructions are required")
	}
	if len([]rune(normalized.Instructions)) > maxManagedSkillInstructionsChars {
		return normalized, "", apperrors.NewBadRequestError("skill instructions exceed maximum length")
	}

	frontmatter, err := yaml.Marshal(struct {
		Name        string `yaml:"name"`
		Description string `yaml:"description"`
	}{
		Name:        normalized.Name,
		Description: normalized.Description,
	})
	if err != nil {
		return normalized, "", fmt.Errorf("failed to encode skill metadata: %w", err)
	}
	content := fmt.Sprintf("---\n%s---\n\n%s\n", string(frontmatter), normalized.Instructions)
	if _, err := skills.ParseSkillFile(content); err != nil {
		return normalized, "", apperrors.NewBadRequestError(err.Error())
	}
	return normalized, content, nil
}

func (s *skillService) safeSkillDir(name string) (string, error) {
	name = strings.TrimSpace(name)
	if name == "" || strings.ContainsAny(name, `/\`) || filepath.IsAbs(name) {
		return "", apperrors.NewBadRequestError("invalid skill name")
	}
	baseAbs, err := filepath.Abs(s.preloadedDir)
	if err != nil {
		return "", err
	}
	candidate := filepath.Join(baseAbs, name)
	if !pathInside(baseAbs, candidate) {
		return "", apperrors.NewBadRequestError("invalid skill path")
	}
	return candidate, nil
}

func (s *skillService) pathInsidePreloadedDir(path string) bool {
	baseAbs, err := filepath.Abs(s.preloadedDir)
	if err != nil {
		return false
	}
	return pathInside(baseAbs, path)
}

func pathInside(baseAbs, target string) bool {
	targetAbs, err := filepath.Abs(target)
	if err != nil {
		return false
	}
	rel, err := filepath.Rel(baseAbs, targetAbs)
	if err != nil {
		return false
	}
	return rel != "." && rel != ".." && !strings.HasPrefix(rel, ".."+string(os.PathSeparator))
}
