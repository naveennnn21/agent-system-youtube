export function formatNumber(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "0";
  }
  if (typeof value === "string") {
    return value;
  }
  return new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(value);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "0%";
  }
  const normalized = value <= 1 ? value * 100 : value;
  return `${new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(normalized)}%`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

export function secondsToShortTime(value: number | null | undefined): string {
  if (!value) {
    return "0s";
  }
  if (value < 60) {
    return `${value}s`;
  }
  const minutes = Math.floor(value / 60);
  const seconds = value % 60;
  return seconds ? `${minutes}m ${seconds}s` : `${minutes}m`;
}
