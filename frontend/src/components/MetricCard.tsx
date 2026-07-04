import type { LucideIcon } from "lucide-react";
import { formatNumber, formatPercent } from "../lib/format";

type MetricCardProps = {
  label: string;
  value: number | string | null;
  detail?: string | null;
  icon: LucideIcon;
  accent?: "teal" | "coral" | "amber" | "violet";
  percent?: boolean;
};

const accentClass = {
  teal: "bg-teal/10 text-teal",
  coral: "bg-coral/10 text-coral",
  amber: "bg-amber/10 text-amber",
  violet: "bg-violet/10 text-violet"
};

export function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  accent = "teal",
  percent = false
}: MetricCardProps) {
  const display =
    typeof value === "number" && percent ? formatPercent(value) : formatNumber(value);

  return (
    <section className="rounded-lg border border-line bg-panel p-4 shadow-panel">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-muted">{label}</p>
          <p className="mt-2 truncate text-2xl font-semibold text-ink">{display}</p>
        </div>
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${accentClass[accent]}`}>
          <Icon aria-hidden="true" size={20} />
        </div>
      </div>
      {detail ? <p className="mt-3 truncate text-xs text-muted">{detail}</p> : null}
    </section>
  );
}
