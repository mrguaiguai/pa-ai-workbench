import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Database,
  ExternalLink,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, NativeStatusCenterResponse, apiClient } from "../api/client";
import type { NativeCapabilityGroup, NativeDataSourceOverviewResponse } from "../api/client";
import { EmptyState, ErrorState } from "../components/workbench";

type CapabilityState =
  | { state: "loading"; data: null; error: null }
  | { state: "ready"; data: NativeStatusCenterResponse; error: null }
  | { state: "error"; data: null; error: string };

type DataSourceState =
  | {
      state: "loading";
      overview: null;
      detail: null;
      error: null;
      action: null;
      lastAuditId: null;
      lastAction: null;
    }
  | {
      state: "ready";
      overview: NativeDataSourceOverviewResponse;
      detail: NativeDataSourceOverviewResponse | null;
      error: null;
      action: string | null;
      lastAuditId: string | null;
      lastAction: string | null;
    }
  | {
      state: "error";
      overview: null;
      detail: null;
      error: string;
      action: null;
      lastAuditId: null;
      lastAction: null;
    };

type ConfigRow = {
  label: string;
  detail: unknown;
  configured: boolean;
};

const statusLabels: Record<string, string> = {
  live: "可用",
  partial: "部分",
  blocked: "阻塞",
  backlog: "待处理",
};

const statusIcons = {
  live: CheckCircle2,
  partial: AlertTriangle,
  blocked: XCircle,
  backlog: CircleDashed,
};

function statusClassName(status: string) {
  return status.replace(/[\s_]+/g, "-").toLowerCase();
}

function errorLabel(error: unknown) {
  if (error instanceof ApiError) {
    return `HTTP ${error.status}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "未知错误";
}

function asText(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "none";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "number") {
    return String(value);
  }
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return `${value.length} items`;
  }
  return "object";
}

function groupSummary(group: NativeCapabilityGroup) {
  const summary = group.summary || {};
  if (group.id === "workspace_knowledge_base") {
    return [
      "mapping_status",
      "mutations_status",
      "kb_mutations",
      "pin_mutations",
      "tag_mutations",
      "confirm_token_id",
    ]
      .filter((key) => key in summary)
      .map((key) => `${key}: ${asText(summary[key])}`);
  }
  if (group.id === "chunk_management") {
    return [
      "basic_mutations_status",
      "content_rewrite_status",
      "generated_question_seed_status",
      "generated_question_delete_status",
      "search_by_chunk_status",
      "blocker_reason",
    ]
      .filter((key) => key in summary)
      .map((key) => `${key}: ${asText(summary[key])}`);
  }
  if (group.id === "model_embedding_rerank_parser") {
    return [
      "config_source_status",
      "pa_bridge_alignment_status",
      "parser_engine_count",
      "storage_engine_count",
    ]
      .filter((key) => key in summary)
      .map((key) => `${key}: ${asText(summary[key])}`);
  }
  if (group.id === "vector_store") {
    return [
      "store_read_status",
      "store_test_status",
      "mutations_status",
      "embedding_status",
    ]
      .filter((key) => key in summary)
      .map((key) => `${key}: ${asText(summary[key])}`);
  }
  if (group.id === "faq_tags_favorites_skills") {
    return [
      "faq_status",
      "faq_count",
      "tags_status",
      "favorites_status",
      "mutations_status",
      "tag_mutations",
      "favorite_mutations",
      "skill_read_status",
      "skill_management_status",
      "skill_management_scope",
      "skill_test_status",
      "skill_script_upload_status",
      "skill_mutations",
      "skills_count",
    ]
      .filter((key) => key in summary)
      .map((key) => `${key}: ${asText(summary[key])}`);
  }
  return Object.entries(summary)
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${asText(value)}`);
}

function groupCounts(data: NativeStatusCenterResponse | null) {
  const counts = { live: 0, partial: 0, blocked: 0, backlog: 0 };
  if (!data) {
    return counts;
  }
  Object.values(data.groups).forEach((group) => {
    const status = group.status in counts ? group.status : "blocked";
    counts[status as keyof typeof counts] += 1;
  });
  return counts;
}

function nativeSurface(
  data: NativeDataSourceOverviewResponse | null,
  name: string,
): Record<string, unknown> {
  if (!data || !data.surfaces || typeof data.surfaces[name] !== "object") {
    return {};
  }
  return data.surfaces[name] as Record<string, unknown>;
}

function firstDataSourceIndex(data: NativeDataSourceOverviewResponse | null): number | null {
  const dataSources = nativeSurface(data, "data_sources");
  const items = Array.isArray(dataSources.items) ? dataSources.items : [];
  const first = items.find((item) => item && typeof item === "object") as
    | Record<string, unknown>
    | undefined;
  if (!first) {
    return null;
  }
  const safeIndex = Number(first.safe_index);
  return Number.isFinite(safeIndex) ? safeIndex : null;
}

function firstDataSourceItem(data: NativeDataSourceOverviewResponse | null) {
  const dataSources = nativeSurface(data, "data_sources");
  const items = Array.isArray(dataSources.items) ? dataSources.items : [];
  return (items.find((item) => item && typeof item === "object") || null) as
    | Record<string, unknown>
    | null;
}

async function loadDataSourceSnapshot() {
  const overview = await apiClient.getNativeDataSourceOverview({ limit: 5 });
  const sourceIndex = firstDataSourceIndex(overview);
  const detail =
    sourceIndex === null ? null : await apiClient.getNativeDataSourceDetail(sourceIndex);
  return { overview, detail };
}

function configRows(data: NativeStatusCenterResponse): ConfigRow[] {
  const config = data.config || {};
  const weknora = (config.weknora || {}) as Record<string, unknown>;
  const chat = (config.chat_model || {}) as Record<string, unknown>;
  const embedding = (config.embedding || {}) as Record<string, unknown>;
  return [
    { label: "WeKnora 客户端", detail: weknora.status, configured: Boolean(weknora.configured) },
    {
      label: "WeKnora 认证",
      detail: "service_token_configured",
      configured: Boolean(weknora.service_token_configured),
    },
    {
      label: "工作区",
      detail: "workspace_configured",
      configured: Boolean(weknora.workspace_configured),
    },
    {
      label: "知识库",
      detail: "kb_configured",
      configured: Boolean(weknora.kb_configured),
    },
    { label: "对话模型", detail: chat.provider, configured: Boolean(chat.configured) },
    {
      label: "向量模型",
      detail: embedding.provider,
      configured: Boolean(embedding.configured),
    },
  ];
}

export function CapabilityCenterPage() {
  const [state, setState] = useState<CapabilityState>({
    state: "loading",
    data: null,
    error: null,
  });
  const [dataSourceState, setDataSourceState] = useState<DataSourceState>({
    state: "loading",
    overview: null,
    detail: null,
    error: null,
    action: null,
    lastAuditId: null,
    lastAction: null,
  });

  const refreshDataSources = useCallback(() => {
    setDataSourceState({
      state: "loading",
      overview: null,
      detail: null,
      error: null,
      action: null,
      lastAuditId: null,
      lastAction: null,
    });
    loadDataSourceSnapshot()
      .then(({ overview, detail }) => {
        setDataSourceState({
          state: "ready",
          overview,
          detail,
          error: null,
          action: null,
          lastAuditId: null,
          lastAction: null,
        });
      })
      .catch((error: unknown) => {
        setDataSourceState({
          state: "error",
          overview: null,
          detail: null,
          error: errorLabel(error),
          action: null,
          lastAuditId: null,
          lastAction: null,
        });
      });
  }, []);

  useEffect(() => {
    let isMounted = true;
    apiClient
      .getNativeStatusCenter({ limit: 20 })
      .then((data) => {
        if (isMounted) {
          setState({ state: "ready", data, error: null });
        }
      })
      .catch((error: unknown) => {
        if (isMounted) {
          setState({ state: "error", data: null, error: errorLabel(error) });
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    refreshDataSources();
  }, [refreshDataSources]);

  const runDataSourceAction = useCallback(
    async (action: "sync" | "pause" | "resume" | "delete") => {
      if (dataSourceState.state !== "ready") {
        return;
      }
      const sourceIndex = firstDataSourceIndex(dataSourceState.overview);
      if (sourceIndex === null) {
        return;
      }
      if (
        action === "delete" &&
        !window.confirm("Delete this native data source? This cannot be undone.")
      ) {
        return;
      }
      setDataSourceState({ ...dataSourceState, action });
      try {
        const mutation =
          action === "sync"
            ? await apiClient.syncNativeDataSource(sourceIndex)
            : action === "pause"
              ? await apiClient.pauseNativeDataSource(sourceIndex)
              : action === "resume"
                ? await apiClient.resumeNativeDataSource(sourceIndex)
                : await apiClient.deleteNativeDataSource(sourceIndex);
        const snapshot = await loadDataSourceSnapshot();
        setDataSourceState({
          state: "ready",
          overview: snapshot.overview,
          detail: snapshot.detail,
          error: null,
          action: null,
          lastAuditId: mutation.audit?.id || null,
          lastAction: action,
        });
      } catch (error: unknown) {
        setDataSourceState({
          state: "error",
          overview: null,
          detail: null,
          error: errorLabel(error),
          action: null,
          lastAuditId: null,
          lastAction: null,
        });
      }
    },
    [dataSourceState],
  );

  const counts = useMemo(() => groupCounts(state.data), [state.data]);
  const groups = useMemo(
    () => (state.data ? Object.values(state.data.groups) : []),
    [state.data],
  );

  if (state.state === "loading") {
    return (
      <div className="capability-page">
        <EmptyState icon={Loader2} text="正在读取 native status center" loading wide />
      </div>
    );
  }

  if (state.state === "error") {
    return (
      <div className="capability-page">
        <ErrorState message={state.error} />
      </div>
    );
  }

  return (
    <div className="capability-page">
      <section className="capability-summary-band" aria-label="设置与调试概览">
        <div className="capability-summary-main">
          <div className="capability-summary-title">
            <ShieldCheck size={20} aria-hidden="true" />
            <div>
              <span>设置与调试</span>
              <strong>Native 状态</strong>
            </div>
          </div>
          <div className="capability-summary-detail">
            <span>{state.data.source}</span>
            <span>{state.data.schema_version}</span>
            <span>{state.data.evidence_type}</span>
            <span>{state.data.masked ? "已脱敏" : "未脱敏"}</span>
            <span>{state.data.group_count} 组</span>
          </div>
        </div>
        <div className="capability-counts" aria-label="能力状态统计">
          <StatusCount label="可用" value={counts.live} status="live" />
          <StatusCount label="部分" value={counts.partial} status="partial" />
          <StatusCount label="阻塞" value={counts.blocked} status="blocked" />
          <StatusCount label="待处理" value={counts.backlog} status="backlog" />
        </div>
      </section>

      <section className="capability-section-shortcuts" aria-label="设置分组">
        <article className="capability-section-card">
          <ShieldCheck size={18} aria-hidden="true" />
          <span>运行状态</span>
          <strong>系统健康与服务状态</strong>
        </article>
        <article className="capability-section-card">
          <SlidersHorizontal size={18} aria-hidden="true" />
          <span>模型与检索</span>
          <strong>模型、向量库与检索链路</strong>
        </article>
        <article className="capability-section-card">
          <Database size={18} aria-hidden="true" />
          <span>数据与连接</span>
          <strong>数据源、MCP 与外部连接</strong>
        </article>
        <article className="capability-section-card action">
          <Search size={18} aria-hidden="true" />
          <span>高级调试</span>
          <strong>检索调试与排障工具</strong>
          <a className="capability-shortcut-link" href="#/rag-debug">
            打开检索调试
            <ExternalLink size={14} aria-hidden="true" />
          </a>
        </article>
      </section>

      <section className="capability-layout" aria-label="设置与调试详情">
        <div className="capability-matrix" aria-label="能力分组">
          {groups.map((group) => (
            <CapabilityCard group={group} key={group.id} />
          ))}
        </div>

        <aside className="capability-side" aria-label="配置与告警">
          <DataSourceOpsPanel
            state={dataSourceState}
            onRefresh={refreshDataSources}
            onAction={runDataSourceAction}
          />

          <div className="capability-side-panel">
            <div className="capability-side-heading">
              <SlidersHorizontal size={17} aria-hidden="true" />
              <strong>运行配置</strong>
            </div>
            <div className="capability-config-list">
              {configRows(state.data).map((row) => (
                <div className="capability-config-row" key={row.label}>
                  <span>{row.label}</span>
                  <strong>{asText(row.detail)}</strong>
                  <em>{row.configured ? "已配置" : "缺失"}</em>
                </div>
              ))}
            </div>
          </div>

          <div className="capability-side-panel">
            <div className="capability-side-heading">
              <AlertTriangle size={17} aria-hidden="true" />
              <strong>告警</strong>
            </div>
            {state.data.warnings.length ? (
              <div className="capability-warning-list">
                {state.data.warnings.map((warning) => (
                  <span key={warning}>{warning}</span>
                ))}
              </div>
            ) : (
              <EmptyState icon={CheckCircle2} text="暂无告警" compact />
            )}
          </div>
        </aside>
      </section>
    </div>
  );
}

function DataSourceOpsPanel({
  state,
  onRefresh,
  onAction,
}: {
  state: DataSourceState;
  onRefresh: () => void;
  onAction: (action: "sync" | "pause" | "resume" | "delete") => void;
}) {
  const overview = state.state === "ready" ? state.overview : null;
  const detail = state.state === "ready" ? state.detail : null;
  const source = firstDataSourceItem(overview);
  const dataSources = nativeSurface(overview, "data_sources");
  const resources = nativeSurface(detail, "resources");
  const validation = nativeSurface(detail, "validation");
  const syncLogs = nativeSurface(detail, "sync_logs");
  const syncControl = nativeSurface(detail || overview, "sync_control");
  const deleteControl = nativeSurface(detail || overview, "delete_control");
  const sourceCount = Number(dataSources.count || 0);
  const hasSource = Boolean(source);
  const disabled = state.state !== "ready" || !hasSource || Boolean(state.action);
  return (
    <div className="capability-side-panel data-source-ops-panel" data-testid="native-data-source-ops">
      <div className="capability-side-heading">
        <Database size={17} aria-hidden="true" />
        <strong>数据源调试</strong>
      </div>
      {state.state === "loading" ? (
        <EmptyState icon={Loader2} text="正在读取数据源状态" loading compact />
      ) : state.state === "error" ? (
        <ErrorState message={state.error} />
      ) : (
        <>
          <div className="native-ds-summary">
            <span>data_source_count: {sourceCount}</span>
            <span>overview_status: {overview?.status || "none"}</span>
            <span>source: {overview?.source || "none"}</span>
          </div>
          {source ? (
            <>
              <div className="native-ds-selected">
                <strong>{asText(source.name)}</strong>
                <span>类型：{asText(source.type)}</span>
                <span>状态：{asText(source.status)}</span>
              </div>
              <div className="native-ds-status-grid">
                <span>resources_status: {asText(resources.status)}</span>
                <span>validation_status: {asText(validation.status)}</span>
                <span>sync_logs_status: {asText(syncLogs.status)}</span>
                <span>sync_control_status: {asText(syncControl.status)}</span>
                <span>delete_control_status: {asText(deleteControl.status)}</span>
                <span>native_data_source_delete: {asText(deleteControl.delete_confirm_phrase)}</span>
              </div>
              <div className="native-ds-action-row">
                <button
                  className={state.action === "sync" ? "icon-button loading" : "icon-button"}
                  type="button"
                  title="同步数据源"
                  aria-label="同步数据源"
                  disabled={disabled}
                  onClick={() => onAction("sync")}
                >
                  {state.action === "sync" ? <Loader2 size={15} /> : <RefreshCw size={15} />}
                  <span>同步</span>
                </button>
                <button
                  className={state.action === "pause" ? "icon-button loading" : "icon-button"}
                  type="button"
                  title="暂停数据源"
                  aria-label="暂停数据源"
                  disabled={disabled}
                  onClick={() => onAction("pause")}
                >
                  {state.action === "pause" ? <Loader2 size={15} /> : <Pause size={15} />}
                  <span>暂停</span>
                </button>
                <button
                  className={state.action === "resume" ? "icon-button loading" : "icon-button"}
                  type="button"
                  title="恢复数据源"
                  aria-label="恢复数据源"
                  disabled={disabled}
                  onClick={() => onAction("resume")}
                >
                  {state.action === "resume" ? <Loader2 size={15} /> : <Play size={15} />}
                  <span>恢复</span>
                </button>
                <button
                  className={state.action === "delete" ? "icon-button danger loading" : "icon-button danger"}
                  type="button"
                  title="删除数据源"
                  aria-label="删除数据源"
                  disabled={disabled}
                  onClick={() => onAction("delete")}
                >
                  {state.action === "delete" ? <Loader2 size={15} /> : <Trash2 size={15} />}
                  <span>删除</span>
                </button>
              </div>
              {state.lastAuditId ? (
                <div className="native-ds-audit">
                  <span>last_action: {state.lastAction}</span>
                  <span>audit_id: {state.lastAuditId}</span>
                </div>
              ) : null}
            </>
          ) : (
            <EmptyState icon={CircleDashed} text="暂无原生数据源" compact />
          )}
          <button
            className="secondary-action compact native-ds-refresh"
            type="button"
            onClick={onRefresh}
          >
            <RefreshCw size={14} aria-hidden="true" />
            刷新
          </button>
        </>
      )}
    </div>
  );
}

function StatusCount({
  label,
  value,
  status,
}: {
  label: string;
  value: number;
  status: string;
}) {
  return (
    <div className={`capability-count ${statusClassName(status)}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CapabilityCard({ group }: { group: NativeCapabilityGroup }) {
  const normalizedStatus = statusClassName(group.status);
  const Icon =
    statusIcons[normalizedStatus as keyof typeof statusIcons] || AlertTriangle;
  return (
    <article className={`capability-card ${normalizedStatus}`}>
      <div className="capability-card-head">
        <Icon size={18} aria-hidden="true" />
        <div>
          <span>{group.id}</span>
          <strong>{group.label}</strong>
        </div>
        <em>{statusLabels[normalizedStatus] || group.status}</em>
      </div>
      <div className="capability-card-meta">
        <span>{group.configured ? "已配置" : "未配置"}</span>
        <span>{group.masked ? "已脱敏" : "未脱敏"}</span>
        <span>{group.next_action}</span>
      </div>
      <div className="capability-endpoints">
        <span>
          <ExternalLink size={13} aria-hidden="true" />
          {group.source_endpoint}
        </span>
        {group.native_endpoint ? (
          <span>
            <ExternalLink size={13} aria-hidden="true" />
            {group.native_endpoint}
          </span>
        ) : null}
      </div>
      <div className="capability-card-summary">
        {groupSummary(group).map((item) => (
          <span key={item}>{item}</span>
        ))}
      </div>
    </article>
  );
}
