import { BadgeCheck, Brain, Lightbulb, Scale } from "lucide-react";
import { DataTable, type Column } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import { Panel } from "../components/Panel";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../components/StateBlocks";
import { StatusBadge } from "../components/StatusBadge";
import { dashboardApi } from "../lib/api";
import { formatDate, formatNumber } from "../lib/format";
import { useAsyncData } from "../lib/hooks";
import type { LearningInsight } from "../types/api";

const columns: Array<Column<LearningInsight>> = [
  {
    key: "signal",
    header: "Signal",
    render: (row) => (
      <div className="min-w-56">
        <p className="line-clamp-2 font-medium">{row.signal}</p>
        <p className="mt-1 truncate text-xs text-muted">{row.video_title || row.video_id || "Global insight"}</p>
      </div>
    )
  },
  { key: "type", header: "Type", render: (row) => <StatusBadge value={row.feedback_type} /> },
  {
    key: "score",
    header: "Score",
    render: (row) => (
      <span className="inline-flex items-center gap-1 whitespace-nowrap">
        <Scale size={14} /> {formatNumber(row.score)}
      </span>
    )
  },
  {
    key: "recommendations",
    header: "Recommendations",
    render: (row) => <RecommendationPreview recommendations={row.recommendations} />
  },
  {
    key: "applied",
    header: "Applied",
    render: (row) => (
      <span className="inline-flex items-center gap-1 whitespace-nowrap">
        <BadgeCheck size={14} /> {row.applied ? "Yes" : "No"}
      </span>
    )
  },
  { key: "created", header: "Created", render: (row) => <span className="whitespace-nowrap">{formatDate(row.created_at)}</span> }
];

export function LearningInsights() {
  const { data, loading, error } = useAsyncData(dashboardApi.learningInsights, []);
  const insights = data || [];
  const applied = insights.filter((item) => item.applied).length;
  const unapplied = insights.length - applied;
  const averageScore =
    insights.length > 0
      ? insights.reduce((sum, item) => sum + (item.score || 0), 0) / insights.length
      : 0;

  if (loading) {
    return <LoadingBlock />;
  }
  if (error) {
    return <ErrorBlock message={error} />;
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <MetricCard label="Insights" value={insights.length} detail="Recent learning signals" icon={Brain} accent="teal" />
        <MetricCard label="Unapplied" value={unapplied} detail="Still available" icon={Lightbulb} accent="amber" />
        <MetricCard label="Average Score" value={averageScore} detail={`${applied} applied`} icon={Scale} accent="violet" />
      </div>
      <Panel title="Learning Insights">
        {insights.length ? (
          <DataTable columns={columns} rows={insights} getRowKey={(row) => row.id} />
        ) : (
          <EmptyBlock label="No learning insights yet" />
        )}
      </Panel>
    </div>
  );
}

function RecommendationPreview({
  recommendations
}: {
  recommendations: Record<string, unknown>;
}) {
  const entries = Object.entries(recommendations).slice(0, 3);
  if (!entries.length) {
    return <span className="text-muted">-</span>;
  }
  return (
    <div className="flex min-w-56 flex-wrap gap-1.5">
      {entries.map(([key, value]) => (
        <span key={key} className="max-w-full truncate rounded-md bg-paper px-2 py-1 text-xs text-ink">
          {key}: {String(value)}
        </span>
      ))}
    </div>
  );
}
