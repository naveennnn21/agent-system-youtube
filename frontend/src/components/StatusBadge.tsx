const toneByStatus: Record<string, string> = {
  published: "bg-teal/10 text-teal border-teal/25",
  rendered: "bg-violet/10 text-violet border-violet/25",
  rendering: "bg-amber/10 text-amber border-amber/25",
  uploading: "bg-amber/10 text-amber border-amber/25",
  succeeded: "bg-teal/10 text-teal border-teal/25",
  failed: "bg-coral/10 text-coral border-coral/25",
  retrying: "bg-amber/10 text-amber border-amber/25",
  pending: "bg-slate-100 text-slate-700 border-slate-200",
  planned: "bg-slate-100 text-slate-700 border-slate-200",
  active: "bg-teal/10 text-teal border-teal/25",
  scheduled: "bg-violet/10 text-violet border-violet/25",
  reserved: "bg-amber/10 text-amber border-amber/25",
  idle: "bg-slate-100 text-slate-700 border-slate-200",
  error: "bg-coral/10 text-coral border-coral/25"
};

type StatusBadgeProps = {
  value: string | null | undefined;
};

export function StatusBadge({ value }: StatusBadgeProps) {
  const normalized = (value || "unknown").toLowerCase();
  const tone = toneByStatus[normalized] || "bg-slate-100 text-slate-700 border-slate-200";
  return (
    <span className={`inline-flex max-w-full items-center rounded-md border px-2 py-1 text-xs font-medium ${tone}`}>
      <span className="truncate">{normalized.replaceAll("_", " ")}</span>
    </span>
  );
}
