import {
  BookOpen,
  Bot,
  ChevronDown,
  Database,
  FileText,
  Globe2,
  Image as ImageIcon,
  Loader2,
  MessageSquareText,
  MessagesSquare,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Send,
  Sparkles,
  Wrench,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  Citation,
  Conversation,
  ConversationMessage,
  NativeAgentCatalogResponse,
  NativeAgentItem,
  NativeAgentQaResponse,
  NativeAnswerMode,
  NativeAgentStrategy,
  NativeKnowledgeBaseOverviewResponse,
  NativeKnowledgeChatResponse,
  NativeMcpExecutionResponse,
  NativeMcpOverviewResponse,
  NativeMcpPromptReadResponse,
  NativeWebSearchOverviewResponse,
  NativeWebSearchProviderMutationResponse,
  apiClient,
} from "../api/client";
import {
  CitationList,
  EmptyState,
  ErrorState,
  ResultPanel,
  WarningList,
  parseWarningsJson,
} from "../components/workbench";

type LoadState = "idle" | "loading" | "error";
type DialogueMode = "agentqa" | "quickqa";
type DialogueRun = NativeAgentQaResponse | NativeKnowledgeChatResponse;
type AnswerMode = NativeAnswerMode;
const MCP_EXECUTION_CONFIRM_TOKEN = "EXECUTE_NATIVE_MCP_TOOL";
const MCP_TEST_CONFIRM_TOKEN = "TEST_NATIVE_MCP_SERVICE";
const WEB_SEARCH_MUTATION_CONFIRM_TOKEN = "MUTATE_NATIVE_WEB_SEARCH_PROVIDER";
const WEB_SEARCH_TEST_CONFIRM_TOKEN = "TEST_NATIVE_WEB_SEARCH_PROVIDER";
const WIKI_AGENT_RUN_CONFIRM_TOKEN = "CONFIRM_NATIVE_WIKI_AGENT_RUN";
const SAFE_MCP_TOOL_NAME = "ping";
const SAFE_MCP_PROMPT_NAME = "pa-safe-summary";
const SAFE_WEB_SEARCH_PROVIDER = "duckduckgo";
const WIKI_MUTATION_TOOLS = new Set([
  "wiki_write_page",
  "wiki_replace_text",
  "wiki_rename_page",
  "wiki_delete_page",
  "wiki_flag_issue",
  "wiki_update_issue",
]);
const PRIMARY_DIALOGUE_AGENT_IDS = [
  "builtin-quick-answer",
  "builtin-smart-reasoning",
  "builtin-wiki-researcher",
];
const SMART_REASONING_AGENT_ID = "builtin-smart-reasoning";
const ANSWER_MODE_OPTIONS: Array<{ id: AnswerMode; label: string }> = [
  { id: "qa", label: "普通问答" },
  { id: "policy_analysis", label: "政策分析" },
  { id: "case_review", label: "案例复盘" },
];

function isPrimaryDialogueAgent(agent: NativeAgentItem) {
  return Boolean(agent.id && agent.is_builtin && PRIMARY_DIALOGUE_AGENT_IDS.includes(agent.id));
}

function selectDefaultDialogueAgentId(agents: NativeAgentItem[], selectedAgentId?: string | null) {
  if (selectedAgentId && agents.some((agent) => agent.id === selectedAgentId)) {
    return selectedAgentId;
  }
  for (const preferredId of PRIMARY_DIALOGUE_AGENT_IDS) {
    if (agents.some((agent) => agent.id === preferredId)) {
      return preferredId;
    }
  }
  return agents[0]?.id ?? "";
}

function modeForAgent(agent: NativeAgentItem | null): DialogueMode {
  return agent?.agent_mode === "quick-answer" ? "quickqa" : "agentqa";
}

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

function csvValues(value: string) {
  return value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && Boolean(item)) : [];
}

function boolLabel(value: boolean) {
  return value ? "live" : "off";
}

function countLabel(value: unknown) {
  if (typeof value === "number") {
    return String(value);
  }
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  return "0";
}

function numberLabel(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? String(parsed) : value;
  }
  return "0";
}

function stringValue(value: unknown) {
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  return null;
}

function recordValue(record: Record<string, unknown> | undefined, key: string) {
  return record && Object.prototype.hasOwnProperty.call(record, key) ? record[key] : undefined;
}

function nestedRecord(record: Record<string, unknown> | undefined, key: string) {
  const value = recordValue(record, key);
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : undefined;
}

function modeLabel(mode: DialogueMode) {
  return mode === "quickqa" ? "Quick Q&A" : "AgentQA";
}

function answerModeLabel(mode: AnswerMode) {
  return ANSWER_MODE_OPTIONS.find((item) => item.id === mode)?.label ?? "普通问答";
}

function isAgentQaRun(run: DialogueRun | null): run is NativeAgentQaResponse {
  return run?.task.task_type === "native_agentqa";
}

function strategyDefaults(): NativeAgentStrategy {
  return {
    system_prompt: "",
    context_template: "",
    allowed_tools: [],
    mcp_selection_mode: "none",
    mcp_services: [],
    web_search_enabled: false,
    web_search_provider_id: "",
    web_fetch_enabled: false,
    web_fetch_top_n: 0,
    multi_turn_enabled: false,
    history_turns: 0,
    embedding_top_k: 0,
    keyword_threshold: 0,
    vector_threshold: 0,
    rerank_top_k: 0,
    rerank_threshold: 0,
    suggested_prompts: [],
  };
}

function strategyFromAgent(agent: NativeAgentItem | null): NativeAgentStrategy {
  return { ...strategyDefaults(), ...(agent?.strategy ?? {}) };
}

function linesToValues(value: string) {
  return value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function valuesToLines(values: string[]) {
  return values.join("\n");
}

function hasWikiMutationTools(strategy: NativeAgentStrategy) {
  return (strategy.allowed_tools ?? []).some((tool) => WIKI_MUTATION_TOOLS.has(tool));
}

export function DialoguePage() {
  const [catalog, setCatalog] = useState<NativeAgentCatalogResponse | null>(null);
  const [kbOverview, setKbOverview] = useState<NativeKnowledgeBaseOverviewResponse | null>(null);
  const [mcpOverview, setMcpOverview] = useState<NativeMcpOverviewResponse | null>(null);
  const [webSearchOverview, setWebSearchOverview] = useState<NativeWebSearchOverviewResponse | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [query, setQuery] = useState("");
  const [title, setTitle] = useState("");
  const [selectedKbId, setSelectedKbId] = useState("");
  const [knowledgeScope, setKnowledgeScope] = useState("");
  const [answerMode, setAnswerMode] = useState<AnswerMode>("qa");
  const [dialogueMode, setDialogueMode] = useState<DialogueMode>("agentqa");
  const [run, setRun] = useState<DialogueRun | null>(null);
  const [strategyDraft, setStrategyDraft] = useState<NativeAgentStrategy>(strategyDefaults);
  const [strategyState, setStrategyState] = useState<LoadState>("idle");
  const [strategyMessage, setStrategyMessage] = useState<string | null>(null);
  const [catalogState, setCatalogState] = useState<LoadState>("idle");
  const [historyState, setHistoryState] = useState<LoadState>("idle");
  const [messageState, setMessageState] = useState<LoadState>("idle");
  const [runState, setRunState] = useState<LoadState>("idle");
  const [mcpExecutionState, setMcpExecutionState] = useState<LoadState>("idle");
  const [mcpExecutionResult, setMcpExecutionResult] = useState<NativeMcpExecutionResponse | null>(null);
  const [mcpPromptState, setMcpPromptState] = useState<LoadState>("idle");
  const [mcpPromptResult, setMcpPromptResult] = useState<NativeMcpPromptReadResponse | null>(null);
  const [webSearchSetupState, setWebSearchSetupState] = useState<LoadState>("idle");
  const [webSearchSetupResult, setWebSearchSetupResult] = useState<NativeWebSearchProviderMutationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const dialogueAgents = useMemo(() => (catalog?.agents ?? []).filter(isPrimaryDialogueAgent), [catalog]);
  const selectedAgent = useMemo(
    () => dialogueAgents.find((agent) => agent.id === selectedAgentId) ?? null,
    [dialogueAgents, selectedAgentId],
  );
  const warnings = useMemo(() => parseWarningsJson(run?.output.warnings_json), [run]);
  const activeSelection = kbOverview?.active_selection ?? null;
  const kbSelectOptions = useMemo(() => {
    const options = (kbOverview?.items ?? [])
      .filter((item) => Boolean(item.id))
      .map((item) => ({
        id: item.id ?? "",
        name: item.name?.trim() || item.id || "未命名知识库",
        note: `${item.knowledge_count ?? 0} 知识`,
      }));
    if (
      activeSelection?.kb_id &&
      !options.some((item) => item.id === activeSelection.kb_id)
    ) {
      return [
        {
          id: activeSelection.kb_id,
          name: activeSelection.name?.trim() || activeSelection.kb_id,
          note: "当前默认",
        },
        ...options,
      ];
    }
    return options;
  }, [activeSelection, kbOverview]);
  const selectedKb = useMemo(
    () => kbSelectOptions.find((item) => item.id === selectedKbId) ?? null,
    [kbSelectOptions, selectedKbId],
  );
  const selectedKbLabel =
    selectedKb?.name ?? activeSelection?.name ?? activeSelection?.kb_id ?? "默认知识库";
  const runtime = run?.runtime ?? null;
  const safeMcpService = useMemo(() => selectedSafeMcpService(mcpOverview), [mcpOverview]);
  const safeWebSearchProvider = useMemo(
    () => selectedSafeWebSearchProvider(webSearchOverview),
    [webSearchOverview],
  );

  const loadCatalog = () => {
    setCatalogState("loading");
    setError(null);
    Promise.all([
      apiClient.listNativeAgents(),
      apiClient.getNativeKnowledgeBaseOverview(12),
    ])
      .then(([nextCatalog, nextKbOverview]) => {
        const nextDialogueAgents = nextCatalog.agents.filter(isPrimaryDialogueAgent);
        setCatalog(nextCatalog);
        setKbOverview(nextKbOverview);
        setSelectedAgentId((current) =>
          current && nextDialogueAgents.some((agent) => agent.id === current)
            ? current
            : selectDefaultDialogueAgentId(nextDialogueAgents, nextCatalog.selected_agent_id),
        );
        setSelectedKbId((current) =>
          current ||
          nextKbOverview.active_selection?.kb_id ||
          nextCatalog.active_knowledge_base_id ||
          nextKbOverview.items.find((item) => item.id)?.id ||
          "",
        );
        setCatalogState("idle");
      })
      .catch((loadError: unknown) => {
        setCatalogState("error");
        setError(errorMessage(loadError));
      });
  };

  const refreshWebSearch = () => {
    apiClient
      .getNativeWebSearchOverview({ limit: 10 })
      .then(setWebSearchOverview)
      .catch((loadError: unknown) => setError(errorMessage(loadError)));
  };

  const loadConversations = () => {
    setHistoryState("loading");
    setError(null);
    apiClient
      .listConversations()
      .then((response) => {
        setConversations(response.items);
        setHistoryState("idle");
      })
      .catch((loadError: unknown) => {
        setHistoryState("error");
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
        setMessageState("error");
        setError(errorMessage(loadError));
      });
  };

  useEffect(() => {
    loadCatalog();
    loadConversations();
  }, []);

  useEffect(() => {
    setStrategyDraft(strategyFromAgent(selectedAgent));
    setStrategyMessage(null);
  }, [selectedAgentId, selectedAgent]);

  useEffect(() => {
    if (selectedAgent) {
      setDialogueMode(modeForAgent(selectedAgent));
    }
  }, [selectedAgent]);

  const selectConversation = (conversation: Conversation) => {
    setSelectedConversation(conversation);
    setRun(null);
    setError(null);
    loadMessages(conversation);
  };

  const startNewConversation = () => {
    setSelectedConversation(null);
    setMessages([]);
    setRun(null);
    setQuery("");
    setTitle("");
    setError(null);
  };

  const runDialogue = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedQuery = query.trim();
    executeDialogue(normalizedQuery, title.trim() || null);
  };

  const executeDialogue = (normalizedQuery: string, titleOverride: string | null) => {
    if (!normalizedQuery) {
      setError("请输入对话问题");
      return;
    }
    const smartReasoningAgent = dialogueAgents.find((agent) => agent.id === SMART_REASONING_AGENT_ID);
    const effectiveAgentId =
      answerMode === "qa" ? selectedAgentId : smartReasoningAgent?.id ?? selectedAgentId;
    const effectiveDialogueMode: DialogueMode = answerMode === "qa" ? dialogueMode : "agentqa";
    if (answerMode !== "qa" && smartReasoningAgent?.id && selectedAgentId !== smartReasoningAgent.id) {
      setSelectedAgentId(smartReasoningAgent.id);
      setDialogueMode("agentqa");
    }
    if (effectiveDialogueMode === "agentqa" && !effectiveAgentId) {
      setError("请选择原生 Agent");
      return;
    }
    const wikiRunConfirmToken =
      effectiveDialogueMode === "agentqa" && hasWikiMutationTools(strategyDraft)
        ? window.prompt("native Wiki AgentQA mutation run requires confirmation token")
        : null;
    if (effectiveDialogueMode === "agentqa" && hasWikiMutationTools(strategyDraft) && wikiRunConfirmToken !== WIKI_AGENT_RUN_CONFIRM_TOKEN) {
      setError("Wiki AgentQA mutation run requires explicit confirmation");
      return;
    }

    setRunState("loading");
    setError(null);
    const knowledgeBaseIds = selectedKbId ? [selectedKbId] : [];
    const commonPayload = {
      conversation_id: selectedConversation?.id ?? null,
      query: normalizedQuery,
      title: titleOverride,
      knowledge_base_ids: knowledgeBaseIds,
      knowledge_ids: csvValues(knowledgeScope),
      answer_mode: answerMode,
    };
    const request =
      effectiveDialogueMode === "quickqa"
        ? apiClient.runNativeKnowledgeChat({
            ...commonPayload,
            current_run: {
              task_id: "WNID-OPT-03",
              source: "dialogue_shell",
              mode: "quick_q_and_a",
              answer_mode: answerMode,
            },
          })
        : apiClient.runNativeAgentQa({
            ...commonPayload,
            agent_id: effectiveAgentId,
            web_search_enabled: strategyDraft.web_search_enabled,
            confirm_token: wikiRunConfirmToken,
          });
    request
      .then((response) => {
        setRun(response);
        setSelectedConversation(response.conversation);
        setMessages(response.messages);
        setQuery("");
        setTitle("");
        loadConversations();
      })
      .catch((runError: unknown) => setError(errorMessage(runError)))
      .finally(() => setRunState("idle"));
  };

  const saveStrategy = () => {
    if (!selectedAgentId) {
      setError("请选择原生 Agent");
      return;
    }
    setStrategyState("loading");
    setStrategyMessage(null);
    setError(null);
    apiClient
      .updateNativeAgentStrategy(selectedAgentId, {
        ...strategyDraft,
        ["confirm_" + "token"]: "CONFIRM_NATIVE_AGENT_MUTATION",
      })
      .then((response) => {
        const auditStatus = response.audit?.status ?? response.status;
        setStrategyMessage(`strategy ${response.status}; audit ${auditStatus}`);
        loadCatalog();
      })
      .catch((saveError: unknown) => setError(errorMessage(saveError)))
      .finally(() => setStrategyState("idle"));
  };

  const runMcpExecution = (approvalDecision: "approve" | "reject") => {
    if (!safeMcpService?.id) {
      setError("PA Safe Local MCP is not configured");
      return;
    }
    setMcpExecutionState("loading");
    setError(null);
    apiClient
      .setNativeMcpToolApproval(
        safeMcpService.id,
        SAFE_MCP_TOOL_NAME,
        true,
        MCP_EXECUTION_CONFIRM_TOKEN,
      )
      .then(() =>
        apiClient.executeNativeMcpTool(safeMcpService.id, SAFE_MCP_TOOL_NAME, {
          arguments: { message: "wnid-p3-02" },
          approval_decision: approvalDecision,
          conversation_id: selectedConversation?.id ?? run?.conversation.id ?? null,
          confirm_token: MCP_EXECUTION_CONFIRM_TOKEN,
        }),
      )
      .then((result) => {
        setMcpExecutionResult(result);
        setMcpExecutionState("idle");
        loadCatalog();
        loadConversations();
      })
      .catch((executeError: unknown) => {
        setMcpExecutionState("error");
        setError(errorMessage(executeError));
      });
  };

  const readMcpPrompt = () => {
    if (!safeMcpService?.id) {
      setError("PA Safe Local MCP is not configured");
      return;
    }
    setMcpPromptState("loading");
    setError(null);
    apiClient
      .readNativeMcpPrompt(safeMcpService.id, SAFE_MCP_PROMPT_NAME, {
        arguments: {},
        confirm_token: MCP_TEST_CONFIRM_TOKEN,
      })
      .then((result) => {
        setMcpPromptResult(result);
        setMcpPromptState("idle");
        loadCatalog();
      })
      .catch((promptError: unknown) => {
        setMcpPromptState("error");
        setError(errorMessage(promptError));
      });
  };

  const setupDuckDuckGoProvider = () => {
    setWebSearchSetupState("loading");
    setError(null);
    apiClient
      .createNativeWebSearchProvider({
        name: "PA WNID DuckDuckGo Search",
        provider: SAFE_WEB_SEARCH_PROVIDER,
        description: "WNID-P4-01 no-credential provider setup",
        parameters: {},
        is_default: true,
        confirm_token: WEB_SEARCH_MUTATION_CONFIRM_TOKEN,
      })
      .then((result) => {
        setWebSearchSetupResult(result);
        setWebSearchSetupState("idle");
        refreshWebSearch();
        loadConversations();
      })
      .catch((setupError: unknown) => {
        setWebSearchSetupState("error");
        setError(errorMessage(setupError));
      });
  };

  const testWebSearchProvider = () => {
    if (!safeWebSearchProvider?.id) {
      setError("No ready native Web Search provider is configured");
      return;
    }
    setWebSearchSetupState("loading");
    setError(null);
    apiClient
      .testNativeWebSearchProvider(safeWebSearchProvider.id, WEB_SEARCH_TEST_CONFIRM_TOKEN)
      .then((result) => {
        setWebSearchSetupResult(result);
        setWebSearchSetupState("idle");
        refreshWebSearch();
      })
      .catch((testError: unknown) => {
        setWebSearchSetupState("error");
        setError(errorMessage(testError));
      });
  };

  return (
    <div className={detailsOpen ? "dialogue-page weknora-dialogue-page" : "dialogue-page weknora-dialogue-page details-collapsed"}>
      <aside className="dialogue-side weknora-dialogue-side" aria-label="智能对话导航">
        <div className="weknora-brand-row">
          <strong>智能对话</strong>
          <button className="icon-button" type="button" onClick={loadCatalog} title="刷新 Agent">
            <RefreshCw size={16} aria-hidden="true" />
          </button>
        </div>

        <nav className="weknora-nav" aria-label="智能对话功能导航">
          <a href="#/library">
            <BookOpen size={17} aria-hidden="true" />
            <span>资料库</span>
          </a>
          <a href="#/rag-debug">
            <Search size={17} aria-hidden="true" />
            <span>检索</span>
          </a>
          <a href="#/wiki">
            <MessagesSquare size={17} aria-hidden="true" />
            <span>Wiki</span>
          </a>
          <button className="active" type="button" onClick={startNewConversation}>
            <MessageSquareText size={17} aria-hidden="true" />
            <span>对话</span>
            <Plus size={16} aria-hidden="true" />
          </button>
        </nav>

        <section className="weknora-recents" aria-label="最近对话">
          <div className="weknora-recents-heading">
            <span>近7天</span>
            <button className="icon-button" type="button" onClick={loadConversations} title="刷新历史">
              <RefreshCw size={15} aria-hidden="true" />
            </button>
          </div>
          {historyState === "loading" ? (
            <EmptyState text="加载历史" loading compact />
          ) : conversations.length === 0 ? (
            <EmptyState text="暂无对话" compact />
          ) : (
            <div className="weknora-recent-list">
              {conversations.slice(0, 7).map((conversation) => (
                <button
                  className={selectedConversation?.id === conversation.id ? "active" : ""}
                  key={conversation.id}
                  type="button"
                  onClick={() => selectConversation(conversation)}
                >
                  <span>{conversation.title}</span>
                  <small>{formatDate(conversation.updated_at)}</small>
                </button>
              ))}
            </div>
          )}
        </section>
      </aside>

      <section className="dialogue-workspace dialogue-chat-workspace weknora-chat-workspace" aria-label="智能问答对话">
        <header className="weknora-chat-topline">
          <span>
            <MessageSquareText size={18} aria-hidden="true" />
            智能问答对话
          </span>
        </header>

        {error ? <ErrorState message={error} /> : null}

        <section className="dialogue-message-panel dialogue-chat-panel weknora-chat-stage" aria-label="对话消息">
          {messageState === "loading" ? (
            <EmptyState text="加载消息" loading />
          ) : messages.length === 0 ? (
            <div className="weknora-empty-dialogue" aria-hidden="true" />
          ) : (
            <div className="message-stream dialogue-message-stream weknora-message-stream">
              {messages.map((message) => (
                <article className={`message-bubble ${message.role}`} key={message.id}>
                  <div className="message-meta">
                    <strong>{roleLabel(message.role)}</strong>
                    <span>{formatDate(message.created_at)}</span>
                  </div>
                  <p>{message.content}</p>
                </article>
              ))}
            </div>
          )}
        </section>

        <form className="dialogue-composer weknora-composer" onSubmit={runDialogue}>
          <div className="weknora-knowledge-tags">
            <span>
              <Database size={14} aria-hidden="true" />
              {selectedKbLabel}
            </span>
          </div>

          <label className="dialogue-query-field dialogue-composer-field weknora-input-field">
            <span>问题</span>
            <textarea
              rows={3}
              value={query}
              placeholder="向知识库提问"
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>

          <div className="dialogue-composer-actions weknora-composer-toolbar">
            <div className="weknora-toolbar-left">
              <label className="weknora-agent-control weknora-kb-control">
                <Database size={15} aria-hidden="true" />
                <select
                  aria-label="知识库"
                  value={selectedKbId}
                  disabled={catalogState === "loading" || kbSelectOptions.length === 0}
                  onChange={(event) => setSelectedKbId(event.target.value)}
                >
                  {kbSelectOptions.length === 0 ? (
                    <option value="">默认知识库</option>
                  ) : (
                    kbSelectOptions.map((kb) => (
                      <option key={kb.id} value={kb.id}>
                        {kb.name}
                      </option>
                    ))
                  )}
                </select>
                <ChevronDown size={14} aria-hidden="true" />
              </label>
              <label className="weknora-agent-control weknora-answer-control">
                <Sparkles size={15} aria-hidden="true" />
                <select
                  aria-label="回答类型"
                  value={answerMode}
                  onChange={(event) => {
                    const nextMode = event.target.value as AnswerMode;
                    setAnswerMode(nextMode);
                    if (nextMode !== "qa") {
                      const smartReasoningAgent = dialogueAgents.find(
                        (agent) => agent.id === SMART_REASONING_AGENT_ID,
                      );
                      if (smartReasoningAgent?.id) {
                        setSelectedAgentId(smartReasoningAgent.id);
                        setDialogueMode("agentqa");
                      }
                    }
                  }}
                >
                  {ANSWER_MODE_OPTIONS.map((mode) => (
                    <option key={mode.id} value={mode.id}>
                      {mode.label}
                    </option>
                  ))}
                </select>
                <ChevronDown size={14} aria-hidden="true" />
              </label>
              <label className="weknora-agent-control">
                <Bot size={15} aria-hidden="true" />
                <select
                  aria-label="Agent"
                  value={selectedAgentId}
                  disabled={catalogState === "loading" || dialogueAgents.length === 0}
                  onChange={(event) => {
                    const nextAgentId = event.target.value;
                    const nextAgent = dialogueAgents.find((agent) => agent.id === nextAgentId) ?? null;
                    setSelectedAgentId(nextAgentId);
                    setDialogueMode(modeForAgent(nextAgent));
                    if (answerMode !== "qa" && nextAgentId !== SMART_REASONING_AGENT_ID) {
                      setAnswerMode("qa");
                    }
                  }}
                >
                  {dialogueAgents.map((agent) => (
                    <option key={agent.id ?? agent.name} value={agent.id ?? ""}>
                      {agent.name}
                    </option>
                  ))}
                </select>
                <ChevronDown size={14} aria-hidden="true" />
              </label>
              <button className="weknora-tool-button active" type="button" title="网络检索状态">
                <Globe2 size={16} aria-hidden="true" />
              </button>
              <button className="weknora-tool-button" type="button" title="附件">
                <ImageIcon size={16} aria-hidden="true" />
              </button>
              <button
                className={detailsOpen ? "weknora-tool-button active" : "weknora-tool-button"}
                type="button"
                onClick={() => setDetailsOpen((current) => !current)}
                title="来源详情"
              >
                <FileText size={16} aria-hidden="true" />
                {run?.citations.length ? <em>{run.citations.length}</em> : null}
              </button>
              <span className="weknora-runtime-chip">
                {answerMode !== "qa"
                  ? answerModeLabel(answerMode)
                  : dialogueMode === "agentqa"
                  ? `多轮 ${strategyDraft.multi_turn_enabled ? strategyDraft.history_turns || 5 : "off"}`
                  : "RAG"}
              </span>
            </div>
            <div className="weknora-toolbar-right">
              <span className="weknora-model-pill">{catalog?.status === "ready" ? "模型已就绪" : catalog?.status ?? "pending"}</span>
              <button
                className="primary-action weknora-send-button"
                type="submit"
                disabled={runState === "loading" || (dialogueMode === "agentqa" && !selectedAgentId)}
                title="发送"
              >
                {runState === "loading" ? <Loader2 size={16} aria-hidden="true" /> : <Send size={16} aria-hidden="true" />}
              </button>
            </div>
          </div>
        </form>
      </section>

      {detailsOpen ? (
        <aside className="dialogue-inspector dialogue-details-drawer weknora-detail-drawer" aria-label="来源与运行详情">
          <section className="dialogue-panel" aria-label="运行摘要">
            <div className="analysis-panel-heading">
              <span>运行</span>
              <strong>{dialogueMode === "quickqa" ? "native-rag" : selectedAgent?.agent_mode ?? "pending"}</strong>
            </div>
            <StrategySummary
              agent={selectedAgent}
              answerMode={answerMode}
              kbOverview={kbOverview}
              mode={dialogueMode}
              selectedKbLabel={selectedKbLabel}
            />
          </section>

          <section className="dialogue-panel" aria-label="高级范围">
            <div className="analysis-panel-heading">
              <span>高级范围</span>
              <strong>{activeSelection?.name ?? "default"}</strong>
            </div>
            <div className="dialogue-control-grid compact">
              <label>
                <span>标题</span>
                <input value={title} onChange={(event) => setTitle(event.target.value)} />
              </label>
              <label>
                <span>知识库</span>
                <input value={selectedKbLabel} readOnly />
              </label>
              <label>
                <span>指定文档 ID（高级）</span>
                <input value={knowledgeScope} onChange={(event) => setKnowledgeScope(event.target.value)} />
              </label>
            </div>
          </section>

          <section className="dialogue-panel" aria-label="引用">
            <div className="analysis-panel-heading">
              <span>引用</span>
              <strong>{run?.citations.length ?? 0}</strong>
            </div>
            {warnings.length ? <WarningList warnings={warnings} emptyText="暂无警告" /> : null}
            <CitationList citations={(run?.citations ?? []) as Citation[]} />
          </section>

          <section className="dialogue-panel" aria-label="工具 Trace">
            <div className="analysis-panel-heading">
              <span>{dialogueMode === "quickqa" ? "检索过程" : "工具过程"}</span>
              <strong>{isAgentQaRun(run) ? stringList(run.runtime.tool_names).length : runtime?.reference_count ?? 0}</strong>
            </div>
            <ToolTrace run={run} />
          </section>
        </aside>
      ) : null}
    </div>
  );
}

function StrategyEditor({
  disabled,
  draft,
  message,
  onChange,
  onSave,
  state,
}: {
  disabled: boolean;
  draft: NativeAgentStrategy;
  message: string | null;
  onChange: (next: NativeAgentStrategy) => void;
  onSave: () => void;
  state: LoadState;
}) {
  const update = <K extends keyof NativeAgentStrategy>(key: K, value: NativeAgentStrategy[K]) => {
    onChange({ ...draft, [key]: value });
  };
  return (
    <div className="dialogue-strategy-editor" aria-label="Conversation Strategy Editor">
      <label>
        <span>system_prompt</span>
        <textarea
          rows={4}
          value={draft.system_prompt}
          onChange={(event) => update("system_prompt", event.target.value)}
        />
      </label>
      <label>
        <span>context_template</span>
        <textarea
          rows={3}
          value={draft.context_template}
          onChange={(event) => update("context_template", event.target.value)}
        />
      </label>
      <div className="dialogue-strategy-editor-grid">
        <label>
          <span>allowed_tools</span>
          <textarea
            rows={3}
            value={valuesToLines(draft.allowed_tools)}
            onChange={(event) => update("allowed_tools", linesToValues(event.target.value))}
          />
        </label>
        <label>
          <span>suggested_prompts</span>
          <textarea
            rows={3}
            value={valuesToLines(draft.suggested_prompts)}
            onChange={(event) => update("suggested_prompts", linesToValues(event.target.value))}
          />
        </label>
      </div>
      <div className="dialogue-strategy-editor-grid">
        <label>
          <span>mcp_selection_mode</span>
          <select
            value={draft.mcp_selection_mode}
            onChange={(event) => update("mcp_selection_mode", event.target.value)}
          >
            <option value="none">none</option>
            <option value="selected">selected</option>
            <option value="all">all</option>
          </select>
        </label>
        <label>
          <span>mcp_services</span>
          <input
            value={draft.mcp_services.join(",")}
            onChange={(event) => update("mcp_services", linesToValues(event.target.value))}
          />
        </label>
      </div>
      <div className="dialogue-strategy-toggles">
        <label>
          <input
            type="checkbox"
            checked={draft.web_search_enabled}
            onChange={(event) => update("web_search_enabled", event.target.checked)}
          />
          <span>web_search_enabled</span>
        </label>
        <label>
          <input
            type="checkbox"
            checked={draft.web_fetch_enabled}
            onChange={(event) => update("web_fetch_enabled", event.target.checked)}
          />
          <span>web_fetch_enabled</span>
        </label>
        <label>
          <input
            type="checkbox"
            checked={draft.multi_turn_enabled}
            onChange={(event) => update("multi_turn_enabled", event.target.checked)}
          />
          <span>multi_turn_enabled</span>
        </label>
      </div>
      <div className="dialogue-strategy-number-grid">
        <label>
          <span>history_turns</span>
          <input
            type="number"
            min={0}
            max={50}
            value={draft.history_turns}
            onChange={(event) => update("history_turns", Number(event.target.value))}
          />
        </label>
        <label>
          <span>embedding_top_k</span>
          <input
            type="number"
            min={0}
            max={200}
            value={draft.embedding_top_k}
            onChange={(event) => update("embedding_top_k", Number(event.target.value))}
          />
        </label>
        <label>
          <span>rerank_top_k</span>
          <input
            type="number"
            min={0}
            max={200}
            value={draft.rerank_top_k}
            onChange={(event) => update("rerank_top_k", Number(event.target.value))}
          />
        </label>
        <label>
          <span>keyword_threshold</span>
          <input
            type="number"
            min={0}
            max={1}
            step={0.01}
            value={draft.keyword_threshold}
            onChange={(event) => update("keyword_threshold", Number(event.target.value))}
          />
        </label>
        <label>
          <span>vector_threshold</span>
          <input
            type="number"
            min={0}
            max={1}
            step={0.01}
            value={draft.vector_threshold}
            onChange={(event) => update("vector_threshold", Number(event.target.value))}
          />
        </label>
        <label>
          <span>rerank_threshold</span>
          <input
            type="number"
            min={-10}
            max={10}
            step={0.01}
            value={draft.rerank_threshold}
            onChange={(event) => update("rerank_threshold", Number(event.target.value))}
          />
        </label>
      </div>
      <label>
        <span>web_search_provider_id</span>
        <input
          value={draft.web_search_provider_id}
          onChange={(event) => update("web_search_provider_id", event.target.value)}
        />
      </label>
      <label>
        <span>web_fetch_top_n</span>
        <input
          type="number"
          min={0}
          max={20}
          value={draft.web_fetch_top_n}
          onChange={(event) => update("web_fetch_top_n", Number(event.target.value))}
        />
      </label>
      <button className="secondary-action" type="button" disabled={disabled} onClick={onSave}>
        {state === "loading" ? <Loader2 size={16} aria-hidden="true" /> : <Save size={16} aria-hidden="true" />}
        <span>{state === "loading" ? "保存中" : "保存 Strategy"}</span>
      </button>
      {message ? <p className="dialogue-strategy-message">{message}</p> : null}
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
    <div className="dialogue-agent-list" role="listbox" aria-label="原生 Agent">
      {agents.map((agent) => (
        <button
          className={agent.id === selectedAgentId ? "dialogue-agent-option active" : "dialogue-agent-option"}
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

function StrategySummary({
  agent,
  answerMode,
  kbOverview,
  mode,
  selectedKbLabel,
}: {
  agent: NativeAgentItem | null;
  answerMode: AnswerMode;
  kbOverview: NativeKnowledgeBaseOverviewResponse | null;
  mode: DialogueMode;
  selectedKbLabel: string;
}) {
  const activeKb = kbOverview?.active_selection;
  return (
    <div className="dialogue-strategy-grid">
      <span>
        <MessagesSquare size={14} aria-hidden="true" />
        mode {modeLabel(mode)}
      </span>
      <span>
        <Sparkles size={14} aria-hidden="true" />
        answer {answerModeLabel(answerMode)}
      </span>
      <span>
        <Search size={14} aria-hidden="true" />
        model {mode === "quickqa" ? "native" : agent ? boolLabel(agent.model_configured) : "pending"}
      </span>
      <span>
        <FileText size={14} aria-hidden="true" />
        rerank {agent ? boolLabel(agent.rerank_configured) : "pending"}
      </span>
      <span>
        <Wrench size={14} aria-hidden="true" />
        tools {mode === "quickqa" ? 0 : agent?.allowed_tools.length ?? 0}
      </span>
      <span>
        <FileText size={14} aria-hidden="true" />
        kb {selectedKbLabel || activeKb?.name || activeKb?.kb_id || "pending"}
      </span>
    </div>
  );
}

function McpReadPath({ overview }: { overview: NativeMcpOverviewResponse | null }) {
  if (!overview) {
    return <EmptyState icon={Wrench} text="加载 MCP 状态" compact />;
  }
  const services = surfaceValue(overview, "services");
  const tools = surfaceValue(overview, "tools");
  const resources = surfaceValue(overview, "resources");
  const prompts = surfaceValue(overview, "prompts");
  const approval = surfaceValue(overview, "approval");
  const execution = surfaceValue(overview, "tool_execution");
  return (
    <div className="dialogue-trace">
      <div className="dialogue-trace-row">
        <span>source</span>
        <strong>{overview.source}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>services</span>
        <strong>{`${statusText(services)}:${numberLabel(recordValue(services, "count"))}`}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>tools</span>
        <strong>{statusText(tools)}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>resources</span>
        <strong>{statusText(resources)}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>prompts</span>
        <strong>{stringValue(recordValue(prompts, "reason")) ?? statusText(prompts)}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>approval</span>
        <strong>{statusText(approval)}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>tool_execution</span>
        <strong>{stringValue(recordValue(execution, "reason")) ?? statusText(execution)}</strong>
      </div>
      <div className="dialogue-event-grid" aria-label="MCP Read Path Surfaces">
        {[
          ["services", services],
          ["tools", tools],
          ["resources", resources],
          ["prompts", prompts],
        ].map(([name, surface]) => (
          <span key={name as string}>
            <em>{name as string}</em>
            <strong>{statusText(surface as Record<string, unknown> | undefined)}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}

function McpExecutionPanel({
  disabled,
  result,
  serviceName,
  state,
  onApprove,
  onReject,
}: {
  disabled: boolean;
  result: NativeMcpExecutionResponse | null;
  serviceName: string | null;
  state: LoadState;
  onApprove: () => void;
  onReject: () => void;
}) {
  const execution = result?.surfaces.tool_execution;
  const resultRecord = nestedRecord(execution, "result");
  const history = nestedRecord(execution, "history");
  return (
    <div className="dialogue-mcp-execution" aria-label="MCP Tool Execution">
      <div className="dialogue-execution-actions">
        <button type="button" disabled={disabled} onClick={onReject}>
          <Wrench size={14} aria-hidden="true" />
          <span>{state === "loading" ? "Running" : "Reject ping"}</span>
        </button>
        <button type="button" disabled={disabled} onClick={onApprove}>
          <Send size={14} aria-hidden="true" />
          <span>{state === "loading" ? "Running" : "Approve ping"}</span>
        </button>
      </div>
      <div className="dialogue-trace-row">
        <span>safe_service</span>
        <strong>{serviceName ?? "not_configured"}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>execution_status</span>
        <strong>{statusText(execution)}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>approval_decision</span>
        <strong>{stringValue(recordValue(resultRecord, "approval_decision")) ?? "pending"}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>history_output</span>
        <strong>{stringValue(recordValue(history, "output_id")) ?? "pending"}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>audit</span>
        <strong>{result?.audit?.status ?? "pending"}</strong>
      </div>
    </div>
  );
}

function McpPromptPanel({
  disabled,
  overview,
  result,
  state,
  onRead,
}: {
  disabled: boolean;
  overview: NativeMcpOverviewResponse | null;
  result: NativeMcpPromptReadResponse | null;
  state: LoadState;
  onRead: () => void;
}) {
  const promptSurface = overview ? surfaceValue(overview, "prompts") : undefined;
  const promptRead = result?.surfaces.prompt_read;
  const prompt = nestedRecord(promptRead, "prompt");
  return (
    <div className="dialogue-mcp-prompt" aria-label="MCP Prompt Parity">
      <div className="dialogue-execution-actions single">
        <button type="button" disabled={disabled} onClick={onRead}>
          <Sparkles size={14} aria-hidden="true" />
          <span>{state === "loading" ? "Reading" : "Read prompt"}</span>
        </button>
      </div>
      <div className="dialogue-trace-row">
        <span>prompt_parity</span>
        <strong>{statusText(promptSurface)}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>prompt_name</span>
        <strong>{stringValue(recordValue(prompt, "name")) ?? SAFE_MCP_PROMPT_NAME}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>prompt_messages</span>
        <strong>{numberLabel(recordValue(promptRead, "message_count"))}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>prompt_read</span>
        <strong>{statusText(promptRead)}</strong>
      </div>
    </div>
  );
}

function WebSearchProviderPanel({
  disabled,
  overview,
  providerName,
  result,
  state,
  onSetup,
  onTest,
}: {
  disabled: boolean;
  overview: NativeWebSearchOverviewResponse | null;
  providerName: string | null;
  result: NativeWebSearchProviderMutationResponse | null;
  state: LoadState;
  onSetup: () => void;
  onTest: () => void;
}) {
  if (!overview) {
    return <EmptyState icon={Search} text="加载 Web Search 状态" compact />;
  }
  const providerTypes = surfaceValue(overview, "provider_types");
  const configured = surfaceValue(overview, "configured_providers");
  const providerSetup = surfaceValue(overview, "provider_setup");
  const providerTest = result?.surfaces.provider_test ?? result?.surfaces.mutation ?? surfaceValue(overview, "provider_test");
  const mutation = result?.surfaces.mutation;
  const canTest = Boolean(providerName);
  return (
    <div className="dialogue-web-search-provider" aria-label="Web Search Provider Setup Details">
      <div className="dialogue-execution-actions">
        <button type="button" disabled={disabled} onClick={onSetup}>
          <Search size={14} aria-hidden="true" />
          <span>{state === "loading" ? "Running" : "Setup DuckDuckGo"}</span>
        </button>
        <button type="button" disabled={disabled || !canTest} onClick={onTest}>
          <Send size={14} aria-hidden="true" />
          <span>{state === "loading" ? "Running" : "Test provider"}</span>
        </button>
      </div>
      <div className="dialogue-trace-row">
        <span>provider_types</span>
        <strong>{`${statusText(providerTypes)}:${numberLabel(recordValue(providerTypes, "count"))}`}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>configured</span>
        <strong>{`${statusText(configured)}:${numberLabel(recordValue(configured, "ready_provider_count"))}`}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>selected_provider</span>
        <strong>{providerName ?? stringValue(recordValue(providerSetup, "reason")) ?? "not_configured"}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>provider_setup</span>
        <strong>{statusText(mutation ?? providerSetup)}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>provider_test</span>
        <strong>{statusText(providerTest)}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>audit</span>
        <strong>{result?.audit?.status ?? "pending"}</strong>
      </div>
    </div>
  );
}

function selectedSafeMcpService(overview: NativeMcpOverviewResponse | null) {
  const surfaces = overview?.surfaces ?? {};
  const services = surfaces.services;
  const items = Array.isArray(services?.items) ? services.items : [];
  for (const item of items) {
    if (item && typeof item === "object" && !Array.isArray(item)) {
      const record = item as Record<string, unknown>;
      if (record.name === "PA Safe Local MCP" && typeof record.id === "string") {
        return { id: record.id, name: String(record.name) };
      }
    }
  }
  return null;
}

function selectedSafeWebSearchProvider(overview: NativeWebSearchOverviewResponse | null) {
  const surfaces = overview?.surfaces ?? {};
  const configured = surfaces.configured_providers;
  const items = Array.isArray(configured?.items) ? configured.items : [];
  for (const item of items) {
    if (item && typeof item === "object" && !Array.isArray(item)) {
      const record = item as Record<string, unknown>;
      if (record.provider === SAFE_WEB_SEARCH_PROVIDER && typeof record.id === "string") {
        return { id: record.id, name: String(record.name || record.provider) };
      }
    }
  }
  return null;
}

function surfaceValue(
  overview: NativeMcpOverviewResponse | NativeWebSearchOverviewResponse,
  name: string,
) {
  const surface = overview.surfaces[name];
  return surface && typeof surface === "object" ? surface : undefined;
}

function statusText(surface: Record<string, unknown> | undefined) {
  return stringValue(recordValue(surface, "status")) ?? "pending";
}

function ToolTrace({ run }: { run: DialogueRun | null }) {
  const runtime = run?.runtime;
  if (!runtime) {
    return <EmptyState icon={Wrench} text="暂无工具事件" compact />;
  }
  const isAgentRun = isAgentQaRun(run);
  const eventEntries = Object.entries(runtime.event_counts ?? {});
  const runContract = isAgentRun ? run.runtime.run_contract : undefined;
  const selectedAgent = isAgentRun ? run.runtime.selected_agent : undefined;
  const selectedStrategy = nestedRecord(selectedAgent, "strategy");
  const continuity = isAgentRun ? run.runtime.conversation_continuity : undefined;
  const toolNames = isAgentRun ? stringList(run.runtime.tool_names) : [];
  const webProviders = isAgentRun ? stringList(run.runtime.web_providers) : [];
  const wikiSlugs = isAgentRun ? stringList(run.runtime.wiki_slugs) : [];
  return (
    <div className="dialogue-trace">
      <div className="dialogue-trace-row">
        <span>source</span>
        <strong>{runtime.source}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>references</span>
        <strong>{runtime.reference_count}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>reference_source</span>
        <strong>{runtime.reference_event_source}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>citations</span>
        <strong>{runtime.saved_citation_count}</strong>
      </div>
      <div className="dialogue-trace-row">
        <span>{isAgentQaRun(run) ? "citation_blocked" : "current_run_guard"}</span>
        <strong>
          {isAgentRun
            ? String(run.runtime.citation_blocked)
            : String(Boolean(run.runtime.current_run_guard?.passed))}
        </strong>
      </div>
      {isAgentRun ? (
        <>
          <div className="dialogue-trace-row">
            <span>Run Contract</span>
            <strong>{String(Boolean(recordValue(runContract, "complete_seen")))}</strong>
          </div>
          <div className="dialogue-trace-row">
            <span>native_session</span>
            <strong>{run.runtime.native_session_reused ? "reused" : run.runtime.native_session_source}</strong>
          </div>
          <div className="dialogue-trace-row">
            <span>selected_agent</span>
            <strong>{stringValue(recordValue(selectedAgent, "name")) ?? run.runtime.agent_name ?? "pending"}</strong>
          </div>
          <div className="dialogue-trace-row">
            <span>agent_type</span>
            <strong>{stringValue(recordValue(selectedAgent, "agent_type")) ?? "native"}</strong>
          </div>
          <div className="dialogue-trace-row">
            <span>multi_turn</span>
            <strong>{String(Boolean(recordValue(selectedStrategy, "multi_turn_enabled")))}</strong>
          </div>
          <div className="dialogue-trace-row">
            <span>conversation_continuity</span>
            <strong>{numberLabel(recordValue(continuity, "message_count"))}</strong>
          </div>
          <div className="dialogue-trace-row">
            <span>web_references</span>
            <strong>{numberLabel(run.runtime.web_reference_count)}</strong>
          </div>
          <div className="dialogue-trace-row">
            <span>web_providers</span>
            <strong>{webProviders.length ? webProviders.join(", ") : "none"}</strong>
          </div>
          <div className="dialogue-trace-row">
            <span>wiki_references</span>
            <strong>{numberLabel(run.runtime.wiki_reference_count)}</strong>
          </div>
          <div className="dialogue-trace-row">
            <span>wiki_pages</span>
            <strong>{wikiSlugs.length ? wikiSlugs.join(", ") : "none"}</strong>
          </div>
          <div className="dialogue-event-grid" aria-label="Run Contract Events">
            {["thinking", "tool_call", "tool_result", "references", "answer", "complete"].map((name) => (
              <span key={name}>
                <em>{name}</em>
                <strong>{numberLabel(recordValue(runContract, `${name}_count`))}</strong>
              </span>
            ))}
          </div>
        </>
      ) : null}
      {toolNames.length ? (
        <div className="dialogue-tool-list">
          {toolNames.map((tool) => (
            <span key={tool}>{tool}</span>
          ))}
        </div>
      ) : null}
      {eventEntries.length ? (
        <div className="dialogue-event-grid">
          {eventEntries.map(([name, count]) => (
            <span key={name}>
              <em>{name}</em>
              <strong>{countLabel(count)}</strong>
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
