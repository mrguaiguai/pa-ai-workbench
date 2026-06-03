import {
  BarChart3,
  BookOpenText,
  Database,
  FileClock,
  Home,
  Library,
  MessageSquareText,
  PanelLeft,
  Search,
  Settings,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { HomePage } from "./pages/HomePage";
import { LibraryPage } from "./pages/LibraryPage";

type RouteId = "/" | "/library" | "/analysis" | "/wiki" | "/history";

type NavItem = {
  id: RouteId;
  label: string;
  icon: typeof Home;
};

const navItems: NavItem[] = [
  { id: "/", label: "首页", icon: Home },
  { id: "/library", label: "资料库", icon: Library },
  { id: "/analysis", label: "智能分析", icon: MessageSquareText },
  { id: "/wiki", label: "Wiki", icon: BookOpenText },
  { id: "/history", label: "历史", icon: FileClock },
];

const pageMeta: Record<RouteId, { title: string; eyebrow: string; icon: typeof Home }> = {
  "/": { title: "工作台首页", eyebrow: "Overview", icon: BarChart3 },
  "/library": { title: "资料库", eyebrow: "Library", icon: Database },
  "/analysis": { title: "智能分析台", eyebrow: "Analysis", icon: MessageSquareText },
  "/wiki": { title: "Wiki 知识库", eyebrow: "Wiki", icon: Search },
  "/history": { title: "生成历史", eyebrow: "History", icon: FileClock },
};

function getHashRoute(): RouteId {
  const hash = window.location.hash.replace(/^#/, "");
  if (hash === "/library" || hash === "/analysis" || hash === "/wiki" || hash === "/history") {
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
            <div className="brand-subtitle">独立产品</div>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = item.id === route;
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

      <main className="main-panel">
        <header className="topbar">
          <button className="icon-button" type="button" aria-label="导航">
            <PanelLeft size={18} aria-hidden="true" />
          </button>
          <div className="topbar-title">
            <span>{currentPage.eyebrow}</span>
            <strong>{currentPage.title}</strong>
          </div>
          <button className="icon-button" type="button" aria-label="设置">
            <Settings size={18} aria-hidden="true" />
          </button>
        </header>

        <section className="page-surface" aria-labelledby="page-title">
          <div className="page-heading">
            <div className="page-icon" aria-hidden="true">
              <PageIcon size={22} />
            </div>
            <div>
              <p>{currentPage.eyebrow}</p>
              <h1 id="page-title">{currentPage.title}</h1>
            </div>
          </div>

          {route === "/" ? (
            <HomePage navigateTo={navigateTo} />
          ) : route === "/library" ? (
            <LibraryPage />
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
                  <strong>Ready</strong>
                </div>
                <div className="status-stack">
                  <span>API Client</span>
                  <span>Hash Navigation</span>
                  <span>App Shell</span>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
