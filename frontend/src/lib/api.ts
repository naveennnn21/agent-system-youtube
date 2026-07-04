import type {
  AgentLog,
  AnalyticsReport,
  LearningInsight,
  Overview,
  QueueSnapshot,
  Upload,
  Video
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" }
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const dashboardApi = {
  overview: () => request<Overview>("/dashboard/overview"),
  videos: () => request<Video[]>("/dashboard/videos"),
  uploads: () => request<Upload[]>("/dashboard/uploads"),
  agentLogs: () => request<QueueSnapshot>("/dashboard/agent-logs"),
  learningInsights: () => request<LearningInsight[]>("/dashboard/learning-insights"),
  analyticsReport: () => request<AnalyticsReport>("/analytics/report"),
  queues: () => request<QueueSnapshot>("/automation/queues")
};

export function fallbackOverview(): Overview {
  return {
    metrics: [
      { label: "Videos", value: 0, detail: "0 published" },
      { label: "Views", value: 0, detail: "All stored analytics snapshots" },
      { label: "Watch Time", value: 0, detail: "Seconds watched" },
      { label: "Avg CTR", value: 0, detail: "Stored snapshot average" },
      { label: "Avg Retention", value: 0, detail: "Stored snapshot average" },
      { label: "Subscribers", value: 0, detail: "Net gained from snapshots" },
      { label: "Pending Uploads", value: 0, detail: "Queued, uploading, or retrying" },
      { label: "Failures", value: 0, detail: "Videos marked failed" }
    ],
    video_status_counts: {},
    upload_status_counts: {},
    trend: []
  };
}

export function fallbackLogs(error: string): QueueSnapshot {
  const log: AgentLog = {
    id: "dashboard-error",
    level: "error",
    source: "dashboard",
    message: error,
    metadata: {}
  };
  return { queue_lengths: {}, logs: [log] };
}
