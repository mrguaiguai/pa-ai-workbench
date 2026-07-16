import {
  Database,
  Download,
  Edit3,
  Eye,
  FileText,
  Keyboard,
  Link,
  Loader2,
  Pin,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  ToggleLeft,
  ToggleRight,
  Trash2,
  Upload,
  X,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

import {
  ApiError,
  Document,
  DocumentChunk,
  DocumentChunkActionResponse,
  DocumentChunkSimilarResult,
  DocumentSpansResponse,
  DocumentProcessingEvent,
  NATIVE_KB_CONFIRM_PHRASE,
  NativeKnowledgeBaseItem,
  NativeKnowledgeBaseOverviewResponse,
  apiClient,
} from "../api/client";
import {
  DocumentStatusBadge,
  EmptyState,
  ErrorState,
} from "../components/workbench";

type LibraryForm = {
  title: string;
  businessArea: string;
  documentType: string;
  source: string;
  url: string;
  manualContent: string;
};

type LibraryFilters = {
  status: string;
  knowledgeBackend: string;
  knowledgeBaseId: string;
  errorOnly: boolean;
};

type LoadState = "idle" | "loading" | "error";
type ChunkLoadState = "idle" | "loading" | "error";
type EventLoadState = "idle" | "loading" | "error";
type KnowledgeBaseLoadState = "idle" | "loading" | "error";
type IngestionMode = "file" | "url" | "manual";
type KnowledgeBaseFormMode = "create" | "edit";

type KnowledgeBaseDraft = {
  name: string;
  description: string;
};

const initialForm: LibraryForm = {
  title: "",
  businessArea: "",
  documentType: "",
  source: "手动上传",
  url: "",
  manualContent: "",
};

const initialFilters: LibraryFilters = {
  status: "all",
  knowledgeBackend: "all",
  knowledgeBaseId: "all",
  errorOnly: false,
};

const initialKnowledgeBaseDraft: KnowledgeBaseDraft = {
  name: "",
  description: "",
};

const runningStatuses = new Set(["uploaded", "parsing", "chunking", "embedding", "indexing", "deleting"]);
const parsedStatuses = new Set(["parsed", "chunked", "embedding", "indexing", "indexed"]);
const readyStatuses = new Set(["indexed"]);

function formatFileSize(size: number | null) {
  if (size === null) {
    return "-";
  }
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return `HTTP ${error.status}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "未知错误";
}

function chunkAuditMessage(response: DocumentChunkActionResponse) {
  if (!response.audit) {
    return null;
  }
  return `审计：${response.audit.status} · ${response.audit.id.slice(0, 12)}`;
}

function stageClass(state: string) {
  if (state.includes("失败") || state === "failed") {
    return "failed";
  }
  if (state.includes("中") || state === "partial" || state === "pending") {
    return "active";
  }
  if (state.includes("完成") || state.includes("已") || state === "indexed" || state === "可提问") {
    return "done";
  }
  return "idle";
}

function parseStatus(document: Document) {
  if (document.status === "failed" && document.failed_step === "parse") {
    return "解析失败";
  }
  if (document.status === "parsing") {
    return "解析中";
  }
  if (parsedStatuses.has(document.status) || document.chunk_count > 0) {
    return "已解析";
  }
  return "待解析";
}

function chunkStatus(document: Document) {
  if (document.status === "failed" && document.failed_step === "chunk") {
    return "分块失败";
  }
  if (document.status === "chunking") {
    return "分块中";
  }
  if (document.chunk_count > 0) {
    return `${document.chunk_count} 个分块`;
  }
  return "待分块";
}

function embeddingStatus(document: Document) {
  if (document.embedding_status === "indexed") {
    return `${document.indexed_chunk_count}/${document.chunk_count} 已向量化`;
  }
  if (document.embedding_status === "partial") {
    return `${document.indexed_chunk_count}/${document.chunk_count} 向量化中`;
  }
  if (document.embedding_status === "failed") {
    return "向量化失败";
  }
  if (document.status === "indexing" || document.embedding_status === "pending") {
    return "向量化中";
  }
  return "待向量化";
}

function indexStatus(document: Document) {
  if (document.status === "indexed") {
    return "已索引";
  }
  if (document.status === "indexing") {
    return "索引中";
  }
  if (document.status === "deleting") {
    return "删除中";
  }
  if (document.status === "failed" && document.failed_step === "index") {
    return "索引失败";
  }
  if (document.status === "failed" && document.failed_step === "embedding") {
    return "向量化失败";
  }
  if (document.status === "embedding") {
    return "向量化中";
  }
  return "待索引";
}

function readinessStatus(document: Document) {
  if (document.status === "failed") {
    return "失败";
  }
  if (document.processing_timed_out || document.processing_state === "stalled") {
    return "超时";
  }
  if (readyStatuses.has(document.status)) {
    return "可提问";
  }
  if (runningStatuses.has(document.status)) {
    return "处理中";
  }
  return "等待处理";
}

function readinessClass(document: Document) {
  if (document.status === "failed") {
    return "failed";
  }
  if (document.processing_timed_out || document.processing_state === "stalled") {
    return "failed";
  }
  if (readyStatuses.has(document.status)) {
    return "ready";
  }
  if (runningStatuses.has(document.status)) {
    return "active";
  }
  return "idle";
}

function statusHint(document: Document) {
  if (document.processing_message) {
    return localizedProcessingMessage(document.processing_message);
  }
  if (document.status === "failed") {
    return document.failed_step
      ? `失败位置：${stepLabel(document.failed_step)}`
      : "处理失败";
  }
  if (document.status === "indexed") {
    return document.chunk_count > 0
      ? `${document.chunk_count} 个分块可用`
      : "索引完成，等待分块预览";
  }
  if (document.status === "indexing") {
    return "索引完成后可提问";
  }
  if (document.status === "deleting") {
    return "删除任务已提交";
  }
  if (document.status === "embedding") {
    return "向量化完成后进入索引";
  }
  if (document.status === "chunking") {
    return "分块完成后进入索引";
  }
  if (document.status === "parsing") {
    return "解析完成后进入分块";
  }
  return "等待 WeKnora/本地流程处理";
}

function localizedProcessingMessage(message: string) {
  const normalized = message.trim();
  const labels: Record<string, string> = {
    "Document is indexed and ready for grounded answers.": "文档已索引，可用于有依据回答。",
    "Document parsed, chunked, embedded, and indexed.": "文档已完成解析、分块、向量化和索引。",
    "Document chunks rebuilt, embedded, and indexed.": "文档分块已重建、向量化并完成索引。",
  };
  return labels[normalized] ?? normalized;
}

function backendLabel(document: Document) {
  return document.knowledge_backend === "weknora_api" ? "WeKnora" : document.knowledge_backend;
}

function knowledgeBaseShortLabel(item: NativeKnowledgeBaseItem) {
  return item.name || item.id || "未命名知识库";
}

function documentKnowledgeBaseLabel(
  document: Document,
  overview: NativeKnowledgeBaseOverviewResponse | null,
) {
  if (!document.knowledge_base_id) {
    return "未归类";
  }
  const knowledgeBase = overview?.items.find((item) => item.id === document.knowledge_base_id);
  return knowledgeBase ? knowledgeBaseShortLabel(knowledgeBase) : "未知知识库";
}

function activeKnowledgeBaseLabel(overview: NativeKnowledgeBaseOverviewResponse | null) {
  const active = overview?.active_selection;
  if (!active) {
    return "未验证活动知识库";
  }
  return active.name || active.kb_id || "活动知识库";
}

function mutationKnowledgeBase(
  response: { surfaces: Record<string, Record<string, unknown>> },
  action: string,
) {
  const surface = response.surfaces[action];
  const knowledgeBase = surface?.knowledge_base;
  return knowledgeBase && typeof knowledgeBase === "object"
    ? (knowledgeBase as NativeKnowledgeBaseItem)
    : null;
}

function mutationSucceeded(
  response: { status: string; warnings: string[]; surfaces: Record<string, Record<string, unknown>> },
  action: string,
) {
  const surface = response.surfaces[action];
  return response.status === "live" && surface?.status === "live";
}

function buildDocumentFilters(filters: LibraryFilters) {
  return {
    status: filters.status,
    knowledge_backend: filters.knowledgeBackend,
    knowledge_base_id: filters.knowledgeBaseId,
    has_error: filters.errorOnly ? true : undefined,
  };
}

function stepLabel(step: string | null) {
  const normalized = (step || "").trim().toLowerCase();
  if (normalized === "parse" || normalized === "parsing") {
    return "解析";
  }
  if (normalized === "chunk" || normalized === "chunking") {
    return "分块";
  }
  if (normalized === "index" || normalized === "indexing" || normalized === "embedding") {
    if (normalized === "embedding") {
      return "向量化";
    }
    return "索引";
  }
  if (normalized === "weknora_upload") {
    return "WeKnora 上传";
  }
  if (normalized === "weknora_status") {
    return "WeKnora 状态刷新";
  }
  if (normalized === "weknora_chunks") {
    return "WeKnora 分块";
  }
  return step || "流程";
}

function eventLabel(event: DocumentProcessingEvent) {
  const message = event.error_message || event.message || event.status;
  return `${stepLabel(event.step)}：${message}`;
}

function chunkExcerpt(text: string, maxChars = 360) {
  const normalized = text.split(/\s+/).join(" ");
  if (normalized.length <= maxChars) {
    return normalized;
  }
  return `${normalized.slice(0, maxChars)}[已截断]`;
}

function chunkLocation(chunk: DocumentChunk) {
  const parts = [
    chunk.page_number === null ? null : `第 ${chunk.page_number} 页`,
    chunk.start_char === null || chunk.end_char === null
      ? null
      : `${chunk.start_char}-${chunk.end_char}`,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "无位置偏移";
}

function chunkMetadata(chunk: DocumentChunk): Record<string, unknown> {
  if (!chunk.metadata_json) {
    return {};
  }
  try {
    const parsed = JSON.parse(chunk.metadata_json) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

function chunkIsEnabled(chunk: DocumentChunk) {
  const metadata = chunkMetadata(chunk);
  return metadata.weknora_is_enabled !== false && chunk.embedding_status !== "disabled";
}

function generatedQuestions(chunk: DocumentChunk) {
  const metadata = chunkMetadata(chunk);
  const questions = metadata.generated_questions;
  if (!Array.isArray(questions)) {
    return [];
  }
  return questions
    .filter((question) => question && typeof question === "object")
    .map((question) => question as { id?: string; question?: string });
}

function chunkEmptyText(document: Document) {
  if (document.status === "failed") {
    return "处理失败，暂无分块";
  }
  if (document.status !== "indexed") {
    return "索引完成后显示分块";
  }
  return "暂无分块";
}

function libraryHashTarget() {
  const query = window.location.hash.split("?")[1] || "";
  const params = new URLSearchParams(query);
  return {
    documentId: params.get("document"),
    chunkId: params.get("chunk"),
  };
}

function chunkMatchesTarget(chunk: DocumentChunk, targetChunkId: string | null) {
  if (!targetChunkId) {
    return false;
  }
  return chunk.id === targetChunkId || chunk.vector_id === targetChunkId;
}

function chunkDomId(chunk: DocumentChunk) {
  return `chunk-${chunk.id.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

export function LibraryPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [ingestionMode, setIngestionMode] = useState<IngestionMode>("file");
  const [form, setForm] = useState<LibraryForm>(initialForm);
  const [filters, setFilters] = useState<LibraryFilters>(initialFilters);
  const [isUploading, setIsUploading] = useState(false);
  const [isRefreshingStatuses, setIsRefreshingStatuses] = useState(false);
  const [reindexingId, setReindexingId] = useState<string | null>(null);
  const [lifecycleActionId, setLifecycleActionId] = useState<string | null>(null);
  const [previewDocumentId, setPreviewDocumentId] = useState<string | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [spans, setSpans] = useState<DocumentSpansResponse | null>(null);
  const [chunkLoadState, setChunkLoadState] = useState<ChunkLoadState>("idle");
  const [chunkError, setChunkError] = useState<string | null>(null);
  const [chunkAuditNotice, setChunkAuditNotice] = useState<string | null>(null);
  const [events, setEvents] = useState<DocumentProcessingEvent[]>([]);
  const [eventLoadState, setEventLoadState] = useState<EventLoadState>("idle");
  const [eventError, setEventError] = useState<string | null>(null);
  const [targetChunkId, setTargetChunkId] = useState<string | null>(null);
  const [chunkActionId, setChunkActionId] = useState<string | null>(null);
  const [editingChunkId, setEditingChunkId] = useState<string | null>(null);
  const [chunkDraft, setChunkDraft] = useState("");
  const [similarResults, setSimilarResults] = useState<Record<string, DocumentChunkSimilarResult[]>>({});
  const [kbOverview, setKbOverview] = useState<NativeKnowledgeBaseOverviewResponse | null>(null);
  const [kbLoadState, setKbLoadState] = useState<KnowledgeBaseLoadState>("idle");
  const [kbError, setKbError] = useState<string | null>(null);
  const [selectedKbId, setSelectedKbId] = useState("");
  const [selectingKb, setSelectingKb] = useState(false);
  const [savingKb, setSavingKb] = useState(false);
  const [pinningKb, setPinningKb] = useState(false);
  const [deletingKb, setDeletingKb] = useState(false);
  const [kbActionNotice, setKbActionNotice] = useState<string | null>(null);
  const [kbFormMode, setKbFormMode] = useState<KnowledgeBaseFormMode>("create");
  const [kbFormOpen, setKbFormOpen] = useState(false);
  const [kbDraft, setKbDraft] = useState<KnowledgeBaseDraft>(initialKnowledgeBaseDraft);

  const indexedCount = useMemo(
    () => documents.filter((document) => document.status === "indexed").length,
    [documents],
  );
  const processingCount = useMemo(
    () => documents.filter((document) => runningStatuses.has(document.status)).length,
    [documents],
  );
  const failedCount = useMemo(
    () => documents.filter((document) => document.status === "failed").length,
    [documents],
  );
  const previewDocument = useMemo(
    () => documents.find((document) => document.id === previewDocumentId) ?? null,
    [documents, previewDocumentId],
  );
  const activeKbId = kbOverview?.active_selection?.kb_id ?? "";
  const selectedKb = useMemo(
    () => kbOverview?.items.find((item) => item.id === selectedKbId) ?? null,
    [kbOverview, selectedKbId],
  );
  const knowledgeBaseActionsDisabled = selectingKb || savingKb || pinningKb || deletingKb;

  const applyHashTarget = (nextDocuments: Document[]) => {
    const target = libraryHashTarget();
    if (!target.documentId) {
      return;
    }
    if (nextDocuments.some((document) => document.id === target.documentId)) {
      loadPreview(target.documentId, target.chunkId);
    }
  };

  const applyDocumentItems = (nextDocuments: Document[]) => {
    setDocuments(nextDocuments);
    if (
      previewDocumentId &&
      !nextDocuments.some((document) => document.id === previewDocumentId)
    ) {
      setPreviewDocumentId(null);
      setChunks([]);
      setEvents([]);
      setSpans(null);
    }
    applyHashTarget(nextDocuments);
  };

  const loadDocuments = () => {
    setLoadState("loading");
    setError(null);
    apiClient
      .listDocuments({ ...buildDocumentFilters(filters), refresh_status: true })
      .then((response) => {
        applyDocumentItems(response.items);
        setLoadState("idle");
      })
      .catch((loadError: unknown) => {
        setError(errorMessage(loadError));
        setLoadState("error");
      });
  };

  const loadKnowledgeBases = () => {
    setKbLoadState("loading");
    setKbError(null);
    apiClient
      .getNativeKnowledgeBaseOverview(50)
      .then((response) => {
        setKbOverview(response);
        setSelectedKbId(response.active_selection?.kb_id ?? response.items[0]?.id ?? "");
        setKbLoadState("idle");
        setKbActionNotice(null);
      })
      .catch((loadError: unknown) => {
        setKbError(errorMessage(loadError));
        setKbLoadState("error");
      });
  };

  useEffect(() => {
    loadDocuments();
  }, [filters.status, filters.knowledgeBackend, filters.knowledgeBaseId, filters.errorOnly]);

  useEffect(() => {
    if (processingCount === 0) {
      return undefined;
    }
    const intervalId = window.setInterval(() => {
      apiClient
        .listDocuments({ ...buildDocumentFilters(filters), refresh_status: true })
        .then((response) => applyDocumentItems(response.items))
        .catch((loadError: unknown) => setError(errorMessage(loadError)));
    }, 10000);
    return () => window.clearInterval(intervalId);
  }, [processingCount, filters.status, filters.knowledgeBackend, filters.knowledgeBaseId, filters.errorOnly, previewDocumentId]);

  useEffect(() => {
    loadKnowledgeBases();
  }, []);

  useEffect(() => {
    const onLocate = () => {
      const target = libraryHashTarget();
      if (target.documentId) {
        loadPreview(target.documentId, target.chunkId);
      }
    };
    window.addEventListener("pa:citation-locate", onLocate);
    window.addEventListener("hashchange", onLocate);
    return () => {
      window.removeEventListener("pa:citation-locate", onLocate);
      window.removeEventListener("hashchange", onLocate);
    };
  }, []);

  useEffect(() => {
    if (!targetChunkId || chunkLoadState === "loading") {
      return;
    }
    const chunk = chunks.find((item) => chunkMatchesTarget(item, targetChunkId));
    if (!chunk) {
      return;
    }
    window.requestAnimationFrame(() => {
      document.getElementById(chunkDomId(chunk))?.scrollIntoView({
        block: "center",
        behavior: "smooth",
      });
    });
  }, [chunks, targetChunkId, chunkLoadState]);

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    if (file && !form.title) {
      setForm((current) => ({ ...current, title: file.name }));
    }
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (ingestionMode === "file" && !selectedFile) {
      setError("请选择文件");
      return;
    }
    if (ingestionMode === "url" && !form.url.trim()) {
      setError("请输入 URL");
      return;
    }
    if (ingestionMode === "manual" && (!form.title.trim() || !form.manualContent.trim())) {
      setError("请输入标题和正文");
      return;
    }

    setIsUploading(true);
    setError(null);
    const sourceValue =
      ingestionMode === "file"
        ? form.source.trim()
        : form.source.trim() && form.source.trim() !== initialForm.source
          ? form.source.trim()
          : ingestionMode;
    const commonPayload = {
      title: form.title.trim(),
      business_area: form.businessArea.trim(),
      document_type: form.documentType.trim(),
      source: sourceValue,
      knowledge_base_id: selectedKbId || undefined,
    };
    const requestPromise =
      ingestionMode === "file"
        ? apiClient.uploadDocument({
            file: selectedFile as File,
            ...commonPayload,
            title: commonPayload.title || (selectedFile as File).name,
          })
        : ingestionMode === "url"
          ? apiClient.ingestDocumentUrl({
              ...commonPayload,
              title: commonPayload.title || form.url.trim(),
              url: form.url.trim(),
              source: commonPayload.source || "url",
              document_type: commonPayload.document_type || "url",
            })
          : apiClient.ingestManualDocument({
              ...commonPayload,
              title: commonPayload.title,
              content: form.manualContent.trim(),
              source: commonPayload.source || "manual",
              document_type: commonPayload.document_type || "manual",
            });
    requestPromise
      .then(() => {
        setSelectedFile(null);
        setForm(initialForm);
        loadDocuments();
        loadKnowledgeBases();
      })
      .catch((uploadError: unknown) => setError(errorMessage(uploadError)))
      .finally(() => setIsUploading(false));
  };

  const onStartCreateKnowledgeBase = () => {
    setKbFormMode("create");
    setKbDraft(initialKnowledgeBaseDraft);
    setKbFormOpen(true);
    setKbError(null);
    setKbActionNotice(null);
  };

  const onStartEditKnowledgeBase = () => {
    if (!selectedKb) {
      setKbError("请选择知识库");
      return;
    }
    setKbFormMode("edit");
    setKbDraft({
      name: selectedKb.name || "",
      description: selectedKb.description || "",
    });
    setKbFormOpen(true);
    setKbError(null);
    setKbActionNotice(null);
  };

  const onCancelKnowledgeBaseForm = () => {
    setKbFormOpen(false);
    setKbDraft(initialKnowledgeBaseDraft);
  };

  const onSaveKnowledgeBase = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const name = kbDraft.name.trim();
    const description = kbDraft.description.trim();
    if (!name) {
      setKbError("请输入知识库名称");
      return;
    }
    if (kbFormMode === "edit" && !selectedKbId) {
      setKbError("请选择要管理的知识库");
      return;
    }

    setSavingKb(true);
    setKbError(null);
    setKbActionNotice(null);
    const payload = {
      name,
      description,
      type: selectedKb?.type || "document",
      is_temporary: false,
      confirm_token: NATIVE_KB_CONFIRM_PHRASE,
    };
    const request =
      kbFormMode === "create"
        ? apiClient.createNativeKnowledgeBase(payload)
        : apiClient.updateNativeKnowledgeBase(selectedKbId, payload);
    request
      .then((response) => {
        const action = kbFormMode === "create" ? "create" : "update";
        if (!mutationSucceeded(response, action)) {
          setKbError(response.warnings[0] ?? "知识库保存未完成，请查看设置与调试中的 Native 状态。");
          return undefined;
        }
        const nextKb = mutationKnowledgeBase(response, action);
        const nextKbId = nextKb?.id || selectedKbId;
        const activeRequest =
          kbFormMode === "create" && nextKbId
            ? apiClient.selectActiveKnowledgeBase(nextKbId)
            : Promise.resolve(null);
        return activeRequest.then(() => {
          if (nextKbId) {
            setSelectedKbId(nextKbId);
          }
          setKbFormOpen(false);
          setKbDraft(initialKnowledgeBaseDraft);
          setKbActionNotice(
            kbFormMode === "create"
              ? `已新建知识库「${name}」`
              : `已更新知识库「${name}」`,
          );
          loadKnowledgeBases();
        });
      })
      .catch((saveError: unknown) => setKbError(errorMessage(saveError)))
      .finally(() => setSavingKb(false));
  };

  const onSelectKnowledgeBase = () => {
    if (!selectedKbId || selectedKbId === activeKbId) {
      return;
    }
    setSelectingKb(true);
    setKbError(null);
    setKbActionNotice(null);
    apiClient
      .selectActiveKnowledgeBase(selectedKbId)
      .then(() => {
        loadKnowledgeBases();
      })
      .catch((selectError: unknown) => setKbError(errorMessage(selectError)))
      .finally(() => setSelectingKb(false));
  };

  const onToggleKnowledgeBasePin = () => {
    if (!selectedKbId || pinningKb) {
      return;
    }
    setPinningKb(true);
    setKbError(null);
    setKbActionNotice(null);
    apiClient
      .toggleNativeKnowledgeBasePin(selectedKbId, NATIVE_KB_CONFIRM_PHRASE)
      .then((response) => {
        if (!mutationSucceeded(response, "pin_toggle")) {
          setKbError(response.warnings[0] ?? "知识库置顶状态未更新，请查看设置与调试中的 Native 状态。");
          return;
        }
        const pinnedKb = mutationKnowledgeBase(response, "pin_toggle");
        setKbActionNotice(pinnedKb?.is_pinned ? "知识库已置顶" : "已取消置顶");
        loadKnowledgeBases();
      })
      .catch((pinError: unknown) => setKbError(errorMessage(pinError)))
      .finally(() => setPinningKb(false));
  };

  const onDeleteKnowledgeBase = () => {
    if (!selectedKbId || deletingKb) {
      return;
    }
    const label = selectedKb?.name || selectedKbId;
    const activeHint = selectedKbId === activeKbId ? "当前活动知识库会被一并删除。" : "";
    if (
      !window.confirm(
        `确认删除知识库「${label}」？${activeHint}该操作会删除 WeKnora 原生知识库及其资料，不能撤销。`,
      )
    ) {
      return;
    }
    setDeletingKb(true);
    setKbError(null);
    setKbActionNotice(null);
    apiClient
      .deleteNativeKnowledgeBase(selectedKbId, NATIVE_KB_CONFIRM_PHRASE)
      .then((response) => {
        const deleteSurface = response.surfaces.delete;
        if (response.status !== "live" || deleteSurface?.deleted !== true) {
          setKbError(response.warnings[0] ?? "知识库删除未完成，请查看设置与调试中的 Native 状态。");
          return;
        }
        setKbActionNotice("知识库已删除");
        setSelectedKbId("");
        loadKnowledgeBases();
      })
      .catch((deleteError: unknown) => setKbError(errorMessage(deleteError)))
      .finally(() => setDeletingKb(false));
  };

  const loadPreview = (documentId: string, chunkId: string | null = null) => {
    setPreviewDocumentId(documentId);
    setTargetChunkId(chunkId);
    setChunkLoadState("loading");
    setChunkError(null);
    setEditingChunkId(null);
    setChunkDraft("");
    setSimilarResults({});
    setEventLoadState("loading");
    setEventError(null);
    apiClient
      .listDocumentChunks(documentId)
      .then((response) => {
        setChunks(response.items);
        setChunkLoadState("idle");
      })
      .catch((chunkLoadError: unknown) => {
        setChunks([]);
        setChunkError(errorMessage(chunkLoadError));
        setChunkLoadState("error");
      });
    apiClient
      .getDocumentSpans(documentId)
      .then((response) => {
        setSpans(response);
      })
      .catch(() => {
        setSpans(null);
      });
    apiClient
      .listDocumentEvents(documentId)
      .then((response) => {
        setEvents(response.items.slice(-6).reverse());
        setEventLoadState("idle");
      })
      .catch((eventLoadError: unknown) => {
        setEvents([]);
        setEventError(errorMessage(eventLoadError));
        setEventLoadState("error");
      });
  };

  const onRecoverDocument = (documentId: string) => {
    setReindexingId(documentId);
    setError(null);
    apiClient
      .retryDocumentProcessing(documentId)
      .then((response) => {
        setDocuments((current) =>
          current.map((document) =>
            document.id === documentId ? response.document : document,
          ),
        );
        if (previewDocumentId === documentId) {
          loadPreview(documentId);
        }
      })
      .catch((reindexError: unknown) => setError(errorMessage(reindexError)))
      .finally(() => setReindexingId(null));
  };

  const updateDocument = (nextDocument: Document) => {
    setDocuments((current) =>
      current.map((document) =>
        document.id === nextDocument.id ? nextDocument : document,
      ),
    );
  };

  const onRefreshChunk = (documentId: string, chunkId: string) => {
    setChunkActionId(chunkId);
    setChunkError(null);
    setChunkAuditNotice(null);
    apiClient
      .getDocumentChunk(documentId, chunkId)
      .then((chunk) => {
        setChunks((current) =>
          current.map((item) => (item.id === chunk.id ? chunk : item)),
        );
        setTargetChunkId(chunk.id);
      })
      .catch((chunkErrorResponse: unknown) => setChunkError(errorMessage(chunkErrorResponse)))
      .finally(() => setChunkActionId(null));
  };

  const onToggleChunk = (documentId: string, chunk: DocumentChunk) => {
    const nextEnabled = !chunkIsEnabled(chunk);
    setChunkActionId(chunk.id);
    setChunkError(null);
    setChunkAuditNotice(null);
    apiClient
      .setDocumentChunkEnabled(documentId, chunk.id, nextEnabled)
      .then((response) => {
        setChunkAuditNotice(chunkAuditMessage(response));
        updateDocument(response.document);
        if (response.chunk) {
          setChunks((current) =>
            current.map((item) => (item.id === response.chunk?.id ? response.chunk : item)),
          );
        }
        loadPreview(documentId, chunk.id);
      })
      .catch((chunkErrorResponse: unknown) => setChunkError(errorMessage(chunkErrorResponse)))
      .finally(() => setChunkActionId(null));
  };

  const onStartEditChunk = (chunk: DocumentChunk) => {
    setEditingChunkId(chunk.id);
    setChunkDraft(chunk.content);
    setTargetChunkId(chunk.id);
    setChunkError(null);
  };

  const onCancelEditChunk = () => {
    setEditingChunkId(null);
    setChunkDraft("");
  };

  const onSaveChunkContent = (documentId: string, chunk: DocumentChunk) => {
    const nextContent = chunkDraft.trim();
    if (!nextContent) {
      setChunkError("分块内容不能为空。");
      return;
    }
    if (nextContent === chunk.content.trim()) {
      onCancelEditChunk();
      return;
    }
    setChunkActionId(chunk.id);
    setChunkError(null);
    setChunkAuditNotice(null);
    apiClient
      .rewriteDocumentChunkContent(documentId, chunk.id, nextContent)
      .then((response) => {
        setChunkAuditNotice(chunkAuditMessage(response));
        updateDocument(response.document);
        if (response.chunk) {
          setChunks((current) =>
            current.map((item) => (item.id === response.chunk?.id ? response.chunk : item)),
          );
        }
        setEditingChunkId(null);
        setChunkDraft("");
        loadPreview(documentId, chunk.id);
      })
      .catch((chunkErrorResponse: unknown) => setChunkError(errorMessage(chunkErrorResponse)))
      .finally(() => setChunkActionId(null));
  };

  const onSearchSimilarChunks = (documentId: string, chunk: DocumentChunk) => {
    setChunkActionId(chunk.id);
    setChunkError(null);
    apiClient
      .searchSimilarDocumentChunks(documentId, chunk.id, 5)
      .then((response) => {
        setTargetChunkId(chunk.id);
        setSimilarResults((current) => ({
          ...current,
          [chunk.id]: response.items,
        }));
        setChunkAuditNotice(`相似分块：${response.total}`);
      })
      .catch((chunkErrorResponse: unknown) => setChunkError(errorMessage(chunkErrorResponse)))
      .finally(() => setChunkActionId(null));
  };

  const onDeleteGeneratedQuestion = (
    documentId: string,
    chunk: DocumentChunk,
    questionId: string,
  ) => {
    if (!questionId || !window.confirm("确认删除这个生成问题？")) {
      return;
    }
    setChunkActionId(chunk.id);
    setChunkError(null);
    setChunkAuditNotice(null);
    apiClient
      .deleteGeneratedQuestion(documentId, chunk.id, questionId)
      .then((response) => {
        setChunkAuditNotice(chunkAuditMessage(response));
        updateDocument(response.document);
        if (response.chunk) {
          setChunks((current) =>
            current.map((item) => (item.id === response.chunk?.id ? response.chunk : item)),
          );
        }
        loadPreview(documentId, chunk.id);
      })
      .catch((chunkErrorResponse: unknown) => setChunkError(errorMessage(chunkErrorResponse)))
      .finally(() => setChunkActionId(null));
  };

  const onDeleteChunk = (documentId: string, chunk: DocumentChunk) => {
    if (!window.confirm("确认删除这个 WeKnora 分块？")) {
      return;
    }
    setChunkActionId(chunk.id);
    setChunkError(null);
    setChunkAuditNotice(null);
    apiClient
      .deleteDocumentChunk(documentId, chunk.id)
      .then((response) => {
        setChunkAuditNotice(chunkAuditMessage(response));
        updateDocument(response.document);
        setChunks((current) => current.filter((item) => item.id !== chunk.id));
        loadPreview(documentId);
      })
      .catch((chunkErrorResponse: unknown) => setChunkError(errorMessage(chunkErrorResponse)))
      .finally(() => setChunkActionId(null));
  };

  const onLifecycleAction = (
    document: Document,
    action: "reparse" | "cancel" | "delete",
  ) => {
    if (action === "delete" && !window.confirm("确认提交 WeKnora 删除任务？")) {
      return;
    }
    setLifecycleActionId(document.id);
    setError(null);
    const requestPromise =
      action === "reparse"
        ? apiClient.reparseNativeDocument(document.id)
        : action === "cancel"
          ? apiClient.cancelDocumentProcessing(document.id)
          : apiClient.deleteDocument(document.id);
    requestPromise
      .then((response) => {
        if (action === "delete") {
          setDocuments((current) => current.filter((item) => item.id !== document.id));
          if (previewDocumentId === document.id) {
            setPreviewDocumentId(null);
            setChunks([]);
            setEvents([]);
            setSpans(null);
          }
          loadKnowledgeBases();
          return;
        }
        updateDocument(response.document);
        if (previewDocumentId === document.id) {
          loadPreview(document.id, targetChunkId);
        }
      })
      .catch((actionError: unknown) => setError(errorMessage(actionError)))
      .finally(() => setLifecycleActionId(null));
  };

  const openNativeFile = (document: Document, mode: "preview" | "download") => {
    const url =
      mode === "preview"
        ? apiClient.documentPreviewUrl(document.id)
        : apiClient.documentDownloadUrl(document.id);
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const onRefreshStatuses = () => {
    setIsRefreshingStatuses(true);
    setError(null);
    apiClient
      .refreshDocumentStatuses(buildDocumentFilters(filters))
      .then((response) => {
        applyDocumentItems(response.items);
      })
      .catch((refreshError: unknown) => setError(errorMessage(refreshError)))
      .finally(() => setIsRefreshingStatuses(false));
  };

  return (
    <div className="library-page">
      <section className="library-summary" aria-label="资料库概览">
        <div className="library-stat">
          <span>总资料</span>
          <strong>{documents.length}</strong>
        </div>
        <div className="library-stat">
          <span>已索引</span>
          <strong>{indexedCount}</strong>
        </div>
        <div className="library-stat">
          <span>处理中</span>
          <strong>{processingCount}</strong>
        </div>
        <div className="library-stat">
          <span>失败</span>
          <strong>{failedCount}</strong>
        </div>
      </section>

      <section className="library-grid">
        <div className="library-side">
          <section className="kb-management-panel" aria-label="知识库管理">
            <div className="library-panel-heading">
              <div>
                <span>知识库</span>
                <strong>知识库管理</strong>
              </div>
              <div className="library-heading-actions">
                <button
                  className="icon-button"
                  type="button"
                  onClick={loadKnowledgeBases}
                  title="刷新知识库"
                >
                  <RefreshCw size={16} aria-hidden="true" />
                </button>
                <button
                  className="secondary-action compact"
                  type="button"
                  onClick={onStartCreateKnowledgeBase}
                  disabled={knowledgeBaseActionsDisabled}
                >
                  <Plus size={16} aria-hidden="true" />
                  <span>新建</span>
                </button>
              </div>
            </div>

            <div className="kb-selector" aria-label="知识库选择">
              <label>
                <span>管理对象</span>
                <select
                  value={selectedKbId}
                  onChange={(event) => {
                    setSelectedKbId(event.target.value);
                    setKbFormOpen(false);
                  }}
                  disabled={kbLoadState === "loading" || knowledgeBaseActionsDisabled}
                >
                  {kbOverview?.items.length ? (
                    kbOverview.items.map((item) => (
                      <option value={item.id ?? ""} key={item.id ?? item.name ?? "unknown"}>
                        {knowledgeBaseShortLabel(item)}
                      </option>
                    ))
                  ) : (
                    <option value="">暂无知识库</option>
                  )}
                </select>
              </label>

              {selectedKb ? (
                <div className="kb-selected-card">
                  <div className="kb-selected-title">
                    <strong>{knowledgeBaseShortLabel(selectedKb)}</strong>
                    <span className={selectedKbId === activeKbId ? "active" : ""}>
                      {selectedKbId === activeKbId ? "当前活动" : "未设为当前"}
                    </span>
                  </div>
                  <p>{selectedKb.description || "暂无描述"}</p>
                  <div className="kb-quick-metrics">
                    <span>{`${selectedKb.knowledge_count ?? 0} 个资料`}</span>
                    <span>{`${selectedKb.processing_count ?? 0} 个处理中`}</span>
                    <span>{selectedKb.is_pinned ? "已置顶" : "未置顶"}</span>
                  </div>
                  <details className="kb-advanced-details">
                    <summary>技术信息</summary>
                    <div>
                      <span>{`类型：${selectedKb.type || "document"}`}</span>
                      <span>{`分块：${selectedKb.chunk_count ?? 0}`}</span>
                      <span>{`来源：${selectedKb.source || "weknora_api"}`}</span>
                      <span>
                        {`向量：${String(selectedKb.vector_store?.status ?? "默认")}`}
                      </span>
                    </div>
                  </details>
                </div>
              ) : (
                <EmptyState text="暂无知识库" compact />
              )}

              {kbError ? <ErrorState message={kbError} /> : null}
              {kbActionNotice ? <div className="kb-action-notice">{kbActionNotice}</div> : null}

              <div className="kb-action-row">
                <button
                  className="secondary-action compact"
                  type="button"
                  onClick={onSelectKnowledgeBase}
                  disabled={
                    !selectedKbId ||
                    selectedKbId === activeKbId ||
                    knowledgeBaseActionsDisabled
                  }
                >
                  {selectingKb ? <Loader2 size={16} aria-hidden="true" /> : <Database size={16} />}
                  <span>{selectedKbId === activeKbId ? "当前活动" : "设为当前"}</span>
                </button>
                <button
                  className="secondary-action compact"
                  type="button"
                  onClick={onStartEditKnowledgeBase}
                  disabled={!selectedKbId || knowledgeBaseActionsDisabled}
                >
                  <Edit3 size={16} aria-hidden="true" />
                  <span>命名</span>
                </button>
                <button
                  className="secondary-action compact"
                  type="button"
                  onClick={onToggleKnowledgeBasePin}
                  disabled={!selectedKbId || knowledgeBaseActionsDisabled}
                >
                  {pinningKb ? <Loader2 size={16} aria-hidden="true" /> : <Pin size={16} />}
                  <span>{selectedKb?.is_pinned ? "取消置顶" : "置顶"}</span>
                </button>
                <button
                  className="secondary-action compact danger"
                  type="button"
                  onClick={onDeleteKnowledgeBase}
                  disabled={!selectedKbId || knowledgeBaseActionsDisabled}
                >
                  {deletingKb ? <Loader2 size={16} aria-hidden="true" /> : <Trash2 size={16} />}
                  <span>{deletingKb ? "删除中" : "删除"}</span>
                </button>
              </div>

              {kbFormOpen ? (
                <form className="kb-edit-form" onSubmit={onSaveKnowledgeBase}>
                  <label>
                    <span>{kbFormMode === "create" ? "新知识库名称" : "知识库名称"}</span>
                    <input
                      value={kbDraft.name}
                      onChange={(event) =>
                        setKbDraft((current) => ({ ...current, name: event.target.value }))
                      }
                      placeholder="例如：部门制度知识库"
                    />
                  </label>
                  <label>
                    <span>描述</span>
                    <textarea
                      value={kbDraft.description}
                      onChange={(event) =>
                        setKbDraft((current) => ({
                          ...current,
                          description: event.target.value,
                        }))
                      }
                      placeholder="可选，用来区分资料范围"
                    />
                  </label>
                  <div className="kb-form-actions">
                    <button className="secondary-action compact" type="submit" disabled={savingKb}>
                      {savingKb ? <Loader2 size={16} aria-hidden="true" /> : <Save size={16} />}
                      <span>{savingKb ? "保存中" : "保存"}</span>
                    </button>
                    <button
                      className="secondary-action compact"
                      type="button"
                      onClick={onCancelKnowledgeBaseForm}
                      disabled={savingKb}
                    >
                      <X size={16} aria-hidden="true" />
                      <span>取消</span>
                    </button>
                  </div>
                </form>
              ) : null}
            </div>
          </section>

          <form className="upload-panel" onSubmit={onSubmit}>
            <div className="library-panel-heading">
              <span>上传</span>
              <strong>上传资料</strong>
            </div>

            <label className="upload-target-select">
              <span>目标知识库</span>
              <select
                value={selectedKbId}
                onChange={(event) => setSelectedKbId(event.target.value)}
                disabled={kbLoadState === "loading" || knowledgeBaseActionsDisabled}
              >
                {kbOverview?.items.length ? (
                  kbOverview.items.map((item) => (
                    <option value={item.id ?? ""} key={item.id ?? item.name ?? "unknown"}>
                      {knowledgeBaseShortLabel(item)}
                    </option>
                  ))
                ) : (
                  <option value="">暂无知识库</option>
                )}
              </select>
            </label>

          <div className="ingestion-mode-tabs" aria-label="资料入口">
            <button
              className={ingestionMode === "file" ? "active" : ""}
              type="button"
              onClick={() => setIngestionMode("file")}
              title="文件"
            >
              <Upload size={16} aria-hidden="true" />
              <span>文件</span>
            </button>
            <button
              className={ingestionMode === "url" ? "active" : ""}
              type="button"
              onClick={() => setIngestionMode("url")}
              title="URL"
            >
              <Link size={16} aria-hidden="true" />
              <span>URL</span>
            </button>
            <button
              className={ingestionMode === "manual" ? "active" : ""}
              type="button"
              onClick={() => setIngestionMode("manual")}
              title="手工录入"
            >
              <Keyboard size={16} aria-hidden="true" />
              <span>手工</span>
            </button>
          </div>

          {ingestionMode === "file" ? (
            <label className="file-drop">
              <input type="file" onChange={onFileChange} />
              <Upload size={20} aria-hidden="true" />
              <span>{selectedFile ? selectedFile.name : "选择文件"}</span>
            </label>
          ) : ingestionMode === "url" ? (
            <label className="url-input-row">
              <span>URL</span>
              <input
                value={form.url}
                onChange={(event) => setForm({ ...form, url: event.target.value })}
                placeholder="https://"
              />
            </label>
          ) : (
            <label className="manual-input-row">
              <span>正文</span>
              <textarea
                value={form.manualContent}
                onChange={(event) =>
                  setForm({ ...form, manualContent: event.target.value })
                }
              />
            </label>
          )}

          <div className="form-grid">
            <label>
              <span>标题</span>
              <input
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
              />
            </label>
          </div>

          <details className="advanced-controls library-upload-advanced">
            <summary>高级信息</summary>
            <div className="form-grid advanced-filter-grid">
              <label>
                <span>业务域</span>
                <input
                  value={form.businessArea}
                  onChange={(event) =>
                    setForm({ ...form, businessArea: event.target.value })
                  }
                />
              </label>
              <label>
                <span>类型</span>
                <input
                  value={form.documentType}
                  onChange={(event) =>
                    setForm({ ...form, documentType: event.target.value })
                  }
                />
              </label>
              <label>
                <span>来源</span>
                <input
                  value={form.source}
                  onChange={(event) => setForm({ ...form, source: event.target.value })}
                />
              </label>
            </div>
          </details>

          <button className="primary-action" type="submit" disabled={isUploading}>
            {isUploading ? <Loader2 size={16} aria-hidden="true" /> : <Upload size={16} />}
            <span>{isUploading ? "提交中" : "提交"}</span>
          </button>
          </form>
        </div>

        <section className="documents-panel" aria-label="资料列表">
          <div className="library-panel-heading">
            <span>资料列表</span>
            <div className="library-heading-actions">
              <button
                className="icon-button"
                type="button"
                onClick={loadDocuments}
                title="重新加载列表"
              >
                <RefreshCw size={16} aria-hidden="true" />
              </button>
              <button
                className="secondary-action compact"
                type="button"
                onClick={onRefreshStatuses}
                disabled={isRefreshingStatuses}
              >
                {isRefreshingStatuses ? (
                  <Loader2 size={16} aria-hidden="true" />
                ) : (
                  <RefreshCw size={16} aria-hidden="true" />
                )}
                <span>批量刷新状态</span>
              </button>
            </div>
          </div>

          <div className="library-filter-bar" aria-label="资料筛选">
            <label>
              <span>知识库</span>
              <select
                value={filters.knowledgeBaseId}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    knowledgeBaseId: event.target.value,
                  }))
                }
                disabled={kbLoadState === "loading"}
              >
                <option value="all">全部知识库</option>
                {kbOverview?.items
                  .filter((item) => item.id)
                  .map((item) => (
                    <option value={item.id ?? ""} key={item.id ?? item.name ?? "unknown"}>
                      {knowledgeBaseShortLabel(item)}
                    </option>
                  ))}
                <option value="__unassigned__">未归类</option>
              </select>
            </label>
            <label>
              <span>状态</span>
              <select
                value={filters.status}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, status: event.target.value }))
                }
              >
                <option value="all">全部</option>
                <option value="uploaded">已上传</option>
                <option value="processing">处理中</option>
                <option value="indexed">已索引</option>
                <option value="failed">失败</option>
                <option value="unavailable">不可用</option>
              </select>
            </label>
            <details className="advanced-controls library-filter-advanced">
              <summary>高级筛选</summary>
              <label>
                <span>处理来源</span>
                <select
                  value={filters.knowledgeBackend}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      knowledgeBackend: event.target.value,
                    }))
                  }
                >
                  <option value="all">全部</option>
                  <option value="weknora_api">在线知识服务</option>
                  <option value="mock">模拟模式</option>
                  <option value="extracted">本地抽取</option>
                </select>
              </label>
              <label className="library-filter-toggle">
                <input
                  type="checkbox"
                  checked={filters.errorOnly}
                  onChange={(event) =>
                    setFilters((current) => ({ ...current, errorOnly: event.target.checked }))
                  }
                />
                <span>仅错误/不可用</span>
              </label>
            </details>
          </div>

          {error ? <ErrorState message={error} /> : null}

          {loadState === "loading" ? (
            <EmptyState text="加载中" loading />
          ) : documents.length === 0 ? (
            <EmptyState icon={FileText} text="暂无资料" />
          ) : (
            <div className="document-list">
              {documents.map((document) => (
                <article className="document-row" key={document.id}>
                  <div className="document-main">
                    <div className="document-title">
                      <FileText size={16} aria-hidden="true" />
                      <strong>{document.title}</strong>
                      <span className={`document-readiness ${readinessClass(document)}`}>
                        {readinessStatus(document)}
                      </span>
                    </div>
                    <div className="document-meta">
                      <span>{document.business_area || "-"}</span>
                      <span>{document.document_type || "-"}</span>
                      <span>{formatFileSize(document.file_size)}</span>
                      <span>{formatDate(document.created_at)}</span>
                      <span>{`知识库：${documentKnowledgeBaseLabel(document, kbOverview)}`}</span>
                      <span>{backendLabel(document)}</span>
                    </div>
                    <details className="document-advanced">
                      <summary>处理详情</summary>
                      <div className="document-pipeline" aria-label="处理状态">
                        <span className={stageClass(parseStatus(document))}>
                          解析：{parseStatus(document)}
                        </span>
                        <span className={stageClass(chunkStatus(document))}>
                          分块：{chunkStatus(document)}
                        </span>
                        <span className={stageClass(document.embedding_status || "")}>
                          向量：{embeddingStatus(document)}
                        </span>
                        <span className={stageClass(indexStatus(document))}>
                          索引：{indexStatus(document)}
                        </span>
                        <span className={stageClass(readinessStatus(document))}>
                          提问：{statusHint(document)}
                        </span>
                      </div>
                    </details>
                    {document.status === "failed" || document.processing_timed_out ? (
                      <div className="document-error">
                        <span>{document.processing_timed_out ? "处理超时" : stepLabel(document.failed_step)}</span>
                        <strong>
                          {document.error_message || document.processing_message || "处理失败"}
                        </strong>
                      </div>
                    ) : null}
                  </div>

                  <div className="document-actions">
                    <DocumentStatusBadge status={document.status} />
                    <button
                      className="icon-button"
                      type="button"
                      onClick={() => loadPreview(document.id)}
                      title="预览分块"
                    >
                      <Eye size={16} aria-hidden="true" />
                    </button>
                    <button
                      className="icon-button"
                      type="button"
                      onClick={() => openNativeFile(document, "preview")}
                      disabled={!document.external_doc_id || document.knowledge_backend !== "weknora_api"}
                      title="原文预览"
                    >
                      <FileText size={16} aria-hidden="true" />
                    </button>
                    <button
                      className="icon-button"
                      type="button"
                      onClick={() => openNativeFile(document, "download")}
                      disabled={!document.external_doc_id || document.knowledge_backend !== "weknora_api"}
                      title="下载原文"
                    >
                      <Download size={16} aria-hidden="true" />
                    </button>
                    <button
                      className="icon-button"
                      type="button"
                      onClick={() => onRecoverDocument(document.id)}
                      disabled={reindexingId === document.id}
                      title={document.retryable ? "恢复处理" : "刷新/恢复处理"}
                    >
                      {reindexingId === document.id ? (
                        <Loader2 size={16} aria-hidden="true" />
                      ) : (
                        <RotateCcw size={16} aria-hidden="true" />
                      )}
                    </button>
                    <button
                      className="icon-button"
                      type="button"
                      onClick={() => onLifecycleAction(document, "reparse")}
                      disabled={
                        lifecycleActionId === document.id ||
                        !document.external_doc_id ||
                        document.knowledge_backend !== "weknora_api"
                      }
                      title="WeKnora 重解析"
                    >
                      {lifecycleActionId === document.id ? (
                        <Loader2 size={16} aria-hidden="true" />
                      ) : (
                        <RefreshCw size={16} aria-hidden="true" />
                      )}
                    </button>
                    <button
                      className="icon-button"
                      type="button"
                      onClick={() => onLifecycleAction(document, "cancel")}
                      disabled={
                        lifecycleActionId === document.id ||
                        !runningStatuses.has(document.status) ||
                        document.status === "deleting" ||
                        !document.external_doc_id ||
                        document.knowledge_backend !== "weknora_api"
                      }
                      title="取消解析"
                    >
                      <XCircle size={16} aria-hidden="true" />
                    </button>
                    <button
                      className="icon-button danger"
                      type="button"
                      onClick={() => onLifecycleAction(document, "delete")}
                      disabled={
                        lifecycleActionId === document.id ||
                        document.status === "deleting" ||
                        !document.external_doc_id ||
                        document.knowledge_backend !== "weknora_api"
                      }
                      title="删除"
                    >
                      <Trash2 size={16} aria-hidden="true" />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}

          {previewDocument ? (
            <section className="chunk-preview-panel" aria-label="Chunk 预览">
              <div className="chunk-preview-heading">
                <div>
                  <span>分块</span>
                  <strong>{previewDocument.title}</strong>
                  <small>{`${readinessStatus(previewDocument)} · ${backendLabel(previewDocument)}`}</small>
                </div>
                <button
                  className="icon-button"
                  type="button"
                  onClick={() => loadPreview(previewDocument.id, targetChunkId)}
                  title="刷新分块"
                >
                  <RefreshCw size={16} aria-hidden="true" />
                </button>
              </div>

              {chunkError ? <ErrorState message={chunkError} /> : null}

              <div className="document-preview-status">
                <span className={readinessClass(previewDocument)}>
                  {statusHint(previewDocument)}
                </span>
                {spans?.current_stage ? <span>{`阶段：${spans.current_stage}`}</span> : null}
                {spans?.current_attempt ? <span>{`尝试：${spans.current_attempt}`}</span> : null}
                <span>{`分块：${previewDocument.chunk_count}`}</span>
                <span>{`已索引：${previewDocument.indexed_chunk_count}`}</span>
                <span>{`待处理：${previewDocument.pending_chunk_count}`}</span>
                <span>{`失败：${previewDocument.failed_chunk_count}`}</span>
                {chunkAuditNotice ? <span>{chunkAuditNotice}</span> : null}
              </div>

              {chunkLoadState === "loading" ? (
                <EmptyState text="加载分块" loading compact />
              ) : chunks.length === 0 ? (
                <EmptyState text={chunkEmptyText(previewDocument)} compact />
              ) : (
                <div className="chunk-preview-list">
                  {chunks.map((chunk) => {
                    const isEditing = editingChunkId === chunk.id;
                    const currentSimilarResults = similarResults[chunk.id] || [];
                    return (
                    <article
                      className={
                        chunkMatchesTarget(chunk, targetChunkId)
                          ? "chunk-preview-item located"
                          : "chunk-preview-item"
                      }
                      id={chunkDomId(chunk)}
                      key={chunk.id}
                    >
                      <div className="chunk-preview-title">
                        <strong>#{chunk.chunk_index}</strong>
                        <span>{chunk.embedding_status}</span>
                        <span>{chunkIsEnabled(chunk) ? "已启用" : "已禁用"}</span>
                        <span>{chunk.source}</span>
                        <span>{`生成问题：${generatedQuestions(chunk).length}`}</span>
                      </div>
                      {isEditing ? (
                        <textarea
                          className="chunk-edit-textarea"
                          value={chunkDraft}
                          onChange={(event) => setChunkDraft(event.target.value)}
                          rows={6}
                        />
                      ) : (
                        <p>{chunkExcerpt(chunk.content)}</p>
                      )}
                      {generatedQuestions(chunk).length > 0 ? (
                        <div className="chunk-generated-questions">
                          {generatedQuestions(chunk)
                            .slice(0, 3)
                            .map((question) => (
                              <span className="chunk-generated-question" key={question.id || question.question}>
                                <span>{question.question || question.id}</span>
                                {question.id ? (
                                  <button
                                    className="inline-icon-button"
                                    type="button"
                                    onClick={() =>
                                      onDeleteGeneratedQuestion(
                                        previewDocument.id,
                                        chunk,
                                        question.id || "",
                                      )
                                    }
                                    disabled={
                                      chunkActionId === chunk.id ||
                                      previewDocument.knowledge_backend !== "weknora_api"
                                    }
                                    title="删除生成问题"
                                  >
                                    <X size={12} aria-hidden="true" />
                                  </button>
                                ) : null}
                              </span>
                            ))}
                        </div>
                      ) : null}
                      <div className="chunk-preview-meta">
                        <span>{chunkLocation(chunk)}</span>
                        <span>{chunk.token_count} 个词元</span>
                        <span>{chunk.char_count} 个字符</span>
                        {chunk.external_doc_id ? <span>{chunk.external_doc_id}</span> : null}
                        <a
                          href={`#/library?document=${previewDocument.id}&chunk=${chunk.id}`}
                          onClick={() => setTargetChunkId(chunk.id)}
                        >
                          定位
                        </a>
                      </div>
                      <div className="chunk-preview-actions" aria-label="分块操作">
                        <button
                          className="icon-button"
                          type="button"
                          onClick={() => onRefreshChunk(previewDocument.id, chunk.id)}
                          disabled={chunkActionId === chunk.id}
                          title="读取分块详情"
                        >
                          <RefreshCw size={15} aria-hidden="true" />
                        </button>
                        {isEditing ? (
                          <>
                            <button
                              className="icon-button"
                              type="button"
                              onClick={() => onSaveChunkContent(previewDocument.id, chunk)}
                              disabled={
                                chunkActionId === chunk.id ||
                                previewDocument.knowledge_backend !== "weknora_api"
                              }
                              title="保存分块内容"
                            >
                              <Save size={15} aria-hidden="true" />
                            </button>
                            <button
                              className="icon-button"
                              type="button"
                              onClick={onCancelEditChunk}
                              disabled={chunkActionId === chunk.id}
                              title="取消编辑"
                            >
                              <X size={15} aria-hidden="true" />
                            </button>
                          </>
                        ) : (
                          <button
                            className="icon-button"
                            type="button"
                            onClick={() => onStartEditChunk(chunk)}
                            disabled={
                              chunkActionId === chunk.id ||
                              previewDocument.knowledge_backend !== "weknora_api"
                            }
                            title="编辑分块内容"
                          >
                            <Edit3 size={15} aria-hidden="true" />
                          </button>
                        )}
                        <button
                          className="icon-button"
                          type="button"
                          onClick={() => onSearchSimilarChunks(previewDocument.id, chunk)}
                          disabled={
                            chunkActionId === chunk.id ||
                            previewDocument.knowledge_backend !== "weknora_api"
                          }
                          title="搜索相似分块"
                        >
                          <Search size={15} aria-hidden="true" />
                        </button>
                        <button
                          className="icon-button"
                          type="button"
                          onClick={() => onToggleChunk(previewDocument.id, chunk)}
                          disabled={
                            chunkActionId === chunk.id ||
                            previewDocument.knowledge_backend !== "weknora_api"
                          }
                          title={chunkIsEnabled(chunk) ? "禁用分块" : "启用分块"}
                        >
                          {chunkIsEnabled(chunk) ? (
                            <ToggleRight size={16} aria-hidden="true" />
                          ) : (
                            <ToggleLeft size={16} aria-hidden="true" />
                          )}
                        </button>
                        <button
                          className="icon-button danger"
                          type="button"
                          onClick={() => onDeleteChunk(previewDocument.id, chunk)}
                          disabled={
                            chunkActionId === chunk.id ||
                            previewDocument.knowledge_backend !== "weknora_api"
                          }
                          title="删除分块"
                        >
                          <Trash2 size={15} aria-hidden="true" />
                        </button>
                      </div>
                      {currentSimilarResults.length > 0 ? (
                        <div className="chunk-similar-results">
                          {currentSimilarResults.slice(0, 3).map((result) => (
                            <div className="chunk-similar-result" key={`${chunk.id}-${result.id}`}>
                              <span>{`#${result.chunk_index} · ${result.score.toFixed(3)}`}</span>
                              <p>{chunkExcerpt(result.content, 180)}</p>
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </article>
                    );
                  })}
                </div>
              )}

              <section className="document-event-panel" aria-label="处理事件">
                <div className="document-event-heading">
                  <span>事件</span>
                  <strong>最近处理事件</strong>
                </div>
                {eventError ? <ErrorState message={eventError} /> : null}
                {eventLoadState === "loading" ? (
                  <EmptyState text="加载事件" loading compact />
                ) : events.length === 0 ? (
                  <EmptyState text="暂无事件" compact />
                ) : (
                  <div className="document-event-list">
                    {events.map((event) => (
                      <div className={`document-event-item ${event.status}`} key={event.id}>
                        <span>{formatDate(event.created_at)}</span>
                        <strong>{eventLabel(event)}</strong>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </section>
          ) : null}
        </section>
      </section>
    </div>
  );
}
