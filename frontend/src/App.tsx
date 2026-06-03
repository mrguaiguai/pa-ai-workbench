import { Database, FileSearch, ShieldCheck, Sparkles } from "lucide-react";

const modules = [
  {
    title: "资料库",
    status: "待接入",
    icon: Database,
  },
  {
    title: "智能分析台",
    status: "待接入",
    icon: Sparkles,
  },
  {
    title: "Wiki 知识库",
    status: "待接入",
    icon: FileSearch,
  },
];

export function App() {
  return (
    <main className="app-shell">
      <section className="intro">
        <div className="eyebrow">
          <ShieldCheck size={18} aria-hidden="true" />
          独立产品 · Mock Ready
        </div>
        <h1>PA 智能工作台</h1>
        <p>
          面向金融公共事务团队的内部 AI 工作台。
        </p>
      </section>

      <section className="module-grid" aria-label="MVP modules">
        {modules.map((item) => {
          const Icon = item.icon;
          return (
            <article className="module-card" key={item.title}>
              <Icon size={24} aria-hidden="true" />
              <h2>{item.title}</h2>
              <p>{item.status}</p>
            </article>
          );
        })}
      </section>
    </main>
  );
}
