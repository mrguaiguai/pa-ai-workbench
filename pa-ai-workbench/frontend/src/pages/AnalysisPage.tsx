import {
  Bot,
  BookOpenText,
  FileSearch,
  FilePlus2,
  Loader2,
  MessageSquareText,
  Plus,
  RefreshCw,
  Scale,
  Send,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  AnalysisTaskType,
  Citation,
  Conversation,
  ConversationMessage,
  GeneratedOutput,
  NativeAgentCatalogResponse,
  NativeAgentItem,
  NativeAgentQaResponse,
  RetrievalScope,
  Task,
  WikiPage,
  apiClient,
} from "../api/client";
import {
  CitationList,
  EmptyState,
  ErrorState,
  ResultPanel,
  TaskProgress,
  WarningList,
  WeKnoraFirstStatusStrip,
  parseWarningsJson,
} from "../components/workbench";

type LoadState = "idle" | "loading" | "error";

const SELECTED_WIKI_STORAGE_KEY = "pa_workbench:selected_wiki_slug";

type AnalysisForm = {
  query: string;
  title: string;
  businessArea: string;
  documentType: string;
  extraRequirements: string;
  retrievalScope: RetrievalScope;
};

const initialForm: AnalysisForm = {
  query: "",
  title: "",
  businessArea: "",
  documentType: "",
  extraRequirements: "",
  retrievalScope: "all",
};

const taskOptions: Array<{
  id: AnalysisTaskType;
  label: string;
  description: string;
  icon: typeof MessageSquareText;
}> = [
  {
    id: "knowledge_qa",
    label: "知识问答",
    description: "基于资料库回答问题",
    icon: MessageSquareText,
  },
  {
    id: "policy_analysis",
    label: "政策分析",
    description: "拆解政策要点与影响",
    icon: Scale,
  },
  {
    id: "case_review",
    label: "案例复盘",
    description: "梳理事实、风险与建议",
    icon: FileSearch,
  },
];

const retrievalScopeOptions: Array<{
  id: RetrievalScope;
  label: string;
  note: string;
}> = [
  {
    id: "all",
    label: "全部知识",
    note: "文档 + Wiki",
  },
  {
    id: "document",
    label: "仅文档",
    note: "资料库文档",
  },
  {
    id: "wiki",
    label: "仅 Wiki",
    note: "已发布 Wiki",
  },
];

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

function roleLabel(role: ConversationMessage["role"]) {
  if (role === "assistant") {
    return "助手";
  }
  if (role === "system_status") {
    return "状态";
  }
  return "你";
}

function citationSourceType(citation: Citation) {
  const metadata = citationMetadata(citation);
  const normalized = String(
    citation.source_type ||
      metadata.citation_source_type ||
      metadata.source_type ||
      (citation.wiki_page_id || metadata.wiki_page_id ? "wiki_page" : ""),
  )
    .trim()
    .toLowerCase();
  if (["document", "document_chunk", "chunk"].includes(normalized)) {
    return "document_chunk";
  }
  if (["wiki", "wiki_page", "wiki-page"].includes(normalized)) {
    return "wiki_page";
  }
  if (citation.source === "mock") {
    return "mock";
  }
  return normalized || "unknown";
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

function ragMode(citations: Citation[]) {
  if (citations.length === 0) {
    return "无可用证据";
  }
  if (citations.some(isWeKnoraCitation)) {
    return "真实 WeKnora RAG";
  }
  if (citations.some((citation) => citation.source !== "mock")) {
    return "真实 RAG";
  }
  return "模拟模式回退";
}

function hasInsufficientEvidenceWarning(warnings: string[]) {
  return warnings.some((warning) =>
    [
      "No evidence",
      "No policy evidence",
      "No case evidence",
      "does not match retrieved evidence",
      "missing",
      "不足",
      "未检索",
    ].some((token) => warning.includes(token)),
  );
}

export function AnalysisPage() {
  const [taskType, setTaskType] = useState<AnalysisTaskType>("knowledge_qa");
  const [form, setForm] = useState<AnalysisForm>(initialForm);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [latestOutput, setLatestOutput] = useState<GeneratedOutput | null>(null);
  const [latestCitations, setLatestCitations] = useState<Citation[]>([]);
  const [latestTask, setLatestTask] = useState<Task | null>(null);
  const [conversationState, setConversationState] = useState<LoadState>("idle");
  const [messageState, setMessageState] = useState<LoadState>("idle");
  const [draftState, setDraftState] = useState<LoadState>("idle");
  const [draftError, setDraftError] = useState<string | null>(null);
  const [createdDraft, setCreatedDraft] = useState<WikiPage | null>(null);
  const [agentCatalog, setAgentCatalog] = useState<NativeAgentCatalogResponse | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [agentState, setAgentState] = useState<LoadState>("idle");
  const [agentRun, setAgentRun] = useState<NativeAgentQaResponse | null>(null);
  const [agentRunState, setAgentRunState] = useState<LoadState>("idle");
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const warnings = useMemo(
    () => parseWarningsJson(latestOutput?.warnings_json),
    [latestOutput],
  );
  const evidenceSummary = useMemo(() => {
    const documentCount = latestCitations.filter(
      (citation) => citationSourceType(citation) === "document_chunk",
    ).length;
    const wikiCount = latestCitations.filter(
      (citation) => citationSourceType(citation) === "wiki_page",
    ).length;
    const weknoraCount = latestCitations.filter(isWeKnoraCitation).length;
    return {
      mode: ragMode(latestCitations),
      documentCount,
      wikiCount,
      weknoraCount,
      totalCount: latestCitations.length,
      insufficient: hasInsufficientEvidenceWarning(warnings),
    };
  }, [latestCitations, warnings]);
  const activeTask = taskOptions.find((option) => option.id === taskType) ?? taskOptions[0];
  const selectedAgent = useMemo(
    () => agentCatalog?.agents.find((agent) => agent.id === selectedAgentId) ?? null,
    [agentCatalog, selectedAgentId],
  );

  const loadConversations = () => {
    setConversationState("loading");
    setError(null);
    apiClient
      .listConversations()
      .then((response) => {
        setConversations(response.items);
        setConversationState("idle");
      })
      .catch((loadError: unknown) => {
        setError(errorMessage(loadError));
        setConversationState("error");
      });
  };

  const loadNativeAgents = () => {
    setAgentState("loading");
    apiClient
      .listNativeAgents()
      .then((catalog) => {
        setAgentCatalog(catalog);
        setSelectedAgentId((current) => current || catalog.selected_agent_id || catalog.agents[0]?.id || "");
        setAgentState("idle");
      })
      .catch((loadError: unknown) => {
        setAgentState("error");
        setError(errorMessage(loadError));
      });
  };

  const loadMessages = (conversation: Conversation) => {
    setMessageState("loading");
    setError(null);
    apiClient
      .listConversationMessages(conversation.id)
      .then((response) => {
        setMessages(response.items);
        setMessageState("idle");
      })
      .catch((loadError: unknown) => {
        setError(errorMessage(loadError));
        setMessageState("error");
      });
  };

  useEffect(() => {
    loadConversations();
    loadNativeAgents();
  }, []);

  const selectConversation = (conversation: Conversation) => {
    setSelectedConversation(conversation);
    setTaskType(conversation.default_task_type as AnalysisTaskType);
    setLatestOutput(null);
    setLatestCitations([]);
    setLatestTask(null);
    setCreatedDraft(null);
    setDraftError(null);
    setDraftState("idle");
    setAgentRun(null);
    loadMessages(conversation);
  };

  const startNewConversation = () => {
    setSelectedConversation(null);
    setMessages([]);
    setLatestOutput(null);
    setLatestCitations([]);
    setLatestTask(null);
    setCreatedDraft(null);
    setDraftError(null);
    setDraftState("idle");
    setAgentRun(null);
    setForm(initialForm);
    setError(null);
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = form.query.trim();
    if (!query) {
      setError("请输入问题或分析主题");
      return;
    }

    setIsRunning(true);
    setError(null);
    apiClient
      .runAnalysis({
        conversation_id: selectedConversation?.id ?? null,
        task_type: taskType,
        title: form.title.trim() || null,
        query_or_topic: query,
        business_area: form.businessArea.trim() || null,
        document_type: form.documentType.trim() || null,
        extra_requirements: form.extraRequirements.trim() || null,
        ...(taskType === "knowledge_qa" ? { retrieval_scope: form.retrievalScope } : {}),
      })
      .then((response) => {
        setSelectedConversation(response.conversation);
        setMessages(response.messages);
        setLatestOutput(response.output);
        setLatestCitations(response.citations);
        setLatestTask(response.task);
        setCreatedDraft(null);
        setDraftError(null);
        setDraftState("idle");
        setForm((current) => ({ ...current, query: "", title: "" }));
        setTaskType(response.conversation.default_task_type as AnalysisTaskType);
        loadConversations();
      })
      .catch((runError: unknown) => setError(errorMessage(runError)))
      .finally(() => setIsRunning(false));
  };

  const runNativeAgent = () => {
    const query = form.query.trim();
    if (!query) {
      setError("请输入问题或分析主题");
      return;
    }
    if (!selectedAgentId) {
      setError("请选择原生 Agent");
      return;
    }

    setAgentRunState("loading");
    setError(null);
    apiClient
      .runNativeAgentQa({
        conversation_id: selectedConversation?.id ?? null,
        query,
        agent_id: selectedAgentId,
        title: form.title.trim() || null,
      })
      .then((response) => {
        setAgentRun(response);
        setSelectedConversation(response.conversation);
        setMessages(response.messages);
        setLatestOutput(response.output);
        setLatestCitations(response.citations);
        setLatestTask(response.task);
        setCreatedDraft(null);
        setDraftError(null);
        setDraftState("idle");
        setForm((current) => ({ ...current, query: "", title: "" }));
        loadConversations();
      })
      .catch((runError: unknown) => setError(errorMessage(runError)))
      .finally(() => setAgentRunState("idle"));
  };

  const createWikiDraft = () => {
    if (!latestOutput || draftState === "loading") {
      return;
    }

    setDraftState("loading");
    setDraftError(null);
    apiClient
      .createWikiDraftFromOutput(latestOutput.id, {
        title: latestOutput.title,
        metadata: {
          source: "analysis_page",
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
    <div className="analysis-page">
      <WeKnoraFirstStatusStrip page="知识问答" />

      <aside className="analysis-conversations" aria-label="会话列表">
        <div className="analysis-panel-heading">
          <span>会话</span>
          <div className="heading-actions">
            <button className="icon-button" type="button" onClick={startNewConversation} title="新会话">
              <Plus size={16} aria-hidden="true" />
            </button>
            <button className="icon-button" type="button" onClick={loadConversations} title="刷新">
              <RefreshCw size={16} aria-hidden="true" />
            </button>
          </div>
        </div>

        {conversationState === "loading" ? (
          <EmptyState text="加载中" loading compact />
        ) : conversations.length === 0 ? (
          <EmptyState text="暂无会话" compact />
        ) : (
          <div className="conversation-list">
            {conversations.map((conversation) => (
              <button
                className={
                  selectedConversation?.id === conversation.id
                    ? "conversation-item active"
                    : "conversation-item"
                }
                key={conversation.id}
                type="button"
                onClick={() => selectConversation(conversation)}
              >
                <strong>{conversation.title}</strong>
                <span>{formatDate(conversation.updated_at)}</span>
              </button>
            ))}
          </div>
        )}
      </aside>

      <section className="analysis-workspace" aria-label="当前会话">
        <div className="analysis-panel-heading">
          <span>消息</span>
          <strong>{selectedConversation?.title ?? "新分析"}</strong>
        </div>

        {error ? <ErrorState message={error} /> : null}

        <div className="message-stream">
          {messageState === "loading" ? (
            <EmptyState text="加载消息中" loading />
          ) : messages.length === 0 ? (
            <EmptyState icon={MessageSquareText} text="从右侧提交一个问题开始" />
          ) : (
            messages.map((message) => (
              <article className={`message-bubble ${message.role}`} key={message.id}>
                <div className="message-meta">
                  <strong>{roleLabel(message.role)}</strong>
                  <span>{formatDate(message.created_at)}</span>
                </div>
                <p>{message.content}</p>
              </article>
            ))
          )}
        </div>

        {latestOutput ? (
          <ResultPanel title={latestOutput.title} content={latestOutput.content_markdown} />
        ) : null}
      </section>

      <aside className="analysis-tools" aria-label="分析参数">
        <form className="analysis-form" onSubmit={onSubmit}>
          <div className="analysis-panel-heading">
            <span>分析流</span>
            <strong>{activeTask.label}</strong>
          </div>

          <div className="task-switcher" role="tablist" aria-label="任务类型">
            {taskOptions.map((option) => {
              const Icon = option.icon;
              return (
                <button
                  className={option.id === taskType ? "task-option active" : "task-option"}
                  key={option.id}
                  type="button"
                  onClick={() => setTaskType(option.id)}
                >
                  <Icon size={16} aria-hidden="true" />
                  <span>{option.label}</span>
                </button>
              );
            })}
          </div>

          <p className="task-description">{activeTask.description}</p>

          {taskType === "knowledge_qa" ? (
            <fieldset className="knowledge-source-switcher">
              <legend>知识来源</legend>
              <div className="scope-options" role="radiogroup" aria-label="知识来源">
                {retrievalScopeOptions.map((option) => (
                  <button
                    className={
                      option.id === form.retrievalScope ? "scope-option active" : "scope-option"
                    }
                    key={option.id}
                    type="button"
                    role="radio"
                    aria-checked={option.id === form.retrievalScope}
                    onClick={() =>
                      setForm((current) => ({
                        ...current,
                        retrievalScope: option.id,
                      }))
                    }
                  >
                    <strong>{option.label}</strong>
                    <span>{option.note}</span>
                  </button>
                ))}
              </div>
            </fieldset>
          ) : null}

          <div className="form-grid analysis-fields">
            <label>
              <span>问题或主题</span>
              <textarea
                rows={5}
                value={form.query}
                onChange={(event) => setForm({ ...form, query: event.target.value })}
              />
            </label>
            <label>
              <span>标题</span>
              <input
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
              />
            </label>
            <label>
              <span>业务域</span>
              <input
                value={form.businessArea}
                onChange={(event) => setForm({ ...form, businessArea: event.target.value })}
              />
            </label>
            <label>
              <span>资料类型</span>
              <input
                value={form.documentType}
                onChange={(event) => setForm({ ...form, documentType: event.target.value })}
              />
            </label>
            <label>
              <span>额外要求</span>
              <textarea
                rows={4}
                value={form.extraRequirements}
                onChange={(event) =>
                  setForm({ ...form, extraRequirements: event.target.value })
                }
              />
            </label>
          </div>

          <button className="primary-action" type="submit" disabled={isRunning}>
            {isRunning ? <Loader2 size={16} aria-hidden="true" /> : <Send size={16} />}
            <span>{isRunning ? "分析中" : "运行分析"}</span>
          </button>
        </form>

        {latestTask ? <TaskProgress task={latestTask} /> : null}

        <section className="native-agent-panel" aria-label="原生 AgentQA">
          <div className="analysis-panel-heading">
            <span>原生 AgentQA</span>
            <strong>{selectedAgent?.name ?? "未选择"}</strong>
          </div>

          {agentState === "loading" ? (
            <EmptyState text="加载 Agent" loading compact />
          ) : agentState === "error" ? (
            <ErrorState message="原生 Agent 列表不可用" />
          ) : (
            <>
              <AgentPicker
                agents={agentCatalog?.agents ?? []}
                selectedAgentId={selectedAgentId}
                onSelect={setSelectedAgentId}
              />
              <NativeAgentStatus catalog={agentCatalog} selectedAgent={selectedAgent} />
            </>
          )}

          <button
            className="secondary-action"
            type="button"
            disabled={agentRunState === "loading" || !selectedAgentId}
            onClick={runNativeAgent}
          >
            {agentRunState === "loading" ? (
              <Loader2 size={16} aria-hidden="true" />
            ) : (
              <Bot size={16} aria-hidden="true" />
            )}
            <span>{agentRunState === "loading" ? "运行中" : "运行原生 Agent"}</span>
          </button>

          {agentRun ? (
            <div className="native-agent-result">
              <span>{agentRun.runtime.source}</span>
              <strong>
                references {agentRun.runtime.reference_count} / citations{" "}
                {agentRun.runtime.saved_citation_count}
              </strong>
              <p>{agentRun.runtime.citation_blocked ? "Citation blocker 已记录" : "Citation 已绑定"}</p>
              {agentRun.runtime.tool_names.length > 0 ? (
                <small>{agentRun.runtime.tool_names.join(", ")}</small>
              ) : null}
            </div>
          ) : null}
        </section>

        <section className="wiki-draft-action" aria-label="Wiki 草稿">
          <div className="analysis-panel-heading">
            <span>Wiki 草稿</span>
            <strong>{createdDraft?.status ?? "准备就绪"}</strong>
          </div>

          <button
            className="secondary-action"
            type="button"
            disabled={!latestOutput || draftState === "loading"}
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
            <div className="wiki-draft-result">
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

        <section className="citation-panel" aria-label="引用与警告">
          <div className="analysis-panel-heading">
            <span>证据</span>
            <strong>{latestCitations.length}</strong>
          </div>

          <div className="rag-summary">
            <div
              className={`rag-mode ${
                evidenceSummary.mode.includes("真实") ? "real" : ""
              } ${evidenceSummary.mode.includes("WeKnora") ? "weknora" : ""}`}
            >
              <span>RAG</span>
              <strong>{evidenceSummary.mode}</strong>
            </div>
            <div className="rag-source-counts">
              <span>文档 {evidenceSummary.documentCount}</span>
              <span>Wiki {evidenceSummary.wikiCount}</span>
              <span>WeKnora {evidenceSummary.weknoraCount}</span>
            </div>
            <div className="rag-source-counts compact">
              <span>合计 {evidenceSummary.totalCount}</span>
              <span>{latestTask?.task_type ?? taskType}</span>
              <span>{latestTask?.status ?? "准备就绪"}</span>
            </div>
            {evidenceSummary.insufficient ? (
              <div className="evidence-warning">依据不足或引用需要复核</div>
            ) : null}
          </div>

          <WarningList warnings={warnings} emptyText="暂无依据不足提示" />
          <CitationList citations={latestCitations} />
        </section>
      </aside>
    </div>
  );
}

function AgentPicker({
  agents,
  selectedAgentId,
  onSelect,
}: {
  agents: NativeAgentItem[];
  selectedAgentId: string;
  onSelect: (agentId: string) => void;
}) {
  if (agents.length === 0) {
    return <EmptyState icon={Bot} text="暂无可用原生 Agent" compact />;
  }
  return (
    <div className="native-agent-list" role="listbox" aria-label="原生 Agent">
      {agents.slice(0, 6).map((agent) => (
        <button
          className={agent.id === selectedAgentId ? "native-agent-option active" : "native-agent-option"}
          key={agent.id ?? agent.name}
          type="button"
          role="option"
          aria-selected={agent.id === selectedAgentId}
          onClick={() => onSelect(agent.id ?? "")}
        >
          <Bot size={16} aria-hidden="true" />
          <span>
            <strong>{agent.name}</strong>
            <small>{agent.agent_mode}</small>
          </span>
        </button>
      ))}
    </div>
  );
}

function NativeAgentStatus({
  catalog,
  selectedAgent,
}: {
  catalog: NativeAgentCatalogResponse | null;
  selectedAgent: NativeAgentItem | null;
}) {
  if (!catalog) {
    return null;
  }
  return (
    <div className="native-agent-status">
      <span>{catalog.status}</span>
      <span>agents {catalog.agents.length}</span>
      <span>presets {catalog.presets.length}</span>
      <span>copy {catalog.surfaces.copy ?? "backlog"}</span>
      {selectedAgent ? (
        <span>{selectedAgent.allowed_tools.length} tools</span>
      ) : null}
    </div>
  );
}
