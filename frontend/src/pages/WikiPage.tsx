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
  ShieldCheck,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  BackendCapabilitiesResponse,
  WikiPage as WikiPageDetail,
  WikiCitation,
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

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "not set";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
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

function metadataString(metadata: Record<string, unknown> | undefined, key: string) {
  const value = metadata?.[key];
  if (value === null || value === undefined || value === "") {
    return null;
  }
  return String(value);
}

function indexStatus(page: WikiPageDetail | null) {
  if (!page) {
    return "not loaded";
  }
  if (page.wiki_state) {
    return page.wiki_state.replace(/_/g, " ");
  }
  const status = statusLabel(page.status);
  const syncStatus = metadataString(page.metadata, "weknora_sync_status");
  const weknoraIndexStatus = metadataString(page.metadata, "weknora_index_status");
  if (status !== "published") {
    return "draft not searchable";
  }
  if (syncStatus === "failed") {
    return "sync failed";
  }
  if (page.embedding_status === "indexed" || page.indexed_at || page.vector_id) {
    return "indexed searchable";
  }
  if (page.embedding_status === "indexing" || weknoraIndexStatus === "indexing") {
    return "indexing";
  }
  if (page.embedding_status) {
    return page.embedding_status;
  }
  return "published not indexed";
}

function indexStatusClass(page: WikiPageDetail | null) {
  return indexStatus(page).replace(/\s+/g, "-").toLowerCase();
}

function ragAvailability(page: WikiPageDetail | null) {
  const status = indexStatus(page);
  if (page?.wiki_retrievable || status === "retrievable" || status === "indexed searchable") {
    return {
      label: "可被 RAG 检索",
      className: "searchable",
      hint: page?.wiki_message || "页面已发布并完成索引。",
    };
  }
  if (status === "indexing") {
    return {
      label: "索引中",
      className: "indexing",
      hint: page?.wiki_message || "页面已发布，但索引完成前不要视为可检索。",
    };
  }
  if (status === "sync failed" || status === "publish failed") {
    return {
      label: "同步失败",
      className: "failed",
      hint: page?.wiki_message || "发布或同步 WeKnora 失败，需要查看错误并重试。",
    };
  }
  if (
    status === "published not indexed" ||
    status === "published not retrievable" ||
    status === "index timeout" ||
    status === "refresh failed"
  ) {
    return {
      label: "未进入 RAG",
      className: "not-indexed",
      hint: page?.wiki_message || "页面已发布，但尚未完成索引。",
    };
  }
  return {
    label: "草稿不可检索",
    className: "draft",
    hint: page?.wiki_message || "发布前不会进入 RAG 检索。",
  };
}

function evidenceTypeLabel(sourceType?: string | null) {
  const normalized = String(sourceType || "").trim().toLowerCase();
  if (["document", "document_chunk", "chunk"].includes(normalized)) {
    return "Document";
  }
  if (["wiki", "wiki_page", "wiki-page"].includes(normalized)) {
    return "Wiki";
  }
  if (normalized === "mock") {
    return "Mock";
  }
  return normalized || "Evidence";
}

function wikiCitationScoreDisplay(citation: WikiCitation) {
  const display = optionalString(citation.metadata?.score_display);
  if (display) {
    return display;
  }
  if (citation.score === null || citation.score === undefined) {
    return "Score unavailable";
  }
  return `Score ${citation.score.toFixed(2)}`;
}

function wikiCitationScoreTitle(citation: WikiCitation) {
  return (
    optionalString(citation.metadata?.score_semantics) ||
    (citation.score === null || citation.score === undefined
      ? "No backend score returned"
      : "Backend retrieval score")
  );
}

function optionalString(value: unknown) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value).trim();
}

function sourceRefCount(page: WikiPageDetail | null) {
  if (!page) {
    return 0;
  }
  return (
    (page.source_output_id ? 1 : 0) +
    (page.source_document_ids?.length ?? 0) +
    (page.source_citation_ids?.length ?? 0)
  );
}

function publishRisks(page: WikiPageDetail, availability: ReturnType<typeof ragAvailability>) {
  const risks: string[] = [];
  if (sourceRefCount(page) === 0 && (page.wiki_citations?.length ?? 0) === 0) {
    risks.push("No source refs or citation bindings are attached.");
  }
  if (!page.content.trim()) {
    risks.push("Page content is empty.");
  }
  if (availability.className !== "searchable") {
    risks.push("Published pages are not considered retrievable until indexing succeeds.");
  }
  if (page.source === "mock") {
    risks.push("This page is backed by mock data.");
  }
  return risks;
}

function PublishConfirmPanel({
  page,
  availability,
  onCancel,
  onConfirm,
  loading,
}: {
  page: WikiPageDetail;
  availability: ReturnType<typeof ragAvailability>;
  onCancel: () => void;
  onConfirm: () => void;
  loading: boolean;
}) {
  const risks = publishRisks(page, availability);
  return (
    <section className="wiki-publish-confirm" aria-label="发布确认">
      <div>
        <strong>Publish confirmation</strong>
        <span>{availability.label}</span>
      </div>
      <p>{availability.hint}</p>
      <div className="wiki-ref-list compact">
        <span>{`source refs: ${sourceRefCount(page)}`}</span>
        <span>{`bindings: ${page.wiki_citations?.length ?? 0}`}</span>
        <span>{`citations: ${page.citations.length}`}</span>
        <span>{`status: ${page.status ?? "draft"}`}</span>
      </div>
      {risks.length ? (
        <div className="wiki-publish-risks">
          {risks.map((risk) => (
            <span key={risk}>{risk}</span>
          ))}
        </div>
      ) : null}
      <div className="wiki-publish-actions">
        <button className="secondary-action compact" type="button" onClick={onCancel}>
          <X size={16} aria-hidden="true" />
          <span>取消</span>
        </button>
        <button className="primary-action compact" type="button" onClick={onConfirm} disabled={loading}>
          {loading ? <Loader2 size={16} aria-hidden="true" /> : <Send size={16} aria-hidden="true" />}
          <span>{loading ? "发布中" : "确认发布"}</span>
        </button>
      </div>
    </section>
  );
}

function wikiSlugFromHash() {
  const query = window.location.hash.split("?")[1] || "";
  return new URLSearchParams(query).get("slug");
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
  const [indexState, setIndexState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [editorError, setEditorError] = useState<string | null>(null);
  const [editorNotice, setEditorNotice] = useState<string | null>(null);
  const [publishConfirmOpen, setPublishConfirmOpen] = useState(false);
  const [capabilities, setCapabilities] = useState<BackendCapabilitiesResponse | null>(null);

  const selectedSummary = useMemo(
    () => results.find((result) => result.slug === selectedSlug) ?? null,
    [results, selectedSlug],
  );
  const isEditing = editorMode === "create" || editorMode === "edit";
  const pageStatus = statusLabel(page?.status);
  const availability = ragAvailability(page);
  const featureFlags = capabilities?.feature_flags.ui;
  const wikiWriteAvailable = featureFlags?.can_create_update_publish_wiki !== false;
  const statusRecoveryAvailable = featureFlags?.can_recover_status !== false;

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
        setEditorNotice(null);
        setPublishConfirmOpen(false);
        setIndexState("idle");
        setPageState("idle");
        upsertResult(response);
      })
      .catch((pageError: unknown) => {
        setError(errorMessage(pageError));
        setPageState("error");
      });
  };

  useEffect(() => {
    let isMounted = true;
    apiClient
      .getCapabilities()
      .then((response) => {
        if (isMounted) {
          setCapabilities(response);
        }
      })
      .catch(() => {
        if (isMounted) {
          setCapabilities(null);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    const onLocate = () => {
      const nextSlug = wikiSlugFromHash();
      if (nextSlug) {
        setSelectedSlug(nextSlug);
        loadPage(nextSlug);
      }
    };
    window.addEventListener("pa:citation-locate", onLocate);
    window.addEventListener("hashchange", onLocate);

    const hashSlug = wikiSlugFromHash();
    if (hashSlug) {
      setSelectedSlug(hashSlug);
      loadPage(hashSlug);
      return () => {
        window.removeEventListener("pa:citation-locate", onLocate);
        window.removeEventListener("hashchange", onLocate);
      };
    }
    const pendingSlug = window.sessionStorage.getItem(SELECTED_WIKI_STORAGE_KEY);
    if (pendingSlug) {
      window.sessionStorage.removeItem(SELECTED_WIKI_STORAGE_KEY);
      setSelectedSlug(pendingSlug);
      loadPage(pendingSlug);
      return () => {
        window.removeEventListener("pa:citation-locate", onLocate);
        window.removeEventListener("hashchange", onLocate);
      };
    }
    runSearch(initialForm);
    return () => {
      window.removeEventListener("pa:citation-locate", onLocate);
      window.removeEventListener("hashchange", onLocate);
    };
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
    if (!wikiWriteAvailable) {
      setError("Wiki write actions are unavailable for the active backend.");
      return;
    }
    setPage(null);
    setSelectedSlug(null);
    setEditorForm(emptyEditorForm);
    setEditorMode("create");
    setEditorError(null);
    setEditorNotice(null);
    setPublishConfirmOpen(false);
    setIndexState("idle");
    setError(null);
  };

  const startEdit = () => {
    if (!page || !wikiWriteAvailable) {
      return;
    }
    setEditorForm(formFromPage(page));
    setEditorMode("edit");
    setEditorError(null);
    setEditorNotice(null);
    setPublishConfirmOpen(false);
  };

  const cancelEdit = () => {
    setEditorMode("view");
    setEditorError(null);
    setEditorNotice(null);
  };

  const savePage = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!wikiWriteAvailable) {
      setEditorError("Wiki write actions are unavailable for the active backend.");
      return;
    }
    const title = editorForm.title.trim();
    const content = editorForm.content.trim();
    const slug = normalizeSlug(editorForm.slug || title);

    if (!title || !slug) {
      setEditorError("标题和 slug 不能为空");
      return;
    }

    setSaveState("loading");
    setEditorError(null);
    setEditorNotice(null);

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
        setEditorNotice("Draft saved.");
        setPublishConfirmOpen(false);
        setIndexState("idle");
        upsertResult(response);
      })
      .catch((saveError: unknown) => {
        setEditorError(errorMessage(saveError));
        setSaveState("error");
      });
  };

  const requestPublish = () => {
    if (!page || !wikiWriteAvailable || publishState === "loading" || pageStatus === "published") {
      return;
    }
    setPublishConfirmOpen(true);
  };

  const publishPage = () => {
    if (!page || !wikiWriteAvailable || publishState === "loading") {
      return;
    }

    setPublishState("loading");
    setError(null);
    setPublishConfirmOpen(false);
    apiClient
      .publishWikiPage(page.slug)
      .then((response) => {
        setPage(response);
        setSelectedSlug(response.slug);
        setPublishState("idle");
        setIndexState("idle");
        upsertResult(response);
      })
      .catch((publishError: unknown) => {
        setError(errorMessage(publishError));
        setPublishState("error");
      });
  };

  const reindexPage = () => {
    if (!page || !statusRecoveryAvailable || indexState === "loading") {
      return;
    }

    setIndexState("loading");
    setError(null);
    const request = page.wiki_retryable
      ? apiClient.recoverWikiStatus(page.slug)
      : apiClient.refreshWikiStatus(page.slug);
    request
      .then((response) => {
        setPage(response);
        setSelectedSlug(response.slug);
        setIndexState("idle");
        upsertResult(response);
      })
      .catch((indexError: unknown) => {
        setError(errorMessage(indexError));
        setIndexState("error");
      });
  };

  return (
    <div className="wiki-page">
      <aside className="wiki-search-panel" aria-label="Wiki 搜索">
        <form className="wiki-search-form" onSubmit={onSubmit}>
          <div className="wiki-panel-heading">
            <span>Search</span>
            <div className="heading-actions">
              <button
                className="icon-button"
                type="button"
                title={wikiWriteAvailable ? "新建 Wiki" : "Wiki 写入不可用"}
                disabled={!wikiWriteAvailable}
                onClick={startCreate}
              >
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
                <button
                  className="icon-button"
                  type="button"
                  title={wikiWriteAvailable ? "编辑" : "Wiki 写入不可用"}
                  disabled={!wikiWriteAvailable}
                  onClick={startEdit}
                >
                  <Pencil size={16} aria-hidden="true" />
                </button>
                <button
                  className={publishState === "loading" ? "icon-button loading" : "icon-button"}
                  type="button"
                  title={
                    !wikiWriteAvailable
                      ? "Wiki 写入不可用"
                      : pageStatus === "published"
                        ? "已发布"
                        : "发布"
                  }
                  disabled={!wikiWriteAvailable || publishState === "loading" || pageStatus === "published"}
                  onClick={requestPublish}
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
                title={statusRecoveryAvailable ? "刷新状态" : "状态恢复不可用"}
                disabled={!selectedSlug || !statusRecoveryAvailable || pageState === "loading"}
                onClick={() => {
                  if (!selectedSlug) {
                    return;
                  }
                  setPageState("loading");
                  setError(null);
                  apiClient
                    .refreshWikiStatus(selectedSlug)
                    .then((response) => {
                      setPage(response);
                      setSelectedSlug(response.slug);
                      setPageState("idle");
                      upsertResult(response);
                    })
                    .catch((refreshError: unknown) => {
                      setError(errorMessage(refreshError));
                      setPageState("error");
                    });
                }}
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
            {editorNotice ? <div className="wiki-editor-notice">{editorNotice}</div> : null}

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
              <button
                className="primary-action compact"
                type="submit"
                disabled={!wikiWriteAvailable || saveState === "loading"}
              >
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
            {editorNotice ? <div className="wiki-editor-notice">{editorNotice}</div> : null}
            {publishConfirmOpen ? (
              <PublishConfirmPanel
                page={page}
                availability={availability}
                onCancel={() => setPublishConfirmOpen(false)}
                onConfirm={publishPage}
                loading={publishState === "loading"}
              />
            ) : null}
            <div className="wiki-article-title">
              <div className="wiki-status-pills">
                <span>{pageStatus}</span>
                <span className={availability.className}>{availability.label}</span>
              </div>
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

      <aside className="wiki-citation-panel" aria-label="Wiki 引用与索引状态">
        <section className="wiki-side-section" aria-label="索引状态">
          <div className="wiki-panel-heading">
            <span>Index</span>
            <div className="heading-actions">
              <strong>{indexStatus(page)}</strong>
              <button
                className={indexState === "loading" ? "icon-button loading" : "icon-button"}
                type="button"
                title={
                  statusRecoveryAvailable
                    ? page?.wiki_retryable
                      ? "恢复 Wiki 状态"
                      : "刷新 Wiki 状态"
                    : "状态恢复不可用"
                }
                disabled={!page || !statusRecoveryAvailable || pageStatus !== "published" || indexState === "loading"}
                onClick={reindexPage}
              >
                {indexState === "loading" ? (
                  <Loader2 size={16} aria-hidden="true" />
                ) : (
                  <RefreshCw size={16} aria-hidden="true" />
                )}
              </button>
            </div>
          </div>

          {page ? (
            <div className="wiki-index-card">
              <div className={`wiki-index-state ${indexStatusClass(page)} ${availability.className}`}>
                <ShieldCheck size={16} aria-hidden="true" />
                <span>{availability.label}</span>
              </div>
              <p className="wiki-index-hint">{availability.hint}</p>
              <div className="wiki-ref-list">
                <span>{`status: ${page.status ?? "draft"}`}</span>
                <span>{`published: ${formatDateTime(page.published_at)}`}</span>
                <span>{`indexed: ${formatDateTime(page.indexed_at)}`}</span>
                <span>{`embedding: ${page.embedding_status ?? "not set"}`}</span>
                <span>{`vector: ${page.vector_id ?? "not set"}`}</span>
                <span>{`weknora sync: ${metadataString(page.metadata, "weknora_sync_status") ?? "not set"}`}</span>
                <span>{`weknora index: ${metadataString(page.metadata, "weknora_index_status") ?? "not set"}`}</span>
                <span>{`retrievable: ${page.wiki_retrievable ? "yes" : "no"}`}</span>
                <span>{`timeout: ${page.wiki_index_timed_out ? "yes" : "no"}`}</span>
              </div>
              {metadataString(page.metadata, "weknora_sync_error") ||
              metadataString(page.metadata, "weknora_index_error") ? (
                <div className="wiki-index-error">
                  {metadataString(page.metadata, "weknora_sync_error") ||
                    metadataString(page.metadata, "weknora_index_error")}
                </div>
              ) : null}
            </div>
          ) : (
            <EmptyState text="未选择页面" compact />
          )}
        </section>

        <section className="wiki-side-section" aria-label="来源引用">
          <div className="wiki-panel-heading">
            <span>Sources</span>
            <strong>{sourceRefCount(page)}</strong>
          </div>

          {page ? (
            <div className="wiki-ref-list">
              {page.source_output_id ? <span>{`output: ${page.source_output_id}`}</span> : null}
              {(page.source_document_ids ?? []).map((documentId) => (
                <span key={`document-${documentId}`}>{`document: ${documentId}`}</span>
              ))}
              {(page.source_citation_ids ?? []).map((citationId) => (
                <span key={`citation-${citationId}`}>{`citation: ${citationId}`}</span>
              ))}
              {sourceRefCount(page) === 0 ? <span>no source refs</span> : null}
            </div>
          ) : (
            <EmptyState text="暂无来源" compact />
          )}
        </section>

        <section className="wiki-side-section" aria-label="Wiki Citation 绑定">
          <div className="wiki-panel-heading">
            <span>Bindings</span>
            <strong>{page?.wiki_citations?.length ?? 0}</strong>
          </div>

          {page?.wiki_citations?.length ? (
            <div className="wiki-binding-list">
              {page.wiki_citations.map((citation) => (
                <article className="wiki-binding-item" key={citation.id}>
                  <div>
                    <strong>{evidenceTypeLabel(citation.source_type)}</strong>
                    <span title={wikiCitationScoreTitle(citation)}>
                      {wikiCitationScoreDisplay(citation)}
                    </span>
                  </div>
                  <p>{citation.excerpt}</p>
                  <div className="wiki-ref-list compact">
                    {citation.document_id ? <span>{`document: ${citation.document_id}`}</span> : null}
                    {citation.chunk_id ? <span>{`chunk: ${citation.chunk_id}`}</span> : null}
                    {citation.output_id ? <span>{`output: ${citation.output_id}`}</span> : null}
                    {citation.citation_id ? <span>{`citation: ${citation.citation_id}`}</span> : null}
                    {citation.evidence_id ? <span>{`evidence: ${citation.evidence_id}`}</span> : null}
                    {citation.external_doc_id ? (
                      <span>{`external: ${citation.external_doc_id}`}</span>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState text="暂无绑定" compact />
          )}
        </section>

        <section className="wiki-side-section" aria-label="Evidence">
          <div className="wiki-panel-heading">
            <span>Evidence</span>
            <strong>{page?.citations.length ?? 0}</strong>
          </div>

          <CitationList citations={page?.citations ?? []} />
        </section>
      </aside>
    </div>
  );
}
