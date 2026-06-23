const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || DEFAULT_API_BASE_URL;

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

export type DocumentUploadResponse = {
  document: Document;
};

export type DocumentRetryIndexResponse = {
  document: Document;
  message: string;
};

export type DocumentListFilters = {
  status?: string;
  processing_state?: string;
  has_error?: boolean;
  knowledge_backend?: string;
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

export type HistoryListFilters = {
  query?: string;
  task_type?: string;
  status?: string;
  citation_source?: string;
  source_type?: string;
  evidence_state?: string;
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

export type DocumentIndexResponse = {
  document: Document;
  chunk_count: number;
  message: string;
};

export type AnalysisTaskType = "knowledge_qa" | "policy_analysis" | "case_review";
export type RetrievalScope = "all" | "document" | "wiki";

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
  warning_count: number;
  evidence_state: string;
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
  getNativeMcpOverview: (params: NativeMcpOverviewParams = {}) => {
    const searchParams = nativeMcpOverviewParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeMcpOverviewResponse>(`/api/mcp/native/overview${suffix}`);
  },
  getNativeWebSearchOverview: (params: NativeWebSearchOverviewParams = {}) => {
    const searchParams = nativeWebSearchOverviewParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeWebSearchOverviewResponse>(
      `/api/web-search/native/overview${suffix}`,
    );
  },
  getNativeVectorStoreOverview: (params: NativeVectorStoreOverviewParams = {}) => {
    const searchParams = nativeVectorStoreOverviewParams(params);
    const suffix = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return request<NativeVectorStoreOverviewResponse>(
      `/api/vector-stores/native/overview${suffix}`,
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
  listDocumentChunks: (documentId: string) =>
    request<DocumentChunkListResponse>(`/api/documents/${documentId}/chunks`),
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
