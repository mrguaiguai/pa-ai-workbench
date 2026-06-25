import {
  BookOpenText,
  FileClock,
  FilePlus2,
  Loader2,
  RefreshCw,
  Search,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  ApiError,
  Citation,
  GeneratedOutput,
  HistoryListFilters,
  WikiPage,
  apiClient,
} from "../api/client";
import {
  CitationList,
  EmptyState,
  ErrorState,
  StatusBadge,
  WarningList,
  parseWarningsJson,
} from "../components/workbench";

type LoadState = "idle" | "loading" | "error";

const SELECTED_WIKI_STORAGE_KEY = "pa_workbench:selected_wiki_slug";

type HistoryFilters = {
  query: string;
  taskType: string;
  status: string;
  citationSource: string;
  sourceType: string;
  evidenceState: string;
  warningFilter: string;
};

const initialFilters: HistoryFilters = {
  query: "",
  taskType: "all",
  status: "all",
  citationSource: "all",
  sourceType: "all",
  evidenceState: "all",
  warningFilter: "all",
};

const baseTaskTypeOptions = ["knowledge_qa", "policy_analysis", "case_review", "wiki_draft"];
const baseStatusOptions = ["completed", "failed", "running", "created"];

const evidenceStateLabels: Record<string, string> = {
  citation_blocked: "引用阻断",
  no_evidence: "无证据",
  mock_only: "仅模拟证据",
  weknora: "WeKnora",
  mixed: "混合来源",
  other: "其他来源",
  unknown: "未知",
};

const taskTypeLabels: Record<string, string> = {
  knowledge_qa: "知识问答",
  native_agentqa: "Native AgentQA",
  native_knowledge_chat: "Native 知识对话",
  policy_analysis: "政策分析",
  case_review: "案例复盘",
  wiki_draft: "Wiki 草稿",
};

const statusLabels: Record<string, string> = {
  completed: "已完成",
  failed: "失败",
  running: "运行中",
  created: "已创建",
};

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

function formatContent(output: GeneratedOutput | null) {
  if (!output) {
    return "";
  }
  if (output.content_markdown) {
    return output.content_markdown;
  }
  if (!output.content_json) {
    return "无结果内容";
  }
  try {
    return JSON.stringify(JSON.parse(output.content_json), null, 2);
  } catch {
    return output.content_json;
  }
}

function citationMetadata(citation: Citation) {
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

function isWeKnoraCitation(citation: Citation) {
  const metadata = citationMetadata(citation);
  return citation.source === "weknora_api" || metadata.source === "weknora_api";
}

function historyListFilters(filters: HistoryFilters): HistoryListFilters {
  return {
    query: filters.query,
    task_type: filters.taskType,
    status: filters.status,
    citation_source: filters.citationSource,
    source_type: filters.sourceType,
    evidence_state: filters.evidenceState,
    has_warnings:
      filters.warningFilter === "with_warnings"
        ? true
        : filters.warningFilter === "no_warnings"
          ? false
          : undefined,
  };
}

function evidenceStateLabel(output: GeneratedOutput) {
  return evidenceStateLabels[output.evidence_state || "unknown"] ?? output.evidence_state;
}

function compactCountLabel(label: string, count: number | undefined) {
  return `${label} ${count ?? 0}`;
}

function taskTypeLabel(value: string) {
  return taskTypeLabels[value] ?? value;
}

function outputStatusLabel(value: string) {
  return statusLabels[value] ?? value;
}

export function HistoryPage() {
  const [filters, setFilters] = useState<HistoryFilters>(initialFilters);
  const [outputs, setOutputs] = useState<GeneratedOutput[]>([]);
  const [selectedOutputId, setSelectedOutputId] = useState<string | null>(null);
  const [selectedOutput, setSelectedOutput] = useState<GeneratedOutput | null>(null);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [historyState, setHistoryState] = useState<LoadState>("idle");
  const [detailState, setDetailState] = useState<LoadState>("idle");
  const [draftState, setDraftState] = useState<LoadState>("idle");
  const [draftError, setDraftError] = useState<string | null>(null);
  const [createdDraft, setCreatedDraft] = useState<WikiPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const taskTypeOptions = useMemo(
    () => Array.from(new Set([...baseTaskTypeOptions, ...outputs.map((output) => output.task_type)])).sort(),
    [outputs],
  );
  const statusOptions = useMemo(
    () => Array.from(new Set([...baseStatusOptions, ...outputs.map((output) => output.status)])).sort(),
    [outputs],
  );
  const warnings = useMemo(
    () => parseWarningsJson(selectedOutput?.warnings_json),
    [selectedOutput],
  );
  const citationSummary = useMemo(() => {
    if (selectedOutput) {
      return {
        weknoraCount: selectedOutput.weknora_citation_count,
        mockCount: selectedOutput.mock_citation_count,
        otherCount:
          selectedOutput.citation_count -
          selectedOutput.weknora_citation_count -
          selectedOutput.mock_citation_count,
        totalCount: selectedOutput.citation_count,
      };
    }
    const weknoraCount = citations.filter(isWeKnoraCitation).length;
    return {
      weknoraCount,
      mockCount: citations.filter((citation) => citation.source === "mock").length,
      otherCount: citations.length - weknoraCount,
      totalCount: citations.length,
    };
  }, [citations, selectedOutput]);
  const displayContent = useMemo(() => formatContent(selectedOutput), [selectedOutput]);

  const loadDetail = (outputId: string) => {
    setDetailState("loading");
    setError(null);
    apiClient
      .getHistoryOutput(outputId)
      .then((response) => {
        setSelectedOutput(response.output);
        setSelectedOutputId(response.output.id);
        setCitations(response.citations);
        setCreatedDraft(null);
        setDraftError(null);
        setDraftState("idle");
        setDetailState("idle");
      })
      .catch((detailError: unknown) => {
        setError(errorMessage(detailError));
        setDetailState("error");
      });
  };

  const loadHistory = () => {
    setHistoryState("loading");
    setError(null);
    apiClient
      .listHistory(historyListFilters(filters))
      .then((response) => {
        setOutputs(response.items);
        setHistoryState("idle");
        const firstOutput = response.items[0];
        if (firstOutput) {
          loadDetail(firstOutput.id);
        } else {
          setSelectedOutputId(null);
          setSelectedOutput(null);
          setCitations([]);
          setCreatedDraft(null);
          setDraftError(null);
          setDraftState("idle");
        }
      })
      .catch((historyError: unknown) => {
        setError(errorMessage(historyError));
        setHistoryState("error");
      });
  };

  useEffect(() => {
    loadHistory();
  }, [filters]);

  const onSelectOutput = (outputId: string) => {
    setSelectedOutputId(outputId);
    loadDetail(outputId);
  };

  const createWikiDraft = () => {
    if (!selectedOutput || draftState === "loading") {
      return;
    }

    setDraftState("loading");
    setDraftError(null);
    apiClient
      .createWikiDraftFromOutput(selectedOutput.id, {
        title: selectedOutput.title,
        metadata: {
          source: "history_page",
          history_output_id: selectedOutput.id,
        },
      })
      .then((page) => {
        setCreatedDraft(page);
        setDraftState("idle");
      })
      .catch((draftCreateError: unknown) => {
        setDraftError(errorMessage(draftCreateError));
        setDraftState("error");
      });
  };

  const openCreatedDraft = () => {
    if (!createdDraft) {
      return;
    }
    window.sessionStorage.setItem(SELECTED_WIKI_STORAGE_KEY, createdDraft.slug);
    window.location.hash = "/wiki";
  };

  return (
    <div className="history-page">
      <aside className="history-list-panel" aria-label="生成历史列表">
        <section className="history-filter-panel">
          <div className="history-panel-heading">
            <span>筛选</span>
            <button
              className={historyState === "loading" ? "icon-button loading" : "icon-button"}
              type="button"
              title="刷新"
              onClick={loadHistory}
              disabled={historyState === "loading"}
            >
              {historyState === "loading" ? (
                <Loader2 size={16} aria-hidden="true" />
              ) : (
                <RefreshCw size={16} aria-hidden="true" />
              )}
            </button>
          </div>

          <div className="form-grid history-fields">
            <label>
              <span>关键词</span>
              <div className="history-search-input">
                <Search size={15} aria-hidden="true" />
                <input
                  value={filters.query}
                  onChange={(event) => setFilters({ ...filters, query: event.target.value })}
                />
              </div>
            </label>
            <label>
              <span>任务类型</span>
              <select
                value={filters.taskType}
                onChange={(event) =>
                  setFilters({ ...filters, taskType: event.target.value })
                }
              >
                <option value="all">全部</option>
                {taskTypeOptions.map((taskType) => (
                  <option value={taskType} key={taskType}>
                    {taskTypeLabel(taskType)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>状态</span>
              <select
                value={filters.status}
                onChange={(event) => setFilters({ ...filters, status: event.target.value })}
              >
                <option value="all">全部</option>
                {statusOptions.map((status) => (
                  <option value={status} key={status}>
                    {outputStatusLabel(status)}
                  </option>
                ))}
              </select>
            </label>
            <details className="advanced-controls history-filter-advanced">
              <summary>高级筛选</summary>
              <label>
                <span>引用来源</span>
                <select
                  value={filters.citationSource}
                  onChange={(event) =>
                    setFilters({ ...filters, citationSource: event.target.value })
                  }
                >
                  <option value="all">全部</option>
                  <option value="weknora_api">在线知识服务</option>
                  <option value="mock">模拟证据</option>
                  <option value="none">无证据</option>
                  <option value="unknown">未知</option>
                </select>
              </label>
              <label>
                <span>证据类型</span>
                <select
                  value={filters.sourceType}
                  onChange={(event) =>
                    setFilters({ ...filters, sourceType: event.target.value })
                  }
                >
                  <option value="all">全部</option>
                  <option value="document_chunk">文档分块</option>
                  <option value="wiki_page">Wiki 页面</option>
                  <option value="unknown">未知</option>
                </select>
              </label>
              <label>
                <span>证据状态</span>
                <select
                  value={filters.evidenceState}
                  onChange={(event) =>
                    setFilters({ ...filters, evidenceState: event.target.value })
                  }
                >
                  <option value="all">全部</option>
                  <option value="citation_blocked">引用阻断</option>
                  <option value="no_evidence">无证据</option>
                  <option value="mock_only">仅模拟证据</option>
                  <option value="weknora">在线知识服务</option>
                  <option value="mixed">混合来源</option>
                  <option value="other">其他来源</option>
                  <option value="unknown">未知</option>
                </select>
              </label>
              <label>
                <span>警告</span>
                <select
                  value={filters.warningFilter}
                  onChange={(event) =>
                    setFilters({ ...filters, warningFilter: event.target.value })
                  }
                >
                  <option value="all">全部</option>
                  <option value="with_warnings">有警告</option>
                  <option value="no_warnings">无警告</option>
                </select>
              </label>
            </details>
          </div>
        </section>

        <section className="history-results-panel">
          <div className="history-panel-heading">
            <span>结果列表</span>
            <strong>{outputs.length}</strong>
          </div>

          {error ? <ErrorState message={error} /> : null}

          {historyState === "loading" ? (
            <EmptyState text="加载中" loading />
          ) : outputs.length === 0 ? (
            <EmptyState icon={FileClock} text="暂无历史" />
          ) : (
            <div className="history-output-list">
              {outputs.map((output) => (
                <button
                  className={
                    output.id === selectedOutputId
                      ? "history-output-item active"
                      : "history-output-item"
                  }
                  key={output.id}
                  type="button"
                  onClick={() => onSelectOutput(output.id)}
                >
                  <strong>{output.title}</strong>
                  <div>
                    <span>{taskTypeLabel(output.task_type)}</span>
                    <StatusBadge status={output.status} />
                    <span>{evidenceStateLabel(output)}</span>
                  </div>
                  <div className="history-output-metrics">
                    <span>{compactCountLabel("引用", output.citation_count)}</span>
                    <span>{compactCountLabel("可定位", output.traceable_citation_count)}</span>
                    <span>{compactCountLabel("WeKnora", output.weknora_citation_count)}</span>
                    <span>{compactCountLabel("模拟", output.mock_citation_count)}</span>
                    <span>{compactCountLabel("文档", output.document_citation_count)}</span>
                    <span>{compactCountLabel("Wiki", output.wiki_citation_count)}</span>
                    <span>{compactCountLabel("警告", output.warning_count)}</span>
                  </div>
                  <time>{formatDate(output.created_at)}</time>
                </button>
              ))}
            </div>
          )}
        </section>
      </aside>

      <section className="history-detail-panel" aria-label="历史详情">
        <div className="history-panel-heading">
          <span>结果</span>
          <strong>{selectedOutput?.title ?? "未选择结果"}</strong>
        </div>

        {detailState === "loading" ? (
          <EmptyState text="读取中" loading wide />
        ) : selectedOutput ? (
          <article className="history-output-detail">
            <div className="history-detail-meta">
              <span>{taskTypeLabel(selectedOutput.task_type)}</span>
              <span>{outputStatusLabel(selectedOutput.status)}</span>
              <span>{evidenceStateLabel(selectedOutput)}</span>
              <span>{compactCountLabel("引用", selectedOutput.citation_count)}</span>
              <span>{compactCountLabel("可定位", selectedOutput.traceable_citation_count)}</span>
              <span>{compactCountLabel("警告", selectedOutput.warning_count)}</span>
              <span>{formatDate(selectedOutput.created_at)}</span>
            </div>
            {selectedOutput.citation_blocked ? (
              <div className="history-draft-warning">
                {selectedOutput.citation_blocker ||
                  "该原生输出没有可追踪引用，PA 已阻断 citation PASS。"}
              </div>
            ) : null}
            <pre>{displayContent}</pre>
          </article>
        ) : (
          <EmptyState text="选择一条历史记录" wide />
        )}
      </section>

      <aside className="history-evidence-panel" aria-label="引用与警告">
        <section className="history-side-section">
          <div className="history-panel-heading">
            <span>Wiki 草稿</span>
            <strong>{createdDraft?.status ?? "准备就绪"}</strong>
          </div>

          <div className="history-draft-summary">
            <span>{`引用合计 ${citationSummary.totalCount}`}</span>
            <span>{`WeKnora ${citationSummary.weknoraCount}`}</span>
            <span>{`模拟 ${citationSummary.mockCount}`}</span>
          </div>

          {citationSummary.totalCount > 0 && citationSummary.weknoraCount === 0 ? (
            <div className="history-draft-warning">
              当前历史结果没有真实 WeKnora citation，草稿会保留引用但不会标记为真实 WeKnora 来源。
            </div>
          ) : null}

          <button
            className="secondary-action"
            type="button"
            disabled={!selectedOutput || draftState === "loading"}
            onClick={createWikiDraft}
          >
            {draftState === "loading" ? (
              <Loader2 size={16} aria-hidden="true" />
            ) : (
              <FilePlus2 size={16} aria-hidden="true" />
            )}
            <span>{draftState === "loading" ? "生成中" : "生成 Wiki 草稿"}</span>
          </button>

          {draftError ? <ErrorState message={draftError} /> : null}

          {createdDraft ? (
            <div className="history-draft-result">
              <div>
                <BookOpenText size={16} aria-hidden="true" />
                <span>{createdDraft.title}</span>
              </div>
              <p>{createdDraft.slug}</p>
              <button className="text-action" type="button" onClick={openCreatedDraft}>
                查看草稿
              </button>
            </div>
          ) : null}
        </section>

        <section className="history-side-section">
          <div className="history-panel-heading">
            <span>警告</span>
            <strong>{warnings.length}</strong>
          </div>

          <WarningList warnings={warnings} emptyText="暂无警告" />
        </section>

        <section className="history-side-section">
          <div className="history-panel-heading">
            <span>引用</span>
            <strong>{citations.length}</strong>
          </div>

          <CitationList citations={citations} />
        </section>
      </aside>
    </div>
  );
}
