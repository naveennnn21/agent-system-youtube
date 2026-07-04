import {
  Activity,
  BarChart3,
  Brain,
  Clapperboard,
  LayoutDashboard,
  ListVideo,
  UploadCloud
} from "lucide-react";
import type { ReactNode } from "react";
import type { RouteId } from "../routes";

const navItems: Array<{ id: RouteId; label: string; icon: typeof LayoutDashboard }> = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "videos", label: "Videos", icon: ListVideo },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "uploads", label: "Upload Status", icon: UploadCloud },
  { id: "logs", label: "Agent Logs", icon: Activity },
  { id: "learning", label: "Learning Insights", icon: Brain }
];

type LayoutProps = {
  route: RouteId;
  onRouteChange: (route: RouteId) => void;
  children: ReactNode;
};

export function Layout({ route, onRouteChange, children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-line bg-panel lg:block">
        <div className="flex h-16 items-center gap-3 border-b border-line px-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-coral text-white">
            <Clapperboard size={21} aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-ink">Shorts Agent</p>
            <p className="truncate text-xs text-muted">Production Console</p>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = item.id === route;
            return (
              <button
                key={item.id}
                className={`focus-ring flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
                  active ? "bg-teal/10 text-teal" : "text-muted hover:bg-paper hover:text-ink"
                }`}
                onClick={() => onRouteChange(item.id)}
                type="button"
              >
                <Icon aria-hidden="true" size={18} />
                <span className="truncate">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-line bg-panel/95 backdrop-blur">
          <div className="flex min-h-16 flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between lg:px-6">
            <div className="min-w-0">
              <h1 className="truncate text-xl font-semibold text-ink">
                {navItems.find((item) => item.id === route)?.label}
              </h1>
              <p className="truncate text-sm text-muted">YouTube Shorts AI Agent</p>
            </div>
            <div className="flex gap-2 overflow-x-auto lg:hidden">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    className={`focus-ring flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border ${
                      item.id === route
                        ? "border-teal bg-teal text-white"
                        : "border-line bg-white text-muted"
                    }`}
                    onClick={() => onRouteChange(item.id)}
                    title={item.label}
                    type="button"
                  >
                    <Icon aria-hidden="true" size={18} />
                  </button>
                );
              })}
            </div>
          </div>
        </header>
        <main className="px-4 py-6 lg:px-6">{children}</main>
      </div>
    </div>
  );
}
