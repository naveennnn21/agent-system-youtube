import { AlertTriangle, CalendarClock, ExternalLink, Shield } from "lucide-react";
import { DataTable, type Column } from "../components/DataTable";
import { Panel } from "../components/Panel";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../components/StateBlocks";
import { StatusBadge } from "../components/StatusBadge";
import { dashboardApi } from "../lib/api";
import { formatDate } from "../lib/format";
import { useAsyncData } from "../lib/hooks";
import type { Upload } from "../types/api";

const columns: Array<Column<Upload>> = [
  {
    key: "video",
    header: "Video",
    render: (row) => (
      <div className="min-w-56">
        <p className="line-clamp-2 font-medium">{row.video_title || "Untitled video"}</p>
        <p className="mt-1 truncate text-xs text-muted">{row.video_id}</p>
      </div>
    )
  },
  { key: "status", header: "Status", render: (row) => <StatusBadge value={row.status} /> },
  {
    key: "privacy",
    header: "Privacy",
    render: (row) => (
      <span className="inline-flex items-center gap-1 whitespace-nowrap">
        <Shield size={14} /> {row.privacy_status}
      </span>
    )
  },
  {
    key: "external",
    header: "YouTube",
    render: (row) =>
      row.upload_url ? (
        <a
          className="focus-ring inline-flex items-center gap-1 rounded-md text-teal hover:underline"
          href={row.upload_url}
          rel="noreferrer"
          target="_blank"
        >
          Open <ExternalLink size={14} />
        </a>
      ) : (
        <span className="text-muted">{row.external_video_id || "-"}</span>
      )
  },
  {
    key: "time",
    header: "Uploaded",
    render: (row) => (
      <span className="inline-flex items-center gap-1 whitespace-nowrap">
        <CalendarClock size={14} /> {formatDate(row.uploaded_at || row.started_at || row.created_at)}
      </span>
    )
  },
  {
    key: "error",
    header: "Error",
    render: (row) =>
      row.error_message ? (
        <span className="line-clamp-2 inline-flex items-start gap-1 text-coral">
          <AlertTriangle className="mt-0.5 shrink-0" size={14} /> {row.error_message}
        </span>
      ) : (
        <span className="text-muted">-</span>
      )
  }
];

export function UploadStatus() {
  const { data, loading, error } = useAsyncData(dashboardApi.uploads, []);

  if (loading) {
    return <LoadingBlock />;
  }
  if (error) {
    return <ErrorBlock message={error} />;
  }

  return (
    <Panel title="Upload Status">
      {data?.length ? (
        <DataTable columns={columns} rows={data} getRowKey={(row) => row.id} />
      ) : (
        <EmptyBlock label="No upload attempts yet" />
      )}
    </Panel>
  );
}
