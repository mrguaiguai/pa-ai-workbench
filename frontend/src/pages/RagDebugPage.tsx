import {
  AlertTriangle,
  Database,
  FileSearch,
  Loader2,
  RotateCcw,
  Search,
} from "lucide-react";
import { useMemo, useState } from "react";
import type { Dispatch, FormEvent, SetStateAction } from "react";

import {
  ApiError,
  RagDebugEvidence,
  RagDebugResponse,
  apiClient,
} from "../api/client";
import { EmptyState, ErrorState, WarningList } from "../components/workbench";

type DebugForm = {
  query: string;
  topK: string;
  sourceType: "all" | "document_chunk" | "wiki_page";
  documentIds: string;
  kbId: string;
  businessArea: string;
  documentType: string;
};

const initialForm: DebugForm = {
  query: "",
  topK: "8",
  sourceType: "all",
  documentIds: "",
  kbId: "",
  businessArea: "",
  documentType: "",
};

export function RagDebugPage() {
  const [form, setForm] = useState<DebugForm>(initialForm);
  const [result, setResult] = useState<RagDebugResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const filters = useMemo(() => buildFilters(form), [form]);
  const parsedTopK = Number.parseInt(form.topK, 10);
  const canSubmit = form.query.trim().length > 0 && parsedTopK >= 1 && parsedTopK <= 50;

  const runDebug = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await apiClient.debugRag({
        query: form.query.trim(),
        top_k: parsedTopK,
        filters,
      });
      setResult(response);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rag-debug-page">
      <form className="rag-debug-controls" onSubmit={runDebug}>
        <label className="field-group wide">
          <span>Query</span>
          <textarea
            value={form.query}
            onChange={(event) => setFormField(setForm, "query", event.target.value)}
            maxLength={1000}
          />
        </label>

        <div className="rag-debug-grid">
          <label className="field-group">
            <span>Top K</span>
            <input
              type="number"
              min={1}
              max={50}
              value={form.topK}
              onChange={(event) => setFormField(setForm, "topK", event.target.value)}
            />
          </label>

          <label className="field-group">
            <span>Source</span>
            <select
              value={form.sourceType}
              onChange={(event) =>
                setFormField(
                  setForm,
                  "sourceType",
                  event.target.value as DebugForm["sourceType"],
                )
              }
            >
              <option value="all">All</option>
              <option value="document_chunk">Document</option>
              <option value="wiki_page">Wiki</option>
            </select>
          </label>

          <label className="field-group">
            <span>Document IDs</span>
            <input
              value={form.documentIds}
              onChange={(event) => setFormField(setForm, "documentIds", event.target.value)}
            />
          </label>

          <label className="field-group">
            <span>KB ID</span>
            <input
              value={form.kbId}
              onChange={(event) => setFormField(setForm, "kbId", event.target.value)}
            />
          </label>

          <label className="field-group">
            <span>Business</span>
            <input
              value={form.businessArea}
              onChange={(event) => setFormField(setForm, "businessArea", event.target.value)}
            />
          </label>

          <label className="field-group">
            <span>Document Type</span>
            <input
              value={form.documentType}
              onChange={(event) => setFormField(setForm, "documentType", event.target.value)}
            />
          </label>
        </div>

        <div className="rag-debug-actions">
          <button
            className={`primary-action ${loading ? "loading" : ""}`}
            type="submit"
            disabled={!canSubmit || loading}
          >
            {loading ? <Loader2 size={16} aria-hidden="true" /> : <Search size={16} aria-hidden="true" />}
            <span>Run</span>
          </button>
          <button
            className="secondary-action"
            type="button"
            onClick={() => {
              setForm(initialForm);
              setResult(null);
              setError(null);
            }}
          >
            <RotateCcw size={16} aria-hidden="true" />
            <span>Reset</span>
          </button>
        </div>
      </form>

      <section className="rag-debug-output" aria-label="RAG debug result">
        {loading ? (
          <EmptyState icon={Loader2} text="Running" loading />
        ) : error ? (
          <ErrorState message={error} />
        ) : result ? (
          <DebugResult result={result} />
        ) : (
          <EmptyState icon={FileSearch} text="No trace" />
        )}
      </section>
    </div>
  );
}

function DebugResult({ result }: { result: RagDebugResponse }) {
  return (
    <div className="rag-debug-result">
      <div className="rag-debug-trace">
        <span>{result.status}</span>
        <strong>{result.trace_id}</strong>
        <span>{`${result.total} hits`}</span>
      </div>

      {result.error ? (
        <div className="rag-debug-error">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>{result.error.message}</span>
        </div>
      ) : null}

      <WarningList warnings={result.warnings} />

      <div className="rag-debug-filter-row">
        <span>{`top_k=${result.top_k}`}</span>
        {Object.entries(result.filters).map(([key, value]) => (
          <span key={key}>{`${key}=${formatValue(value)}`}</span>
        ))}
      </div>

      <div className="rag-debug-list">
        {result.items.length === 0 ? (
          <EmptyState icon={Database} text="No evidence" compact />
        ) : (
          result.items.map((item) => <DebugItem item={item} key={debugItemKey(item)} />)
        )}
      </div>
    </div>
  );
}

function DebugItem({ item }: { item: RagDebugEvidence }) {
  return (
    <article className="rag-debug-item">
      <div className="rag-debug-item-head">
        <span>{`#${item.rank}`}</span>
        <strong>{item.title}</strong>
        <span>{scoreDisplay(item)}</span>
      </div>
      <p>{item.summary}</p>
      <div className="rag-debug-meta">
        <span>{item.source_type || "unknown"}</span>
        <span>{item.source}</span>
        {item.evidence_id ? <span>{item.evidence_id}</span> : null}
        {item.chunk_id ? <span>{`chunk:${item.chunk_id}`}</span> : null}
        {item.wiki_page_id ? <span>{`wiki:${item.wiki_page_id}`}</span> : null}
        {item.external_doc_id ? <span>{`external:${item.external_doc_id}`}</span> : null}
      </div>
      {Object.keys(item.metadata).length ? (
        <div className="rag-debug-meta compact">
          {Object.entries(item.metadata).map(([key, value]) => (
            <span key={key}>{`${key}:${formatValue(value)}`}</span>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function buildFilters(form: DebugForm) {
  const filters: Record<string, unknown> = {};
  if (form.sourceType !== "all") {
    filters.source_type = form.sourceType;
  }
  const documentIds = splitList(form.documentIds);
  if (documentIds.length > 0) {
    filters.document_ids = documentIds;
  }
  if (form.kbId.trim()) {
    filters.kb_id = form.kbId.trim();
  }
  if (form.businessArea.trim()) {
    filters.business_area = form.businessArea.trim();
  }
  if (form.documentType.trim()) {
    filters.document_type = form.documentType.trim();
  }
  return filters;
}

function splitList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 20);
}

function setFormField<K extends keyof DebugForm>(
  setForm: Dispatch<SetStateAction<DebugForm>>,
  key: K,
  value: DebugForm[K],
) {
  setForm((current) => ({ ...current, [key]: value }));
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return readableApiError(error);
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error";
}

function readableApiError(error: ApiError) {
  if (typeof error.body === "string") {
    return `HTTP ${error.status}: ${error.body}`;
  }
  if (error.body && typeof error.body === "object" && "detail" in error.body) {
    const detail = (error.body as { detail?: unknown }).detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg?: unknown }).msg)
            : String(item),
        )
        .join("; ");
    }
    return `HTTP ${error.status}: ${String(detail)}`;
  }
  return `HTTP ${error.status}`;
}

function scoreDisplay(item: RagDebugEvidence) {
  const display = optionalString(item.metadata.score_display);
  if (display) {
    return display;
  }
  return item.score === null || item.score === undefined
    ? "Score unavailable"
    : `Score ${item.score.toFixed(2)}`;
}

function debugItemKey(item: RagDebugEvidence) {
  return item.evidence_id || item.chunk_id || item.wiki_page_id || `${item.rank}-${item.title}`;
}

function formatValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.join(",");
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function optionalString(value: unknown) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value).trim();
}
