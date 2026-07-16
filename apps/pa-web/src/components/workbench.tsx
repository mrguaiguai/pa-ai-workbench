import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Copy,
  ExternalLink,
  FileText,
  Loader2,
  ShieldCheck,
  WifiOff,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ApiError, apiClient } from "../api/client";
import type {
  NativeMcpOverviewResponse,
  NativeVectorStoreOverviewResponse,
  NativeWebSearchOverviewResponse,
  NativeWikiOverviewResponse,
  StatusResponse,
  Task,
} from "../api/client";
import { useEffect, useMemo, useState } from "react";

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

type WeKnoraFirstStatusStripState =
  | {
      state: "loading";
      status: null;
      mcpOverview: null;
      vectorStoreOverview: null;
      webSearchOverview: null;
      wikiOverview: null;
      error: null;
      mcpError: null;
      vectorStoreError: null;
      webSearchError: null;
      wikiError: null;
    }
  | {
      state: "ready";
      status: StatusResponse;
      mcpOverview: NativeMcpOverviewResponse | null;
      vectorStoreOverview: NativeVectorStoreOverviewResponse | null;
      webSearchOverview: NativeWebSearchOverviewResponse | null;
      wikiOverview: NativeWikiOverviewResponse | null;
      error: null;
      mcpError: string | null;
      vectorStoreError: string | null;
      webSearchError: string | null;
      wikiError: string | null;
    }
  | {
      state: "error";
      status: null;
      mcpOverview: null;
      vectorStoreOverview: null;
      webSearchOverview: null;
      wikiOverview: null;
      error: string;
      mcpError: null;
      vectorStoreError: null;
      webSearchError: null;
      wikiError: null;
    };

type WeKnoraStatusChip = {
  label: string;
  value: string;
  status: string;
};

export function WeKnoraFirstStatusStrip({ page }: { page: string }) {
  const [state, setState] = useState<WeKnoraFirstStatusStripState>({
    state: "loading",
    status: null,
    mcpOverview: null,
    vectorStoreOverview: null,
    webSearchOverview: null,
    wikiOverview: null,
    error: null,
    mcpError: null,
    vectorStoreError: null,
    webSearchError: null,
    wikiError: null,
  });

  useEffect(() => {
    let isMounted = true;
    Promise.allSettled([
      apiClient.getStatus(),
      apiClient.getNativeWikiOverview({ limit: 5 }),
      apiClient.getNativeMcpOverview({ limit: 5 }),
      apiClient.getNativeWebSearchOverview({ limit: 5 }),
      apiClient.getNativeVectorStoreOverview({ limit: 5 }),
    ])
      .then(([statusResult, wikiResult, mcpResult, webSearchResult, vectorStoreResult]) => {
        if (!isMounted) {
          return;
        }
        if (statusResult.status !== "fulfilled") {
          setState({
            state: "error",
            status: null,
            mcpOverview: null,
            vectorStoreOverview: null,
            webSearchOverview: null,
            wikiOverview: null,
            error: errorLabel(statusResult.reason),
            mcpError: null,
            vectorStoreError: null,
            webSearchError: null,
            wikiError: null,
          });
          return;
        }
        setState({
          state: "ready",
          status: statusResult.value,
          mcpOverview: mcpResult.status === "fulfilled" ? mcpResult.value : null,
          vectorStoreOverview:
            vectorStoreResult.status === "fulfilled" ? vectorStoreResult.value : null,
          webSearchOverview:
            webSearchResult.status === "fulfilled" ? webSearchResult.value : null,
          wikiOverview: wikiResult.status === "fulfilled" ? wikiResult.value : null,
          error: null,
          mcpError: mcpResult.status === "fulfilled" ? null : errorLabel(mcpResult.reason),
          vectorStoreError:
            vectorStoreResult.status === "fulfilled" ? null : errorLabel(vectorStoreResult.reason),
          webSearchError:
            webSearchResult.status === "fulfilled" ? null : errorLabel(webSearchResult.reason),
          wikiError: wikiResult.status === "fulfilled" ? null : errorLabel(wikiResult.reason),
        });
      })
      .catch((error: unknown) => {
        if (isMounted) {
          setState({
            state: "error",
            status: null,
            mcpOverview: null,
            vectorStoreOverview: null,
            webSearchOverview: null,
            wikiOverview: null,
            error: errorLabel(error),
            mcpError: null,
            vectorStoreError: null,
            webSearchError: null,
            wikiError: null,
          });
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const details = useMemo(() => statusStripDetails(state), [state]);
  const chips = useMemo(() => statusStripChips(state), [state]);

  return (
    <section className="weknora-status-strip" aria-label={`${page} WeKnora-first 状态`}>
      <div className="weknora-status-main">
        <div className="weknora-status-title">
          <ShieldCheck size={18} aria-hidden="true" />
          <div>
            <span>{page}</span>
            <strong>WeKnora-first 状态</strong>
          </div>
        </div>
        <div className="weknora-status-detail">
          {details.map((detail) => (
            <span key={detail}>{detail}</span>
          ))}
        </div>
      </div>
      <div className="weknora-status-chips">
        {chips.map((chip) => (
          <span className={`weknora-status-chip ${statusClassName(chip.status)}`} key={chip.label}>
            <span>{chip.label}</span>
            <strong>{chip.value}</strong>
          </span>
        ))}
      </div>
    </section>
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

function statusStripChips(state: WeKnoraFirstStatusStripState): WeKnoraStatusChip[] {
  if (state.state === "loading") {
    return [
      { label: "服务", value: "连接中", status: "partial" },
      { label: "知识库", value: "检查中", status: "partial" },
      { label: "阻塞", value: "检查中", status: "blocked" },
    ];
  }
  if (state.state === "error") {
    return [
      { label: "服务", value: "不可用", status: "blocked" },
      { label: "状态", value: "待恢复", status: "fallback" },
      { label: "阻塞", value: state.error, status: "blocked" },
    ];
  }

  const status = state.status;
  const gates = status.backend_capabilities.weknora_first_status_gates?.status_categories;
  const kbMapping = status.weknora.kb_mapping;
  const wikiStatus = state.wikiOverview?.status ?? (state.wikiError ? "blocked" : "unknown");
  const mcpStatus = state.mcpOverview?.status ?? (state.mcpError ? "blocked" : "unknown");
  const backlogCount =
    (gates?.backlog.length ?? 0) +
    (kbMapping?.backlog.length ?? 0) +
    (state.wikiOverview?.surfaces.mutations?.status === "backlog" ? 1 : 0) +
    (state.mcpOverview?.surfaces.mutations?.status === "backlog" ? 1 : 0);
  const blockedCount =
    (gates?.blocked.length ?? 0) +
    (kbMapping?.status === "blocked" ? 1 : 0) +
    (wikiStatus === "blocked" ? 1 : 0) +
    (mcpStatus === "blocked" ? 1 : 0);

  return [
    {
      label: "WeKnora",
      value: status.weknora.connected ? "已连接" : status.weknora.status,
      status: status.weknora.connected ? "live" : status.weknora.status,
    },
    {
      label: "知识库",
      value: kbMapping?.status === "live" ? "已绑定" : kbMapping?.status ?? "未知",
      status: kbMapping?.status ?? "partial",
    },
    {
      label: "Wiki",
      value: wikiStatus === "live" ? "可用" : wikiStatus,
      status: wikiStatus,
    },
    {
      label: "工具",
      value: mcpStatus === "live" ? "可用" : mcpStatus,
      status: mcpStatus,
    },
    {
      label: "待处理",
      value: String(backlogCount),
      status: backlogCount > 0 ? "backlog" : "live",
    },
    {
      label: "阻塞",
      value: String(blockedCount),
      status: blockedCount > 0 ? "blocked" : "live",
    },
  ];
}

function statusStripDetails(state: WeKnoraFirstStatusStripState) {
  if (state.state === "loading") {
    return ["读取核心状态", "读取知识库与 Wiki 状态"];
  }
  if (state.state === "error") {
    return ["后端状态不可达", `原因：${state.error}`];
  }

  const status = state.status;
  const gates = status.backend_capabilities.weknora_first_status_gates?.status_categories;
  const kbMapping = status.weknora.kb_mapping;
  const details = [
    `链路：${status.knowledge_backend === "weknora_api" ? "WeKnora API" : status.knowledge_backend}`,
    `引用追踪：${status.backend_capabilities.parity_summary.citation_trace}`,
  ];
  if (state.wikiOverview) {
    details.push(`Wiki：${state.wikiOverview.status}`);
  }
  if (state.wikiError) {
    details.push(`Wiki 阻塞：${state.wikiError}`);
  }
  if (state.mcpError) {
    details.push(`工具阻塞：${state.mcpError}`);
  }
  const blocked = gates?.blocked[0];
  if (blocked) {
    details.push(`阻塞：${blocked}`);
  }
  const backlog = gates?.backlog[0] || kbMapping?.backlog[0];
  if (backlog) {
    details.push(`待处理：${backlog}`);
  }
  return details;
}

function errorLabel(error: unknown) {
  if (error instanceof ApiError) {
    return `HTTP ${error.status}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "unknown error";
}

function statusClassName(value: string) {
  return value.replace(/[\s_]+/g, "-").toLowerCase();
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
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(() => new Set());
  const [copyMessage, setCopyMessage] = useState<Record<string, string>>({});

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

  const toggleExpanded = (key: string) => {
    setExpandedKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const copyCitation = (citation: CitationListItem, index: number) => {
    const key = citationKey(citation, index);
    if (!navigator.clipboard) {
      setCopyMessage((current) => ({ ...current, [key]: "复制失败" }));
      return;
    }
    navigator.clipboard
      .writeText(citationCopyText(citation))
      .then(() => {
        setCopyMessage((current) => ({ ...current, [key]: "已复制" }));
      })
      .catch(() => {
        setCopyMessage((current) => ({ ...current, [key]: "复制失败" }));
      });
  };

  return (
    <div className="citation-list">
      {citations.map((citation, index) => {
        const key = citationKey(citation, index);
        const expanded = expandedKeys.has(key);
        const traceable = citationTraceable(citation);
        const metadataEntries = citationMetadataEntries(citation);
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
                <button
                  className="icon-button citation-locate-button"
                  type="button"
                  onClick={() => copyCitation(citation, index)}
                  title="复制引用"
                  aria-label="复制引用"
                >
                  {copyMessage[key] === "已复制" ? (
                    <CheckCircle2 size={15} aria-hidden="true" />
                  ) : (
                    <Copy size={15} aria-hidden="true" />
                  )}
                </button>
                <button
                  className="icon-button citation-locate-button"
                  type="button"
                  onClick={() => toggleExpanded(key)}
                  title={expanded ? "收起" : "展开"}
                  aria-label={expanded ? "收起" : "展开"}
                >
                  {expanded ? (
                    <ChevronUp size={15} aria-hidden="true" />
                  ) : (
                    <ChevronDown size={15} aria-hidden="true" />
                  )}
                </button>
              </div>
            </div>
            <p>{citationExcerpt(citation.text, expanded)}</p>
            <div className="citation-meta-row">
              <span className={`citation-source-type ${citationSourceClass(citation)}`}>
                {citationSourceLabel(citation)}
              </span>
              <span className={traceable ? "citation-locatable" : "citation-not-locatable"}>
                {traceable ? "可定位" : "不可定位"}
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
            {copyMessage[key] ? (
              <div className="citation-copy-message">
                <CheckCircle2 size={14} aria-hidden="true" />
                <span>{copyMessage[key]}</span>
              </div>
            ) : null}
            {expanded && metadataEntries.length > 0 ? (
              <div className="citation-detail-grid" aria-label="引用调试元数据">
                {metadataEntries.map(([label, value]) => (
                  <span key={label}>{`${label}: ${value}`}</span>
                ))}
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
        <span>结果</span>
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
        <span>进度</span>
        <strong>{taskStatusLabel(task.status)}</strong>
      </div>
      <div className="task-progress-track" aria-hidden="true">
        <span style={{ width: `${progress}%` }} />
      </div>
      <div className="task-progress-meta">
        <span>{task.current_step || "准备就绪"}</span>
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
  return <span className={`status-badge ${status}`}>{taskStatusLabel(status)}</span>;
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
    return "WeKnora Wiki 证据";
  }
  if (normalized === "document_chunk" && citation.source === "weknora_api") {
    return "WeKnora 文档证据";
  }
  if (normalized === "wiki_page") {
    return "Wiki 证据";
  }
  if (normalized === "document_chunk") {
    return "文档证据";
  }
  if (citation.source === "mock") {
    return "模拟证据";
  }
  return normalized || "证据";
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
    return "评分不可用";
  }
  return `评分 ${citation.score.toFixed(2)}`;
}

function citationScoreTitle(citation: CitationListItem) {
  const metadata = citationMetadata(citation);
  const semantics = optionalCitationString(metadata.score_semantics);
  if (semantics) {
    return semantics;
  }
  return citation.score === null || citation.score === undefined
    ? "后端未返回评分"
    : "后端检索评分";
}

function citationExcerpt(text: string, expanded: boolean) {
  const normalized = text.split(/\s+/).join(" ");
  if (expanded || normalized.length <= 260) {
    return normalized;
  }
  return `${normalized.slice(0, 257).trim()}...`;
}

function citationTraceable(citation: CitationListItem) {
  const sourceType = citationSourceType(citation);
  if (sourceType === "wiki_page") {
    return Boolean(citationEvidenceId(citation) && citationWikiPageId(citation));
  }
  if (sourceType === "document_chunk") {
    return Boolean(
      citationEvidenceId(citation) &&
        citation.chunk_id &&
        (citation.document_id || citation.external_doc_id),
    );
  }
  return false;
}

function citationMetadataEntries(citation: CitationListItem): Array<[string, string]> {
  const metadata = citationMetadata(citation);
  const entries: Array<[string, string]> = [];
  for (const key of [
    "retrieval_rank",
    "raw_retrieval_rank",
    "score_display",
    "score_semantics",
    "citation_source_type",
    "business_area",
    "document_type",
    "wiki_page_id",
    "chunk_index",
    "page_number",
    "section_path",
  ]) {
    const value = metadata[key];
    if (value !== null && value !== undefined && value !== "") {
      entries.push([key, typeof value === "string" ? value : JSON.stringify(value)]);
    }
  }
  return entries;
}

function citationCopyText(citation: CitationListItem) {
  return [
    `title: ${citation.title}`,
    `source: ${citation.source}`,
    `source_type: ${citationSourceType(citation) || "unknown"}`,
    `evidence_id: ${citationEvidenceId(citation) || ""}`,
    `chunk_id: ${citation.chunk_id || ""}`,
    `wiki_page_id: ${citationWikiPageId(citation) || ""}`,
    `external_doc_id: ${citation.external_doc_id || ""}`,
    `score: ${citationScoreDisplay(citation)}`,
    `text: ${citationExcerpt(citation.text, true)}`,
  ].join("\n");
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
    return "向量化中";
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
  return taskStatusLabel(status || "unknown");
}

function taskStatusLabel(status: string) {
  const normalized = status.trim().toLowerCase();
  if (normalized === "completed" || normalized === "succeeded" || normalized === "ready") {
    return "已完成";
  }
  if (normalized === "failed" || normalized === "error") {
    return "失败";
  }
  if (normalized === "running") {
    return "运行中";
  }
  if (normalized === "created" || normalized === "pending") {
    return "已创建";
  }
  if (normalized === "unknown") {
    return "未知";
  }
  return status || "未知";
}
