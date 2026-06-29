import { useState } from "react";
import {
  BarChart2, TrendingUp, ScanLine, Database, Star,
  Newspaper, Bell, ChevronLeft, Menu, Clock, Wifi
} from "lucide-react";

type Page = "market" | "watchlist" | "stock" | "screener" | "pipeline" | "news" | "alerts";

interface NavItem { id: Page; label: string; labelShort: string; icon: React.ReactNode; }

// Investor-facing pages: what someone tracking the market actually opens.
const navItems: NavItem[] = [
  { id: "market", label: "Tổng quan thị trường", labelShort: "Thị trường", icon: <BarChart2 size={18} /> },
  { id: "watchlist", label: "Bảng giá & Watchlist", labelShort: "Watchlist", icon: <Star size={18} /> },
  { id: "stock", label: "Chi tiết cổ phiếu", labelShort: "Cổ phiếu", icon: <TrendingUp size={18} /> },
  { id: "screener", label: "Bộ lọc cổ phiếu", labelShort: "Bộ lọc", icon: <ScanLine size={18} /> },
  { id: "news", label: "Tin tức & cảm xúc", labelShort: "Tin tức", icon: <Newspaper size={18} /> },
  { id: "alerts", label: "Lịch sử cảnh báo", labelShort: "Cảnh báo", icon: <Bell size={18} /> },
];

// Operational pages: how the data behind the app is doing, not market data
// itself -- kept visually separate so it doesn't compete with investor
// workflows above it.
const adminNavItems: NavItem[] = [
  { id: "pipeline", label: "Giám sát pipeline", labelShort: "Pipeline", icon: <Database size={18} /> },
];

const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };

function renderNavButton(
  item: NavItem,
  currentPage: Page,
  collapsed: boolean,
  onNavigate: (page: Page) => void
) {
  const active = currentPage === item.id;
  return (
    <button
      key={item.id}
      onClick={() => onNavigate(item.id)}
      title={collapsed ? item.label : undefined}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: collapsed ? "13px 0" : "13px 14px",
        justifyContent: collapsed ? "center" : "flex-start",
        borderRadius: 8,
        border: "none",
        cursor: "pointer",
        background: active ? "rgba(245,158,11,0.12)" : "transparent",
        color: active ? "#8b5cf6" : "#6b7fa3",
        fontSize: 20,
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
        <span style={{ marginLeft: "auto", width: 5, height: 5, borderRadius: "50%", background: "#8b5cf6", flexShrink: 0 }} />
      )}
    </button>
  );
}

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
    <div
      style={{
        background: "#0b0f1a",
        color: "#e2e8f0",
        display: "flex",
        fontFamily: "Inter, sans-serif",
        height: "100vh",
        overflow: "hidden",
        width: "100%",
      }}
    >
      {/* Sidebar */}
      <aside
        style={{
          width: collapsed ? 64 : 325,
          background: "#0d1220",
          borderRight: "1px solid rgba(255,255,255,0.07)",
          transition: "width 0.2s ease",
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Logo */}
        <div
          style={{
            alignItems: "center",
            borderBottom: "1px solid rgba(255,255,255,0.07)",
            display: "flex",
            gap: 12,
            minHeight: 70,
            padding: "0 12px",
          }}
        >
          <div
            style={{
              alignItems: "center",
              background: "#8b5cf6",
              borderRadius: 6,
              display: "flex",
              flexShrink: 0,
              height: 40,
              justifyContent: "center",
              width: 40,
            }}
          >
            <BarChart2 size={16} color="#0b0f1a" />
          </div>
          {!collapsed && (
            <span style={{ color: "#e2e8f0", fontFamily: "Inter, sans-serif", fontSize: 20, fontWeight: 700, letterSpacing: "0.01em", whiteSpace: "nowrap" }}>
              VN<span style={{ color: "#8b5cf6" }}>Stock</span> Analytics
            </span>
          )}
        </div>

        {/* Nav */}
        <nav
          style={{
            display: "flex",
            flex: 1,
            flexDirection: "column",
            gap: 8,
            padding: "28px 10px",
          }}
        >
          {navItems.map((item) => renderNavButton(item, currentPage, collapsed, onNavigate))}

          {!collapsed && (
            <div style={{ ...INTER, color: "#3f4a63", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", padding: "16px 14px 4px" }}>
              Quản trị dữ liệu
            </div>
          )}
          {collapsed && <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", margin: "8px 6px" }} />}
          {adminNavItems.map((item) => renderNavButton(item, currentPage, collapsed, onNavigate))}
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
      <div style={{ display: "flex", flex: 1, flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
        {/* Top bar */}
        <header style={{
          height: 70, background: "#0d1220",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          display: "flex", alignItems: "center",
          padding: "0 30px", gap: 28, flexShrink: 0,
        }}>
          <div style={{ flex: 1 }} />
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginLeft: "auto" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 4, color: "#00d97e" }}>
              <Wifi size={12} />
              <span style={{ fontSize: 16, fontFamily: "Inter, sans-serif" }}>Live</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 4, color: "#6b7fa3" }}>
              <Clock size={12} />
              <span style={{ fontSize: 16, fontFamily: "JetBrains Mono, monospace" }}>{dateStr} · {timeStr}</span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main style={{ flex: 1, minHeight: 0, overflowX: "hidden", overflowY: "auto", padding: "32px 30px" }}>
          {children}
        </main>
      </div>
    </div>
  );
}

export type { Page };
