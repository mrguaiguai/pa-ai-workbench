const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || DEFAULT_API_BASE_URL;
const NATIVE_CHUNK_CONFIRM_PHRASE = "CONFIRM_NATIVE_CHUNK_MUTATION";
export const NATIVE_KB_CONFIRM_PHRASE = "CONFIRM_NATIVE_KB_MUTATION";
const NATIVE_DATA_SOURCE_SYNC_PHRASE = "SYNC_NATIVE_DATA_SOURCE";
const NATIVE_DATA_SOURCE_PAUSE_PHRASE = "PAUSE_NATIVE_DATA_SOURCE";
const NATIVE_DATA_SOURCE_RESUME_PHRASE = "RESUME_NATIVE_DATA_SOURCE";
const NATIVE_DATA_SOURCE_DELETE_PHRASE = "DELETE_NATIVE_DATA_SOURCE";

type CapabilityStatus = "supported" | "partial" | "unsupported" | "dev-only" | string;

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export type StatusResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
  knowledge_backend: string;
  mock_mode: boolean;
  weknora: {
    mode: string;
    status: "mock" | "disabled" | "missing_config" | "connected" | "unavailable" | string;
    connected: boolean;
    configured: boolean;
    base_url_configured: boolean;
    service_token_configured: boolean;
    workspace_configured: boolean;
    kb_configured: boolean;
    health_status: string | null;
    message: string | null;
    kb_mapping?: {
      schema_version: string;
      status: "validated" | "configured" | "blocked" | "backlog" | string;
      source: string | null;
      configured: boolean;
      validated: boolean;
      workspace_id: string | null;
      kb_id: string | null;
      selection_source: string | null;
      mapping_name: string | null;
      default_used: boolean | null;
      default_fallback_allowed: boolean;
      mapping_configured: boolean;
      blocked_reason: string | null;
      workspace: Record<string, unknown> | null;
      knowledge_base: Record<string, unknown> | null;
      backlog: string[];
    };
  };
  backend_capabilities: {
    active_backend: string;
    selected_backend: string;
    environment: string;
    strict_fallback_mode: boolean;
    known_backend: boolean;
    release_eligible: boolean;
    capabilities: Record<string, CapabilityStatus>;
    matrix: Record<string, Record<string, CapabilityStatus>>;
    fallback_policy: Record<string, boolean | string>;
    parity_summary: {
      backend: string;
      release_evidence: boolean;
      quality_limit: string;
      data_fact_source: string;
      citation_trace: string;
      wiki: string;
      debug: string;
      status_recovery: string;
      unsupported_capabilities: string[];
      partial_capabilities: string[];
      dev_only_capabilities: string[];
      status_counts: Record<string, number>;
      unsupported_must_fail: boolean;
      fail_closed: boolean;
    };
    feature_flags: {
      schema_version: string;
      backend: string;
      ui: {
        can_upload_documents: boolean;
        can_view_document_chunks: boolean;
        can_retrieve: boolean;
        can_debug_retrieve: boolean;
        can_search_wiki: boolean;
        can_read_wiki: boolean;
        can_create_update_publish_wiki: boolean;
        can_recover_status: boolean;
        can_use_real_citations: boolean;
        can_count_release_evidence: boolean;
      };
      agent: {
        can_retrieve: boolean;
        can_read_wiki: boolean;
        can_publish_wiki: boolean;
        can_use_real_citations: boolean;
        must_not_call: string[];
        requires_citation_trace_for_real_citation: boolean;
      };
      rules: Record<string, boolean | string>;
      probes: Record<
        string,
        {
          status: CapabilityStatus;
          available: boolean;
          release_evidence: boolean;
          ui_policy: string;
          agent_policy: string;
        }
      >;
    };
    kb_mapping?: {
      schema_version: string;
      configured: boolean;
      mapping_count: number;
      selector_keys: string[];
      default_workspace_configured: boolean;
      default_kb_configured: boolean;
      default_fallback_allowed: boolean;
      ids_redacted: boolean;
    };
    weknora_first_status_gates?: {
      schema_version: string;
      status_categories: {
        live: string[];
        mock: string[];
        fallback: string[];
        partial: string[];
        blocked: string[];
        backlog: string[];
      };
      report_gate_requirements: string[];
      unsafe_pass_evidence: Record<string, boolean>;
    };
    notes: string[];
  };
  memory_recent_limit: number;
  database: string;
  counts: Record<string, number>;
};

export type BackendCapabilitiesResponse = StatusResponse["backend_capabilities"];

export type NativeWikiOverviewResponse = {
  schema_version: string;
  status: "live" | "partial" | "blocked" | string;
  source: string;
  kb_id: string | null;
  query: string;
  limit: number;
  warnings: string[];
  surfaces: Record<
    string,
    {
      status: "live" | "partial" | "blocked" | "backlog" | string;
      reason?: string;
      [key: string]: unknown;
    }
  >;
};

export type NativeWikiPageSummary = {
  id?: string | null;
  slug: string;
  title: string;
  page_type?: string | null;
  summary?: string | null;
  status?: string | null;
  source_type?: string | null;
  evidence_id?: string | null;
  wiki_page_id?: string | null;
};

export type NativeWikiPageRead = NativeWikiPageSummary & {
  source?: string | null;
  kb_id?: string | null;
  content_chars?: number;
  content_excerpt?: string;
};

export type NativeWikiPagesResponse = {
  pages?: NativeWikiPageSummary[];
  items?: NativeWikiPageSummary[];
  total?: number | null;
  page?: number | null;
  page_size?: number | null;
  total_pages?: number | null;
  source: string;
  kb_id: string;
};

export type NativeWikiMutationResponse = {
  status?: string;
  mutation?: string;
  slug?: string;
  kb_id?: string;
  source?: string;
  confirmation_required?: boolean;
  [key: string]: unknown;
};

export type NativeWikiPageSaveRequest = {
  confirm_token: string;
  slug?: string;
  title: string;
  summary?: string | null;
  content_markdown?: string;
  page_type?: string | null;
  status?: string;
  aliases?: string[];
  source_refs?: string[];
  chunk_refs?: string[];
  metadata?: Record<string, unknown>;
};

export type NativeMcpOverviewResponse = {
  schema_version: string;
  status: "live" | "partial" | "blocked" | "backlog" | string;
  source: string;
  warnings: string[];
  surfaces: Record<
    string,
    {
      status: "live" | "partial" | "blocked" | "backlog" | string;
      reason?: string;
      count?: number;
      [key: string]: unknown;
    }
  >;
};

export type NativeMcpExecutionResponse = {
  schema_version: string;
  status: "live" | "partial" | "blocked" | "backlog" | string;
  source: string;
  warnings: string[];
  surfaces: Record<string, Record<string, unknown>>;
  audit?: NativeMutationAudit;
  confirmation?: {
    required: boolean;
    method?: string | null;
    token_id?: string | null;
  };
};

export type NativeMcpPromptReadResponse = {
  schema_version: string;
  status: "live" | "partial" | "blocked" | "backlog" | string;
  source: string;
  warnings: string[];
  surfaces: Record<string, Record<string, unknown>>;
};

export type NativeWebSearchOverviewResponse = {
  schema_version: string;
  status: "live" | "partial" | "blocked" | "backlog" | string;
  source: string;
  warnings: string[];
  surfaces: Record<
    string,
    {
      status: "live" | "partial" | "blocked" | "backlog" | "optional" | string;
      reason?: string;
      count?: number;
      [key: string]: unknown;
    }
  >;
};

export type NativeWebSearchProviderMutationResponse = NativeWebSearchOverviewResponse & {
  audit?: NativeMutationAudit;
  confirmation?: {
    required: boolean;
    method?: string | null;
    token_id?: string | null;
  };
};

export type NativeWebSearchProviderCreatePayload = {
  name: string;
  provider: string;
  description?: string | null;
  parameters?: Record<string, unknown>;
  is_default?: boolean;
  confirm_token: string;
};

export type NativeWebSearchProviderUpdatePayload = {
  name?: string | null;
  description?: string | null;
  parameters?: Record<string, unknown>;
  is_default?: boolean | null;
  confirm_token: string;
};

export type NativeWebSearchRawTestPayload = {
  provider: string;
  parameters?: Record<string, unknown>;
  confirm_token: string;
};

export type NativeVectorStoreOverviewResponse = {
  schema_version: string;
  status: "live" | "partial" | "blocked" | "backlog" | string;
  source: string;
  warnings: string[];
  surfaces: Record<
    string,
    {
      status: "live" | "partial" | "blocked" | "backlog" | string;
      reason?: string;
      count?: number;
      [key: string]: unknown;
    }
  >;
};

export type NativeDataSourceOverviewResponse = {
  schema_version: string;
  status: "live" | "partial" | "blocked" | "backlog" | string;
  source: string;
  warnings: string[];
  surfaces: Record<
    string,
    {
      status: "live" | "partial" | "blocked" | "backlog" | string;
      reason?: string;
      count?: number;
      [key: string]: unknown;
    }
  >;
};

export type NativeDataSourceActionResponse = NativeDataSourceOverviewResponse & {
  audit?: NativeMutationAudit;
  confirmation?: {
    required: boolean;
    method?: string | null;
    token_id?: string | null;
  };
};

export type NativeOrganizationOverviewResponse = {
  schema_version: string;
  status: "live" | "partial" | "blocked" | "backlog" | string;
  source: string;
  warnings: string[];
  surfaces: Record<
    string,
    {
      status: "live" | "partial" | "blocked" | "backlog" | string;
      reason?: string;
      count?: number;
      [key: string]: unknown;
    }
  >;
};

export type NativeStatusValue = "live" | "partial" | "blocked" | "backlog" | string;

export type NativeCapabilityGroup = {
  id: string;
  label: string;
  status: NativeStatusValue;
  configured: boolean;
  masked: boolean;
  source_endpoint: string;
  native_endpoint: string | null;
  next_action: string;
  summary: Record<string, unknown>;
};

export type NativeStatusCenterResponse = {
  schema_version: string;
  source: string;
  status: NativeStatusValue;
  evidence_type: string;
  configured: boolean;
  masked: boolean;
  config: Record<string, unknown>;
  groups: Record<string, NativeCapabilityGroup>;
  group_count: number;
  warnings: string[];
  next_action: string;
};

export type NativeStatusCenterParams = {
  limit?: number;
};

export type NativeKnowledgeBaseItem = {
  id: string | null;
  name: string | null;
  description: string | null;
  type: string | null;
  is_temporary: boolean;
  knowledge_count: number | null;
  chunk_count: number | null;
  processing_count: number | null;
  share_count: number | null;
  is_processing: boolean;
  is_pinned: boolean;
  creator_name: string | null;
  my_permission: string | null;
  vector_store: Record<string, unknown> | null;
  source: string;
};

export type NativeKnowledgeBaseSelection = {
  workspace_id: string | null;
  kb_id: string | null;
  name: string | null;
  type: string | null;
  selection_source: string | null;
  mapping_name: string | null;
  default_used: boolean;
  validated: boolean;
  snapshot_saved: boolean;
  source: string;
  vector_store: Record<string, unknown> | null;
  created_at?: string | null;
};

export type NativeKnowledgeBaseOverviewResponse = {
  schema_version: string;
  source: string;
  status: NativeStatusValue;
  evidence_type: string;
  masked: boolean;
  workspace_id_configured: boolean;
  default_kb_configured: boolean;
  active_selection: NativeKnowledgeBaseSelection | null;
  items: NativeKnowledgeBaseItem[];
  total: number;
  surfaces: Record<string, Record<string, unknown>>;
  warnings: string[];
  next_action: string;
};

export type ActiveKnowledgeBaseSelectionResponse = {
  schema_version: string;
  status: NativeStatusValue;
  evidence_type: string;
  source: string;
  active_selection: NativeKnowledgeBaseSelection;
  tags: Array<Record<string, unknown>>;
  mutation_backlog: string[];
  mutation_status?: Record<string, unknown>;
};

export type NativeKnowledgeBaseMutationResponse = {
  schema_version: string;
  source: string;
  status: NativeStatusValue;
  masked: boolean;
  surfaces: Record<string, Record<string, unknown>>;
  warnings: string[];
  audit?: Record<string, unknown>;
  confirmation?: Record<string, unknown>;
};

export type NativeKnowledgeBaseMutationPayload = {
  name?: string;
  description?: string;
  type?: string;
  is_temporary?: boolean;
  confirm_token?: string;
};

export type ModelProviderStatus = {
  provider: string;
  model: string;
  configured: boolean;
  mock: boolean;
  base_url_configured: boolean;
  api_key_configured: boolean;
  timeout_seconds: number;
  temperature: number | null;
  dimension: number | null;
};

export type ModelStatusResponse = {
  chat_provider: string;
  embedding_provider: string;
  mock_mode: boolean;
  configured: boolean;
  chat: ModelProviderStatus;
  embedding: ModelProviderStatus;
};

export type Document = {
  id: string;
  title: string;
  business_area: string | null;
  document_type: string | null;
  source: string | null;
  keywords_json: string | null;
  file_name: string | null;
  file_path: string | null;
  file_size: number | null;
  mime_type: string | null;
  knowledge_backend: string;
  knowledge_base_id: string | null;
  external_doc_id: string | null;
  summary: string | null;
  status: string;
  error_message: string | null;
  failed_step: string | null;
  chunk_count: number;
  indexed_chunk_count: number;
  pending_chunk_count: number;
  failed_chunk_count: number;
  embedding_status: string | null;
  processing_state: string;
  processing_message: string | null;
  next_action: string | null;
  retryable: boolean;
  processing_seconds: number;
  processing_timed_out: boolean;
  created_at: string;
  updated_at: string;
};

export type DocumentUploadRequest = {
  file: File;
  title?: string;
  business_area?: string;
  document_type?: string;
  source?: string;
  keywords_json?: string;
  knowledge_base_id?: string;
};

export type DocumentUrlCreateRequest = {
  url: string;
  title?: string;
  business_area?: string;
  document_type?: string;
  source?: string;
  keywords_json?: string;
  knowledge_base_id?: string;
};

export type DocumentManualCreateRequest = {
  title: string;
  content: string;
  business_area?: string;
  document_type?: string;
  source?: string;
  keywords_json?: string;
  knowledge_base_id?: string;
};

export type DocumentUploadResponse = {
  document: Document;
};

export type DocumentRetryIndexResponse = {
  document: Document;
  message: string;
};

export type DocumentLifecycleActionResponse = {
  document: Document;
  action: string;
  message: string;
  evidence_type: string;
  source: string;
};

export type DocumentListFilters = {
  status?: string;
  processing_state?: string;
  has_error?: boolean;
  knowledge_backend?: string;
  knowledge_base_id?: string;
  refresh_status?: boolean;
};

export type NativeWikiOverviewParams = {
  kb_id?: string;
  query?: string;
  limit?: number;
};

export type NativeMcpOverviewParams = {
  limit?: number;
};

export type NativeWebSearchOverviewParams = {
  limit?: number;
};

export type NativeVectorStoreOverviewParams = {
  limit?: number;
};

export type NativeDataSourceOverviewParams = {
  limit?: number;
};

export type NativeOrganizationOverviewParams = {
  limit?: number;
};

export type HistoryListFilters = {
  query?: string;
  task_type?: string;
  status?: string;
  citation_source?: string;
  source_type?: string;
  evidence_state?: string;
  wnid_capability?: string;
  wnid_evidence_state?: string;
  has_warnings?: boolean;
};

export type DocumentBulkRefreshResponse = {
  items: Document[];
  total: number;
  refreshed: number;
};

export type DocumentChunk = {
  id: string;
  document_id: string;
  external_doc_id: string | null;
  chunk_index: number;
  title: string | null;
  content: string;
  content_hash: string;
  token_count: number;
  char_count: number;
  start_char: number | null;
  end_char: number | null;
  page_number: number | null;
  section_path: string | null;
  paragraph_start_index: number | null;
  paragraph_end_index: number | null;
  business_area: string | null;
  document_type: string | null;
  source: string;
  metadata_json: string | null;
  embedding_status: string;
  vector_id: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentChunkListResponse = {
  items: DocumentChunk[];
  total: number;
};

export type DocumentChunkSimilarResult = {
  id: string;
  external_doc_id: string | null;
  knowledge_base_id: string | null;
  chunk_index: number;
  content: string;
  score: number;
  match_type: number | string | null;
  retriever_type: string | null;
  retriever_engine: string | null;
  matched_content: string | null;
  source_id: string | null;
};

export type DocumentChunkSimilarResponse = {
  items: DocumentChunkSimilarResult[];
  total: number;
  evidence_type: string;
  source: string;
};

export type NativeConfirmation = {
  required: boolean;
  method: string | null;
  token_id: string | null;
};

export type NativeMutationAudit = {
  id: string;
  capability: string;
  operation: string;
  target_type: string;
  target_id: string | null;
  source: string;
  status: string;
  confirmation_required: boolean;
  confirmation_method: string | null;
  confirm_token_id: string | null;
  reason: string | null;
  request_summary_json: string | null;
  response_summary_json: string | null;
  error_message: string | null;
  wnid_capability: string | null;
  wnid_evidence_state: string;
  created_at: string;
};

export type NativeMutationAuditListResponse = {
  items: NativeMutationAudit[];
  total: number;
};

export type DocumentChunkActionResponse = {
  document: Document;
  chunk: DocumentChunk | null;
  action: string;
  message: string;
  evidence_type: string;
  source: string;
  audit_step: string;
  audit: NativeMutationAudit | null;
  confirmation: NativeConfirmation | null;
};

export type DocumentProcessingEvent = {
  id: string;
  document_id: string;
  external_doc_id: string | null;
  step: string;
  status: string;
  message: string | null;
  metadata_json: string | null;
  error_message: string | null;
  created_at: string;
};

export type DocumentSpansResponse = {
  source: string;
  external_doc_id: string | null;
  parse_status: string | null;
  current_attempt: number | null;
  current_stage: string | null;
  trace: Record<string, unknown>;
  last_error: Record<string, unknown> | null;
};

export type DocumentIndexResponse = {
  document: Document;
  chunk_count: number;
  message: string;
};

export type AnalysisTaskType = "knowledge_qa" | "policy_analysis" | "case_review";
export type RetrievalScope = "all" | "document" | "wiki";
export type NativeAnswerMode = "qa" | "policy_analysis" | "case_review";

export type Conversation = {
  id: string;
  title: string;
  summary: string | null;
  default_task_type: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system_status";
  content: string;
  metadata_json: string | null;
  created_at: string;
};

export type Citation = {
  id: string;
  task_id: string | null;
  output_id: string | null;
  document_id: string | null;
  external_doc_id: string | null;
  chunk_id: string | null;
  title: string;
  text: string;
  score: number | null;
  source: string;
  evidence_id: string | null;
  source_type: "document_chunk" | "wiki_page" | string | null;
  wiki_page_id: string | null;
  metadata_json: string | null;
  created_at: string;
};

export type CitationLocateRequest = {
  id?: string | null;
  document_id?: string | null;
  external_doc_id?: string | null;
  chunk_id?: string | null;
  evidence_id?: string | null;
  source_type?: string | null;
  wiki_page_id?: string | null;
  source?: string | null;
  metadata_json?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type CitationLocateResponse = {
  located: boolean;
  target_type: "document_chunk" | "wiki_page" | string | null;
  route: string | null;
  ui_hash: string | null;
  message: string;
  document_id: string | null;
  external_doc_id: string | null;
  chunk_id: string | null;
  chunk_index: number | null;
  wiki_page_id: string | null;
  wiki_slug: string | null;
};

export type Evidence = {
  evidence_id?: string | null;
  source_type?: "document_chunk" | "wiki_page" | string | null;
  document_id: string | null;
  external_doc_id: string | null;
  chunk_id: string | null;
  wiki_page_id?: string | null;
  title: string;
  text: string;
  score: number | null;
  source: string;
  metadata: Record<string, unknown>;
};

export type RagDebugRequest = {
  query: string;
  filters?: Record<string, unknown>;
  top_k?: number;
};

export type RagDebugEvidence = {
  rank: number;
  source_type: "document_chunk" | "wiki_page" | string | null;
  source: string;
  score: number | null;
  evidence_id: string | null;
  document_id: string | null;
  external_doc_id: string | null;
  chunk_id: string | null;
  wiki_page_id: string | null;
  title: string;
  summary: string;
  metadata: Record<string, unknown>;
};

export type RagDebugResponse = {
  trace_id: string;
  status: "ok" | "error" | string;
  query: string;
  filters: Record<string, unknown>;
  top_k: number;
  requested_source_type: string | null;
  retrieval_options: Record<string, unknown>;
  debug_trace: Array<Record<string, unknown>>;
  items: RagDebugEvidence[];
  total: number;
  warnings: string[];
  error: {
    error_code: string;
    message: string;
    operation: string | null;
    retryable: boolean;
  } | null;
};

export type NativeKnowledgeChatRequest = {
  query: string;
  conversation_id?: string | null;
  title?: string | null;
  knowledge_base_ids?: string[];
  knowledge_ids?: string[];
  web_search_enabled?: boolean;
  answer_mode?: NativeAnswerMode;
  current_run?: Record<string, unknown>;
};

export type NativeKnowledgeChatRuntime = {
  native_session_id: string | null;
  answer_mode: NativeAnswerMode;
  event_counts: Record<string, unknown>;
  reference_count: number;
  reference_event_source: string;
  saved_citation_count: number;
  warnings: string[];
  assistant_message_id: string | null;
  user_message_id: string | null;
  current_run_guard: Record<string, unknown>;
  evidence_type: string;
  source: string;
};

export type NativeKnowledgeChatResponse = {
  conversation: Conversation;
  messages: ConversationMessage[];
  task: Task;
  output: GeneratedOutput;
  citations: Citation[];
  runtime: NativeKnowledgeChatRuntime;
};

export type Task = {
  id: string;
  conversation_id: string | null;
  task_type: string;
  title: string | null;
  input_json: string | null;
  status: string;
  current_step: string | null;
  progress: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type GeneratedOutput = {
  id: string;
  task_id: string;
  conversation_id: string | null;
  task_type: string;
  title: string;
  content_json: string | null;
  content_markdown: string | null;
  warnings_json: string | null;
  status: string;
  citation_count: number;
  weknora_citation_count: number;
  mock_citation_count: number;
  document_citation_count: number;
  wiki_citation_count: number;
  web_search_citation_count: number;
  traceable_citation_count: number;
  warning_count: number;
  evidence_state: string;
  wnid_capability: string | null;
  wnid_capabilities: string[];
  wnid_evidence_state: string;
  evidence_source_types: string[];
  citation_blocked: boolean;
  citation_blocker: string | null;
  created_at: string;
  updated_at: string;
};

export type AnalysisRunRequest = {
  conversation_id?: string | null;
  task_type: AnalysisTaskType;
  title?: string | null;
  query_or_topic: string;
  business_area?: string | null;
  document_type?: string | null;
  document_ids?: string[];
  extra_requirements?: string | null;
  retrieval_scope?: RetrievalScope;
  current_run?: Record<string, unknown>;
  expected_source_types?: Array<"document_chunk" | "wiki_page">;
  should_answer_insufficient?: boolean;
  forbidden_anchors?: string[];
  question_type?: string | null;
};

export type AnalysisRunResponse = {
  conversation: Conversation;
  messages: ConversationMessage[];
  task: Task;
  output: GeneratedOutput;
  citations: Citation[];
};

export type NativeAgentItem = {
  id: string | null;
  name: string;
  description: string | null;
  avatar: string | null;
  is_builtin: boolean;
  creator_name: string | null;
  runnable_by_viewer: boolean;
  agent_mode: string;
  agent_type: string | null;
  allowed_tools: string[];
  knowledge_base_count: number;
  model_configured: boolean;
  rerank_configured: boolean;
  web_search_enabled: boolean;
  suggested_prompt_count: number;
  strategy: NativeAgentStrategy;
};

export type NativeAgentStrategy = {
  system_prompt: string;
  context_template: string;
  allowed_tools: string[];
  mcp_selection_mode: string;
  mcp_services: string[];
  web_search_enabled: boolean;
  web_search_provider_id: string;
  web_fetch_enabled: boolean;
  web_fetch_top_n: number;
  multi_turn_enabled: boolean;
  history_turns: number;
  embedding_top_k: number;
  keyword_threshold: number;
  vector_threshold: number;
  rerank_top_k: number;
  rerank_threshold: number;
  suggested_prompts: string[];
};

export type NativeAgentCatalogResponse = {
  schema_version: string;
  source: string;
  status: string;
  agents: NativeAgentItem[];
  presets: Array<{
    agent_type: string | null;
    name: string | null;
    description: string | null;
    allowed_tools: string[];
  }>;
  placeholder_groups: Record<string, number>;
  suggested_questions: Array<{
    question: string | null;
    source: string | null;
    knowledge_base_id: string | null;
  }>;
  selected_agent_id: string | null;
  active_knowledge_base_id: string | null;
  surfaces: Record<string, string>;
  warnings: string[];
};

export type NativeAgentSuggestedQuestion = {
  question: string | null;
  source: string | null;
  knowledge_base_id: string | null;
};

export type NativeAgentSuggestedQuestionsResponse = {
  schema_version: string;
  source: string;
  status: string;
  agent_id: string | null;
  knowledge_base_ids: string[];
  knowledge_ids: string[];
  questions: NativeAgentSuggestedQuestion[];
  source_counts: Record<string, number>;
  surfaces: Record<string, string>;
  warnings: string[];
};

export type NativeAgentQaRequest = {
  query: string;
  agent_id?: string | null;
  conversation_id?: string | null;
  title?: string | null;
  knowledge_base_ids?: string[];
  knowledge_ids?: string[];
  web_search_enabled?: boolean;
  answer_mode?: NativeAnswerMode;
  confirm_token?: string | null;
};

export type NativeAgentMutationRequest = {
  name?: string | null;
  description?: string | null;
  avatar?: string | null;
  config?: Record<string, unknown>;
  confirm_token?: string | null;
};

export type NativeAgentStrategyUpdateRequest = Partial<NativeAgentStrategy> & {
  confirm_token?: string | null;
};

export type NativeAgentMutationResponse = {
  schema_version: string;
  source: string;
  status: string;
  masked: boolean;
  surfaces: Record<string, unknown>;
  warnings: string[];
  audit?: NativeMutationAudit;
  confirmation?: {
    required: boolean;
    method?: string | null;
    token_id?: string | null;
  };
};

export type NativeAgentQaRuntime = {
  native_session_id: string | null;
  answer_mode: NativeAnswerMode;
  native_session_reused: boolean;
  native_session_source: string;
  agent_id: string | null;
  agent_name: string | null;
  event_counts: Record<string, unknown>;
  event_sequence: string[];
  run_contract: Record<string, unknown>;
  selected_agent: Record<string, unknown>;
  conversation_continuity: Record<string, unknown>;
  tool_names: string[];
  reference_count: number;
  reference_event_source: string;
  web_reference_count: number;
  web_providers: string[];
  wiki_reference_count: number;
  wiki_slugs: string[];
  wiki_mode_mutation_required: boolean;
  wiki_mode_audit?: Record<string, unknown> | null;
  saved_citation_count: number;
  citation_blocked: boolean;
  warnings: string[];
  assistant_message_id: string | null;
  user_message_id: string | null;
  evidence_type: string;
  source: string;
};

export type NativeAgentQaResponse = {
  conversation: Conversation;
  messages: ConversationMessage[];
  task: Task;
  output: GeneratedOutput;
  citations: Citation[];
  runtime: NativeAgentQaRuntime;
};

export type WikiPageSummary = {
  id?: string | null;
  slug: string;
  title: string;
  page_type: string | null;
  summary: string | null;
  status?: string | null;
  tags?: string[];
  source: string;
  metadata: Record<string, unknown>;
};

export type WikiPage = {
  id?: string | null;
  slug: string;
  title: string;
  page_type: string | null;
  summary: string | null;
  content: string;
  content_markdown?: string | null;
  status?: string | null;
  tags?: string[];
  business_area?: string | null;
  source_output_id?: string | null;
  source_document_ids?: string[];
  source_citation_ids?: string[];
  citations: Evidence[];
  wiki_citations?: WikiCitation[];
  source: string;
  metadata: Record<string, unknown>;
  created_by?: string | null;
  published_at?: string | null;
  embedding_status?: string | null;
  vector_id?: string | null;
  indexed_at?: string | null;
  wiki_state: string;
  wiki_message: string | null;
  wiki_next_action: string | null;
  wiki_retryable: boolean;
  wiki_retrievable: boolean;
  wiki_index_timed_out: boolean;
  wiki_processing_seconds: number;
  created_at?: string | null;
  updated_at?: string | null;
};

export type WikiCitation = {
  id: string;
  wiki_page_id: string;
  document_id: string | null;
  external_doc_id: string | null;
  chunk_id: string | null;
  output_id: string | null;
  citation_id: string | null;
  evidence_id: string | null;
  source_type: string;
  excerpt: string;
  score: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type WikiDraftFromOutputRequest = {
  slug?: string | null;
  title?: string | null;
  summary?: string | null;
  tags?: string[] | null;
  business_area?: string | null;
  page_type?: string | null;
  created_by?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type WikiPageCreateRequest = {
  slug: string;
  title: string;
  summary?: string | null;
  content_markdown?: string;
  tags?: string[];
  business_area?: string | null;
  page_type?: string | null;
  created_by?: string | null;
  metadata?: Record<string, unknown>;
};

export type WikiPageUpdateRequest = {
  title?: string | null;
  summary?: string | null;
  content_markdown?: string | null;
  tags?: string[] | null;
  business_area?: string | null;
  page_type?: string | null;
  created_by?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type WikiSearchResponse = {
  items: WikiPageSummary[];
  total: number;
};

export type ListResponse<T> = {
  items: T[];
  total: number;
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isFormData = init.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: isFormData
      ? init.headers
      : {
          "Content-Type": "application/json",
          ...init.headers,
        },
    ...init,
  });

  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new ApiError(`API request failed: ${response.status}`, response.status, body);
  }

  return body as T;
}

function documentFilterParams(filters: DocumentListFilters) {
  const params = new URLSearchParams();
  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  if (filters.processing_state && filters.processing_state !== "all") {
    params.set("processing_state", filters.processing_state);
  }
  if (filters.has_error !== undefined) {
    params.set("has_error", String(filters.has_error));
  }
  if (filters.knowledge_backend && filters.knowledge_backend !== "all") {
    params.set("knowledge_backend", filters.knowledge_backend);
  }
  if (filters.knowledge_base_id && filters.knowledge_base_id !== "all") {
    params.set("knowledge_base_id", filters.knowledge_base_id);
  }
  if (filters.refresh_status !== undefined) {
    params.set("refresh_status", String(filters.refresh_status));
  }
  return params;
}

function historyFilterParams(filters: HistoryListFilters) {
  const params = new URLSearchParams();
  if (filters.query?.trim()) {
    params.set("query", filters.query.trim());
  }
  if (filters.task_type && filters.task_type !== "all") {
    params.set("task_type", filters.task_type);
  }
  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  if (filters.citation_source && filters.citation_source !== "all") {
    params.set("citation_source", filters.citation_source);
  }
  if (filters.source_type && filters.source_type !== "all") {
    params.set("source_type", filters.source_type);
  }
  if (filters.evidence_state && filters.evidence_state !== "all") {
    params.set("evidence_state", filters.evidence_state);
  }
  if (filters.wnid_capability && filters.wnid_capability !== "all") {
    params.set("wnid_capability", filters.wnid_capability);
  }
  if (filters.wnid_evidence_state && filters.wnid_evidence_state !== "all") {
    params.set("wnid_evidence_state", filters.wnid_evidence_state);
  }
  if (filters.has_warnings !== undefined) {
    params.set("has_warnings", String(filters.has_warnings));
  }
  return params;
}

function nativeWikiOverviewParams(params: NativeWikiOverviewParams = {}) {
  const searchParams = new URLSearchParams();
  if (params.kb_id) {
    searchParams.set("kb_id", params.kb_id);
  }
  if (params.query) {
    searchParams.set("query", params.query);
  }
  if (params.limit) {
    searchParams.set("limit", String(params.limit));
  }
  return searchParams;
}

function nativeMcpOverviewParams(params: NativeMcpOverviewParams = {}) {
  const searchParams = new URLSearchParams();
  if (params.limit) {
    searchParams.set("limit", String(params.limit));
  }
  return searchParams;
}

function nativeWebSearchOverviewParams(params: NativeWebSearchOverviewParams = {}) {
  const searchParams = new URLSearchParams();
  if (params.limit) {
    searchParams.set("limit", String(params.limit));
  }
  return searchParams;
}

function nativeVectorStoreOverviewParams(params: NativeVectorStoreOverviewParams = {}) {
  const searchParams = new URLSearchParams();
  if (params.limit) {
    searchParams.set("limit", String(params.limit));
  }
  return searchParams;
}

function nativeDataSourceOverviewParams(params: NativeDataSourceOverviewParams = {}) {
  const searchParams = new URLSearchParams();
  if (params.limit) {
    searchParams.set("limit", String(params.limit));
  }
  return searchParams;
}

function nativeOrganizationOverviewParams(params: NativeOrganizationOverviewParams = {}) {
  const searchParams = new URLSearchParams();
  if (params.limit) {
    searchParams.set("limit", String(params.limit));
  }
  return searchParams;
}

function nativeStatusCenterParams(params: NativeStatusCenterParams = {}) {
  const searchParams = new URLSearchParams();
  if (params.limit) {
    searchParams.set("limit", String(params.limit));
  }
  return searchParams;
}

export const apiClient = {
  baseUrl: API_BASE_URL,
  getStatus: () => request<StatusResponse>("/api/status"),
  getCapabilities: () => request<BackendCapabilitiesResponse>("/api/capabilities"),
  getModelStatus: () => request<ModelStatusResponse>("/api/model/status"),
  getNativeWikiOverview: (params: NativeWikiOverviewParams = {}) => {
    const searchParams = nativeWikiOverviewParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeWikiOverviewResponse>(`/api/wiki/native/overview${suffix}`);
  },
  listNativeWikiPages: (params: NativeWikiOverviewParams & { pageSize?: number } = {}) => {
    const searchParams = nativeWikiOverviewParams(params);
    if (params.pageSize) {
      searchParams.set("page_size", String(params.pageSize));
    }
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeWikiPagesResponse>(`/api/wiki/native/pages${suffix}`);
  },
  searchNativeWikiPages: (query: string, kbId?: string, limit = 10) => {
    const searchParams = new URLSearchParams({ query, limit: String(limit) });
    if (kbId) {
      searchParams.set("kb_id", kbId);
    }
    return request<NativeWikiPagesResponse>(`/api/wiki/native/search?${searchParams.toString()}`);
  },
  getNativeWikiPage: (slug: string, kbId?: string) => {
    const searchParams = new URLSearchParams({ slug });
    if (kbId) {
      searchParams.set("kb_id", kbId);
    }
    return request<NativeWikiPageRead>(`/api/wiki/native/page?${searchParams.toString()}`);
  },
  createNativeWikiPage: (payload: NativeWikiPageSaveRequest, kbId?: string) => {
    const suffix = kbId ? `?${new URLSearchParams({ kb_id: kbId }).toString()}` : "";
    return request<NativeWikiPageRead>(`/api/wiki/native/pages${suffix}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  updateNativeWikiPage: (slug: string, payload: NativeWikiPageSaveRequest, kbId?: string) => {
    const searchParams = new URLSearchParams({ slug });
    if (kbId) {
      searchParams.set("kb_id", kbId);
    }
    return request<NativeWikiPageRead>(`/api/wiki/native/page?${searchParams.toString()}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  deleteNativeWikiPage: (slug: string, confirmToken: string, kbId?: string) => {
    const suffix = kbId ? `?${new URLSearchParams({ kb_id: kbId }).toString()}` : "";
    return request<NativeWikiMutationResponse>(`/api/wiki/native/page/delete${suffix}`, {
      method: "POST",
      body: JSON.stringify({ slug, confirm_token: confirmToken }),
    });
  },
  getNativeWikiIndex: (params: NativeWikiOverviewParams = {}) => {
    const searchParams = nativeWikiOverviewParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<Record<string, unknown>>(`/api/wiki/native/index${suffix}`);
  },
  getNativeWikiLog: (params: NativeWikiOverviewParams = {}) => {
    const searchParams = nativeWikiOverviewParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<Record<string, unknown>>(`/api/wiki/native/log${suffix}`);
  },
  getNativeWikiGraph: (params: NativeWikiOverviewParams = {}) => {
    const searchParams = nativeWikiOverviewParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<Record<string, unknown>>(`/api/wiki/native/graph${suffix}`);
  },
  getNativeWikiStats: (kbId?: string) => {
    const suffix = kbId ? `?${new URLSearchParams({ kb_id: kbId }).toString()}` : "";
    return request<Record<string, unknown>>(`/api/wiki/native/stats${suffix}`);
  },
  getNativeWikiLint: (kbId?: string) => {
    const suffix = kbId ? `?${new URLSearchParams({ kb_id: kbId }).toString()}` : "";
    return request<Record<string, unknown>>(`/api/wiki/native/lint${suffix}`);
  },
  getNativeWikiIssues: (kbId?: string) => {
    const suffix = kbId ? `?${new URLSearchParams({ kb_id: kbId }).toString()}` : "";
    return request<Record<string, unknown>>(`/api/wiki/native/issues${suffix}`);
  },
  rebuildNativeWikiLinks: (confirmToken: string, kbId?: string) => {
    const suffix = kbId ? `?${new URLSearchParams({ kb_id: kbId }).toString()}` : "";
    return request<NativeWikiMutationResponse>(`/api/wiki/native/rebuild-links${suffix}`, {
      method: "POST",
      body: JSON.stringify({ confirm_token: confirmToken }),
    });
  },
  autoFixNativeWiki: (confirmToken: string, kbId?: string) => {
    const suffix = kbId ? `?${new URLSearchParams({ kb_id: kbId }).toString()}` : "";
    return request<NativeWikiMutationResponse>(`/api/wiki/native/auto-fix${suffix}`, {
      method: "POST",
      body: JSON.stringify({ confirm_token: confirmToken }),
    });
  },
  getNativeMcpOverview: (params: NativeMcpOverviewParams = {}) => {
    const searchParams = nativeMcpOverviewParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeMcpOverviewResponse>(`/api/mcp/native/overview${suffix}`);
  },
  setNativeMcpToolApproval: (
    serviceId: string,
    toolName: string,
    requireApproval: boolean,
    confirmToken: string,
  ) =>
    request<NativeMcpExecutionResponse>(
      `/api/mcp/native/services/${encodeURIComponent(serviceId)}/tool-approvals/${encodeURIComponent(toolName)}`,
      {
        method: "PUT",
        body: JSON.stringify({
          require_approval: requireApproval,
          confirm_token: confirmToken,
        }),
      },
    ),
  executeNativeMcpTool: (
    serviceId: string,
    toolName: string,
    payload: {
      arguments?: Record<string, unknown>;
      approval_decision?: "approve" | "reject" | string;
      conversation_id?: string | null;
      confirm_token: string;
    },
  ) =>
    request<NativeMcpExecutionResponse>(
      `/api/mcp/native/services/${encodeURIComponent(serviceId)}/tools/${encodeURIComponent(toolName)}/execute`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    ),
  readNativeMcpPrompt: (
    serviceId: string,
    promptName: string,
    payload: {
      arguments?: Record<string, unknown>;
      confirm_token: string;
    },
  ) =>
    request<NativeMcpPromptReadResponse>(
      `/api/mcp/native/services/${encodeURIComponent(serviceId)}/prompts/${encodeURIComponent(promptName)}/read`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    ),
  getNativeWebSearchOverview: (params: NativeWebSearchOverviewParams = {}) => {
    const searchParams = nativeWebSearchOverviewParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeWebSearchOverviewResponse>(
      `/api/web-search/native/overview${suffix}`,
    );
  },
  createNativeWebSearchProvider: (payload: NativeWebSearchProviderCreatePayload) =>
    request<NativeWebSearchProviderMutationResponse>("/api/web-search/native/providers", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateNativeWebSearchProvider: (
    providerId: string,
    payload: NativeWebSearchProviderUpdatePayload,
  ) =>
    request<NativeWebSearchProviderMutationResponse>(
      `/api/web-search/native/providers/${encodeURIComponent(providerId)}`,
      {
        method: "PUT",
        body: JSON.stringify(payload),
      },
    ),
  deleteNativeWebSearchProvider: (providerId: string, confirmToken: string) =>
    request<NativeWebSearchProviderMutationResponse>(
      `/api/web-search/native/providers/${encodeURIComponent(providerId)}`,
      {
        method: "DELETE",
        body: JSON.stringify({ confirm_token: confirmToken }),
      },
    ),
  testNativeWebSearchProvider: (providerId: string, confirmToken: string) =>
    request<NativeWebSearchProviderMutationResponse>(
      `/api/web-search/native/providers/${encodeURIComponent(providerId)}/test`,
      {
        method: "POST",
        body: JSON.stringify({ confirm_token: confirmToken }),
      },
    ),
  testNativeWebSearchProviderRaw: (payload: NativeWebSearchRawTestPayload) =>
    request<NativeWebSearchProviderMutationResponse>("/api/web-search/native/providers/test", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getNativeVectorStoreOverview: (params: NativeVectorStoreOverviewParams = {}) => {
    const searchParams = nativeVectorStoreOverviewParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeVectorStoreOverviewResponse>(
      `/api/vector-stores/native/overview${suffix}`,
    );
  },
  getNativeDataSourceOverview: (params: NativeDataSourceOverviewParams = {}) => {
    const searchParams = nativeDataSourceOverviewParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeDataSourceOverviewResponse>(
      `/api/data-sources/native/overview${suffix}`,
    );
  },
  getNativeDataSourceDetail: (dataSourceIndex: number) =>
    request<NativeDataSourceOverviewResponse>(
      `/api/data-sources/native/sources/by-index/${encodeURIComponent(String(dataSourceIndex))}`,
    ),
  syncNativeDataSource: (dataSourceIndex: number) =>
    request<NativeDataSourceActionResponse>(
      `/api/data-sources/native/sources/by-index/${encodeURIComponent(String(dataSourceIndex))}/sync`,
      {
        method: "POST",
        body: JSON.stringify({ confirm_token: NATIVE_DATA_SOURCE_SYNC_PHRASE }),
      },
    ),
  pauseNativeDataSource: (dataSourceIndex: number) =>
    request<NativeDataSourceActionResponse>(
      `/api/data-sources/native/sources/by-index/${encodeURIComponent(String(dataSourceIndex))}/pause`,
      {
        method: "POST",
        body: JSON.stringify({ confirm_token: NATIVE_DATA_SOURCE_PAUSE_PHRASE }),
      },
    ),
  resumeNativeDataSource: (dataSourceIndex: number) =>
    request<NativeDataSourceActionResponse>(
      `/api/data-sources/native/sources/by-index/${encodeURIComponent(String(dataSourceIndex))}/resume`,
      {
        method: "POST",
        body: JSON.stringify({ confirm_token: NATIVE_DATA_SOURCE_RESUME_PHRASE }),
      },
    ),
  deleteNativeDataSource: (dataSourceIndex: number) =>
    request<NativeDataSourceActionResponse>(
      `/api/data-sources/native/sources/by-index/${encodeURIComponent(String(dataSourceIndex))}`,
      {
        method: "DELETE",
        body: JSON.stringify({ confirm_token: NATIVE_DATA_SOURCE_DELETE_PHRASE }),
      },
    ),
  getNativeOrganizationOverview: (params: NativeOrganizationOverviewParams = {}) => {
    const searchParams = nativeOrganizationOverviewParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeOrganizationOverviewResponse>(
      `/api/organization/native/overview${suffix}`,
    );
  },
  getNativeStatusCenter: (params: NativeStatusCenterParams = {}) => {
    const searchParams = nativeStatusCenterParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeStatusCenterResponse>(`/api/native/status${suffix}`);
  },
  getNativeKnowledgeBaseOverview: (limit = 20) => {
    const searchParams = new URLSearchParams({ limit: String(limit) });
    return request<NativeKnowledgeBaseOverviewResponse>(
      `/api/knowledge-bases/native/overview?${searchParams.toString()}`,
    );
  },
  selectActiveKnowledgeBase: (kbId: string) =>
    request<ActiveKnowledgeBaseSelectionResponse>("/api/knowledge-bases/native/active", {
      method: "POST",
      body: JSON.stringify({ kb_id: kbId }),
    }),
  createNativeKnowledgeBase: (payload: NativeKnowledgeBaseMutationPayload) =>
    request<NativeKnowledgeBaseMutationResponse>("/api/knowledge-bases/native", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateNativeKnowledgeBase: (kbId: string, payload: NativeKnowledgeBaseMutationPayload) =>
    request<NativeKnowledgeBaseMutationResponse>(`/api/knowledge-bases/native/${encodeURIComponent(kbId)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteNativeKnowledgeBase: async (kbId: string, confirmToken: string) => {
    const encodedKbId = encodeURIComponent(kbId);
    const payload = { confirm_token: confirmToken };
    try {
      return await request<NativeKnowledgeBaseMutationResponse>(
        `/api/knowledge-bases/native/${encodedKbId}`,
        {
          method: "DELETE",
          body: JSON.stringify(payload),
        },
      );
    } catch (error) {
      if (error instanceof ApiError && (error.status === 404 || error.status === 405)) {
        return request<NativeKnowledgeBaseMutationResponse>(
          `/api/knowledge-bases/native/${encodedKbId}/delete`,
          {
            method: "POST",
            body: JSON.stringify(payload),
          },
        );
      }
      throw error;
    }
  },
  toggleNativeKnowledgeBasePin: (kbId: string, confirmToken: string) =>
    request<NativeKnowledgeBaseMutationResponse>(
      `/api/knowledge-bases/native/${encodeURIComponent(kbId)}/pin-toggle`,
      {
        method: "POST",
        body: JSON.stringify({ confirm_token: confirmToken }),
      },
    ),
  listDocuments: (filters: DocumentListFilters = {}) => {
    const params = documentFilterParams(filters);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return request<ListResponse<Document>>(`/api/documents${suffix}`);
  },
  refreshDocumentStatuses: (filters: DocumentListFilters = {}, limit = 50) => {
    const params = documentFilterParams(filters);
    params.set("limit", String(limit));
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return request<DocumentBulkRefreshResponse>(`/api/documents/refresh-status${suffix}`, {
      method: "POST",
    });
  },
  uploadDocument: (payload: DocumentUploadRequest) => {
    const formData = new FormData();
    formData.append("file", payload.file);
    if (payload.title) {
      formData.append("title", payload.title);
    }
    if (payload.business_area) {
      formData.append("business_area", payload.business_area);
    }
    if (payload.document_type) {
      formData.append("document_type", payload.document_type);
    }
    if (payload.source) {
      formData.append("source", payload.source);
    }
    if (payload.keywords_json) {
      formData.append("keywords_json", payload.keywords_json);
    }
    if (payload.knowledge_base_id) {
      formData.append("knowledge_base_id", payload.knowledge_base_id);
    }
    return request<DocumentUploadResponse>("/api/documents", {
      method: "POST",
      body: formData,
      headers: {},
    });
  },
  ingestDocumentUrl: (payload: DocumentUrlCreateRequest) =>
    request<DocumentUploadResponse>("/api/documents/url", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  ingestManualDocument: (payload: DocumentManualCreateRequest) =>
    request<DocumentUploadResponse>("/api/documents/manual", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  retryDocumentIndex: (documentId: string) =>
    request<DocumentRetryIndexResponse>(`/api/documents/${documentId}/retry-index`, {
      method: "POST",
    }),
  retryDocumentProcessing: (documentId: string) =>
    request<DocumentRetryIndexResponse>(`/api/documents/${documentId}/retry-processing`, {
      method: "POST",
    }),
  reindexDocument: (documentId: string) =>
    request<DocumentIndexResponse>(`/api/documents/${documentId}/reindex`, {
      method: "POST",
    }),
  reparseNativeDocument: (documentId: string) =>
    request<DocumentLifecycleActionResponse>(`/api/documents/${documentId}/native-reparse`, {
      method: "POST",
    }),
  cancelDocumentProcessing: (documentId: string) =>
    request<DocumentLifecycleActionResponse>(`/api/documents/${documentId}/cancel-processing`, {
      method: "POST",
    }),
  deleteDocument: (documentId: string) =>
    request<DocumentLifecycleActionResponse>(`/api/documents/${documentId}`, {
      method: "DELETE",
    }),
  documentPreviewUrl: (documentId: string) =>
    `${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}/preview`,
  documentDownloadUrl: (documentId: string) =>
    `${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}/download`,
  getDocumentSpans: (documentId: string) =>
    request<DocumentSpansResponse>(`/api/documents/${documentId}/spans`),
  listDocumentChunks: (documentId: string) =>
    request<DocumentChunkListResponse>(`/api/documents/${documentId}/chunks`),
  getDocumentChunk: (documentId: string, chunkId: string) =>
    request<DocumentChunk>(
      `/api/documents/${encodeURIComponent(documentId)}/chunks/${encodeURIComponent(chunkId)}`,
    ),
  setDocumentChunkEnabled: (documentId: string, chunkId: string, isEnabled: boolean) =>
    request<DocumentChunkActionResponse>(
      `/api/documents/${encodeURIComponent(documentId)}/chunks/${encodeURIComponent(chunkId)}/enabled`,
      {
        method: "PATCH",
        body: JSON.stringify({
          confirm_token: NATIVE_CHUNK_CONFIRM_PHRASE,
          is_enabled: isEnabled,
          reason: "library_chunk_control",
        }),
      },
    ),
  rewriteDocumentChunkContent: (documentId: string, chunkId: string, content: string) =>
    request<DocumentChunkActionResponse>(
      `/api/documents/${encodeURIComponent(documentId)}/chunks/${encodeURIComponent(chunkId)}/content`,
      {
        method: "PATCH",
        body: JSON.stringify({
          confirm_token: NATIVE_CHUNK_CONFIRM_PHRASE,
          content,
          reason: "library_chunk_control",
        }),
      },
    ),
  deleteGeneratedQuestion: (documentId: string, chunkId: string, questionId: string) =>
    request<DocumentChunkActionResponse>(
      `/api/documents/${encodeURIComponent(documentId)}/chunks/${encodeURIComponent(chunkId)}/questions/${encodeURIComponent(questionId)}`,
      {
        method: "DELETE",
        body: JSON.stringify({
          confirm_token: NATIVE_CHUNK_CONFIRM_PHRASE,
          reason: "library_chunk_control",
        }),
      },
    ),
  searchSimilarDocumentChunks: (documentId: string, chunkId: string, topK = 5) =>
    request<DocumentChunkSimilarResponse>(
      `/api/documents/${encodeURIComponent(documentId)}/chunks/${encodeURIComponent(chunkId)}/similar?top_k=${encodeURIComponent(String(topK))}`,
    ),
  deleteDocumentChunk: (documentId: string, chunkId: string) =>
    request<DocumentChunkActionResponse>(
      `/api/documents/${encodeURIComponent(documentId)}/chunks/${encodeURIComponent(chunkId)}`,
      {
        method: "DELETE",
        body: JSON.stringify({
          confirm_token: NATIVE_CHUNK_CONFIRM_PHRASE,
          reason: "library_chunk_control",
        }),
      },
    ),
  listNativeAuditEvents: (params: {
    limit?: number;
    capability?: string;
    operation?: string;
    target_type?: string;
    target_id?: string;
    status?: string;
    wnid_capability?: string;
  } = {}) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        searchParams.set(key, String(value));
      }
    });
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeMutationAuditListResponse>(`/api/native-audit/events${suffix}`);
  },
  listDocumentEvents: (documentId: string) =>
    request<ListResponse<DocumentProcessingEvent>>(`/api/documents/${documentId}/events`),
  listConversations: () => request<ListResponse<Conversation>>("/api/conversations"),
  listConversationMessages: (conversationId: string) =>
    request<ListResponse<ConversationMessage>>(`/api/conversations/${conversationId}/messages`),
  runAnalysis: (payload: AnalysisRunRequest) =>
    request<AnalysisRunResponse>("/api/analysis/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listNativeAgents: () => request<NativeAgentCatalogResponse>("/api/analysis/native-agents"),
  listNativeAgentSuggestedQuestions: (
    agentId: string,
    params: { knowledge_base_ids?: string[]; knowledge_ids?: string[]; limit?: number } = {},
  ) => {
    const searchParams = new URLSearchParams();
    if (params.knowledge_base_ids?.length) {
      searchParams.set("knowledge_base_ids", params.knowledge_base_ids.join(","));
    }
    if (params.knowledge_ids?.length) {
      searchParams.set("knowledge_ids", params.knowledge_ids.join(","));
    }
    if (params.limit) {
      searchParams.set("limit", String(params.limit));
    }
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeAgentSuggestedQuestionsResponse>(
      `/api/analysis/native-agents/${encodeURIComponent(agentId)}/suggested-questions${suffix}`,
    );
  },
  createNativeAgent: (payload: NativeAgentMutationRequest) =>
    request<NativeAgentMutationResponse>("/api/analysis/native-agents", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateNativeAgent: (agentId: string, payload: NativeAgentMutationRequest) =>
    request<NativeAgentMutationResponse>(`/api/analysis/native-agents/${encodeURIComponent(agentId)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  updateNativeAgentStrategy: (agentId: string, payload: NativeAgentStrategyUpdateRequest) =>
    request<NativeAgentMutationResponse>(`/api/analysis/native-agents/${encodeURIComponent(agentId)}/strategy`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  copyNativeAgent: (agentId: string, payload: { confirm_token?: string | null }) =>
    request<NativeAgentMutationResponse>(`/api/analysis/native-agents/${encodeURIComponent(agentId)}/copy`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteNativeAgent: (agentId: string, payload: { confirm_token?: string | null }) =>
    request<NativeAgentMutationResponse>(`/api/analysis/native-agents/${encodeURIComponent(agentId)}`, {
      method: "DELETE",
      body: JSON.stringify(payload),
    }),
  runNativeAgentQa: (payload: NativeAgentQaRequest) =>
    request<NativeAgentQaResponse>("/api/analysis/native-agentqa", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getTask: (taskId: string) => request<Task>(`/api/tasks/${taskId}`),
  getOutput: (outputId: string) =>
    request<{ output: GeneratedOutput; citations: Citation[] }>(`/api/outputs/${outputId}`),
  listHistory: (filters: HistoryListFilters = {}) => {
    const params = historyFilterParams(filters);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return request<ListResponse<GeneratedOutput>>(`/api/history${suffix}`);
  },
  getHistoryOutput: (outputId: string) =>
    request<{ output: GeneratedOutput; citations: Citation[] }>(`/api/history/${outputId}`),
  locateCitation: (payload: CitationLocateRequest) =>
    request<CitationLocateResponse>("/api/citations/locate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  debugRag: (payload: RagDebugRequest) =>
    request<RagDebugResponse>("/api/rag/debug", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runNativeKnowledgeChat: (payload: NativeKnowledgeChatRequest) =>
    request<NativeKnowledgeChatResponse>("/api/rag/knowledge-chat", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  searchWiki: (query: string, kbId?: string, limit = 10) => {
    const params = new URLSearchParams({
      query,
      limit: String(limit),
    });
    if (kbId) {
      params.set("kb_id", kbId);
    }
    return request<WikiSearchResponse>(`/api/wiki/search?${params.toString()}`);
  },
  getWikiPage: (slug: string, kbId?: string) => {
    const params = new URLSearchParams();
    if (kbId) {
      params.set("kb_id", kbId);
    }
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return request<WikiPage>(`/api/wiki/pages/${encodeURIComponent(slug)}${suffix}`);
  },
  createWikiPage: (payload: WikiPageCreateRequest) =>
    request<WikiPage>("/api/wiki/pages", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateWikiPage: (slug: string, payload: WikiPageUpdateRequest) =>
    request<WikiPage>(`/api/wiki/pages/${encodeURIComponent(slug)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  publishWikiPage: (slug: string) =>
    request<WikiPage>(`/api/wiki/pages/${encodeURIComponent(slug)}/publish`, {
      method: "POST",
    }),
  refreshWikiStatus: (slug: string) =>
    request<WikiPage>(`/api/wiki/pages/${encodeURIComponent(slug)}/refresh-status`, {
      method: "POST",
    }),
  recoverWikiStatus: (slug: string) =>
    request<WikiPage>(`/api/wiki/pages/${encodeURIComponent(slug)}/recover-status`, {
      method: "POST",
    }),
  reindexWikiPage: (slug: string) =>
    request<WikiPage>(`/api/wiki/pages/${encodeURIComponent(slug)}/reindex`, {
      method: "POST",
    }),
  createWikiDraftFromOutput: (outputId: string, payload: WikiDraftFromOutputRequest = {}) =>
    request<WikiPage>(`/api/wiki/drafts/from-output/${encodeURIComponent(outputId)}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
