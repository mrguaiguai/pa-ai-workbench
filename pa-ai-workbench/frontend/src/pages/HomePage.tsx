import {
  ArrowRight,
  BookOpenText,
  BrainCircuit,
  Cable,
  Database,
  FileClock,
  Layers3,
  MessageSquareText,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ApiError, ModelStatusResponse, StatusResponse, apiClient } from "../api/client";
import { BackendStatusBadge, WeKnoraFirstStatusStrip } from "../components/workbench";

type HomePageProps = {
  navigateTo: (route: "/library" | "/analysis" | "/wiki" | "/history") => void;
};

type StatusState =
  | { state: "loading"; data: null; error: null }
  | { state: "ready"; data: StatusResponse; error: null }
  | { state: "error"; data: null; error: string };

type ModelStatusState =
  | { state: "loading"; data: null; error: null }
  | { state: "ready"; data: ModelStatusResponse; error: null }
  | { state: "error"; data: null; error: string };

type RuntimeStatusKey =
  | "real"
  | "mock"
  | "fallback"
  | "partial"
  | "blocked"
  | "backlog"
  | "unavailable"
  | "missing_config"
  | "indexing"
  | "retrievable"
  | "fail_closed"
  | "loading"
  | "error";

type RuntimeStatusCard = {
  id: string;
  label: string;
  icon: typeof BrainCircuit;
  state: StatusState["state"] | ModelStatusState["state"];
  status: RuntimeStatusKey;
  primary: string;
  secondary: string;
  details: string[];
};

const workflows = [
  {
    title: "知识问答",
    taskType: "knowledge_qa",
    route: "/analysis" as const,
    accent: "blue",
  },
  {
    title: "政策分析",
    taskType: "policy_analysis",
    route: "/analysis" as const,
    accent: "green",
  },
  {
    title: "案例复盘",
    taskType: "case_review",
    route: "/analysis" as const,
    accent: "amber",
  },
];

const quickLinks = [
  { label: "资料库", route: "/library" as const, icon: Database },
  { label: "智能分析", route: "/analysis" as const, icon: MessageSquareText },
  { label: "Wiki", route: "/wiki" as const, icon: BookOpenText },
  { label: "生成历史", route: "/history" as const, icon: FileClock },
];

function statusClass(value: string) {
  return value.replace(/[\s_]+/g, "-").toLowerCase();
}

function configuredLabel(label: string, configured: boolean | undefined) {
  return `${label}：${configured ? "已配置" : "缺失"}`;
}

function runtimeStatusLabel(status: RuntimeStatusKey) {
  const labels: Record<RuntimeStatusKey, string> = {
    real: "real 真实可用",
    mock: "mock 模式",
    fallback: "fallback 回退",
    partial: "partial 部分可用",
    blocked: "blocked 阻塞",
    backlog: "backlog 待办",
    unavailable: "unavailable 不可用",
    missing_config: "配置缺失",
    indexing: "索引中",
    retrievable: "可检索",
    fail_closed: "失败关闭",
    loading: "加载中",
    error: "错误",
  };
  return labels[status];
}

function modelProviderRuntimeStatus(
  state: ModelStatusState["state"],
  provider: { configured: boolean; mock: boolean } | null,
): RuntimeStatusKey {
  if (state === "loading") {
    return "loading";
  }
  if (state === "error" || !provider) {
    return "error";
  }
  if (provider.mock) {
    return "mock";
  }
  return provider.configured ? "real" : "missing_config";
}

function countStatus(statusCounts: Record<string, number>, key: string) {
  return Number(statusCounts[key] ?? 0);
}

export function HomePage({ navigateTo }: HomePageProps) {
  const [status, setStatus] = useState<StatusState>({
    state: "loading",
    data: null,
    error: null,
  });
  const [modelStatus, setModelStatus] = useState<ModelStatusState>({
    state: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    let isMounted = true;
    const loadErrorMessage = (error: unknown) =>
      error instanceof ApiError
        ? `HTTP ${error.status}`
        : error instanceof Error
          ? error.message
          : "未知错误";

    Promise.allSettled([apiClient.getStatus(), apiClient.getModelStatus()]).then((results) => {
      if (!isMounted) {
        return;
      }

      const [statusResult, modelResult] = results;
      if (statusResult.status === "fulfilled") {
        setStatus({ state: "ready", data: statusResult.value, error: null });
      } else {
        setStatus({
          state: "error",
          data: null,
          error: loadErrorMessage(statusResult.reason),
        });
      }

      if (modelResult.status === "fulfilled") {
        setModelStatus({ state: "ready", data: modelResult.value, error: null });
      } else {
        setModelStatus({
          state: "error",
          data: null,
          error: loadErrorMessage(modelResult.reason),
        });
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  const counts = status.data?.counts;
  const metrics = useMemo(
    () => [
      { label: "资料", value: counts?.documents ?? 0 },
      { label: "分块", value: counts?.document_chunks ?? 0 },
      { label: "任务", value: counts?.tasks ?? 0 },
      { label: "输出", value: counts?.outputs ?? 0 },
    ],
    [counts],
  );
  const backendLabel =
    status.state === "ready"
      ? `${status.data.service} · ${status.data.knowledge_backend}`
      : status.state === "loading"
        ? "连接中"
        : status.error;
  const statusCards = useMemo<RuntimeStatusCard[]>(() => {
    const modelReady = modelStatus.state === "ready";
    const backendReady = status.state === "ready";
    const model = modelReady ? modelStatus.data : null;
    const backend = backendReady ? status.data : null;
    const weknora = backend?.weknora;
    const capabilities = backend?.backend_capabilities;
    const parity = capabilities?.parity_summary;
    const kbMapping = weknora?.kb_mapping;
    const capabilityKbMapping = capabilities?.kb_mapping;
    const statusGates = capabilities?.weknora_first_status_gates;
    const gateCategories = statusGates?.status_categories;
    const statusCounts = parity?.status_counts ?? {};
    const partialCapabilityCount =
      countStatus(statusCounts, "partial") + (parity?.partial_capabilities.length ?? 0);
    const unsupportedCapabilityCount =
      countStatus(statusCounts, "unsupported") + (parity?.unsupported_capabilities.length ?? 0);
    const devOnlyCapabilityCount =
      countStatus(statusCounts, "dev-only") + (parity?.dev_only_capabilities.length ?? 0);
    const modelMock = Boolean(model?.mock_mode || model?.chat.mock || model?.embedding.mock);
    const ragStatus: RuntimeStatusKey =
      backendReady && weknora?.mode === "weknora_api"
        ? backend?.mock_mode || modelMock
          ? "fallback"
          : weknora.connected
            ? "real"
            : weknora.status === "missing_config"
              ? "missing_config"
              : "unavailable"
        : backendReady
          ? backend?.mock_mode || backend?.knowledge_backend === "mock"
            ? "mock"
            : "fallback"
          : status.state === "loading"
            ? "loading"
            : "error";
    const ragPrimary =
      backendReady && weknora?.mode === "weknora_api"
        ? "weknora_api"
        : backend?.knowledge_backend ?? "未知";
    const ragSecondary =
      backendReady && weknora?.mode === "weknora_api"
        ? weknora.message || "WeKnora 状态不可用"
        : backendReady
          ? `${counts?.document_chunks ?? 0} 个分块已索引或存储`
          : "后端状态不可用";
    const ragDetails =
      backend && weknora?.mode === "weknora_api"
        ? [
            configuredLabel("认证", weknora.service_token_configured),
            configuredLabel("工作区", weknora.workspace_configured),
            configuredLabel("知识库", weknora.kb_configured),
            `健康状态：${weknora.health_status ?? weknora.status}`,
            ]
        : backend
          ? [
              `后端模拟模式：${backend.mock_mode ? "是" : "否"}`,
              `模型模拟模式：${model?.mock_mode ? "是" : "否"}`,
              `数据库：${backend.database}`,
            ]
          : [status.state === "loading" ? "加载中" : status.error ?? "错误"];
    const capabilityStatus = backendReady
      ? parity?.fail_closed
        ? "fail_closed"
        : (gateCategories?.blocked.length ?? 0) > 0
          ? "blocked"
        : partialCapabilityCount > 0
          ? "partial"
          : unsupportedCapabilityCount > 0 && !parity?.release_evidence
            ? "unavailable"
            : parity?.release_evidence
              ? "real"
              : devOnlyCapabilityCount > 0
                ? "fallback"
                : "unavailable"
      : status.state === "loading"
        ? "loading"
        : "error";
    const capabilitySecondary = parity
      ? `${statusCounts.supported ?? 0} 项支持 · ${statusCounts.partial ?? 0} 项部分支持 · ${
          statusCounts.unsupported ?? 0
        } 项不支持`
      : "能力摘要不可用";
    const capabilityDetails = parity
      ? [
          `事实来源：${parity.data_fact_source}`,
          `知识库映射：${kbMapping?.status ?? "unknown"}`,
          `映射来源：${kbMapping?.selection_source ?? "unknown"}`,
          `活动 KB：${kbMapping?.kb_id ?? "unknown"}`,
          `映射配置数：${capabilityKbMapping?.mapping_count ?? 0}`,
          `引用追踪：${parity.citation_trace}`,
          `Wiki 发布：${parity.wiki}`,
          `调试能力：${parity.debug}`,
          `live：${gateCategories?.live.length ?? 0}`,
          `mock：${gateCategories?.mock.length ?? 0}`,
          `partial：${gateCategories?.partial.length ?? 0}`,
          `blocked：${gateCategories?.blocked.length ?? 0}`,
          `backlog：${gateCategories?.backlog.length ?? 0}`,
          `fixture-only PASS：禁止`,
        ]
      : [status.state === "loading" ? "加载中" : status.error ?? "错误"];
    return [
      {
        id: "chat",
        label: "对话模型",
        icon: BrainCircuit,
        state: modelStatus.state,
        status: modelProviderRuntimeStatus(modelStatus.state, model?.chat ?? null),
        primary: model?.chat.provider ?? "未知",
        secondary: model?.chat.model || "未设置模型",
        details:
          model
            ? [
                `模拟模式：${model.chat.mock ? "是" : "否"}`,
                `API 密钥：${model.chat.api_key_configured ? "已设置" : "未设置"}`,
                `超时：${model.chat.timeout_seconds}s`,
              ]
            : [modelStatus.state === "loading" ? "加载中" : modelStatus.error ?? "错误"],
      },
      {
        id: "embedding",
        label: "向量模型",
        icon: Layers3,
        state: modelStatus.state,
        status: modelProviderRuntimeStatus(modelStatus.state, model?.embedding ?? null),
        primary: model?.embedding.provider ?? "未知",
        secondary: model?.embedding.model || "未设置模型",
        details:
          model
            ? [
                `模拟模式：${model.embedding.mock ? "是" : "否"}`,
                `维度：${model.embedding.dimension ?? "未设置"}`,
                `API 密钥：${model.embedding.api_key_configured ? "已设置" : "未设置"}`,
              ]
            : [modelStatus.state === "loading" ? "加载中" : modelStatus.error ?? "错误"],
      },
      {
        id: "rag",
        label: "RAG 检索链路",
        icon: Cable,
        state: backendReady && modelReady ? "ready" : status.state,
        status: ragStatus,
        primary: ragPrimary,
        secondary: ragSecondary,
        details: ragDetails,
      },
      {
        id: "capability",
        label: "能力边界",
        icon: ShieldCheck,
        state: status.state,
        status: capabilityStatus,
        primary: capabilities?.active_backend ?? "未知",
        secondary: capabilitySecondary,
        details: capabilityDetails,
      },
    ];
  }, [counts, modelStatus, status]);

  return (
    <div className="home-page">
      <section className="overview-strip" aria-label="工作台总览">
        <div className="overview-copy">
          <p>PA AI Workbench</p>
          <h2>公共事务智能工作台</h2>
        </div>
        <BackendStatusBadge state={status.state} label={backendLabel} />
      </section>

      <WeKnoraFirstStatusStrip page="首页" />

      <section className="metric-grid" aria-label="核心数据">
        {metrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </section>

      <section className="runtime-status-grid" aria-label="模型、RAG 与能力状态">
        {statusCards.map((card) => {
          const Icon = card.icon;
          return (
            <article className={`runtime-status-card ${statusClass(card.status)}`} key={card.id}>
              <div className="runtime-status-title">
                <Icon size={18} aria-hidden="true" />
                <span>{card.label}</span>
                <strong>{runtimeStatusLabel(card.status)}</strong>
              </div>
              <h3>{card.primary}</h3>
              <p>{card.secondary}</p>
              <div className="runtime-status-meta">
                {card.details.map((detail) => (
                  <span key={detail}>{detail}</span>
                ))}
              </div>
            </article>
          );
        })}
      </section>

      <section className="home-grid">
        <div className="home-panel workflow-panel">
          <div className="home-panel-heading">
            <span>Agent 分析流</span>
            <strong>内置分析流</strong>
          </div>
          <div className="workflow-list">
            {workflows.map((workflow) => (
              <button
                className={`workflow-row ${workflow.accent}`}
                key={workflow.taskType}
                type="button"
                onClick={() => navigateTo(workflow.route)}
              >
                <span>{workflow.title}</span>
                <code>{workflow.title}</code>
                <ArrowRight size={16} aria-hidden="true" />
              </button>
            ))}
          </div>
        </div>

        <div className="home-panel quick-panel">
          <div className="home-panel-heading">
            <span>工作区</span>
            <strong>工作区</strong>
          </div>
          <div className="quick-grid">
            {quickLinks.map((link) => {
              const Icon = link.icon;
              return (
                <button
                  className="quick-link"
                  key={link.route}
                  type="button"
                  onClick={() => navigateTo(link.route)}
                >
                  <Icon size={18} aria-hidden="true" />
                  <span>{link.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}
