import {
  FileSearch,
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
  Task,
  apiClient,
} from "../api/client";
import {
  CitationList,
  EmptyState,
  ErrorState,
  ResultPanel,
  TaskProgress,
  WarningList,
  parseWarningsJson,
} from "../components/workbench";

type LoadState = "idle" | "loading" | "error";

type AnalysisForm = {
  query: string;
  title: string;
  businessArea: string;
  documentType: string;
  extraRequirements: string;
};

const initialForm: AnalysisForm = {
  query: "",
  title: "",
  businessArea: "",
  documentType: "",
  extraRequirements: "",
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

function roleLabel(role: ConversationMessage["role"]) {
  if (role === "assistant") {
    return "Assistant";
  }
  if (role === "system_status") {
    return "Status";
  }
  return "You";
}

function citationSourceType(citation: Citation) {
  const normalized = String(
    citation.source_type || (citation.wiki_page_id ? "wiki_page" : ""),
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

function ragMode(citations: Citation[]) {
  if (citations.length === 0) {
    return "No evidence";
  }
  if (citations.some((citation) => citation.source !== "mock")) {
    return "Real RAG";
  }
  return "Mock fallback";
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
    return {
      mode: ragMode(latestCitations),
      documentCount,
      wikiCount,
      totalCount: latestCitations.length,
      insufficient: hasInsufficientEvidenceWarning(warnings),
    };
  }, [latestCitations, warnings]);
  const activeTask = taskOptions.find((option) => option.id === taskType) ?? taskOptions[0];

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
  }, []);

  const selectConversation = (conversation: Conversation) => {
    setSelectedConversation(conversation);
    setTaskType(conversation.default_task_type as AnalysisTaskType);
    setLatestOutput(null);
    setLatestCitations([]);
    setLatestTask(null);
    loadMessages(conversation);
  };

  const startNewConversation = () => {
    setSelectedConversation(null);
    setMessages([]);
    setLatestOutput(null);
    setLatestCitations([]);
    setLatestTask(null);
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
      })
      .then((response) => {
        setSelectedConversation(response.conversation);
        setMessages(response.messages);
        setLatestOutput(response.output);
        setLatestCitations(response.citations);
        setLatestTask(response.task);
        setForm((current) => ({ ...current, query: "", title: "" }));
        setTaskType(response.conversation.default_task_type as AnalysisTaskType);
        loadConversations();
      })
      .catch((runError: unknown) => setError(errorMessage(runError)))
      .finally(() => setIsRunning(false));
  };

  return (
    <div className="analysis-page">
      <aside className="analysis-conversations" aria-label="会话列表">
        <div className="analysis-panel-heading">
          <span>Conversations</span>
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
          <span>Messages</span>
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
            <span>Workflow</span>
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

        <section className="citation-panel" aria-label="引用与警告">
          <div className="analysis-panel-heading">
            <span>Evidence</span>
            <strong>{latestCitations.length}</strong>
          </div>

          <div className="rag-summary">
            <div className={`rag-mode ${evidenceSummary.mode === "Real RAG" ? "real" : ""}`}>
              <span>RAG</span>
              <strong>{evidenceSummary.mode}</strong>
            </div>
            <div className="rag-source-counts">
              <span>Document {evidenceSummary.documentCount}</span>
              <span>Wiki {evidenceSummary.wikiCount}</span>
              <span>Total {evidenceSummary.totalCount}</span>
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
