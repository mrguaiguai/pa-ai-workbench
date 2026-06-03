import {
  AlertTriangle,
  FileClock,
  FileText,
  Loader2,
  RefreshCw,
  Search,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  ApiError,
  Citation,
  GeneratedOutput,
  apiClient,
} from "../api/client";

type LoadState = "idle" | "loading" | "error";

type HistoryFilters = {
  query: string;
  taskType: string;
  status: string;
};

const initialFilters: HistoryFilters = {
  query: "",
  taskType: "all",
  status: "all",
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
  return "Unknown error";
}

function parseWarnings(output: GeneratedOutput | null) {
  if (!output?.warnings_json) {
    return [];
  }

  try {
    const parsed = JSON.parse(output.warnings_json);
    return Array.isArray(parsed) ? parsed.filter((item) => typeof item === "string") : [];
  } catch {
    return [output.warnings_json];
  }
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

function matchesFilter(output: GeneratedOutput, filters: HistoryFilters) {
  const query = filters.query.trim().toLowerCase();
  const haystack = `${output.title} ${output.task_type} ${output.content_markdown ?? ""} ${
    output.content_json ?? ""
  }`.toLowerCase();

  return (
    (!query || haystack.includes(query)) &&
    (filters.taskType === "all" || output.task_type === filters.taskType) &&
    (filters.status === "all" || output.status === filters.status)
  );
}

export function HistoryPage() {
  const [filters, setFilters] = useState<HistoryFilters>(initialFilters);
  const [outputs, setOutputs] = useState<GeneratedOutput[]>([]);
  const [selectedOutputId, setSelectedOutputId] = useState<string | null>(null);
  const [selectedOutput, setSelectedOutput] = useState<GeneratedOutput | null>(null);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [historyState, setHistoryState] = useState<LoadState>("idle");
  const [detailState, setDetailState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);

  const taskTypeOptions = useMemo(
    () => Array.from(new Set(outputs.map((output) => output.task_type))).sort(),
    [outputs],
  );
  const statusOptions = useMemo(
    () => Array.from(new Set(outputs.map((output) => output.status))).sort(),
    [outputs],
  );
  const filteredOutputs = useMemo(
    () => outputs.filter((output) => matchesFilter(output, filters)),
    [filters, outputs],
  );
  const warnings = useMemo(() => parseWarnings(selectedOutput), [selectedOutput]);
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
      .listHistory()
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
        }
      })
      .catch((historyError: unknown) => {
        setError(errorMessage(historyError));
        setHistoryState("error");
      });
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const onSelectOutput = (outputId: string) => {
    setSelectedOutputId(outputId);
    loadDetail(outputId);
  };

  return (
    <div className="history-page">
      <aside className="history-list-panel" aria-label="生成历史列表">
        <section className="history-filter-panel">
          <div className="history-panel-heading">
            <span>Filter</span>
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
                    {taskType}
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
                    {status}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </section>

        <section className="history-results-panel">
          <div className="history-panel-heading">
            <span>Outputs</span>
            <strong>{filteredOutputs.length}</strong>
          </div>

          {error ? <div className="inline-error">{error}</div> : null}

          {historyState === "loading" ? (
            <div className="history-empty loading">
              <Loader2 size={18} aria-hidden="true" />
              <span>加载中</span>
            </div>
          ) : filteredOutputs.length === 0 ? (
            <div className="history-empty">
              <FileClock size={18} aria-hidden="true" />
              <span>暂无历史</span>
            </div>
          ) : (
            <div className="history-output-list">
              {filteredOutputs.map((output) => (
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
                    <span>{output.task_type}</span>
                    <span className={`history-status ${output.status}`}>{output.status}</span>
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
          <span>Result</span>
          <strong>{selectedOutput?.title ?? "未选择结果"}</strong>
        </div>

        {detailState === "loading" ? (
          <div className="history-empty wide loading">
            <Loader2 size={20} aria-hidden="true" />
            <span>读取中</span>
          </div>
        ) : selectedOutput ? (
          <article className="history-output-detail">
            <div className="history-detail-meta">
              <span>{selectedOutput.task_type}</span>
              <span>{selectedOutput.status}</span>
              <span>{formatDate(selectedOutput.created_at)}</span>
            </div>
            <pre>{displayContent}</pre>
          </article>
        ) : (
          <div className="history-empty wide">
            <FileText size={20} aria-hidden="true" />
            <span>选择一条历史记录</span>
          </div>
        )}
      </section>

      <aside className="history-evidence-panel" aria-label="引用与警告">
        <section className="history-side-section">
          <div className="history-panel-heading">
            <span>Warnings</span>
            <strong>{warnings.length}</strong>
          </div>

          {warnings.length === 0 ? (
            <div className="history-empty compact">
              <AlertTriangle size={18} aria-hidden="true" />
              <span>暂无警告</span>
            </div>
          ) : (
            <div className="history-warning-list">
              {warnings.map((warning) => (
                <div className="history-warning" key={warning}>
                  <AlertTriangle size={15} aria-hidden="true" />
                  <span>{warning}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="history-side-section">
          <div className="history-panel-heading">
            <span>Citations</span>
            <strong>{citations.length}</strong>
          </div>

          {citations.length === 0 ? (
            <div className="history-empty compact">
              <FileText size={18} aria-hidden="true" />
              <span>暂无引用</span>
            </div>
          ) : (
            <div className="history-citation-list">
              {citations.map((citation) => (
                <article className="history-citation" key={citation.id}>
                  <div>
                    <strong>{citation.title}</strong>
                    <span>{citation.score === null ? "-" : citation.score.toFixed(2)}</span>
                  </div>
                  <p>{citation.text}</p>
                  <span>{citation.source}</span>
                </article>
              ))}
            </div>
          )}
        </section>
      </aside>
    </div>
  );
}
