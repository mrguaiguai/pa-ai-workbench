// Package service provides business logic implementations for WeKnora application
// This package contains service layer implementations that coordinate between
// repositories and handlers, applying business rules and transaction management
package service

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/Tencent/WeKnora/internal/application/service/retriever"
	"github.com/Tencent/WeKnora/internal/logger"
	"github.com/Tencent/WeKnora/internal/types"
	"github.com/Tencent/WeKnora/internal/types/interfaces"
)

// chunkService implements the ChunkService interface
// It provides operations for managing document chunks in the knowledge base
// Chunks are segments of documents that have been processed and prepared for indexing
type chunkService struct {
	chunkRepository interfaces.ChunkRepository // Repository for chunk data persistence
	kbRepository    interfaces.KnowledgeBaseRepository
	modelService    interfaces.ModelService
	retrieveEngine  interfaces.RetrieveEngineRegistry
	ownership       retriever.TenantStoreOwnership
}

const maxGeneratedQuestionChars = 2000

// NewChunkService creates a new chunk service
// It initializes a service with the provided chunk repository
// Parameters:
//   - chunkRepository: Repository for chunk operations
//
// Returns:
//   - interfaces.ChunkService: Initialized chunk service implementation
func NewChunkService(
	chunkRepository interfaces.ChunkRepository,
	kbRepository interfaces.KnowledgeBaseRepository,
	modelService interfaces.ModelService,
	retrieveEngine interfaces.RetrieveEngineRegistry,
	ownership retriever.TenantStoreOwnership,
) interfaces.ChunkService {
	return &chunkService{
		chunkRepository: chunkRepository,
		kbRepository:    kbRepository,
		modelService:    modelService,
		retrieveEngine:  retrieveEngine,
		ownership:       ownership,
	}
}

// GetRepository gets the chunk repository
// Parameters:
//   - ctx: Context with authentication and request information
//
// Returns:
//   - interfaces.ChunkRepository: Chunk repository
func (s *chunkService) GetRepository() interfaces.ChunkRepository {
	return s.chunkRepository
}

// CreateChunks creates multiple chunks
// This method persists a batch of document chunks to the repository
// Parameters:
//   - ctx: Context with authentication and request information
//   - chunks: Slice of document chunks to create
//
// Returns:
//   - error: Any error encountered during chunk creation
func (s *chunkService) CreateChunks(ctx context.Context, chunks []*types.Chunk) error {
	err := s.chunkRepository.CreateChunks(ctx, chunks)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_count": len(chunks),
		})
		return err
	}

	logger.Infof(ctx, "Add %d chunks successfully", len(chunks))
	return nil
}

// GetChunkByID retrieves a chunk by its ID
// This method fetches a specific chunk using its ID and validates tenant access
// Parameters:
//   - ctx: Context with authentication and request information
//   - knowledgeID: ID of the knowledge document containing the chunk
//   - id: ID of the chunk to retrieve
//
// Returns:
//   - *types.Chunk: Retrieved chunk if found
//   - error: Any error encountered during retrieval
func (s *chunkService) GetChunkByID(ctx context.Context, id string) (*types.Chunk, error) {
	tenantID := types.MustTenantIDFromContext(ctx)
	logger.Infof(ctx, "Getting chunk by ID, ID: %s, tenant ID: %d", id, tenantID)
	chunk, err := s.chunkRepository.GetChunkByID(ctx, tenantID, id)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"tenant_id": tenantID,
		})
		return nil, err
	}

	logger.Info(ctx, "Chunk retrieved successfully")
	return chunk, nil
}

// GetChunkByIDOnly retrieves a chunk by ID without tenant filter (for permission resolution).
func (s *chunkService) GetChunkByIDOnly(ctx context.Context, id string) (*types.Chunk, error) {
	chunk, err := s.chunkRepository.GetChunkByIDOnly(ctx, id)
	if err != nil {
		if err != nil && err.Error() == "chunk not found" {
			return nil, ErrChunkNotFound
		}
		logger.ErrorWithFields(ctx, err, map[string]interface{}{"chunk_id": id})
		return nil, err
	}
	return chunk, nil
}

// ListChunksByKnowledgeID lists all chunks for a knowledge ID
// This method retrieves all chunks belonging to a specific knowledge document
// Parameters:
//   - ctx: Context with authentication and request information
//   - knowledgeID: ID of the knowledge document
//
// Returns:
//   - []*types.Chunk: List of chunks belonging to the knowledge document
//   - error: Any error encountered during retrieval
func (s *chunkService) ListChunksByKnowledgeID(ctx context.Context, knowledgeID string) ([]*types.Chunk, error) {
	logger.Info(ctx, "Start listing chunks by knowledge ID")
	logger.Infof(ctx, "Knowledge ID: %s", knowledgeID)

	tenantID := types.MustTenantIDFromContext(ctx)
	logger.Infof(ctx, "Tenant ID: %d", tenantID)

	chunks, err := s.chunkRepository.ListChunksByKnowledgeID(ctx, tenantID, knowledgeID)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"knowledge_id": knowledgeID,
			"tenant_id":    tenantID,
		})
		return nil, err
	}

	logger.Infof(ctx, "Retrieved %d chunks successfully", len(chunks))
	return chunks, nil
}

// ListPagedChunksByKnowledgeID lists chunks for a knowledge ID with pagination
// This method retrieves chunks with pagination support for better performance with large datasets
// Parameters:
//   - ctx: Context with authentication and request information
//   - knowledgeID: ID of the knowledge document
//   - page: Pagination parameters including page number and page size
//
// Returns:
//   - *types.PageResult: Paginated result containing chunks and pagination metadata
//   - error: Any error encountered during retrieval
func (s *chunkService) ListPagedChunksByKnowledgeID(ctx context.Context,
	knowledgeID string, page *types.Pagination, chunkType []types.ChunkType,
) (*types.PageResult, error) {
	tenantID := types.MustTenantIDFromContext(ctx)
	chunks, total, err := s.chunkRepository.ListPagedChunksByKnowledgeID(
		ctx,
		tenantID,
		knowledgeID,
		page,
		chunkType,
		"",
		"",
		"",
		"",
		"",
	)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"knowledge_id": knowledgeID,
			"tenant_id":    tenantID,
		})
		return nil, err
	}

	logger.Infof(ctx, "Retrieved %d chunks out of %d total chunks", len(chunks), total)
	return types.NewPageResult(total, page, chunks), nil
}

// updateChunk updates a chunk
// This method updates an existing chunk in the repository
// Parameters:
//   - ctx: Context with authentication and request information
//   - chunk: Chunk with updated fields
//
// Returns:
//   - error: Any error encountered during update
//
// This method handles the actual update logic for a chunk, including updating the vector database representation
func (s *chunkService) UpdateChunk(ctx context.Context, chunk *types.Chunk) error {
	logger.Infof(ctx, "Updating chunk, ID: %s, knowledge ID: %s", chunk.ID, chunk.KnowledgeID)

	tenantID := types.MustTenantIDFromContext(ctx)
	previousChunk, err := s.chunkRepository.GetChunkByID(ctx, tenantID, chunk.ID)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_id":     chunk.ID,
			"knowledge_id": chunk.KnowledgeID,
			"tenant_id":    tenantID,
		})
		return err
	}
	contentChanged := previousChunk.Content != chunk.Content

	// Update the chunk in the repository
	err = s.chunkRepository.UpdateChunk(ctx, chunk)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_id":     chunk.ID,
			"knowledge_id": chunk.KnowledgeID,
		})
		return err
	}

	if contentChanged {
		if err := s.refreshChunkContentIndex(ctx, previousChunk, chunk); err != nil {
			logger.ErrorWithFields(ctx, err, map[string]interface{}{
				"chunk_id":          chunk.ID,
				"knowledge_id":      chunk.KnowledgeID,
				"knowledge_base_id": chunk.KnowledgeBaseID,
			})
			return fmt.Errorf("failed to refresh chunk content index: %w", err)
		}
	}

	logger.Info(ctx, "Chunk updated successfully")
	return nil
}

func (s *chunkService) refreshChunkContentIndex(ctx context.Context, previousChunk, chunk *types.Chunk) error {
	if chunk == nil || previousChunk == nil {
		return nil
	}
	if !isChunkContentIndexable(previousChunk) && !isChunkContentIndexable(chunk) {
		return nil
	}

	tenantID := types.MustTenantIDFromContext(ctx)
	kb, err := s.kbRepository.GetKnowledgeBaseByID(ctx, chunk.KnowledgeBaseID)
	if err != nil {
		return fmt.Errorf("failed to get knowledge base: %w", err)
	}
	kb.EnsureDefaults()
	if !kb.NeedsEmbeddingModel() || kb.EmbeddingModelID == "" {
		logger.Infof(ctx, "Skip chunk content index refresh because KB has no embedding-backed index, chunk ID: %s", chunk.ID)
		return nil
	}

	retrieveEngine, err := retriever.CreateRetrieveEngineForKB(
		ctx, s.retrieveEngine, s.ownership, tenantID, kb.VectorStoreID)
	if err != nil {
		return fmt.Errorf("failed to create retrieve engine: %w", err)
	}

	embeddingModel, err := s.modelService.GetEmbeddingModel(ctx, kb.EmbeddingModelID)
	if err != nil {
		return fmt.Errorf("failed to get embedding model: %w", err)
	}

	// Delete only the main content index entry. Generated-question indexes
	// share chunk_id but use source_id "{chunk_id}-{question_id}", so deleting
	// by chunk_id here would erase unrelated generated-question vectors.
	if isChunkContentIndexable(previousChunk) {
		if err := retrieveEngine.DeleteBySourceIDList(
			ctx,
			[]string{chunk.ID},
			embeddingModel.GetDimensions(),
			kb.Type,
		); err != nil {
			return fmt.Errorf("failed to delete existing chunk content index: %w", err)
		}
	}

	if !isChunkContentIndexable(chunk) {
		logger.Infof(ctx, "Chunk content became non-indexable; old content index removed, chunk ID: %s", chunk.ID)
		return nil
	}

	indexInfo := []*types.IndexInfo{{
		Content:         chunk.EmbeddingContent(),
		SourceID:        chunk.ID,
		SourceType:      types.ChunkSourceType,
		ChunkID:         chunk.ID,
		KnowledgeID:     chunk.KnowledgeID,
		KnowledgeBaseID: chunk.KnowledgeBaseID,
		KnowledgeType:   kb.Type,
		TagID:           chunk.TagID,
		IsEnabled:       chunk.IsEnabled,
		IsRecommended:   chunk.Flags.HasFlag(types.ChunkFlagRecommended),
	}}
	if err := retrieveEngine.BatchIndex(ctx, embeddingModel, indexInfo); err != nil {
		return fmt.Errorf("failed to index updated chunk content: %w", err)
	}
	return nil
}

func isChunkContentIndexable(chunk *types.Chunk) bool {
	if chunk == nil || strings.TrimSpace(chunk.Content) == "" {
		return false
	}
	switch chunk.ChunkType {
	case "", types.ChunkTypeText, types.ChunkTypeSummary, types.ChunkTypeTableColumn,
		types.ChunkTypeTableSummary, types.ChunkTypeFAQ, types.ChunkTypeImageOCR,
		types.ChunkTypeImageCaption, types.ChunkTypeWikiPage:
		return true
	default:
		return false
	}
}

// UpdateChunks updates chunks in batch
func (s *chunkService) UpdateChunks(ctx context.Context, chunks []*types.Chunk) error {
	if len(chunks) == 0 {
		return nil
	}
	logger.Infof(ctx, "Updating %d chunks in batch", len(chunks))

	// Update the chunks in the repository
	err := s.chunkRepository.UpdateChunks(ctx, chunks)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_count": len(chunks),
		})
		return err
	}

	logger.Infof(ctx, "Successfully updated %d chunks", len(chunks))
	return nil
}

// DeleteChunk deletes a chunk by ID
// This method removes a specific chunk from the repository
// Parameters:
//   - ctx: Context with authentication and request information
//   - id: ID of the chunk to delete
//
// Returns:
//   - error: Any error encountered during deletion
func (s *chunkService) DeleteChunk(ctx context.Context, id string) error {
	tenantID := types.MustTenantIDFromContext(ctx)
	err := s.chunkRepository.DeleteChunk(ctx, tenantID, id)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"tenant_id": tenantID,
		})
		return err
	}
	logger.Info(ctx, "Chunk deleted successfully")
	return nil
}

// DeleteChunks deletes chunks by IDs in batch
// This method removes multiple chunks from the repository in a single operation
// Parameters:
//   - ctx: Context with authentication and request information
//   - ids: Slice of chunk IDs to delete
//
// Returns:
//   - error: Any error encountered during batch deletion
func (s *chunkService) DeleteChunks(ctx context.Context, ids []string) error {
	if len(ids) == 0 {
		return nil
	}
	logger.Info(ctx, "Start deleting chunks in batch")
	logger.Infof(ctx, "Deleting %d chunks", len(ids))

	tenantID := types.MustTenantIDFromContext(ctx)
	logger.Infof(ctx, "Tenant ID: %d", tenantID)

	err := s.chunkRepository.DeleteChunks(ctx, tenantID, ids)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_ids": ids,
			"tenant_id": tenantID,
		})
		return err
	}

	logger.Infof(ctx, "Successfully deleted %d chunks", len(ids))
	return nil
}

// DeleteChunksByKnowledgeID deletes all chunks for a knowledge ID
// This method removes all chunks belonging to a specific knowledge document
// Parameters:
//   - ctx: Context with authentication and request information
//   - knowledgeID: ID of the knowledge document
//
// Returns:
//   - error: Any error encountered during bulk deletion
func (s *chunkService) DeleteChunksByKnowledgeID(ctx context.Context, knowledgeID string) error {
	logger.Info(ctx, "Start deleting all chunks by knowledge ID")
	logger.Infof(ctx, "Knowledge ID: %s", knowledgeID)

	tenantID := types.MustTenantIDFromContext(ctx)
	logger.Infof(ctx, "Tenant ID: %d", tenantID)

	err := s.chunkRepository.DeleteChunksByKnowledgeID(ctx, tenantID, knowledgeID)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"knowledge_id": knowledgeID,
			"tenant_id":    tenantID,
		})
		return err
	}

	logger.Info(ctx, "All chunks under knowledge deleted successfully")
	return nil
}

func (s *chunkService) DeleteByKnowledgeList(ctx context.Context, ids []string) error {
	logger.Info(ctx, "Start deleting all chunks by knowledge IDs")
	logger.Infof(ctx, "Knowledge IDs: %v", ids)

	tenantID := types.MustTenantIDFromContext(ctx)
	logger.Infof(ctx, "Tenant ID: %d", tenantID)

	err := s.chunkRepository.DeleteByKnowledgeList(ctx, tenantID, ids)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"knowledge_id": ids,
			"tenant_id":    tenantID,
		})
		return err
	}

	logger.Info(ctx, "All chunks under knowledge deleted successfully")
	return nil
}

func (s *chunkService) ListChunkByParentID(
	ctx context.Context,
	tenantID uint64,
	parentID string,
) ([]*types.Chunk, error) {
	logger.Info(ctx, "Start listing chunk by parent ID")
	logger.Infof(ctx, "Parent ID: %s", parentID)

	chunks, err := s.chunkRepository.ListChunkByParentID(ctx, tenantID, parentID)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"parent_id": parentID,
			"tenant_id": tenantID,
		})
		return nil, err
	}

	logger.Info(ctx, "Chunk listed successfully")
	return chunks, nil
}

// AddGeneratedQuestion adds a single generated question to a chunk and indexes it.
func (s *chunkService) AddGeneratedQuestion(ctx context.Context, chunkID string, question string) (*types.Chunk, *types.GeneratedQuestion, error) {
	normalizedQuestion := strings.TrimSpace(question)
	if normalizedQuestion == "" {
		return nil, nil, fmt.Errorf("question cannot be empty")
	}
	if len([]rune(normalizedQuestion)) > maxGeneratedQuestionChars {
		return nil, nil, fmt.Errorf("question is too long")
	}

	tenantID := types.MustTenantIDFromContext(ctx)
	chunk, err := s.chunkRepository.GetChunkByID(ctx, tenantID, chunkID)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_id":  chunkID,
			"tenant_id": tenantID,
		})
		return nil, nil, fmt.Errorf("failed to get chunk: %w", err)
	}
	if strings.TrimSpace(chunk.Content) == "" {
		return nil, nil, fmt.Errorf("cannot add generated question to an empty chunk")
	}

	meta, err := chunk.DocumentMetadata()
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_id": chunkID,
		})
		return nil, nil, fmt.Errorf("failed to parse chunk metadata: %w", err)
	}
	if meta == nil {
		meta = &types.DocumentChunkMetadata{}
	}

	for _, existing := range meta.GeneratedQuestions {
		if strings.EqualFold(strings.TrimSpace(existing.Question), normalizedQuestion) {
			return nil, nil, fmt.Errorf("generated question already exists for chunk %s", chunkID)
		}
	}

	kb, err := s.kbRepository.GetKnowledgeBaseByID(ctx, chunk.KnowledgeBaseID)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"knowledge_base_id": chunk.KnowledgeBaseID,
		})
		return nil, nil, fmt.Errorf("failed to get knowledge base: %w", err)
	}

	retrieveEngine, err := retriever.CreateRetrieveEngineForKB(
		ctx, s.retrieveEngine, s.ownership, tenantID, kb.VectorStoreID)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_id": chunkID,
		})
		return nil, nil, fmt.Errorf("failed to create retrieve engine: %w", err)
	}

	embeddingModel, err := s.modelService.GetEmbeddingModel(ctx, kb.EmbeddingModelID)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"embedding_model_id": kb.EmbeddingModelID,
		})
		return nil, nil, fmt.Errorf("failed to get embedding model: %w", err)
	}

	generatedQuestion := &types.GeneratedQuestion{
		ID:       fmt.Sprintf("q%d", time.Now().UnixNano()),
		Question: normalizedQuestion,
	}
	sourceID := fmt.Sprintf("%s-%s", chunkID, generatedQuestion.ID)
	indexInfo := []*types.IndexInfo{{
		Content:         normalizedQuestion,
		SourceID:        sourceID,
		SourceType:      types.ChunkSourceType,
		ChunkID:         chunk.ID,
		KnowledgeID:     chunk.KnowledgeID,
		KnowledgeBaseID: chunk.KnowledgeBaseID,
		KnowledgeType:   kb.Type,
		TagID:           chunk.TagID,
		IsEnabled:       chunk.IsEnabled,
	}}
	if err := retrieveEngine.BatchIndex(ctx, embeddingModel, indexInfo); err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_id": chunkID,
		})
		return nil, nil, fmt.Errorf("failed to index generated question: %w", err)
	}

	meta.GeneratedQuestions = append(meta.GeneratedQuestions, *generatedQuestion)
	if err := chunk.SetDocumentMetadata(meta); err != nil {
		_ = retrieveEngine.DeleteBySourceIDList(ctx, []string{sourceID}, embeddingModel.GetDimensions(), kb.Type)
		return nil, nil, fmt.Errorf("failed to set chunk metadata: %w", err)
	}
	if err := s.chunkRepository.UpdateChunk(ctx, chunk); err != nil {
		_ = retrieveEngine.DeleteBySourceIDList(ctx, []string{sourceID}, embeddingModel.GetDimensions(), kb.Type)
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_id": chunkID,
		})
		return nil, nil, fmt.Errorf("failed to update chunk: %w", err)
	}

	logger.Infof(ctx, "Successfully added generated question %s to chunk %s", generatedQuestion.ID, chunkID)
	return chunk, generatedQuestion, nil
}

// DeleteGeneratedQuestion deletes a single generated question from a chunk by question ID
// This updates the chunk metadata and removes the corresponding vector index
func (s *chunkService) DeleteGeneratedQuestion(ctx context.Context, chunkID string, questionID string) error {
	logger.Infof(ctx, "Deleting generated question, chunk ID: %s, question ID: %s", chunkID, questionID)

	tenantID := types.MustTenantIDFromContext(ctx)

	// 1. Get the chunk
	chunk, err := s.chunkRepository.GetChunkByID(ctx, tenantID, chunkID)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_id":  chunkID,
			"tenant_id": tenantID,
		})
		return fmt.Errorf("failed to get chunk: %w", err)
	}

	// 2. Parse the metadata
	meta, err := chunk.DocumentMetadata()
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_id": chunkID,
		})
		return fmt.Errorf("failed to parse chunk metadata: %w", err)
	}

	if meta == nil || len(meta.GeneratedQuestions) == 0 {
		return fmt.Errorf("no generated questions found for chunk %s", chunkID)
	}

	// 3. Find the question by ID
	questionIndex := -1
	for i, q := range meta.GeneratedQuestions {
		if q.ID == questionID {
			questionIndex = i
			break
		}
	}

	if questionIndex == -1 {
		return fmt.Errorf("question with ID %s not found in chunk %s", questionID, chunkID)
	}

	// 4. Get knowledge base to get embedding model
	kb, err := s.kbRepository.GetKnowledgeBaseByID(ctx, chunk.KnowledgeBaseID)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"knowledge_base_id": chunk.KnowledgeBaseID,
		})
		return fmt.Errorf("failed to get knowledge base: %w", err)
	}

	// 5. Delete the vector index for this question
	// The source_id format is: {chunk_id}-{question_id}
	sourceID := fmt.Sprintf("%s-%s", chunkID, questionID)

	retrieveEngine, err := retriever.CreateRetrieveEngineForKB(
		ctx, s.retrieveEngine, s.ownership, tenantID, kb.VectorStoreID)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_id": chunkID,
		})
		return fmt.Errorf("failed to create retrieve engine: %w", err)
	}

	embeddingModel, err := s.modelService.GetEmbeddingModel(ctx, kb.EmbeddingModelID)
	if err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"embedding_model_id": kb.EmbeddingModelID,
		})
		return fmt.Errorf("failed to get embedding model: %w", err)
	}

	// Delete the vector index by source ID
	if err := retrieveEngine.DeleteBySourceIDList(ctx, []string{sourceID}, embeddingModel.GetDimensions(), kb.Type); err != nil {
		logger.Warnf(ctx, "Failed to delete vector index for question (may not exist): %v", err)
		// Continue even if vector deletion fails - the question might not have been indexed
	}

	// 6. Remove the question from metadata
	newQuestions := make([]types.GeneratedQuestion, 0, len(meta.GeneratedQuestions)-1)
	for i, q := range meta.GeneratedQuestions {
		if i != questionIndex {
			newQuestions = append(newQuestions, q)
		}
	}

	// 7. Update chunk metadata
	meta.GeneratedQuestions = newQuestions
	if err := chunk.SetDocumentMetadata(meta); err != nil {
		return fmt.Errorf("failed to set chunk metadata: %w", err)
	}

	if err := s.chunkRepository.UpdateChunk(ctx, chunk); err != nil {
		logger.ErrorWithFields(ctx, err, map[string]interface{}{
			"chunk_id": chunkID,
		})
		return fmt.Errorf("failed to update chunk: %w", err)
	}

	logger.Infof(ctx, "Successfully deleted generated question %s from chunk %s", questionID, chunkID)
	return nil
}

type chunkSearchHit struct {
	index           *types.IndexWithScore
	retrieverType   types.RetrieverType
	retrieverEngine string
}

// SearchSimilarChunks searches a chunk's owning KB using the chunk content as the query.
func (s *chunkService) SearchSimilarChunks(
	ctx context.Context,
	chunkID string,
	topK int,
	vectorThreshold float64,
	keywordThreshold float64,
	includeSelf bool,
) ([]*types.ChunkSearchResult, error) {
	tenantID := types.MustTenantIDFromContext(ctx)
	if topK <= 0 {
		topK = 8
	}
	if topK > 50 {
		topK = 50
	}

	sourceChunk, err := s.chunkRepository.GetChunkByID(ctx, tenantID, chunkID)
	if err != nil {
		return nil, err
	}
	queryText := sourceChunk.EmbeddingContent()
	if strings.TrimSpace(queryText) == "" {
		return []*types.ChunkSearchResult{}, nil
	}

	kb, err := s.kbRepository.GetKnowledgeBaseByID(ctx, sourceChunk.KnowledgeBaseID)
	if err != nil {
		return nil, fmt.Errorf("failed to get knowledge base: %w", err)
	}
	kb.EnsureDefaults()

	retrieveEngine, err := retriever.CreateRetrieveEngineForKB(
		ctx, s.retrieveEngine, s.ownership, tenantID, kb.VectorStoreID)
	if err != nil {
		return nil, fmt.Errorf("failed to create retrieve engine: %w", err)
	}

	searchTopK := topK
	if !includeSelf {
		searchTopK++
	}

	var retrieveParams []types.RetrieveParams
	if retrieveEngine.SupportRetriever(types.VectorRetrieverType) &&
		kb.IsVectorEnabled() && kb.EmbeddingModelID != "" {
		embeddingModel, err := s.modelService.GetEmbeddingModel(ctx, kb.EmbeddingModelID)
		if err != nil {
			return nil, fmt.Errorf("failed to get embedding model: %w", err)
		}
		queryEmbedding, err := embeddingModel.Embed(ctx, queryText)
		if err != nil {
			return nil, fmt.Errorf("failed to embed chunk content: %w", err)
		}
		vectorParams := types.RetrieveParams{
			Query:            queryText,
			Embedding:        queryEmbedding,
			KnowledgeBaseIDs: []string{sourceChunk.KnowledgeBaseID},
			TopK:             searchTopK,
			Threshold:        vectorThreshold,
			RetrieverType:    types.VectorRetrieverType,
		}
		if kb.Type == types.KnowledgeBaseTypeFAQ {
			vectorParams.KnowledgeType = types.KnowledgeTypeFAQ
		}
		retrieveParams = append(retrieveParams, vectorParams)
	}
	if retrieveEngine.SupportRetriever(types.KeywordsRetrieverType) &&
		kb.IsKeywordEnabled() && kb.Type != types.KnowledgeBaseTypeFAQ {
		retrieveParams = append(retrieveParams, types.RetrieveParams{
			Query:            queryText,
			KnowledgeBaseIDs: []string{sourceChunk.KnowledgeBaseID},
			TopK:             searchTopK,
			Threshold:        keywordThreshold,
			RetrieverType:    types.KeywordsRetrieverType,
		})
	}
	if len(retrieveParams) == 0 {
		return []*types.ChunkSearchResult{}, nil
	}

	retrieveResults, err := retrieveEngine.Retrieve(ctx, retrieveParams)
	if err != nil {
		return nil, err
	}

	bestHits := make(map[string]*chunkSearchHit)
	for _, result := range retrieveResults {
		if result == nil {
			continue
		}
		for _, index := range result.Results {
			if index == nil || index.ChunkID == "" {
				continue
			}
			if !includeSelf && index.ChunkID == sourceChunk.ID {
				continue
			}
			if existing, ok := bestHits[index.ChunkID]; ok && existing.index.Score >= index.Score {
				continue
			}
			bestHits[index.ChunkID] = &chunkSearchHit{
				index:           index,
				retrieverType:   result.RetrieverType,
				retrieverEngine: string(result.RetrieverEngineType),
			}
		}
	}
	if len(bestHits) == 0 {
		return []*types.ChunkSearchResult{}, nil
	}

	hits := make([]*chunkSearchHit, 0, len(bestHits))
	chunkIDs := make([]string, 0, len(bestHits))
	for _, hit := range bestHits {
		hits = append(hits, hit)
		chunkIDs = append(chunkIDs, hit.index.ChunkID)
	}
	sort.SliceStable(hits, func(i, j int) bool {
		return hits[i].index.Score > hits[j].index.Score
	})
	if len(hits) > topK {
		hits = hits[:topK]
		chunkIDs = chunkIDs[:0]
		for _, hit := range hits {
			chunkIDs = append(chunkIDs, hit.index.ChunkID)
		}
	}

	chunks, err := s.chunkRepository.ListChunksByID(ctx, tenantID, chunkIDs)
	if err != nil {
		return nil, err
	}
	chunkByID := make(map[string]*types.Chunk, len(chunks))
	for _, chunk := range chunks {
		chunkByID[chunk.ID] = chunk
	}

	results := make([]*types.ChunkSearchResult, 0, len(hits))
	for _, hit := range hits {
		chunk := chunkByID[hit.index.ChunkID]
		if chunk == nil {
			continue
		}
		results = append(results, &types.ChunkSearchResult{
			ID:                 chunk.ID,
			Content:            chunk.Content,
			KnowledgeID:        chunk.KnowledgeID,
			KnowledgeBaseID:    chunk.KnowledgeBaseID,
			ChunkIndex:         chunk.ChunkIndex,
			ChunkType:          chunk.ChunkType,
			ParentChunkID:      chunk.ParentChunkID,
			ImageInfo:          chunk.ImageInfo,
			IsEnabled:          chunk.IsEnabled,
			Score:              hit.index.Score,
			MatchType:          hit.index.MatchType,
			RetrieverType:      hit.retrieverType,
			RetrieverEngine:    hit.retrieverEngine,
			MatchedContent:     hit.index.Content,
			SourceID:           hit.index.SourceID,
			ChunkMetadata:      chunk.Metadata,
			ExcludeSelfApplied: !includeSelf,
		})
	}
	return results, nil
}
