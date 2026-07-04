import {
  AlertTriangle,
  Clock,
  Eye,
  MousePointerClick,
  PlaySquare,
  TrendingUp,
  UploadCloud,
  Users
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { MetricCard } from "../components/MetricCard";
import { Panel } from "../components/Panel";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../components/StateBlocks";
import { dashboardApi, fallbackOverview } from "../lib/api";
import { formatPercent } from "../lib/format";
import { useAsyncData } from "../lib/hooks";

const metricIcons = [PlaySquare, Eye, Clock, MousePointerClick, TrendingUp, Users, UploadCloud, AlertTriangle];
const accents = ["teal", "violet", "amber", "coral"] as const;

export function Overview() {
  const { data, loading, error } = useAsyncData(dashboardApi.overview, []);
  const overview = data || fallbackOverview();
  const statusData = Object.entries(overview.video_status_counts).map(([status, count]) => ({
    status,
    count
  }));

  if (loading) {
    return <LoadingBlock />;
  }

  return (
    <div className="space-y-6">
      {error ? <ErrorBlock message={error} /> : null}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {overview.metrics.map((metric, index) => {
          const Icon = metricIcons[index] || TrendingUp;
          const percent = metric.label.toLowerCase().includes("ctr") || metric.label.toLowerCase().includes("retention");
          return (
            <MetricCard
              key={metric.label}
              label={metric.label}
              value={metric.value}
              detail={metric.detail}
              icon={Icon}
              accent={accents[index % accents.length]}
              percent={percent}
            />
          );
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <Panel title="Views Trend">
          {overview.trend.length ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={overview.trend} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke="#d9dee7" strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value) => String(value)} />
                  <Area type="monotone" dataKey="views" stroke="#1f9d8a" fill="#1f9d8a" fillOpacity={0.18} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyBlock label="No analytics trend yet" />
          )}
        </Panel>

        <Panel title="Video Status">
          {statusData.length ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusData} layout="vertical" margin={{ left: 12, right: 16, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke="#d9dee7" strokeDasharray="3 3" />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis dataKey="status" type="category" width={86} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#df5b45" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyBlock label="No videos yet" />
          )}
        </Panel>
      </div>

      <Panel title="Retention And CTR">
        {overview.trend.length ? (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={overview.trend} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
                <CartesianGrid stroke="#d9dee7" strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={(value) => formatPercent(Number(value))} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value) => formatPercent(Number(value))} />
                <Area type="monotone" dataKey="average_retention" stroke="#7257d5" fill="#7257d5" fillOpacity={0.14} />
                <Area type="monotone" dataKey="average_ctr" stroke="#c88719" fill="#c88719" fillOpacity={0.12} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyBlock label="No retention or CTR data yet" />
        )}
      </Panel>
    </div>
  );
}
