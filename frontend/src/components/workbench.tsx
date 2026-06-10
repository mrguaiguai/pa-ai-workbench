import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  FileText,
  Loader2,
  WifiOff,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ApiError, apiClient } from "../api/client";
import type { Task } from "../api/client";
import { useState } from "react";

export type CitationListItem = {
  id?: string | null;
  document_id?: string | null;
  external_doc_id?: string | null;
  chunk_id?: string | null;
  evidence_id?: string | null;
  source_type?: string | null;
  wiki_page_id?: string | null;
  title: string;
  text: string;
  score?: number | null;
  source: string;
  metadata_json?: string | null;
  metadata?: Record<string, unknown> | null;
};

type EmptyStateProps = {
  icon?: LucideIcon;
  text: string;
  loading?: boolean;
  compact?: boolean;
  wide?: boolean;
};

export function EmptyState({
  icon: Icon = FileText,
  text,
  loading = false,
  compact = false,
  wide = false,
}: EmptyStateProps) {
  const className = [
    "empty-state",
    loading ? "loading" : "",
    compact ? "compact" : "",
    wide ? "wide" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className}>
      {loading ? <Loader2 size={20} aria-hidden="true" /> : <Icon size={20} aria-hidden="true" />}
      <span>{text}</span>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="error-state">
      <AlertTriangle size={16} aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

export function WarningList({
  warnings,
  emptyText,
}: {
  warnings: string[];
  emptyText?: string;
}) {
  if (warnings.length === 0) {
    return emptyText ? (
      <EmptyState icon={AlertTriangle} text={emptyText} compact />
    ) : null;
  }

  return (
    <div className="warning-list">
      {warnings.map((warning) => (
        <div className="warning-item" key={warning}>
          <AlertTriangle size={15} aria-hidden="true" />
          <span>{warning}</span>
        </div>
      ))}
    </div>
  );
}

export function CitationList({
  citations,
  emptyText = "暂无引用",
}: {
  citations: CitationListItem[];
  emptyText?: string;
}) {
  const [locatingKey, setLocatingKey] = useState<string | null>(null);
  const [locationMessage, setLocationMessage] = useState<Record<string, string>>({});

  if (citations.length === 0) {
    return <EmptyState text={emptyText} compact />;
  }

  const locateCitation = (citation: CitationListItem, index: number) => {
    const key = citationKey(citation, index);
    setLocatingKey(key);
    setLocationMessage((current) => ({ ...current, [key]: "" }));
    apiClient
      .locateCitation({
        id: citation.id,
        document_id: citation.document_id,
        external_doc_id: citation.external_doc_id,
        chunk_id: citation.chunk_id,
        evidence_id: citationEvidenceId(citation),
        source_type: citationSourceType(citation),
        wiki_page_id: citationWikiPageId(citation),
        source: citation.source,
        metadata_json: citation.metadata_json,
        metadata: citation.metadata,
      })
      .then((target) => {
        if (!target.located || !target.ui_hash) {
          setLocationMessage((current) => ({ ...current, [key]: target.message }));
          return;
        }
        window.location.hash = target.ui_hash.replace(/^#/, "");
        window.dispatchEvent(new CustomEvent("pa:citation-locate", { detail: target }));
      })
      .catch((error: unknown) => {
        setLocationMessage((current) => ({
          ...current,
          [key]: error instanceof ApiError ? `HTTP ${error.status}` : "无法定位该引用",
        }));
      })
      .finally(() => setLocatingKey(null));
  };

  return (
    <div className="citation-list">
      {citations.map((citation, index) => {
        const key = citationKey(citation, index);
        return (
          <article
            className={`citation-item ${citation.source === "weknora_api" ? "weknora" : ""}`}
            key={key}
          >
            <div className="citation-title-row">
              <strong>{citation.title}</strong>
              <div className="citation-title-actions">
                <span title={citationScoreTitle(citation)}>{citationScoreDisplay(citation)}</span>
                <button
                  className="icon-button citation-locate-button"
                  type="button"
                  onClick={() => locateCitation(citation, index)}
                  title="打开定位"
                  aria-label="打开定位"
                  disabled={locatingKey === key}
                >
                  {locatingKey === key ? (
                    <Loader2 size={15} aria-hidden="true" />
                  ) : (
                    <ExternalLink size={15} aria-hidden="true" />
                  )}
                </button>
              </div>
            </div>
            <p>{citation.text}</p>
            <div className="citation-meta-row">
              <span className={`citation-source-type ${citationSourceClass(citation)}`}>
                {citationSourceLabel(citation)}
              </span>
              <span>{citation.source}</span>
              {citationEvidenceId(citation) ? <span>{citationEvidenceId(citation)}</span> : null}
              {citation.chunk_id ? <span>{citation.chunk_id}</span> : null}
              {citationWikiPageId(citation) ? <span>{citationWikiPageId(citation)}</span> : null}
              {citation.external_doc_id ? <span>{citation.external_doc_id}</span> : null}
            </div>
            {locationMessage[key] ? (
              <div className="citation-locate-message">
                <AlertTriangle size={14} aria-hidden="true" />
                <span>{locationMessage[key]}</span>
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}

export function ResultPanel({
  title,
  content,
  emptyText = "无结果内容",
}: {
  title: string;
  content: string | null | undefined;
  emptyText?: string;
}) {
  return (
    <section className="result-panel" aria-label="结果">
      <div className="component-panel-heading">
        <span>Result</span>
        <strong>{title}</strong>
      </div>
      <pre>{content || emptyText}</pre>
    </section>
  );
}

export function TaskProgress({ task }: { task: Pick<Task, "status" | "progress" | "current_step"> }) {
  const progress = Math.max(0, Math.min(100, task.progress));

  return (
    <section className="task-progress" aria-label="任务进度">
      <div className="component-panel-heading">
        <span>Progress</span>
        <strong>{task.status}</strong>
      </div>
      <div className="task-progress-track" aria-hidden="true">
        <span style={{ width: `${progress}%` }} />
      </div>
      <div className="task-progress-meta">
        <span>{task.current_step || "ready"}</span>
        <strong>{progress}%</strong>
      </div>
    </section>
  );
}

export function DocumentStatusBadge({ status }: { status: string }) {
  const normalized = status.trim().toLowerCase();
  return (
    <span className={`document-status-badge ${normalized}`}>
      {documentStatusLabel(normalized)}
    </span>
  );
}

export function BackendStatusBadge({
  state,
  label,
}: {
  state: "loading" | "ready" | "error";
  label: string;
}) {
  const Icon = state === "loading" ? Loader2 : state === "ready" ? CheckCircle2 : WifiOff;

  return (
    <div className={`backend-status-badge ${state}`}>
      <Icon size={16} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge ${status}`}>{status}</span>;
}

export function parseWarningsJson(warningsJson: string | null | undefined) {
  if (!warningsJson) {
    return [];
  }

  try {
    const parsed = JSON.parse(warningsJson);
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === "string")
      : [];
  } catch {
    return [warningsJson];
  }
}

function citationKey(citation: CitationListItem, index: number) {
  return (
    citation.id ||
    `${citation.source}-${citation.evidence_id || citation.chunk_id || citation.wiki_page_id || citation.document_id || citation.external_doc_id || citation.title}-${index}`
  );
}

function citationSourceLabel(citation: CitationListItem) {
  const normalized = citationSourceType(citation);
  if (normalized === "wiki_page" && citation.source === "weknora_api") {
    return "WeKnora Wiki";
  }
  if (normalized === "document_chunk" && citation.source === "weknora_api") {
    return "WeKnora Document";
  }
  if (normalized === "wiki_page") {
    return "Wiki";
  }
  if (normalized === "document_chunk") {
    return "Document";
  }
  if (citation.source === "mock") {
    return "Mock";
  }
  return normalized || "Evidence";
}

function citationSourceClass(citation: CitationListItem) {
  const normalized = citationSourceType(citation);
  if (citation.source === "weknora_api") {
    return normalized === "wiki_page" ? "weknora-wiki" : "weknora-document";
  }
  if (normalized === "wiki_page") {
    return "wiki";
  }
  if (normalized === "document_chunk") {
    return "document";
  }
  if (citation.source === "mock") {
    return "mock";
  }
  return "unknown";
}

function citationSourceType(citation: CitationListItem) {
  const metadata = citationMetadata(citation);
  const raw =
    citation.source_type ||
    metadata.citation_source_type ||
    metadata.source_type ||
    (citationWikiPageId(citation) ? "wiki_page" : undefined);
  const normalized = String(raw || "").trim().toLowerCase();
  if (["document", "document_chunk", "chunk"].includes(normalized)) {
    return "document_chunk";
  }
  if (["wiki", "wiki_page", "wiki-page"].includes(normalized)) {
    return "wiki_page";
  }
  return normalized;
}

function citationEvidenceId(citation: CitationListItem) {
  return optionalCitationString(citation.evidence_id || citationMetadata(citation).evidence_id);
}

function citationWikiPageId(citation: CitationListItem) {
  return optionalCitationString(citation.wiki_page_id || citationMetadata(citation).wiki_page_id);
}

function citationMetadata(citation: CitationListItem) {
  if (citation.metadata && typeof citation.metadata === "object") {
    return citation.metadata;
  }
  if (!citation.metadata_json) {
    return {} as Record<string, unknown>;
  }
  try {
    const parsed = JSON.parse(citation.metadata_json);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

function citationScoreDisplay(citation: CitationListItem) {
  const metadata = citationMetadata(citation);
  const display = optionalCitationString(metadata.score_display);
  if (display) {
    return display;
  }
  if (citation.score === null || citation.score === undefined) {
    return "Score unavailable";
  }
  return `Score ${citation.score.toFixed(2)}`;
}

function citationScoreTitle(citation: CitationListItem) {
  const metadata = citationMetadata(citation);
  const semantics = optionalCitationString(metadata.score_semantics);
  if (semantics) {
    return semantics;
  }
  return citation.score === null || citation.score === undefined
    ? "No backend score returned"
    : "Backend retrieval score";
}

function optionalCitationString(value: unknown) {
  if (value === null || value === undefined) {
    return null;
  }
  const normalized = String(value).trim();
  return normalized || null;
}

function documentStatusLabel(status: string) {
  if (status === "indexed") {
    return "已索引";
  }
  if (status === "indexing") {
    return "索引中";
  }
  if (status === "embedding") {
    return "Embedding";
  }
  if (status === "chunking") {
    return "分块中";
  }
  if (status === "parsing") {
    return "解析中";
  }
  if (status === "uploaded") {
    return "已上传";
  }
  if (status === "failed") {
    return "失败";
  }
  return status || "unknown";
}
