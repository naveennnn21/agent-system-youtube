import {
  Clock,
  Eye,
  ListVideo,
  Users
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { DataTable, type Column } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import { Panel } from "../components/Panel";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../components/StateBlocks";
import { dashboardApi } from "../lib/api";
import { formatNumber, formatPercent } from "../lib/format";
import { useAsyncData } from "../lib/hooks";

type TopVideo = Record<string, unknown>;

const topVideoColumns: Array<Column<TopVideo>> = [
  {
    key: "video",
    header: "Video",
    render: (row) => <span className="font-mono text-xs">{String(row.video_id || "-")}</span>
  },
  { key: "views", header: "Views", render: (row) => formatNumber(Number(row.views || 0)) },
  {
    key: "watch",
    header: "Watch Time",
    render: (row) => formatNumber(Number(row.watch_time_seconds || 0))
  },
  {
    key: "retention",
    header: "Retention",
    render: (row) => formatPercent(Number(row.retention_rate || 0))
  },
  {
    key: "ctr",
    header: "CTR",
    render: (row) => formatPercent(Number(row.click_through_rate || 0))
  }
];

export function Analytics() {
  const { data, loading, error } = useAsyncData(dashboardApi.analyticsReport, []);

  if (loading) {
    return <LoadingBlock />;
  }
  if (error) {
    return <ErrorBlock message={error} />;
  }
  if (!data) {
    return <EmptyBlock label="No analytics report yet" />;
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Videos" value={data.video_count} icon={ListVideo} accent="teal" />
        <MetricCard label="Views" value={data.total_views} icon={Eye} accent="violet" />
        <MetricCard label="Watch Time" value={data.total_watch_time_seconds} icon={Clock} accent="amber" />
        <MetricCard label="Subscribers" value={data.subscribers_gained} icon={Users} accent="coral" />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Daily Views">
          {data.daily_totals.length ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.daily_totals} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke="#d9dee7" strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="views" fill="#1f9d8a" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyBlock label="No daily analytics yet" />
          )}
        </Panel>

        <Panel title="Daily Watch Time">
          {data.daily_totals.length ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.daily_totals} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke="#d9dee7" strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="watch_time_seconds" stroke="#df5b45" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyBlock label="No watch time data yet" />
          )}
        </Panel>
      </div>

      <Panel title="Top Videos">
        {data.top_videos.length ? (
          <DataTable columns={topVideoColumns} rows={data.top_videos} getRowKey={(row) => String(row.analytics_id)} />
        ) : (
          <EmptyBlock label="No top videos yet" />
        )}
      </Panel>
    </div>
  );
}
