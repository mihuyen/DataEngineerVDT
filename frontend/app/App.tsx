import { Suspense, lazy, useState } from "react";
import { Layout, Page } from "./components/Layout";

const MarketOverview = lazy(() => import("./components/MarketOverview").then((m) => ({ default: m.MarketOverview })));
const StockDetail = lazy(() => import("./components/StockDetail").then((m) => ({ default: m.StockDetail })));
const TechnicalScanner = lazy(() =>
  import("./components/TechnicalScanner").then((m) => ({ default: m.TechnicalScanner }))
);
const PipelineMonitor = lazy(() =>
  import("./components/PipelineMonitor").then((m) => ({ default: m.PipelineMonitor }))
);
const RealtimeVWAP = lazy(() => import("./components/RealtimeVWAP").then((m) => ({ default: m.RealtimeVWAP })));
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
      case "stock":
        return <StockDetail initialTicker={selectedTicker || "VCB"} />;
      case "scanner":
        return <TechnicalScanner onNavigate={handleNavigate} />;
      case "pipeline":
        return <PipelineMonitor />;
      case "vwap":
        return <RealtimeVWAP onNavigate={handleNavigate} />;
      case "news":
        return <NewsSentiment onNavigate={handleNavigate} />;
      case "alerts":
        return <AlertHistory onNavigate={handleNavigate} />;
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
