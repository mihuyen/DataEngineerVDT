import { useEffect, useState } from "react";
import { Star, StarOff, Search } from "lucide-react";
import {
  StockOption,
  WatchlistRow,
  addToWatchlist,
  fetchStocks,
  fetchWatchlist,
  removeFromWatchlist,
} from "./api";

const CARD: React.CSSProperties = {
  background: "#111827", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: 16,
};
const MONO: React.CSSProperties = { fontFamily: "JetBrains Mono, monospace" };
const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };

interface WatchlistProps {
  onNavigate: (page: string, ticker?: string) => void;
}

export function Watchlist({ onNavigate }: WatchlistProps) {
  const [rows, setRows] = useState<WatchlistRow[] | null>(null);
  const [error, setError] = useState(false);
  const [stockOptions, setStockOptions] = useState<StockOption[]>([]);
  const [searchText, setSearchText] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [pendingTicker, setPendingTicker] = useState<string | null>(null);

  const load = () => {
    fetchWatchlist()
      .then((payload) => {
        setRows(payload.data);
        setError(false);
      })
      .catch(() => {
        setRows([]);
        setError(true);
      });
  };

  useEffect(() => {
    load();
    fetchStocks().then(setStockOptions).catch(() => setStockOptions([]));
  }, []);

  const handleAdd = (ticker: string) => {
    setPendingTicker(ticker);
    addToWatchlist(ticker)
      .then(load)
      .finally(() => {
        setPendingTicker(null);
        setSearchText("");
        setSearchOpen(false);
      });
  };

  const handleRemove = (ticker: string) => {
    setPendingTicker(ticker);
    removeFromWatchlist(ticker)
      .then(load)
      .finally(() => setPendingTicker(null));
  };

  const watchedTickers = new Set((rows ?? []).map((r) => r.ticker));
  const keyword = searchText.trim().toLowerCase();
  const searchCandidates = keyword
    ? stockOptions
        .filter((s) => !watchedTickers.has(s.ticker))
        .filter((s) => s.ticker.toLowerCase().includes(keyword) || s.name.toLowerCase().includes(keyword))
        .slice(0, 20)
    : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ color: "#e2e8f0", margin: 0, fontSize: 18, fontWeight: 700, ...INTER }}>Bảng giá & Watchlist</h1>
          <p style={{ color: "#6b7fa3", margin: 0, fontSize: 12, ...INTER }}>
            {rows ? `${rows.length} mã đang theo dõi` : "Đang tải..."}
          </p>
        </div>
        <div style={{ position: "relative", width: 280 }}>
          <div style={{ position: "relative" }}>
            <Search size={14} style={{ position: "absolute", left: 10, top: 9, color: "#6b7fa3" }} />
            <input
              value={searchText}
              onFocus={() => setSearchOpen(true)}
              onChange={(e) => {
                setSearchText(e.target.value);
                setSearchOpen(true);
              }}
              onBlur={() => window.setTimeout(() => setSearchOpen(false), 140)}
              placeholder="Thêm mã vào watchlist..."
              style={{
                width: "100%", background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 5, color: "#e2e8f0", padding: "7px 10px 7px 30px", fontSize: 12,
                ...INTER, outline: "none", boxSizing: "border-box",
              }}
            />
          </div>
          {searchOpen && searchCandidates.length > 0 && (
            <div style={{
              position: "absolute", top: "calc(100% + 4px)", right: 0, width: "100%", maxHeight: 280,
              overflowY: "auto", background: "#111827", border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 6, boxShadow: "0 18px 50px rgba(0,0,0,0.45)", zIndex: 30,
            }}>
              {searchCandidates.map((s) => (
                <button
                  key={s.ticker}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    handleAdd(s.ticker);
                  }}
                  style={{
                    width: "100%", display: "flex", justifyContent: "space-between", gap: 8,
                    padding: "8px 10px", border: "none", borderBottom: "1px solid rgba(255,255,255,0.04)",
                    background: "transparent", color: "#e2e8f0", cursor: "pointer", textAlign: "left",
                  }}
                >
                  <span style={{ ...MONO, color: "#8b5cf6", fontWeight: 700, fontSize: 12 }}>{s.ticker}</span>
                  <span style={{ ...INTER, color: "#6b7fa3", fontSize: 11, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {error && (
        <div style={{ ...CARD, borderColor: "rgba(255,77,109,0.2)", background: "rgba(255,77,109,0.04)" }}>
          <span style={{ color: "#ff4d6d", fontSize: 12, ...INTER }}>Không kết nối được API watchlist.</span>
        </div>
      )}

      <div style={CARD}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
              {["", "Mã", "Tên", "Giá", "+/-", "%", "KL", "GT (tỷ)"].map((h) => (
                <th key={h} style={{ color: "#6b7fa3", fontSize: 11, textAlign: h === "Tên" || h === "" ? "left" : "right", padding: "6px 10px", ...INTER, textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(rows ?? []).map((r) => {
              const up = r.change >= 0;
              return (
                <tr
                  key={r.ticker}
                  style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}
                  onClick={() => onNavigate("stock", r.ticker)}
                >
                  <td style={{ padding: "9px 10px" }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemove(r.ticker);
                      }}
                      disabled={pendingTicker === r.ticker}
                      style={{ background: "none", border: "none", cursor: "pointer", padding: 0, display: "flex" }}
                      title="Bỏ theo dõi"
                    >
                      <Star size={14} fill="#f59e0b" color="#f59e0b" />
                    </button>
                  </td>
                  <td style={{ padding: "9px 10px", ...MONO, color: "#8b5cf6", fontWeight: 700, fontSize: 12 }}>{r.ticker}</td>
                  <td style={{ padding: "9px 10px", color: "#e2e8f0", fontSize: 12, ...INTER, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 220 }}>{r.name}</td>
                  <td style={{ padding: "9px 10px", textAlign: "right", ...MONO, color: up ? "#00d97e" : "#ff4d6d", fontSize: 12 }}>{r.price.toLocaleString("vi-VN")}</td>
                  <td style={{ padding: "9px 10px", textAlign: "right", ...MONO, color: up ? "#00d97e" : "#ff4d6d", fontSize: 12 }}>{up ? "+" : ""}{r.change.toFixed(2)}</td>
                  <td style={{ padding: "9px 10px", textAlign: "right", ...MONO, color: up ? "#00d97e" : "#ff4d6d", fontSize: 12 }}>{up ? "+" : ""}{r.pct.toFixed(2)}%</td>
                  <td style={{ padding: "9px 10px", textAlign: "right", ...MONO, color: "#6b7fa3", fontSize: 12 }}>{(r.volume / 1000).toFixed(0)}K</td>
                  <td style={{ padding: "9px 10px", textAlign: "right", ...MONO, color: "#6b7fa3", fontSize: 12 }}>{(r.value / 1_000_000_000).toFixed(1)}</td>
                </tr>
              );
            })}
            {rows && rows.length === 0 && (
              <tr>
                <td colSpan={8} style={{ padding: "20px 10px", color: "#6b7fa3", fontSize: 12, ...INTER, textAlign: "center" }}>
                  <StarOff size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
                  Chưa có mã nào trong watchlist. Dùng ô tìm kiếm phía trên để thêm.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
