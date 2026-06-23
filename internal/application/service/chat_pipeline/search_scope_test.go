package chatpipeline

import (
	"context"
	"testing"

	"github.com/Tencent/WeKnora/internal/types"
	"github.com/stretchr/testify/require"
)

func TestFilterToExplicitKnowledgeScopeDropsOutOfScopeResults(t *testing.T) {
	chatManage := &types.ChatManage{
		PipelineRequest: types.PipelineRequest{
			KnowledgeIDs: []string{"doc-1"},
			SearchTargets: types.SearchTargets{
				{
					Type:            types.SearchTargetTypeKnowledge,
					KnowledgeBaseID: "kb-1",
					KnowledgeIDs:    []string{"doc-1"},
				},
			},
		},
	}
	results := []*types.SearchResult{
		{ID: "chunk-1", KnowledgeID: "doc-1"},
		{ID: "chunk-2", KnowledgeID: "doc-2"},
		{ID: "web-1"},
	}

	got := filterToExplicitKnowledgeScope(context.Background(), chatManage, results)

	require.Len(t, got, 1)
	require.Equal(t, "chunk-1", got[0].ID)
}

func TestFilterToExplicitKnowledgeScopeKeepsUnionWhenFullKBTargetExists(t *testing.T) {
	chatManage := &types.ChatManage{
		PipelineRequest: types.PipelineRequest{
			KnowledgeBaseIDs: []string{"kb-1"},
			KnowledgeIDs:     []string{"doc-1"},
			SearchTargets: types.SearchTargets{
				{
					Type:            types.SearchTargetTypeKnowledgeBase,
					KnowledgeBaseID: "kb-1",
				},
				{
					Type:            types.SearchTargetTypeKnowledge,
					KnowledgeBaseID: "kb-1",
					KnowledgeIDs:    []string{"doc-1"},
				},
			},
		},
	}
	results := []*types.SearchResult{
		{ID: "chunk-1", KnowledgeID: "doc-1"},
		{ID: "chunk-2", KnowledgeID: "doc-2"},
	}

	got := filterToExplicitKnowledgeScope(context.Background(), chatManage, results)

	require.Len(t, got, 2)
}
