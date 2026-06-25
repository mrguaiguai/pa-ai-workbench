import {
  ArrowRight,
  BookOpenText,
  Database,
  FileClock,
  Gauge,
  MessageSquareText,
} from "lucide-react";

type HomeRoute = "/library" | "/analysis" | "/wiki" | "/history" | "/capabilities";

type HomePageProps = {
  navigateTo: (route: HomeRoute) => void;
};

type HomeEntry = {
  label: string;
  title: string;
  description: string;
  action: string;
  route: HomeRoute;
  icon: typeof Database;
  tone: "blue" | "green" | "amber" | "slate" | "quiet";
};

const homeEntries: HomeEntry[] = [
  {
    label: "资料库",
    title: "管理资料",
    description: "上传资料、管理知识库，并按知识库筛选资料列表。",
    action: "进入资料库",
    route: "/library",
    icon: Database,
    tone: "blue",
  },
  {
    label: "智能分析",
    title: "发起分析",
    description: "围绕问题、政策或案例生成分析结果。",
    action: "开始分析",
    route: "/analysis",
    icon: MessageSquareText,
    tone: "green",
  },
  {
    label: "Wiki",
    title: "查看知识沉淀",
    description: "沉淀常用结论，查找已经整理好的知识内容。",
    action: "打开 Wiki",
    route: "/wiki",
    icon: BookOpenText,
    tone: "amber",
  },
  {
    label: "历史记录",
    title: "查看历史结果",
    description: "回看生成记录，继续整理或复用已有成果。",
    action: "查看历史",
    route: "/history",
    icon: FileClock,
    tone: "slate",
  },
  {
    label: "设置",
    title: "设置与调试",
    description: "集中查看系统设置和高级信息。",
    action: "打开设置",
    route: "/capabilities",
    icon: Gauge,
    tone: "quiet",
  },
];

export function HomePage({ navigateTo }: HomePageProps) {
  return (
    <div className="home-page">
      <section className="home-entry-panel" aria-label="常用功能">
        <div className="home-entry-heading">
          <span>常用功能</span>
          <strong>选择要处理的事项</strong>
        </div>

        <div className="home-entry-grid">
          {homeEntries.map((entry) => {
            const Icon = entry.icon;
            return (
              <button
                className={`home-entry-card ${entry.tone}`}
                key={entry.route}
                type="button"
                onClick={() => navigateTo(entry.route)}
              >
                <span className="home-entry-icon" aria-hidden="true">
                  <Icon size={21} />
                </span>
                <span className="home-entry-copy">
                  <span>{entry.label}</span>
                  <strong>{entry.title}</strong>
                  <small>{entry.description}</small>
                </span>
                <span className="home-entry-action">
                  {entry.action}
                  <ArrowRight size={15} aria-hidden="true" />
                </span>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
