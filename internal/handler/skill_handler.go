package handler

import (
	"net/http"
	"os"

	"github.com/Tencent/WeKnora/internal/agent/skills"
	"github.com/Tencent/WeKnora/internal/errors"
	"github.com/Tencent/WeKnora/internal/logger"
	"github.com/Tencent/WeKnora/internal/types/interfaces"
	"github.com/gin-gonic/gin"
)

// SkillHandler handles skill-related HTTP requests
type SkillHandler struct {
	skillService interfaces.SkillService
}

// NewSkillHandler creates a new skill handler
func NewSkillHandler(skillService interfaces.SkillService) *SkillHandler {
	return &SkillHandler{
		skillService: skillService,
	}
}

// SkillInfoResponse represents the skill info returned to frontend
type SkillInfoResponse struct {
	Name        string `json:"name"`
	Description string `json:"description"`
}

// SkillDetailResponse represents the safe skill detail returned to frontend
type SkillDetailResponse struct {
	Name                  string                    `json:"name"`
	Description           string                    `json:"description"`
	Instructions          string                    `json:"instructions"`
	InstructionsPresent   bool                      `json:"instructions_present"`
	InstructionsCharCount int                       `json:"instructions_char_count"`
	FileCount             int                       `json:"file_count"`
	ScriptCount           int                       `json:"script_count"`
	Files                 []skills.SkillFileSummary `json:"files"`
}

// SkillMutationRequest defines create/update body for a managed SKILL.md.
type SkillMutationRequest struct {
	Name         string `json:"name"`
	Description  string `json:"description" binding:"required"`
	Instructions string `json:"instructions" binding:"required"`
}

// ListSkills godoc
// @Summary      获取预装Skills列表
// @Description  获取所有预装的Agent Skills元数据
// @Tags         Skills
// @Accept       json
// @Produce      json
// @Success      200  {object}  map[string]interface{}  "Skills列表"
// @Failure      500  {object}  errors.AppError         "服务器错误"
// @Security     Bearer
// @Security     ApiKeyAuth
// @Router       /skills [get]
func (h *SkillHandler) ListSkills(c *gin.Context) {
	ctx := c.Request.Context()

	skillsMetadata, err := h.skillService.ListPreloadedSkills(ctx)
	if err != nil {
		logger.ErrorWithFields(ctx, err, nil)
		c.Error(errors.NewInternalServerError("Failed to list skills: " + err.Error()))
		return
	}

	// Convert to response format
	var response []SkillInfoResponse
	for _, meta := range skillsMetadata {
		response = append(response, SkillInfoResponse{
			Name:        meta.Name,
			Description: meta.Description,
		})
	}

	// skills_available: true only when sandbox is enabled (docker or local), so frontend can hide/disable Skills UI
	sandboxMode := os.Getenv("WEKNORA_SANDBOX_MODE")
	skillsAvailable := sandboxMode != "" && sandboxMode != "disabled"

	logger.Infof(ctx, "skills_available: %v, sandboxMode: %s", skillsAvailable, sandboxMode)

	c.JSON(http.StatusOK, gin.H{
		"success":          true,
		"data":             response,
		"skills_available": skillsAvailable,
	})
}

// GetSkill godoc
// @Summary      获取预装Skill详情
// @Description  获取单个预装Agent Skill的元数据和SKILL.md正文
// @Tags         Skills
// @Accept       json
// @Produce      json
// @Param        name  path      string                true  "Skill名称"
// @Success      200   {object}  map[string]interface{} "Skill详情"
// @Failure      404   {object}  errors.AppError        "Skill不存在"
// @Security     Bearer
// @Security     ApiKeyAuth
// @Router       /skills/{name} [get]
func (h *SkillHandler) GetSkill(c *gin.Context) {
	ctx := c.Request.Context()
	name := c.Param("name")

	skill, err := h.skillService.GetSkillByName(ctx, name)
	if err != nil {
		logger.Warnf(ctx, "Failed to get skill %s: %v", name, err)
		c.Error(errors.NewNotFoundError("skill not found"))
		return
	}
	testResult, err := h.skillService.TestSkill(ctx, name)
	if err != nil {
		logger.Warnf(ctx, "Failed to summarize skill %s: %v", name, err)
		c.Error(errors.NewInternalServerError("Failed to summarize skill: " + err.Error()))
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data":    newSkillDetailResponse(skill, testResult),
	})
}

// CreateSkill godoc
// @Summary      创建Skill
// @Description  在预装Skills目录下创建一个仅包含SKILL.md的受管Skill
// @Tags         Skills
// @Accept       json
// @Produce      json
// @Param        request  body      SkillMutationRequest  true  "Skill内容"
// @Success      201      {object}  map[string]interface{} "创建结果"
// @Failure      400      {object}  errors.AppError        "无效请求"
// @Failure      409      {object}  errors.AppError        "Skill已存在"
// @Security     Bearer
// @Security     ApiKeyAuth
// @Router       /skills [post]
func (h *SkillHandler) CreateSkill(c *gin.Context) {
	ctx := c.Request.Context()
	var req SkillMutationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.Error(errors.NewBadRequestError(err.Error()))
		return
	}

	skill, err := h.skillService.CreateSkill(ctx, skillMutationInput(req))
	if err != nil {
		logger.Warnf(ctx, "Failed to create skill %s: %v", req.Name, err)
		c.Error(err)
		return
	}
	testResult, err := h.skillService.TestSkill(ctx, skill.Name)
	if err != nil {
		logger.Warnf(ctx, "Failed to summarize created skill %s: %v", skill.Name, err)
		c.Error(errors.NewInternalServerError("Failed to summarize skill: " + err.Error()))
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"success": true,
		"data":    newSkillDetailResponse(skill, testResult),
	})
}

// UpdateSkill godoc
// @Summary      更新Skill
// @Description  更新受管Skill的SKILL.md；不支持重命名或脚本上传
// @Tags         Skills
// @Accept       json
// @Produce      json
// @Param        name     path      string                true  "Skill名称"
// @Param        request  body      SkillMutationRequest  true  "Skill内容"
// @Success      200      {object}  map[string]interface{} "更新结果"
// @Failure      400      {object}  errors.AppError        "无效请求"
// @Failure      404      {object}  errors.AppError        "Skill不存在"
// @Security     Bearer
// @Security     ApiKeyAuth
// @Router       /skills/{name} [put]
func (h *SkillHandler) UpdateSkill(c *gin.Context) {
	ctx := c.Request.Context()
	name := c.Param("name")
	var req SkillMutationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.Error(errors.NewBadRequestError(err.Error()))
		return
	}

	input := skillMutationInput(req)
	if input.Name == "" {
		input.Name = name
	}
	skill, err := h.skillService.UpdateSkill(ctx, name, input)
	if err != nil {
		logger.Warnf(ctx, "Failed to update skill %s: %v", name, err)
		c.Error(err)
		return
	}
	testResult, err := h.skillService.TestSkill(ctx, skill.Name)
	if err != nil {
		logger.Warnf(ctx, "Failed to summarize updated skill %s: %v", skill.Name, err)
		c.Error(errors.NewInternalServerError("Failed to summarize skill: " + err.Error()))
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data":    newSkillDetailResponse(skill, testResult),
	})
}

// DeleteSkill godoc
// @Summary      删除Skill
// @Description  删除预装Skills目录下的受管Skill
// @Tags         Skills
// @Accept       json
// @Produce      json
// @Param        name  path      string                true  "Skill名称"
// @Success      200   {object}  map[string]interface{} "删除结果"
// @Failure      404   {object}  errors.AppError        "Skill不存在"
// @Security     Bearer
// @Security     ApiKeyAuth
// @Router       /skills/{name} [delete]
func (h *SkillHandler) DeleteSkill(c *gin.Context) {
	ctx := c.Request.Context()
	name := c.Param("name")
	if err := h.skillService.DeleteSkill(ctx, name); err != nil {
		logger.Warnf(ctx, "Failed to delete skill %s: %v", name, err)
		c.Error(err)
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": gin.H{
			"name":    name,
			"deleted": true,
		},
	})
}

// TestSkill godoc
// @Summary      测试Skill
// @Description  校验Skill元数据、正文和文件清单；不会执行Skill脚本
// @Tags         Skills
// @Accept       json
// @Produce      json
// @Param        name  path      string                true  "Skill名称"
// @Success      200   {object}  map[string]interface{} "测试结果"
// @Failure      404   {object}  errors.AppError        "Skill不存在"
// @Security     Bearer
// @Security     ApiKeyAuth
// @Router       /skills/{name}/test [post]
func (h *SkillHandler) TestSkill(c *gin.Context) {
	ctx := c.Request.Context()
	name := c.Param("name")
	result, err := h.skillService.TestSkill(ctx, name)
	if err != nil {
		logger.Warnf(ctx, "Failed to test skill %s: %v", name, err)
		c.Error(err)
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": gin.H{
			"name":                    result.Name,
			"description_present":     result.Description != "",
			"valid":                   result.Valid,
			"instructions_present":    result.InstructionsPresent,
			"instructions_char_count": result.InstructionsCharCount,
			"file_count":              result.FileCount,
			"script_count":            result.ScriptCount,
			"sandbox_mode":            result.SandboxMode,
			"sandbox_available":       result.SandboxAvailable,
			"execution_performed":     false,
			"files":                   result.Files,
		},
	})
}

func skillMutationInput(req SkillMutationRequest) skills.SkillMutationInput {
	return skills.SkillMutationInput{
		Name:         req.Name,
		Description:  req.Description,
		Instructions: req.Instructions,
	}
}

func newSkillDetailResponse(skill *skills.Skill, testResult *skills.SkillTestResult) SkillDetailResponse {
	return SkillDetailResponse{
		Name:                  skill.Name,
		Description:           skill.Description,
		Instructions:          skill.Instructions,
		InstructionsPresent:   testResult.InstructionsPresent,
		InstructionsCharCount: testResult.InstructionsCharCount,
		FileCount:             testResult.FileCount,
		ScriptCount:           testResult.ScriptCount,
		Files:                 testResult.Files,
	}
}
