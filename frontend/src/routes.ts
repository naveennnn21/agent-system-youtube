export type RouteId = "overview" | "videos" | "analytics" | "uploads" | "logs" | "learning";

export function routeFromLocation(): RouteId {
  const value = window.location.pathname.replace("/", "") || "overview";
  if (["overview", "videos", "analytics", "uploads", "logs", "learning"].includes(value)) {
    return value as RouteId;
  }
  return "overview";
}

export function routePath(route: RouteId): string {
  return route === "overview" ? "/" : `/${route}`;
}
