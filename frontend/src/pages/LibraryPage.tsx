import {
  Eye,
  FileText,
  Loader2,
  RefreshCw,
  RotateCcw,
  Upload,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

import {
  ApiError,
  Document,
  DocumentChunk,
  DocumentProcessingEvent,
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
};

type LoadState = "idle" | "loading" | "error";
type ChunkLoadState = "idle" | "loading" | "error";
type EventLoadState = "idle" | "loading" | "error";

const initialForm: LibraryForm = {
  title: "",
  businessArea: "",
  documentType: "",
  source: "manual",
};

const runningStatuses = new Set(["uploaded", "parsing", "chunking", "embedding", "indexing"]);
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
  return "Unknown error";
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
    return `${document.chunk_count} chunks`;
  }
  return "待分块";
}

function embeddingStatus(document: Document) {
  if (document.embedding_status === "indexed") {
    return `${document.indexed_chunk_count}/${document.chunk_count} embedded`;
  }
  if (document.embedding_status === "partial") {
    return `${document.indexed_chunk_count}/${document.chunk_count} embedding`;
  }
  if (document.embedding_status === "failed") {
    return "embedding 失败";
  }
  if (document.status === "indexing" || document.embedding_status === "pending") {
    return "embedding 中";
  }
  return "待 embedding";
}

function indexStatus(document: Document) {
  if (document.status === "indexed") {
    return "已索引";
  }
  if (document.status === "indexing") {
    return "索引中";
  }
  if (document.status === "failed" && document.failed_step === "index") {
    return "索引失败";
  }
  if (document.status === "failed" && document.failed_step === "embedding") {
    return "embedding 失败";
  }
  if (document.status === "embedding") {
    return "embedding 中";
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
    return document.processing_message;
  }
  if (document.status === "failed") {
    return document.failed_step
      ? `失败位置：${stepLabel(document.failed_step)}`
      : "处理失败";
  }
  if (document.status === "indexed") {
    return document.chunk_count > 0
      ? `${document.chunk_count} chunks ready`
      : "索引完成，等待 chunk preview";
  }
  if (document.status === "indexing") {
    return "索引完成后可提问";
  }
  if (document.status === "embedding") {
    return "embedding 完成后进入索引";
  }
  if (document.status === "chunking") {
    return "分块完成后进入索引";
  }
  if (document.status === "parsing") {
    return "解析完成后进入分块";
  }
  return "等待 WeKnora/本地流程处理";
}

function backendLabel(document: Document) {
  return document.knowledge_backend === "weknora_api" ? "WeKnora" : document.knowledge_backend;
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
      return "Embedding";
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
    return "WeKnora chunks";
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
  return `${normalized.slice(0, maxChars)}[truncated]`;
}

function chunkLocation(chunk: DocumentChunk) {
  const parts = [
    chunk.page_number === null ? null : `p.${chunk.page_number}`,
    chunk.start_char === null || chunk.end_char === null
      ? null
      : `${chunk.start_char}-${chunk.end_char}`,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "no offsets";
}

function chunkEmptyText(document: Document) {
  if (document.status === "failed") {
    return "处理失败，暂无 chunks";
  }
  if (document.status !== "indexed") {
    return "索引完成后显示 chunks";
  }
  return "暂无 chunks";
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
  const [form, setForm] = useState<LibraryForm>(initialForm);
  const [isUploading, setIsUploading] = useState(false);
  const [reindexingId, setReindexingId] = useState<string | null>(null);
  const [previewDocumentId, setPreviewDocumentId] = useState<string | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [chunkLoadState, setChunkLoadState] = useState<ChunkLoadState>("idle");
  const [chunkError, setChunkError] = useState<string | null>(null);
  const [events, setEvents] = useState<DocumentProcessingEvent[]>([]);
  const [eventLoadState, setEventLoadState] = useState<EventLoadState>("idle");
  const [eventError, setEventError] = useState<string | null>(null);
  const [targetChunkId, setTargetChunkId] = useState<string | null>(null);

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
      .listDocuments()
      .then((response) => {
        setDocuments(response.items);
        if (
          previewDocumentId &&
          !response.items.some((document) => document.id === previewDocumentId)
        ) {
          setPreviewDocumentId(null);
          setChunks([]);
          setEvents([]);
        }
        applyHashTarget(response.items);
        setLoadState("idle");
      })
      .catch((loadError: unknown) => {
        setError(errorMessage(loadError));
        setLoadState("error");
      });
  };

  useEffect(() => {
    loadDocuments();
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
    if (!selectedFile) {
      setError("请选择文件");
      return;
    }

    setIsUploading(true);
    setError(null);
    apiClient
      .uploadDocument({
        file: selectedFile,
        title: form.title.trim() || selectedFile.name,
        business_area: form.businessArea.trim(),
        document_type: form.documentType.trim(),
        source: form.source.trim(),
      })
      .then((response) => {
        setDocuments((current) => [response.document, ...current]);
        setSelectedFile(null);
        setForm(initialForm);
      })
      .catch((uploadError: unknown) => setError(errorMessage(uploadError)))
      .finally(() => setIsUploading(false));
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

      <section className="library-grid">
        <form className="upload-panel" onSubmit={onSubmit}>
          <div className="library-panel-heading">
            <span>Upload</span>
            <strong>上传资料</strong>
          </div>

          <label className="file-drop">
            <input type="file" onChange={onFileChange} />
            <Upload size={20} aria-hidden="true" />
            <span>{selectedFile ? selectedFile.name : "选择文件"}</span>
          </label>

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
            <span>{isUploading ? "上传中" : "上传"}</span>
          </button>
        </form>

        <section className="documents-panel" aria-label="资料列表">
          <div className="library-panel-heading">
            <span>Documents</span>
            <button className="icon-button" type="button" onClick={loadDocuments} title="刷新">
              <RefreshCw size={16} aria-hidden="true" />
            </button>
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
                      title="预览 chunks"
                    >
                      <Eye size={16} aria-hidden="true" />
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
                  </div>
                </article>
              ))}
            </div>
          )}

          {previewDocument ? (
            <section className="chunk-preview-panel" aria-label="Chunk 预览">
              <div className="chunk-preview-heading">
                <div>
                  <span>Chunks</span>
                  <strong>{previewDocument.title}</strong>
                  <small>{`${readinessStatus(previewDocument)} · ${backendLabel(previewDocument)}`}</small>
                </div>
                <button
                  className="icon-button"
                  type="button"
                  onClick={() => loadPreview(previewDocument.id, targetChunkId)}
                  title="刷新 chunks"
                >
                  <RefreshCw size={16} aria-hidden="true" />
                </button>
              </div>

              {chunkError ? <ErrorState message={chunkError} /> : null}

              <div className="document-preview-status">
                <span className={readinessClass(previewDocument)}>
                  {statusHint(previewDocument)}
                </span>
                <span>{`chunks: ${previewDocument.chunk_count}`}</span>
                <span>{`indexed: ${previewDocument.indexed_chunk_count}`}</span>
                <span>{`pending: ${previewDocument.pending_chunk_count}`}</span>
                <span>{`failed: ${previewDocument.failed_chunk_count}`}</span>
              </div>

              {chunkLoadState === "loading" ? (
                <EmptyState text="加载 chunks" loading compact />
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
                        <span>{chunk.token_count} tokens</span>
                        <span>{chunk.char_count} chars</span>
                        {chunk.external_doc_id ? <span>{chunk.external_doc_id}</span> : null}
                      </div>
                    </article>
                  ))}
                </div>
              )}

              <section className="document-event-panel" aria-label="处理事件">
                <div className="document-event-heading">
                  <span>Events</span>
                  <strong>最近处理事件</strong>
                </div>
                {eventError ? <ErrorState message={eventError} /> : null}
                {eventLoadState === "loading" ? (
                  <EmptyState text="加载 events" loading compact />
                ) : events.length === 0 ? (
                  <EmptyState text="暂无 events" compact />
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
