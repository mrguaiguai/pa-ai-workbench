import {
  BookOpenText,
  CheckCircle2,
  FilePlus2,
  Loader2,
  Pencil,
  RefreshCw,
  Save,
  Search,
  Send,
  X,
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
type EditorMode = "view" | "create" | "edit";

const SELECTED_WIKI_STORAGE_KEY = "pa_workbench:selected_wiki_slug";

type SearchForm = {
  query: string;
  kbId: string;
  limit: string;
};

type WikiEditorForm = {
  slug: string;
  title: string;
  summary: string;
  pageType: string;
  businessArea: string;
  tags: string;
  content: string;
};

const initialForm: SearchForm = {
  query: "",
  kbId: "",
  limit: "10",
};

const emptyEditorForm: WikiEditorForm = {
  slug: "",
  title: "",
  summary: "",
  pageType: "wiki",
  businessArea: "",
  tags: "",
  content: "",
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

function normalizeSlug(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120);
}

function splitTags(value: string) {
  return value
    .split(/[,\n，]/)
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function joinTags(tags?: string[]) {
  return (tags ?? []).join(", ");
}

function formFromPage(page: WikiPageDetail): WikiEditorForm {
  return {
    slug: page.slug,
    title: page.title,
    summary: page.summary ?? "",
    pageType: page.page_type ?? "wiki",
    businessArea: page.business_area ?? "",
    tags: joinTags(page.tags),
    content: page.content_markdown ?? page.content,
  };
}

function summaryFromPage(page: WikiPageDetail): WikiPageSummary {
  return {
    id: page.id,
    slug: page.slug,
    title: page.title,
    page_type: page.page_type,
    summary: page.summary,
    status: page.status,
    tags: page.tags,
    source: page.source,
    metadata: page.metadata,
  };
}

function statusLabel(status?: string | null) {
  if (status === "published") {
    return "published";
  }
  if (status === "archived") {
    return "archived";
  }
  return "draft";
}

export function WikiPage() {
  const [form, setForm] = useState<SearchForm>(initialForm);
  const [results, setResults] = useState<WikiPageSummary[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [page, setPage] = useState<WikiPageDetail | null>(null);
  const [editorMode, setEditorMode] = useState<EditorMode>("view");
  const [editorForm, setEditorForm] = useState<WikiEditorForm>(emptyEditorForm);
  const [searchState, setSearchState] = useState<LoadState>("idle");
  const [pageState, setPageState] = useState<LoadState>("idle");
  const [saveState, setSaveState] = useState<LoadState>("idle");
  const [publishState, setPublishState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [editorError, setEditorError] = useState<string | null>(null);

  const selectedSummary = useMemo(
    () => results.find((result) => result.slug === selectedSlug) ?? null,
    [results, selectedSlug],
  );
  const isEditing = editorMode === "create" || editorMode === "edit";
  const pageStatus = statusLabel(page?.status);

  const upsertResult = (nextPage: WikiPageDetail) => {
    const nextSummary = summaryFromPage(nextPage);
    setResults((current) => {
      const existingIndex = current.findIndex((item) => item.slug === nextSummary.slug);
      if (existingIndex === -1) {
        return [nextSummary, ...current];
      }
      return current.map((item, index) => (index === existingIndex ? nextSummary : item));
    });
  };

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
        setEditorMode("view");
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
        setEditorMode("view");
        setEditorError(null);
        setPageState("idle");
        upsertResult(response);
      })
      .catch((pageError: unknown) => {
        setError(errorMessage(pageError));
        setPageState("error");
      });
  };

  useEffect(() => {
    const pendingSlug = window.sessionStorage.getItem(SELECTED_WIKI_STORAGE_KEY);
    if (pendingSlug) {
      window.sessionStorage.removeItem(SELECTED_WIKI_STORAGE_KEY);
      setSelectedSlug(pendingSlug);
      loadPage(pendingSlug);
      return;
    }
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

  const startCreate = () => {
    setPage(null);
    setSelectedSlug(null);
    setEditorForm(emptyEditorForm);
    setEditorMode("create");
    setEditorError(null);
    setError(null);
  };

  const startEdit = () => {
    if (!page) {
      return;
    }
    setEditorForm(formFromPage(page));
    setEditorMode("edit");
    setEditorError(null);
  };

  const cancelEdit = () => {
    setEditorMode("view");
    setEditorError(null);
  };

  const savePage = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const title = editorForm.title.trim();
    const content = editorForm.content.trim();
    const slug = normalizeSlug(editorForm.slug || title);

    if (!title || !slug) {
      setEditorError("标题和 slug 不能为空");
      return;
    }

    setSaveState("loading");
    setEditorError(null);

    const payload = {
      title,
      summary: editorForm.summary.trim() || null,
      content_markdown: content,
      tags: splitTags(editorForm.tags),
      business_area: editorForm.businessArea.trim() || null,
      page_type: editorForm.pageType.trim() || "wiki",
      metadata: {
        source: "wiki_editor",
      },
    };

    const request =
      editorMode === "create"
        ? apiClient.createWikiPage({
            slug,
            ...payload,
          })
        : apiClient.updateWikiPage(page?.slug ?? slug, payload);

    request
      .then((response) => {
        setPage(response);
        setSelectedSlug(response.slug);
        setEditorForm(formFromPage(response));
        setEditorMode("view");
        setSaveState("idle");
        upsertResult(response);
      })
      .catch((saveError: unknown) => {
        setEditorError(errorMessage(saveError));
        setSaveState("error");
      });
  };

  const publishPage = () => {
    if (!page || publishState === "loading") {
      return;
    }

    setPublishState("loading");
    setError(null);
    apiClient
      .publishWikiPage(page.slug)
      .then((response) => {
        setPage(response);
        setSelectedSlug(response.slug);
        setPublishState("idle");
        upsertResult(response);
      })
      .catch((publishError: unknown) => {
        setError(errorMessage(publishError));
        setPublishState("error");
      });
  };

  return (
    <div className="wiki-page">
      <aside className="wiki-search-panel" aria-label="Wiki 搜索">
        <form className="wiki-search-form" onSubmit={onSubmit}>
          <div className="wiki-panel-heading">
            <span>Search</span>
            <div className="heading-actions">
              <button className="icon-button" type="button" title="新建 Wiki" onClick={startCreate}>
                <FilePlus2 size={16} aria-hidden="true" />
              </button>
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
                  <span>{statusLabel(result.status)}</span>
                  <p>{result.summary || result.page_type || result.slug}</p>
                </button>
              ))}
            </div>
          )}
        </section>
      </aside>

      <section className="wiki-reader" aria-label="Wiki 页面内容">
        <div className="wiki-panel-heading">
          <span>{isEditing ? "Editor" : "Reader"}</span>
          <div className="heading-actions">
            {page && !isEditing ? (
              <>
                <button className="icon-button" type="button" title="编辑" onClick={startEdit}>
                  <Pencil size={16} aria-hidden="true" />
                </button>
                <button
                  className={publishState === "loading" ? "icon-button loading" : "icon-button"}
                  type="button"
                  title={pageStatus === "published" ? "已发布" : "发布"}
                  disabled={publishState === "loading" || pageStatus === "published"}
                  onClick={publishPage}
                >
                  {publishState === "loading" ? (
                    <Loader2 size={16} aria-hidden="true" />
                  ) : pageStatus === "published" ? (
                    <CheckCircle2 size={16} aria-hidden="true" />
                  ) : (
                    <Send size={16} aria-hidden="true" />
                  )}
                </button>
              </>
            ) : null}
            {!isEditing ? (
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
            ) : null}
          </div>
        </div>

        {pageState === "loading" ? (
          <EmptyState text="读取中" loading wide />
        ) : isEditing ? (
          <form className="wiki-editor-form" onSubmit={savePage}>
            {editorError ? <ErrorState message={editorError} /> : null}

            <div className="form-grid wiki-editor-fields">
              <label>
                <span>标题</span>
                <input
                  value={editorForm.title}
                  onChange={(event) => setEditorForm({ ...editorForm, title: event.target.value })}
                />
              </label>
              <label>
                <span>Slug</span>
                <input
                  value={editorForm.slug}
                  disabled={editorMode === "edit"}
                  placeholder="留空时按标题生成"
                  onChange={(event) =>
                    setEditorForm({ ...editorForm, slug: normalizeSlug(event.target.value) })
                  }
                />
              </label>
              <label>
                <span>类型</span>
                <input
                  value={editorForm.pageType}
                  onChange={(event) =>
                    setEditorForm({ ...editorForm, pageType: event.target.value })
                  }
                />
              </label>
              <label>
                <span>业务域</span>
                <input
                  value={editorForm.businessArea}
                  onChange={(event) =>
                    setEditorForm({ ...editorForm, businessArea: event.target.value })
                  }
                />
              </label>
              <label className="wide">
                <span>标签</span>
                <input
                  value={editorForm.tags}
                  placeholder="用逗号分隔"
                  onChange={(event) => setEditorForm({ ...editorForm, tags: event.target.value })}
                />
              </label>
              <label className="wide">
                <span>摘要</span>
                <textarea
                  rows={3}
                  value={editorForm.summary}
                  onChange={(event) =>
                    setEditorForm({ ...editorForm, summary: event.target.value })
                  }
                />
              </label>
              <label className="wide">
                <span>Markdown</span>
                <textarea
                  rows={18}
                  value={editorForm.content}
                  onChange={(event) =>
                    setEditorForm({ ...editorForm, content: event.target.value })
                  }
                />
              </label>
            </div>

            <div className="wiki-editor-actions">
              <button className="secondary-action compact" type="button" onClick={cancelEdit}>
                <X size={16} aria-hidden="true" />
                <span>取消</span>
              </button>
              <button className="primary-action compact" type="submit" disabled={saveState === "loading"}>
                {saveState === "loading" ? (
                  <Loader2 size={16} aria-hidden="true" />
                ) : (
                  <Save size={16} aria-hidden="true" />
                )}
                <span>{saveState === "loading" ? "保存中" : "保存草稿"}</span>
              </button>
            </div>
          </form>
        ) : page ? (
          <article className="wiki-article">
            <div className="wiki-article-title">
              <span>{pageStatus}</span>
              <h2>{page.title}</h2>
              <p>{page.summary}</p>
            </div>

            <div className="wiki-meta-row">
              <span>{page.page_type ?? "wiki"}</span>
              <span>{page.slug}</span>
              {page.business_area ? <span>{page.business_area}</span> : null}
              {(page.tags ?? []).map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
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
