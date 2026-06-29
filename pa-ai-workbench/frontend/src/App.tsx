import {
  BookOpenText,
  Database,
  FileClock,
  Gauge,
  Home,
  Library,
  MessagesSquare,
  MessageSquareText,
  PanelLeft,
  Search,
  Settings,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { CapabilityCenterPage } from "./pages/CapabilityCenterPage";
import { DialoguePage } from "./pages/DialoguePage";
import { HistoryPage } from "./pages/HistoryPage";
import { LibraryPage } from "./pages/LibraryPage";
import { RagDebugPage } from "./pages/RagDebugPage";
import { WikiPage } from "./pages/WikiPage";

type RouteId =
  | "/"
  | "/library"
  | "/dialogue"
  | "/analysis"
  | "/wiki"
  | "/history"
  | "/rag-debug"
  | "/capabilities";

type NavItem = {
  id: RouteId;
  label: string;
  icon: typeof Home;
};

const navItems: NavItem[] = [
  { id: "/", label: "智能对话", icon: MessagesSquare },
  { id: "/library", label: "资料库", icon: Library },
  { id: "/wiki", label: "Wiki", icon: BookOpenText },
  { id: "/history", label: "历史", icon: FileClock },
  { id: "/capabilities", label: "设置", icon: Gauge },
];

const pageMeta: Record<RouteId, { title: string; eyebrow: string; icon: typeof Home }> = {
  "/": { title: "智能对话", eyebrow: "Dialogue", icon: MessagesSquare },
  "/library": { title: "资料库", eyebrow: "资料管理", icon: Database },
  "/dialogue": { title: "智能对话", eyebrow: "Dialogue", icon: MessagesSquare },
  "/analysis": { title: "智能分析已冻结", eyebrow: "冻结", icon: MessageSquareText },
  "/rag-debug": { title: "RAG 检索调试", eyebrow: "检索调试", icon: Search },
  "/wiki": { title: "Wiki 知识库", eyebrow: "Wiki", icon: Search },
  "/history": { title: "生成历史", eyebrow: "历史", icon: FileClock },
  "/capabilities": { title: "设置与调试", eyebrow: "设置", icon: Gauge },
};

function getHashRoute(): RouteId {
  const hash = window.location.hash.replace(/^#/, "").split("?")[0];
  if (
    hash === "/library" ||
    hash === "/dialogue" ||
    hash === "/analysis" ||
    hash === "/rag-debug" ||
    hash === "/wiki" ||
    hash === "/history" ||
    hash === "/capabilities"
  ) {
    return hash;
  }
  return "/";
}

export function App() {
  const [route, setRoute] = useState<RouteId>(() => getHashRoute());

  useEffect(() => {
    const onHashChange = () => setRoute(getHashRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const currentPage = useMemo(() => pageMeta[route], [route]);
  const PageIcon = currentPage.icon;
  const isDialogueRoute = route === "/" || route === "/dialogue";
  const navigateTo = (nextRoute: RouteId) => {
    window.location.hash = nextRoute;
  };

  return (
    <div className="workbench-shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            PA
          </div>
          <div>
            <div className="brand-name">PA 智能工作台</div>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = item.id === route || (item.id === "/" && route === "/dialogue");
            return (
              <a
                className={isActive ? "nav-link active" : "nav-link"}
                href={`#${item.id}`}
                key={item.id}
                aria-current={isActive ? "page" : undefined}
                title={item.label}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{item.label}</span>
              </a>
            );
          })}
        </nav>
      </aside>

      <main className={isDialogueRoute ? "main-panel dialogue-main-panel" : "main-panel"}>
        {!isDialogueRoute ? (
          <header className="topbar">
            <button className="icon-button" type="button" aria-label="导航">
              <PanelLeft size={18} aria-hidden="true" />
            </button>
            <div className="topbar-title">
              <span>{currentPage.eyebrow}</span>
              <strong>{currentPage.title}</strong>
            </div>
            <button
              className="icon-button"
              type="button"
              aria-label="设置"
              onClick={() => navigateTo("/capabilities")}
            >
              <Settings size={18} aria-hidden="true" />
            </button>
          </header>
        ) : null}

        <section
          className={isDialogueRoute ? "page-surface dialogue-route-surface" : "page-surface"}
          aria-label={isDialogueRoute ? currentPage.title : undefined}
          aria-labelledby={isDialogueRoute ? undefined : "page-title"}
        >
          {!isDialogueRoute ? (
            <div className="page-heading">
              <div className="page-icon" aria-hidden="true">
                <PageIcon size={22} />
              </div>
              <div>
                <p>{currentPage.eyebrow}</p>
                <h1 id="page-title">{currentPage.title}</h1>
              </div>
            </div>
          ) : null}

          {route === "/" || route === "/dialogue" ? (
            <DialoguePage />
          ) : route === "/library" ? (
            <LibraryPage />
          ) : route === "/analysis" ? (
            <FrozenAnalysisPage navigateTo={navigateTo} />
          ) : route === "/rag-debug" ? (
            <RagDebugPage />
          ) : route === "/wiki" ? (
            <WikiPage />
          ) : route === "/history" ? (
            <HistoryPage />
          ) : route === "/capabilities" ? (
            <CapabilityCenterPage />
          ) : (
            <div className="workspace-grid">
              <div className="workspace-panel primary-panel">
                <div className="panel-header">
                  <span>当前视图</span>
                  <strong>{currentPage.title}</strong>
                </div>
                <div className="panel-lines" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </div>
              </div>

              <div className="workspace-panel side-panel">
                <div className="panel-header">
                  <span>状态</span>
                  <strong>准备就绪</strong>
                </div>
                <div className="status-stack">
                  <span>API 客户端</span>
                  <span>哈希导航</span>
                  <span>应用外壳</span>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function FrozenAnalysisPage({ navigateTo }: { navigateTo: (route: RouteId) => void }) {
  return (
    <div className="frozen-analysis-page" aria-label="智能分析冻结说明">
      <div className="frozen-analysis-panel">
        <MessageSquareText size={24} aria-hidden="true" />
        <div>
          <span>功能已并入智能对话</span>
          <h2>智能分析暂时冻结</h2>
          <p>政策分析和案例复盘已作为回答类型进入智能对话，旧分析表单本阶段不再作为独立入口展示。</p>
        </div>
        <button className="primary-action compact" type="button" onClick={() => navigateTo("/")}>
          进入智能对话
        </button>
      </div>
    </div>
  );
}
