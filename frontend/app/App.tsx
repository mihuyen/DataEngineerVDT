import { Suspense, lazy, useState } from "react";
import { Layout, Page } from "./components/Layout";

const MarketOverview = lazy(() => import("./components/MarketOverview").then((m) => ({ default: m.MarketOverview })));
const Watchlist = lazy(() => import("./components/Watchlist").then((m) => ({ default: m.Watchlist })));
const StockDetail = lazy(() => import("./components/StockDetail").then((m) => ({ default: m.StockDetail })));
const StockScreener = lazy(() =>
  import("./components/StockScreener").then((m) => ({ default: m.StockScreener }))
);
const PipelineMonitor = lazy(() =>
  import("./components/PipelineMonitor").then((m) => ({ default: m.PipelineMonitor }))
);
const NewsSentiment = lazy(() => import("./components/NewsSentiment").then((m) => ({ default: m.NewsSentiment })));
const AlertHistory = lazy(() => import("./components/AlertHistory").then((m) => ({ default: m.AlertHistory })));

const PageFallback = () => (
  <div style={{ padding: 24, color: "#6b7fa3", fontFamily: "Inter, sans-serif", fontSize: 13 }}>Đang tải...</div>
);

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>("market");
  const [selectedTicker, setSelectedTicker] = useState<string | undefined>(undefined);

  const handleNavigate = (page: string, ticker?: string) => {
    setCurrentPage(page as Page);
    if (ticker) setSelectedTicker(ticker);
  };

  const renderPage = () => {
    switch (currentPage) {
      case "market":
        return <MarketOverview onNavigate={handleNavigate} />;
      case "watchlist":
        return <Watchlist onNavigate={handleNavigate} />;
      case "stock":
        return <StockDetail initialTicker={selectedTicker || "VCB"} onNavigate={handleNavigate} />;
      case "screener":
        return <StockScreener onNavigate={handleNavigate} />;
      case "pipeline":
        return <PipelineMonitor />;
      case "news":
        return <NewsSentiment onNavigate={handleNavigate} />;
      case "alerts":
        return <AlertHistory onNavigate={handleNavigate} initialTicker={selectedTicker} />;
      default:
        return <MarketOverview onNavigate={handleNavigate} />;
    }
  };

  return (
    <Layout currentPage={currentPage} onNavigate={(page) => setCurrentPage(page)}>
      <Suspense fallback={<PageFallback />}>{renderPage()}</Suspense>
    </Layout>
  );
}
