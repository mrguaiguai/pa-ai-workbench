import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  ExternalLink,
  Loader2,
  ShieldCheck,
  SlidersHorizontal,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ApiError, NativeStatusCenterResponse, apiClient } from "../api/client";
import type { NativeCapabilityGroup } from "../api/client";
import { EmptyState, ErrorState } from "../components/workbench";

type CapabilityState =
  | { state: "loading"; data: null; error: null }
  | { state: "ready"; data: NativeStatusCenterResponse; error: null }
  | { state: "error"; data: null; error: string };

type ConfigRow = {
  label: string;
  detail: unknown;
  configured: boolean;
};

const statusLabels: Record<string, string> = {
  live: "live",
  partial: "partial",
  blocked: "blocked",
  backlog: "backlog",
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
  return Object.entries(group.summary || {})
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

function configRows(data: NativeStatusCenterResponse): ConfigRow[] {
  const config = data.config || {};
  const weknora = (config.weknora || {}) as Record<string, unknown>;
  const chat = (config.chat_model || {}) as Record<string, unknown>;
  const embedding = (config.embedding || {}) as Record<string, unknown>;
  return [
    { label: "WeKnora client", detail: weknora.status, configured: Boolean(weknora.configured) },
    {
      label: "WeKnora auth",
      detail: "service_token_configured",
      configured: Boolean(weknora.service_token_configured),
    },
    {
      label: "Workspace",
      detail: "workspace_configured",
      configured: Boolean(weknora.workspace_configured),
    },
    {
      label: "Knowledge base",
      detail: "kb_configured",
      configured: Boolean(weknora.kb_configured),
    },
    { label: "Chat model", detail: chat.provider, configured: Boolean(chat.configured) },
    {
      label: "Embedding",
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

  useEffect(() => {
    let isMounted = true;
    apiClient
      .getNativeStatusCenter({ limit: 5 })
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
      <section className="capability-summary-band" aria-label="Native capability summary">
        <div className="capability-summary-main">
          <div className="capability-summary-title">
            <ShieldCheck size={20} aria-hidden="true" />
            <div>
              <span>Native status center</span>
              <strong>{state.data.schema_version}</strong>
            </div>
          </div>
          <div className="capability-summary-detail">
            <span>{state.data.source}</span>
            <span>{state.data.evidence_type}</span>
            <span>{state.data.masked ? "masked" : "unmasked"}</span>
            <span>{state.data.group_count} groups</span>
          </div>
        </div>
        <div className="capability-counts" aria-label="Capability status counts">
          <StatusCount label="live" value={counts.live} status="live" />
          <StatusCount label="partial" value={counts.partial} status="partial" />
          <StatusCount label="blocked" value={counts.blocked} status="blocked" />
          <StatusCount label="backlog" value={counts.backlog} status="backlog" />
        </div>
      </section>

      <section className="capability-layout" aria-label="Capability center details">
        <div className="capability-matrix" aria-label="Capability groups">
          {groups.map((group) => (
            <CapabilityCard group={group} key={group.id} />
          ))}
        </div>

        <aside className="capability-side" aria-label="Config and warnings">
          <div className="capability-side-panel">
            <div className="capability-side-heading">
              <SlidersHorizontal size={17} aria-hidden="true" />
              <strong>Masked config</strong>
            </div>
            <div className="capability-config-list">
              {configRows(state.data).map((row) => (
                <div className="capability-config-row" key={row.label}>
                  <span>{row.label}</span>
                  <strong>{asText(row.detail)}</strong>
                  <em>{row.configured ? "configured" : "missing"}</em>
                </div>
              ))}
            </div>
          </div>

          <div className="capability-side-panel">
            <div className="capability-side-heading">
              <AlertTriangle size={17} aria-hidden="true" />
              <strong>Warnings</strong>
            </div>
            {state.data.warnings.length ? (
              <div className="capability-warning-list">
                {state.data.warnings.map((warning) => (
                  <span key={warning}>{warning}</span>
                ))}
              </div>
            ) : (
              <EmptyState icon={CheckCircle2} text="no warnings" compact />
            )}
          </div>
        </aside>
      </section>
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
        <span>{group.configured ? "configured" : "not configured"}</span>
        <span>{group.masked ? "masked" : "unmasked"}</span>
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
