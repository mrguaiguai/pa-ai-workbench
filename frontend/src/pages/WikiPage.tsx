import {
  BookOpenText,
  Loader2,
  RefreshCw,
  Search,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  WikiPage as WikiPageDetail,
  WikiPageSummary,
  apiClient,
} from "../api/client";
import {
  CitationList,
  EmptyState,
  ErrorState,
} from "../components/workbench";

type LoadState = "idle" | "loading" | "error";

type SearchForm = {
  query: string;
  kbId: string;
  limit: string;
};

const initialForm: SearchForm = {
  query: "",
  kbId: "",
  limit: "10",
};

function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return `HTTP ${error.status}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error";
}

function metadataEntries(metadata: Record<string, unknown>) {
  return Object.entries(metadata)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => [key, typeof value === "string" ? value : JSON.stringify(value)]);
}

export function WikiPage() {
  const [form, setForm] = useState<SearchForm>(initialForm);
  const [results, setResults] = useState<WikiPageSummary[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [page, setPage] = useState<WikiPageDetail | null>(null);
  const [searchState, setSearchState] = useState<LoadState>("idle");
  const [pageState, setPageState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);

  const selectedSummary = useMemo(
    () => results.find((result) => result.slug === selectedSlug) ?? null,
    [results, selectedSlug],
  );

  const runSearch = (nextForm = form) => {
    setSearchState("loading");
    setError(null);
    apiClient
      .searchWiki(
        nextForm.query.trim(),
        nextForm.kbId.trim() || undefined,
        Number(nextForm.limit) || 10,
      )
      .then((response) => {
        setResults(response.items);
        setSearchState("idle");
        const nextSlug = response.items[0]?.slug ?? null;
        setSelectedSlug(nextSlug);
        if (nextSlug) {
          loadPage(nextSlug, nextForm.kbId.trim() || undefined);
        } else {
          setPage(null);
        }
      })
      .catch((searchError: unknown) => {
        setError(errorMessage(searchError));
        setSearchState("error");
      });
  };

  const loadPage = (slug: string, kbId = form.kbId.trim() || undefined) => {
    setPageState("loading");
    setError(null);
    apiClient
      .getWikiPage(slug, kbId)
      .then((response) => {
        setPage(response);
        setSelectedSlug(response.slug);
        setPageState("idle");
      })
      .catch((pageError: unknown) => {
        setError(errorMessage(pageError));
        setPageState("error");
      });
  };

  useEffect(() => {
    runSearch(initialForm);
  }, []);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    runSearch();
  };

  const onSelectPage = (slug: string) => {
    setSelectedSlug(slug);
    loadPage(slug);
  };

  return (
    <div className="wiki-page">
      <aside className="wiki-search-panel" aria-label="Wiki 搜索">
        <form className="wiki-search-form" onSubmit={onSubmit}>
          <div className="wiki-panel-heading">
            <span>Search</span>
            <button
              className={searchState === "loading" ? "icon-button loading" : "icon-button"}
              type="submit"
              title="搜索"
              disabled={searchState === "loading"}
            >
              {searchState === "loading" ? (
                <Loader2 size={16} aria-hidden="true" />
              ) : (
                <Search size={16} aria-hidden="true" />
              )}
            </button>
          </div>

          <div className="form-grid wiki-fields">
            <label>
              <span>关键词</span>
              <input
                value={form.query}
                onChange={(event) => setForm({ ...form, query: event.target.value })}
              />
            </label>
            <label>
              <span>KB ID</span>
              <input
                value={form.kbId}
                onChange={(event) => setForm({ ...form, kbId: event.target.value })}
              />
            </label>
            <label>
              <span>数量</span>
              <select
                value={form.limit}
                onChange={(event) => setForm({ ...form, limit: event.target.value })}
              >
                <option value="5">5</option>
                <option value="10">10</option>
                <option value="20">20</option>
                <option value="50">50</option>
              </select>
            </label>
          </div>
        </form>

        {error ? <ErrorState message={error} /> : null}

        <section className="wiki-results" aria-label="Wiki 搜索结果">
          <div className="wiki-panel-heading">
            <span>Pages</span>
            <strong>{results.length}</strong>
          </div>

          {searchState === "loading" ? (
            <EmptyState text="加载中" loading />
          ) : results.length === 0 ? (
            <EmptyState icon={BookOpenText} text="暂无页面" />
          ) : (
            <div className="wiki-result-list">
              {results.map((result) => (
                <button
                  className={result.slug === selectedSlug ? "wiki-result active" : "wiki-result"}
                  key={result.slug}
                  type="button"
                  onClick={() => onSelectPage(result.slug)}
                >
                  <strong>{result.title}</strong>
                  <span>{result.page_type}</span>
                  <p>{result.summary}</p>
                </button>
              ))}
            </div>
          )}
        </section>
      </aside>

      <section className="wiki-reader" aria-label="Wiki 页面内容">
        <div className="wiki-panel-heading">
          <span>Reader</span>
          <button
            className={pageState === "loading" ? "icon-button loading" : "icon-button"}
            type="button"
            title="刷新"
            disabled={!selectedSlug || pageState === "loading"}
            onClick={() => selectedSlug && loadPage(selectedSlug)}
          >
            {pageState === "loading" ? (
              <Loader2 size={16} aria-hidden="true" />
            ) : (
              <RefreshCw size={16} aria-hidden="true" />
            )}
          </button>
        </div>

        {pageState === "loading" ? (
          <EmptyState text="读取中" loading wide />
        ) : page ? (
          <article className="wiki-article">
            <div className="wiki-article-title">
              <span>{page.page_type}</span>
              <h2>{page.title}</h2>
              <p>{page.summary}</p>
            </div>

            <div className="wiki-meta-row">
              <span>{page.source}</span>
              <span>{page.slug}</span>
              {metadataEntries(page.metadata).map(([key, value]) => (
                <span key={key}>{`${key}: ${value}`}</span>
              ))}
            </div>

            <pre>{page.content}</pre>
          </article>
        ) : (
          <EmptyState text={selectedSummary?.title ?? "未选择页面"} wide />
        )}
      </section>

      <aside className="wiki-citation-panel" aria-label="Wiki 引用">
        <div className="wiki-panel-heading">
          <span>Citations</span>
          <strong>{page?.citations.length ?? 0}</strong>
        </div>

        <CitationList citations={page?.citations ?? []} />
      </aside>
    </div>
  );
}
