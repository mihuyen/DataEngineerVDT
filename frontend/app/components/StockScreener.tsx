import { useState } from "react";
import { TechnicalScanner } from "./TechnicalScanner";
import { RealtimeVWAP } from "./RealtimeVWAP";

const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };

type Tab = "technical" | "vwap";

interface StockScreenerProps {
  onNavigate: (page: string, ticker?: string) => void;
}

export function StockScreener({ onNavigate }: StockScreenerProps) {
  const [tab, setTab] = useState<Tab>("technical");

  const tabs: { id: Tab; label: string }[] = [
    { id: "technical", label: "Kỹ thuật" },
    { id: "vwap", label: "VWAP" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", gap: 8 }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "6px 16px",
              borderRadius: 6,
              border: "1px solid rgba(255,255,255,0.1)",
              background: tab === t.id ? "#8b5cf6" : "transparent",
              color: tab === t.id ? "#0b0f1a" : "#6b7fa3",
              fontSize: 13,
              ...INTER,
              cursor: "pointer",
              fontWeight: tab === t.id ? 600 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "technical" ? <TechnicalScanner onNavigate={onNavigate} /> : <RealtimeVWAP onNavigate={onNavigate} />}
    </div>
  );
}
