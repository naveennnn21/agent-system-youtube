export type Metric = {
  label: string;
  value: number | string | null;
  detail?: string | null;
};

export type TrendPoint = {
  date: string;
  views: number;
  watch_time_seconds: number;
  average_ctr?: number | null;
  average_retention?: number | null;
};

export type Overview = {
  metrics: Metric[];
  video_status_counts: Record<string, number>;
  upload_status_counts: Record<string, number>;
  trend: TrendPoint[];
};

export type Video = {
  id: string;
  title: string;
  status: string;
  duration_seconds?: number | null;
  file_path?: string | null;
  thumbnail_path?: string | null;
  scheduled_at?: string | null;
  published_at?: string | null;
  created_at: string;
  latest_views: number;
  latest_retention_rate?: number | null;
  latest_ctr?: number | null;
};

export type Upload = {
  id: string;
  video_id: string;
  video_title?: string | null;
  platform: string;
  external_video_id?: string | null;
  upload_url?: string | null;
  status: string;
  privacy_status: string;
  error_message?: string | null;
  started_at?: string | null;
  uploaded_at?: string | null;
  created_at: string;
};

export type AgentLog = {
  id: string;
  level: string;
  source: string;
  message: string;
  queue?: string | null;
  task_id?: string | null;
  status?: string | null;
  created_at?: string | null;
  metadata: Record<string, unknown>;
};

export type QueueSnapshot = {
  queue_lengths: Record<string, number>;
  logs: AgentLog[];
};

export type LearningInsight = {
  id: string;
  feedback_type: string;
  signal: string;
  score?: number | null;
  notes?: string | null;
  recommendations: Record<string, unknown>;
  applied: boolean;
  model_version?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  video_id?: string | null;
  video_title?: string | null;
};

export type AnalyticsReport = {
  start_date: string;
  end_date: string;
  video_count: number;
  total_views: number;
  total_watch_time_seconds: number;
  average_ctr?: number | null;
  average_retention?: number | null;
  subscribers_gained: number;
  top_videos: Array<Record<string, unknown>>;
  daily_totals: Array<Record<string, unknown>>;
};
