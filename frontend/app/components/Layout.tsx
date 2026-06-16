import { useState } from "react";
import {
  BarChart2, TrendingUp, ScanLine, Database, Activity,
  Newspaper, Bell, ChevronLeft, Menu, Clock, Wifi
} from "lucide-react";

type Page = "market" | "stock" | "scanner" | "pipeline" | "vwap" | "news" | "alerts";

interface NavItem { id: Page; label: string; labelShort: string; icon: React.ReactNode; }

const navItems: NavItem[] = [
  { id: "market", label: "Market Overview", labelShort: "Market", icon: <BarChart2 size={18} /> },
  { id: "stock", label: "Stock Detail", labelShort: "Stock", icon: <TrendingUp size={18} /> },
  { id: "scanner", label: "Signal Scanner", labelShort: "Scanner", icon: <ScanLine size={18} /> },
  { id: "pipeline", label: "Pipeline Monitor", labelShort: "Pipeline", icon: <Database size={18} /> },
  { id: "vwap", label: "Realtime VWAP", labelShort: "VWAP", icon: <Activity size={18} /> },
  { id: "news", label: "News & Sentiment", labelShort: "News", icon: <Newspaper size={18} /> },
  { id: "alerts", label: "Alert History", labelShort: "Alerts", icon: <Bell size={18} /> },
];

interface LayoutProps {
  currentPage: Page;
  onNavigate: (page: Page) => void;
  children: React.ReactNode;
}

export function Layout({ currentPage, onNavigate, children }: LayoutProps) {
  const [collapsed, setCollapsed] = useState(false);
  const now = new Date();
  const timeStr = now.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const dateStr = now.toLocaleDateString("vi-VN", { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric" });

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "#0b0f1a", fontFamily: "Inter, sans-serif" }}>
      {/* Sidebar */}
      <aside
        style={{
          width: collapsed ? 56 : 220,
          background: "#0d1220",
          borderRight: "1px solid rgba(255,255,255,0.07)",
          transition: "width 0.2s ease",
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Logo */}
        <div className="flex items-center gap-2 px-3 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)", minHeight: 56 }}>
          <div className="flex items-center justify-center rounded" style={{ width: 28, height: 28, background: "#f59e0b", flexShrink: 0 }}>
            <BarChart2 size={16} color="#0b0f1a" />
          </div>
          {!collapsed && (
            <span style={{ color: "#e2e8f0", fontFamily: "Inter, sans-serif", fontSize: 13, fontWeight: 700, letterSpacing: "0.02em", whiteSpace: "nowrap" }}>
              VN<span style={{ color: "#f59e0b" }}>Stock</span> Analytics
            </span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 flex flex-col gap-0.5 px-2">
          {navItems.map((item) => {
            const active = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                title={collapsed ? item.label : undefined}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: collapsed ? "9px 0" : "9px 10px",
                  justifyContent: collapsed ? "center" : "flex-start",
                  borderRadius: 6,
                  border: "none",
                  cursor: "pointer",
                  background: active ? "rgba(245,158,11,0.12)" : "transparent",
                  color: active ? "#f59e0b" : "#6b7fa3",
                  fontSize: 13,
                  fontWeight: active ? 600 : 400,
                  fontFamily: "Inter, sans-serif",
                  transition: "all 0.15s ease",
                  width: "100%",
                  textAlign: "left",
                  whiteSpace: "nowrap",
                }}
                onMouseEnter={(e) => {
                  if (!active) (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.04)";
                }}
                onMouseLeave={(e) => {
                  if (!active) (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                }}
              >
                <span style={{ flexShrink: 0 }}>{item.icon}</span>
                {!collapsed && <span>{item.label}</span>}
                {active && !collapsed && (
                  <span style={{ marginLeft: "auto", width: 4, height: 4, borderRadius: "50%", background: "#f59e0b", flexShrink: 0 }} />
                )}
              </button>
            );
          })}
        </nav>

        {/* Collapse button */}
        <div style={{ padding: "12px 8px", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
          <button
            onClick={() => setCollapsed(!collapsed)}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              gap: 8, width: "100%", padding: "7px 0", borderRadius: 6,
              border: "none", cursor: "pointer",
              background: "transparent", color: "#6b7fa3", fontSize: 12,
              fontFamily: "Inter, sans-serif",
            }}
          >
            {collapsed ? <Menu size={16} /> : <><ChevronLeft size={16} /><span>Thu gọn</span></>}
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header style={{
          height: 48, background: "#0d1220",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          display: "flex", alignItems: "center",
          padding: "0 20px", gap: 20, flexShrink: 0,
        }}>
          <div style={{ flex: 1, display: "flex", gap: 24, alignItems: "center" }}>
            {/* Market index mini display */}
            {[
              { label: "VN-Index", value: "1.283,7", chg: "+35,2", pct: "+2,82%", up: true },
              { label: "HNX-Index", value: "228,4", chg: "+4,1", pct: "+1,83%", up: true },
              { label: "VN30", value: "1.341,5", chg: "+28,6", pct: "+2,18%", up: true },
            ].map((idx) => (
              <div key={idx.label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ color: "#6b7fa3", fontSize: 11, fontFamily: "Inter, sans-serif" }}>{idx.label}</span>
                <span style={{ color: "#e2e8f0", fontSize: 12, fontWeight: 600, fontFamily: "JetBrains Mono, monospace" }}>{idx.value}</span>
                <span style={{ color: idx.up ? "#00d97e" : "#ff4d6d", fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}>{idx.chg} ({idx.pct})</span>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 4, color: "#00d97e" }}>
              <Wifi size={12} />
              <span style={{ fontSize: 11, fontFamily: "Inter, sans-serif" }}>Live</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 4, color: "#6b7fa3" }}>
              <Clock size={12} />
              <span style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}>{dateStr} · {timeStr}</span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main style={{ flex: 1, overflow: "auto", padding: 20 }}>
          {children}
        </main>
      </div>
    </div>
  );
}

export type { Page };
