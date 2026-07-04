import { Clock, Eye, MousePointerClick, TimerReset } from "lucide-react";
import { DataTable, type Column } from "../components/DataTable";
import { Panel } from "../components/Panel";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../components/StateBlocks";
import { StatusBadge } from "../components/StatusBadge";
import { dashboardApi } from "../lib/api";
import { formatDate, formatNumber, formatPercent, secondsToShortTime } from "../lib/format";
import { useAsyncData } from "../lib/hooks";
import type { Video } from "../types/api";

const columns: Array<Column<Video>> = [
  {
    key: "title",
    header: "Video",
    render: (row) => (
      <div className="min-w-56">
        <p className="line-clamp-2 font-medium">{row.title}</p>
        <p className="mt-1 truncate text-xs text-muted">{row.id}</p>
      </div>
    )
  },
  { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status} /> },
  {
    key: "duration",
    header: "Duration",
    render: (row) => (
      <span className="inline-flex items-center gap-1 whitespace-nowrap">
        <Clock size={14} /> {secondsToShortTime(row.duration_seconds)}
      </span>
    )
  },
  {
    key: "views",
    header: "Views",
    render: (row) => (
      <span className="inline-flex items-center gap-1 whitespace-nowrap">
        <Eye size={14} /> {formatNumber(row.latest_views)}
      </span>
    )
  },
  {
    key: "retention",
    header: "Retention",
    render: (row) => (
      <span className="inline-flex items-center gap-1 whitespace-nowrap">
        <TimerReset size={14} /> {formatPercent(row.latest_retention_rate)}
      </span>
    )
  },
  {
    key: "ctr",
    header: "CTR",
    render: (row) => (
      <span className="inline-flex items-center gap-1 whitespace-nowrap">
        <MousePointerClick size={14} /> {formatPercent(row.latest_ctr)}
      </span>
    )
  },
  { key: "created", header: "Created", render: (row) => <span className="whitespace-nowrap">{formatDate(row.created_at)}</span> }
];

export function Videos() {
  const { data, loading, error } = useAsyncData(dashboardApi.videos, []);

  if (loading) {
    return <LoadingBlock />;
  }
  if (error) {
    return <ErrorBlock message={error} />;
  }

  return (
    <Panel title="Recent Videos">
      {data?.length ? (
        <DataTable columns={columns} rows={data} getRowKey={(row) => row.id} />
      ) : (
        <EmptyBlock label="No videos created yet" />
      )}
    </Panel>
  );
}
