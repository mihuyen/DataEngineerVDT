import { useState } from "react";
import { Layout, Page } from "./components/Layout";
import { MarketOverview } from "./components/MarketOverview";
import { StockDetail } from "./components/StockDetail";
import { TechnicalScanner } from "./components/TechnicalScanner";
import { PipelineMonitor } from "./components/PipelineMonitor";
import { RealtimeVWAP } from "./components/RealtimeVWAP";
import { NewsSentiment } from "./components/NewsSentiment";
import { AlertHistory } from "./components/AlertHistory";

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
      {renderPage()}
    </Layout>
  );
}
