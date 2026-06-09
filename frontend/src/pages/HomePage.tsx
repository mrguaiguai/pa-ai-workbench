import {
  ArrowRight,
  BookOpenText,
  BrainCircuit,
  Cable,
  Database,
  FileClock,
  Layers3,
  MessageSquareText,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ApiError, ModelStatusResponse, StatusResponse, apiClient } from "../api/client";
import { BackendStatusBadge } from "../components/workbench";

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
  return value.replace(/\s+/g, "-").toLowerCase();
}

function configuredLabel(label: string, configured: boolean | undefined) {
  return `${label}: ${configured ? "configured" : "missing"}`;
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
          : "Unknown error";

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
      { label: "Chunks", value: counts?.document_chunks ?? 0 },
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
  const statusCards = useMemo(() => {
    const modelReady = modelStatus.state === "ready";
    const backendReady = status.state === "ready";
    const model = modelReady ? modelStatus.data : null;
    const backend = backendReady ? status.data : null;
    const weknora = backend?.weknora;
    const ragStatus =
      backendReady && weknora?.mode === "weknora_api"
        ? weknora.connected && !backend?.mock_mode
          ? "weknora connected"
          : weknora.status === "missing_config"
            ? "missing config"
            : "weknora unavailable"
        : backendReady
          ? backend?.mock_mode || model?.mock_mode
            ? "mock fallback"
            : "real ready"
          : status.state === "loading"
            ? "loading"
            : "error";
    const ragPrimary =
      backendReady && weknora?.mode === "weknora_api"
        ? "weknora_api"
        : backend?.knowledge_backend ?? "unknown";
    const ragSecondary =
      backendReady && weknora?.mode === "weknora_api"
        ? weknora.message || "WeKnora status unavailable"
        : backendReady
          ? `${counts?.document_chunks ?? 0} chunks indexed/stored`
          : "backend status unavailable";
    const ragDetails =
      backend && weknora?.mode === "weknora_api"
        ? [
            configuredLabel("auth", weknora.service_token_configured),
            configuredLabel("workspace", weknora.workspace_configured),
            configuredLabel("kb", weknora.kb_configured),
            `health: ${weknora.health_status ?? weknora.status}`,
          ]
        : backend
          ? [
              `backend mock: ${backend.mock_mode ? "yes" : "no"}`,
              `model mock: ${model?.mock_mode ? "yes" : "no"}`,
              `database: ${backend.database}`,
            ]
          : [status.state === "loading" ? "loading" : status.error ?? "error"];
    return [
      {
        id: "chat",
        label: "Chat Model",
        icon: BrainCircuit,
        state: modelStatus.state,
        status:
          modelReady
            ? model?.chat.configured
              ? "configured"
              : "missing config"
            : modelStatus.state === "loading"
              ? "loading"
              : "error",
        primary: model?.chat.provider ?? "unknown",
        secondary: model?.chat.model || "model not set",
        details:
          model
            ? [
                `mock: ${model.chat.mock ? "yes" : "no"}`,
                `api key: ${model.chat.api_key_configured ? "set" : "not set"}`,
                `timeout: ${model.chat.timeout_seconds}s`,
              ]
            : [modelStatus.state === "loading" ? "loading" : modelStatus.error ?? "error"],
      },
      {
        id: "embedding",
        label: "Embedding",
        icon: Layers3,
        state: modelStatus.state,
        status:
          modelReady
            ? model?.embedding.configured
              ? "configured"
              : "missing config"
            : modelStatus.state === "loading"
              ? "loading"
              : "error",
        primary: model?.embedding.provider ?? "unknown",
        secondary: model?.embedding.model || "model not set",
        details:
          model
            ? [
                `mock: ${model.embedding.mock ? "yes" : "no"}`,
                `dimension: ${model.embedding.dimension ?? "not set"}`,
                `api key: ${model.embedding.api_key_configured ? "set" : "not set"}`,
              ]
            : [modelStatus.state === "loading" ? "loading" : modelStatus.error ?? "error"],
      },
      {
        id: "rag",
        label: "RAG Pipeline",
        icon: Cable,
        state: backendReady && modelReady ? "ready" : status.state,
        status: ragStatus,
        primary: ragPrimary,
        secondary: ragSecondary,
        details: ragDetails,
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

      <section className="metric-grid" aria-label="核心数据">
        {metrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </section>

      <section className="runtime-status-grid" aria-label="模型与 RAG 状态">
        {statusCards.map((card) => {
          const Icon = card.icon;
          return (
            <article className={`runtime-status-card ${statusClass(card.status)}`} key={card.id}>
              <div className="runtime-status-title">
                <Icon size={18} aria-hidden="true" />
                <span>{card.label}</span>
                <strong>{card.status}</strong>
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
            <span>Agent Workflows</span>
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
                <code>{workflow.taskType}</code>
                <ArrowRight size={16} aria-hidden="true" />
              </button>
            ))}
          </div>
        </div>

        <div className="home-panel quick-panel">
          <div className="home-panel-heading">
            <span>Workspace</span>
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
