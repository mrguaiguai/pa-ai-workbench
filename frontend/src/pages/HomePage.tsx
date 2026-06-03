import {
  Activity,
  ArrowRight,
  BookOpenText,
  Database,
  FileClock,
  MessageSquareText,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ApiError, StatusResponse, apiClient } from "../api/client";

type HomePageProps = {
  navigateTo: (route: "/library" | "/analysis" | "/wiki" | "/history") => void;
};

type StatusState =
  | { state: "loading"; data: null; error: null }
  | { state: "ready"; data: StatusResponse; error: null }
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

export function HomePage({ navigateTo }: HomePageProps) {
  const [status, setStatus] = useState<StatusState>({
    state: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    let isMounted = true;
    apiClient
      .getStatus()
      .then((data) => {
        if (isMounted) {
          setStatus({ state: "ready", data, error: null });
        }
      })
      .catch((error: unknown) => {
        if (!isMounted) {
          return;
        }
        const message =
          error instanceof ApiError
            ? `HTTP ${error.status}`
            : error instanceof Error
              ? error.message
              : "Unknown error";
        setStatus({ state: "error", data: null, error: message });
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const counts = status.data?.counts;
  const metrics = useMemo(
    () => [
      { label: "资料", value: counts?.documents ?? 0 },
      { label: "会话", value: counts?.conversations ?? 0 },
      { label: "任务", value: counts?.tasks ?? 0 },
      { label: "输出", value: counts?.outputs ?? 0 },
    ],
    [counts],
  );

  return (
    <div className="home-page">
      <section className="overview-strip" aria-label="工作台总览">
        <div className="overview-copy">
          <p>PA AI Workbench</p>
          <h2>公共事务智能工作台</h2>
        </div>
        <div className={`backend-pill ${status.state}`}>
          {status.state === "loading" ? (
            <RefreshCw size={16} aria-hidden="true" />
          ) : status.state === "ready" ? (
            <ShieldCheck size={16} aria-hidden="true" />
          ) : (
            <Activity size={16} aria-hidden="true" />
          )}
          <span>
            {status.state === "ready"
              ? `${status.data.service} · ${status.data.knowledge_backend}`
              : status.state === "loading"
                ? "连接中"
                : status.error}
          </span>
        </div>
      </section>

      <section className="metric-grid" aria-label="核心数据">
        {metrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
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
