import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { AgentLogs } from "./pages/AgentLogs";
import { Analytics } from "./pages/Analytics";
import { LearningInsights } from "./pages/LearningInsights";
import { Overview } from "./pages/Overview";
import { UploadStatus } from "./pages/UploadStatus";
import { Videos } from "./pages/Videos";
import { routeFromLocation, routePath, type RouteId } from "./routes";

const pages: Record<RouteId, JSX.Element> = {
  overview: <Overview />,
  videos: <Videos />,
  analytics: <Analytics />,
  uploads: <UploadStatus />,
  logs: <AgentLogs />,
  learning: <LearningInsights />
};

export function App() {
  const [route, setRoute] = useState<RouteId>(routeFromLocation);

  useEffect(() => {
    const onPopState = () => setRoute(routeFromLocation());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function handleRouteChange(nextRoute: RouteId) {
    setRoute(nextRoute);
    window.history.pushState({}, "", routePath(nextRoute));
  }

  return (
    <Layout route={route} onRouteChange={handleRouteChange}>
      {pages[route]}
    </Layout>
  );
}
