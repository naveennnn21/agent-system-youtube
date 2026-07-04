import { Activity, Clock3, ListChecks, Server, Waypoints } from "lucide-react";
import { DataTable, type Column } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import { Panel } from "../components/Panel";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../components/StateBlocks";
import { StatusBadge } from "../components/StatusBadge";
import { dashboardApi, fallbackLogs } from "../lib/api";
import { formatDate, formatNumber } from "../lib/format";
import { useAsyncData } from "../lib/hooks";
import type { AgentLog } from "../types/api";

const columns: Array<Column<AgentLog>> = [
  {
    key: "source",
    header: "Source",
    render: (row) => (
      <div className="min-w-44">
        <p className="truncate font-medium">{row.source}</p>
        <p className="mt-1 truncate text-xs text-muted">{row.task_id || row.id}</p>
      </div>
    )
  },
  { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status || row.level} /> },
  {
    key: "queue",
    header: "Queue",
    render: (row) => (
      <span className="inline-flex items-center gap-1 whitespace-nowrap">
        <Waypoints size={14} /> {row.queue || "-"}
      </span>
    )
  },
  {
    key: "message",
    header: "Message",
    render: (row) => <span className="line-clamp-2 min-w-64">{row.message}</span>
  },
  {
    key: "created",
    header: "Created",
    render: (row) => (
      <span className="inline-flex items-center gap-1 whitespace-nowrap">
        <Clock3 size={14} /> {formatDate(row.created_at)}
      </span>
    )
  }
];

export function AgentLogs() {
  const { data, loading, error } = useAsyncData(dashboardApi.agentLogs, []);
  const snapshot = data || (error ? fallbackLogs(error) : null);
  const queueEntries = Object.entries(snapshot?.queue_lengths || {});

  if (loading) {
    return <LoadingBlock />;
  }

  return (
    <div className="space-y-6">
      {error ? <ErrorBlock message={error} /> : null}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {queueEntries.length ? (
          queueEntries.map(([queue, length], index) => (
            <MetricCard
              key={queue}
              label={queue}
              value={length}
              detail="Pending messages"
              icon={[Activity, ListChecks, Server, Waypoints][index % 4]}
              accent={(["teal", "violet", "amber", "coral"] as const)[index % 4]}
            />
          ))
        ) : (
          <MetricCard label="Queues" value={0} detail="No queue snapshot" icon={Waypoints} accent="teal" />
        )}
      </div>

      <Panel title="Agent Logs">
        {snapshot?.logs.length ? (
          <DataTable columns={columns} rows={snapshot.logs} getRowKey={(row) => row.id} />
        ) : (
          <EmptyBlock label="No agent activity yet" />
        )}
      </Panel>
    </div>
  );
}
