const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || DEFAULT_API_BASE_URL;

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
  memory_recent_limit: number;
  database: string;
  counts: Record<string, number>;
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
};

export type DocumentUploadResponse = {
  document: Document;
};

export type DocumentRetryIndexResponse = {
  document: Document;
  message: string;
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

export type DocumentIndexResponse = {
  document: Document;
  chunk_count: number;
  message: string;
};

export type AnalysisTaskType = "knowledge_qa" | "policy_analysis" | "case_review";

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

export type Evidence = {
  document_id: string | null;
  external_doc_id: string | null;
  chunk_id: string | null;
  title: string;
  text: string;
  score: number | null;
  source: string;
  metadata: Record<string, unknown>;
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
};

export type AnalysisRunResponse = {
  conversation: Conversation;
  messages: ConversationMessage[];
  task: Task;
  output: GeneratedOutput;
  citations: Citation[];
};

export type WikiPageSummary = {
  slug: string;
  title: string;
  page_type: string;
  summary: string;
  source: string;
  metadata: Record<string, unknown>;
};

export type WikiPage = {
  slug: string;
  title: string;
  page_type: string;
  summary: string;
  content: string;
  citations: Evidence[];
  source: string;
  metadata: Record<string, unknown>;
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

export const apiClient = {
  baseUrl: API_BASE_URL,
  getStatus: () => request<StatusResponse>("/api/status"),
  listDocuments: () => request<ListResponse<Document>>("/api/documents"),
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
  reindexDocument: (documentId: string) =>
    request<DocumentIndexResponse>(`/api/documents/${documentId}/reindex`, {
      method: "POST",
    }),
  listDocumentChunks: (documentId: string) =>
    request<DocumentChunkListResponse>(`/api/documents/${documentId}/chunks`),
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
  listHistory: () => request<ListResponse<GeneratedOutput>>("/api/history"),
  getHistoryOutput: (outputId: string) =>
    request<{ output: GeneratedOutput; citations: Citation[] }>(`/api/history/${outputId}`),
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
};
