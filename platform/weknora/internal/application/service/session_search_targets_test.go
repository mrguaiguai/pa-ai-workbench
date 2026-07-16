package service

import (
	"testing"

	"github.com/Tencent/WeKnora/internal/types"
	"github.com/stretchr/testify/require"
)

func TestAppendPartialKnowledgeTargetsKeepsDocumentScopeBesideFullKB(t *testing.T) {
	kbTenantMap := map[string]uint64{"kb-1": 7}
	targets := types.SearchTargets{
		{
			Type:            types.SearchTargetTypeKnowledgeBase,
			KnowledgeBaseID: "kb-1",
			TenantID:        7,
		},
	}

	got := appendPartialKnowledgeTargets(
		targets,
		[]*types.Knowledge{
			{ID: "doc-1", KnowledgeBaseID: "kb-1", TenantID: 7},
			{ID: "doc-2", KnowledgeBaseID: "kb-2", TenantID: 8},
		},
		kbTenantMap,
		7,
	)

	require.Len(t, got, 3)
	require.Equal(t, types.SearchTargetTypeKnowledgeBase, got[0].Type)
	kb1Target := findKnowledgeTarget(got, "kb-1")
	kb2Target := findKnowledgeTarget(got, "kb-2")
	require.NotNil(t, kb1Target)
	require.NotNil(t, kb2Target)
	require.Equal(t, []string{"doc-1"}, kb1Target.KnowledgeIDs)
	require.Equal(t, uint64(7), kb1Target.TenantID)
	require.Equal(t, []string{"doc-2"}, kb2Target.KnowledgeIDs)
	require.Equal(t, uint64(8), kb2Target.TenantID)
}

func findKnowledgeTarget(targets types.SearchTargets, kbID string) *types.SearchTarget {
	for _, target := range targets {
		if target.Type == types.SearchTargetTypeKnowledge && target.KnowledgeBaseID == kbID {
			return target
		}
	}
	return nil
}
