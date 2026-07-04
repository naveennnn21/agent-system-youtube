import { AlertTriangle, Loader2 } from "lucide-react";

export function LoadingBlock() {
  return (
    <div className="flex min-h-40 items-center justify-center rounded-lg border border-dashed border-line bg-white p-6 text-muted">
      <Loader2 className="mr-2 animate-spin" size={18} />
      Loading
    </div>
  );
}

export function ErrorBlock({ message }: { message: string }) {
  return (
    <div className="flex min-h-40 items-center justify-center rounded-lg border border-coral/20 bg-coral/5 p-6 text-coral">
      <AlertTriangle className="mr-2 shrink-0" size={18} />
      <span className="break-words text-sm">{message}</span>
    </div>
  );
}

export function EmptyBlock({ label }: { label: string }) {
  return (
    <div className="flex min-h-40 items-center justify-center rounded-lg border border-dashed border-line bg-white p-6 text-sm text-muted">
      {label}
    </div>
  );
}
