import {
  Database,
  Download,
  Eye,
  FileText,
  Keyboard,
  Link,
  Loader2,
  Pin,
  RefreshCw,
  RotateCcw,
  Trash2,
  Upload,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

import {
  ApiError,
  Document,
  DocumentChunk,
  DocumentSpansResponse,
  DocumentProcessingEvent,
  NativeKnowledgeBaseItem,
  NativeKnowledgeBaseOverviewResponse,
  apiClient,
} from "../api/client";
import {
  DocumentStatusBadge,
  EmptyState,
  ErrorState,
  WeKnoraFirstStatusStrip,
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
  errorOnly: boolean;
};

type LoadState = "idle" | "loading" | "error";
type ChunkLoadState = "idle" | "loading" | "error";
type EventLoadState = "idle" | "loading" | "error";
type KnowledgeBaseLoadState = "idle" | "loading" | "error";
type IngestionMode = "file" | "url" | "manual";

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
  errorOnly: false,
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

function knowledgeBaseLabel(item: NativeKnowledgeBaseItem) {
  const name = item.name || item.id || "未命名知识库";
  const type = item.type ? ` · ${item.type}` : "";
  const count = item.knowledge_count === null ? "" : ` · ${item.knowledge_count} 个资料`;
  return `${name}${type}${count}`;
}

function activeKnowledgeBaseLabel(overview: NativeKnowledgeBaseOverviewResponse | null) {
  const active = overview?.active_selection;
  if (!active) {
    return "未验证活动知识库";
  }
  return active.name || active.kb_id || "活动知识库";
}

function buildDocumentFilters(filters: LibraryFilters) {
  return {
    status: filters.status,
    knowledge_backend: filters.knowledgeBackend,
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
  const [events, setEvents] = useState<DocumentProcessingEvent[]>([]);
  const [eventLoadState, setEventLoadState] = useState<EventLoadState>("idle");
  const [eventError, setEventError] = useState<string | null>(null);
  const [targetChunkId, setTargetChunkId] = useState<string | null>(null);
  const [kbOverview, setKbOverview] = useState<NativeKnowledgeBaseOverviewResponse | null>(null);
  const [kbLoadState, setKbLoadState] = useState<KnowledgeBaseLoadState>("idle");
  const [kbError, setKbError] = useState<string | null>(null);
  const [selectedKbId, setSelectedKbId] = useState("");
  const [selectingKb, setSelectingKb] = useState(false);

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

  const applyHashTarget = (nextDocuments: Document[]) => {
    const target = libraryHashTarget();
    if (!target.documentId) {
      return;
    }
    if (nextDocuments.some((document) => document.id === target.documentId)) {
      loadPreview(target.documentId, target.chunkId);
    }
  };

  const loadDocuments = () => {
    setLoadState("loading");
    setError(null);
    apiClient
      .listDocuments(buildDocumentFilters(filters))
      .then((response) => {
        setDocuments(response.items);
        if (
          previewDocumentId &&
          !response.items.some((document) => document.id === previewDocumentId)
        ) {
          setPreviewDocumentId(null);
          setChunks([]);
          setEvents([]);
          setSpans(null);
        }
        applyHashTarget(response.items);
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
      })
      .catch((loadError: unknown) => {
        setKbError(errorMessage(loadError));
        setKbLoadState("error");
      });
  };

  useEffect(() => {
    loadDocuments();
  }, [filters.status, filters.knowledgeBackend, filters.errorOnly]);

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
      .then((response) => {
        setDocuments((current) => [response.document, ...current]);
        setSelectedFile(null);
        setForm(initialForm);
      })
      .catch((uploadError: unknown) => setError(errorMessage(uploadError)))
      .finally(() => setIsUploading(false));
  };

  const onSelectKnowledgeBase = () => {
    if (!selectedKbId || selectedKbId === activeKbId) {
      return;
    }
    setSelectingKb(true);
    setKbError(null);
    apiClient
      .selectActiveKnowledgeBase(selectedKbId)
      .then(() => {
        loadKnowledgeBases();
      })
      .catch((selectError: unknown) => setKbError(errorMessage(selectError)))
      .finally(() => setSelectingKb(false));
  };

  const loadPreview = (documentId: string, chunkId: string | null = null) => {
    setPreviewDocumentId(documentId);
    setTargetChunkId(chunkId);
    setChunkLoadState("loading");
    setChunkError(null);
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
        setDocuments(response.items);
        if (
          previewDocumentId &&
          !response.items.some((document) => document.id === previewDocumentId)
        ) {
          setPreviewDocumentId(null);
          setChunks([]);
          setEvents([]);
          setSpans(null);
        }
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
        <div className="library-stat">
          <span>后端</span>
          <strong>{documents[0]?.knowledge_backend ?? "mock"}</strong>
        </div>
      </section>

      <WeKnoraFirstStatusStrip page="资料库" />

      <section className="library-grid">
        <form className="upload-panel" onSubmit={onSubmit}>
          <div className="library-panel-heading">
            <span>上传</span>
            <strong>上传资料</strong>
          </div>

          <section className="kb-selector" aria-label="知识库选择">
            <div className="kb-selector-heading">
              <Database size={16} aria-hidden="true" />
              <div>
                <span>活动知识库</span>
                <strong>{activeKnowledgeBaseLabel(kbOverview)}</strong>
              </div>
            </div>
            <label>
              <span>上传目标</span>
              <select
                value={selectedKbId}
                onChange={(event) => setSelectedKbId(event.target.value)}
                disabled={kbLoadState === "loading" || selectingKb}
              >
                {kbOverview?.items.map((item) => (
                  <option value={item.id ?? ""} key={item.id ?? item.name ?? "unknown"}>
                    {knowledgeBaseLabel(item)}
                  </option>
                ))}
              </select>
            </label>
            <div className="kb-selector-meta">
              <span>{kbLoadState === "loading" ? "加载中" : `${kbOverview?.total ?? 0} 个 KB`}</span>
              <span>{selectedKb?.is_pinned ? "已置顶" : "未置顶"}</span>
              <span>{selectedKb?.vector_store?.status ? `向量：${String(selectedKb.vector_store.status)}` : "向量：未知"}</span>
            </div>
            {kbError ? <ErrorState message={kbError} /> : null}
            <button
              className="secondary-action compact"
              type="button"
              onClick={onSelectKnowledgeBase}
              disabled={!selectedKbId || selectedKbId === activeKbId || selectingKb}
            >
              {selectingKb ? <Loader2 size={16} aria-hidden="true" /> : <Pin size={16} />}
              <span>{selectedKbId === activeKbId ? "当前活动" : "设为活动"}</span>
            </button>
          </section>

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

          <button className="primary-action" type="submit" disabled={isUploading}>
            {isUploading ? <Loader2 size={16} aria-hidden="true" /> : <Upload size={16} />}
            <span>{isUploading ? "提交中" : "提交"}</span>
          </button>
        </form>

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
            <label>
              <span>后端</span>
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
                <option value="weknora_api">WeKnora</option>
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
                      <span>{backendLabel(document)}</span>
                    </div>
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
              </div>

              {chunkLoadState === "loading" ? (
                <EmptyState text="加载分块" loading compact />
              ) : chunks.length === 0 ? (
                <EmptyState text={chunkEmptyText(previewDocument)} compact />
              ) : (
                <div className="chunk-preview-list">
                  {chunks.map((chunk) => (
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
                        <span>{chunk.source}</span>
                      </div>
                      <p>{chunkExcerpt(chunk.content)}</p>
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
                    </article>
                  ))}
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
