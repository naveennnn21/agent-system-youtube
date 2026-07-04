import type { ReactNode } from "react";

type PanelProps = {
  title: string;
  action?: ReactNode;
  children: ReactNode;
};

export function Panel({ title, action, children }: PanelProps) {
  return (
    <section className="rounded-lg border border-line bg-panel shadow-panel">
      <div className="flex min-h-14 items-center justify-between gap-4 border-b border-line px-4 py-3">
        <h2 className="truncate text-sm font-semibold text-ink">{title}</h2>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}
