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
  metadata_json: string | null;
  created_at: string;
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
  task_type: "knowledge_qa" | "policy_analysis" | "case_review";
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

export type ListResponse<T> = {
  items: T[];
  total: number;
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
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
};
