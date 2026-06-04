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

import { ApiError, Document, DocumentChunk, apiClient } from "../api/client";
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

const initialForm: LibraryForm = {
  title: "",
  businessArea: "",
  documentType: "",
  source: "manual",
};

const runningStatuses = new Set(["parsing", "chunking", "indexing"]);
const parsedStatuses = new Set(["parsed", "chunked", "indexing", "indexed"]);

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
  if (state.includes("完成") || state.includes("已") || state === "indexed") {
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
  return "待索引";
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
        }
        setLoadState("idle");
      })
      .catch((loadError: unknown) => {
        setError(errorMessage(loadError));
        setLoadState("error");
      });
  };

  useEffect(() => {
    loadDocuments();
  }, []);

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

  const loadChunks = (documentId: string) => {
    setPreviewDocumentId(documentId);
    setChunkLoadState("loading");
    setChunkError(null);
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
  };

  const onReindexDocument = (documentId: string) => {
    setReindexingId(documentId);
    setError(null);
    apiClient
      .reindexDocument(documentId)
      .then((response) => {
        setDocuments((current) =>
          current.map((document) =>
            document.id === documentId ? response.document : document,
          ),
        );
        if (previewDocumentId === documentId) {
          loadChunks(documentId);
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
                    </div>
                    <div className="document-meta">
                      <span>{document.business_area || "-"}</span>
                      <span>{document.document_type || "-"}</span>
                      <span>{formatFileSize(document.file_size)}</span>
                      <span>{formatDate(document.created_at)}</span>
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
                    </div>
                    {document.status === "failed" ? (
                      <div className="document-error">
                        <span>{document.failed_step || "workflow"}</span>
                        <strong>{document.error_message || "处理失败"}</strong>
                      </div>
                    ) : null}
                  </div>

                  <div className="document-actions">
                    <DocumentStatusBadge status={document.status} />
                    <button
                      className="icon-button"
                      type="button"
                      onClick={() => loadChunks(document.id)}
                      title="预览 chunks"
                    >
                      <Eye size={16} aria-hidden="true" />
                    </button>
                    <button
                      className="icon-button"
                      type="button"
                      onClick={() => onReindexDocument(document.id)}
                      disabled={reindexingId === document.id}
                      title="重新索引"
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
                </div>
                <button
                  className="icon-button"
                  type="button"
                  onClick={() => loadChunks(previewDocument.id)}
                  title="刷新 chunks"
                >
                  <RefreshCw size={16} aria-hidden="true" />
                </button>
              </div>

              {chunkError ? <ErrorState message={chunkError} /> : null}

              {chunkLoadState === "loading" ? (
                <EmptyState text="加载 chunks" loading compact />
              ) : chunks.length === 0 ? (
                <EmptyState text="暂无 chunks" compact />
              ) : (
                <div className="chunk-preview-list">
                  {chunks.map((chunk) => (
                    <article className="chunk-preview-item" key={chunk.id}>
                      <div className="chunk-preview-title">
                        <strong>#{chunk.chunk_index}</strong>
                        <span>{chunk.embedding_status}</span>
                      </div>
                      <p>{chunkExcerpt(chunk.content)}</p>
                      <div className="chunk-preview-meta">
                        <span>{chunkLocation(chunk)}</span>
                        <span>{chunk.token_count} tokens</span>
                        <span>{chunk.char_count} chars</span>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          ) : null}
        </section>
      </section>
    </div>
  );
}
