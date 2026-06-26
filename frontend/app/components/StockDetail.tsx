import { useEffect, useState, useMemo } from "react";
import {
  ComposedChart, Line, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";
import { dataSnapshotMeta, generateCandlestickData, newsSentiment, stockList } from "./mockData";
import { Candle, StockOption, fetchCandles, fetchStocks } from "./api";

const CARD: React.CSSProperties = {
  background: "#111827", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: 16,
};
const MONO: React.CSSProperties = { fontFamily: "JetBrains Mono, monospace" };
const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };

function KPICard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div style={CARD}>
      <div style={{ ...INTER, color: "#6b7fa3", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{label}</div>
      <div style={{ ...MONO, color: color || "#e2e8f0", fontSize: 20, fontWeight: 700 }}>{value}</div>
      {sub && <div style={{ ...MONO, color: "#6b7fa3", fontSize: 11, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "10px 14px", fontSize: 12, ...MONO }}>
        <div style={{ color: "#6b7fa3", marginBottom: 6 }}>{label}</div>
        {payload.map((p: any) => (
          <div key={p.dataKey} style={{ color: p.color, marginBottom: 2 }}>
            {p.name}: {typeof p.value === "number" ? p.value.toLocaleString("vi-VN") : p.value}
          </div>
        ))}
      </div>
    );
  }
  return null;
};

interface StockDetailProps { initialTicker?: string; }

export function StockDetail({ initialTicker = "VCB" }: StockDetailProps) {
  const [ticker, setTicker] = useState(initialTicker);
  const [period, setPeriod] = useState("3M");
  const [indicators, setIndicators] = useState({ sma20: true, ema12: false, bb: true, rsi: true, macd: false });
  const [stockOptions, setStockOptions] = useState<StockOption[]>(stockList);
  const [apiData, setApiData] = useState<Candle[] | null>(null);
  const [apiStatus, setApiStatus] = useState("Đang đọc API...");
  const [searchText, setSearchText] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchStocks()
      .then((stocks) => {
        if (cancelled) return;
        setStockOptions(stocks);
        setApiStatus(`API · ${stocks.length} mã`);
      })
      .catch(() => {
        if (cancelled) return;
        setApiStatus(`Snapshot · ${stockList.length} mã`);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setApiData(null);
    fetchCandles(ticker)
      .then((candles) => {
        if (!cancelled) setApiData(candles);
      })
      .catch(() => {
        if (!cancelled) setApiData(null);
      });
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  const data = useMemo(() => apiData ?? generateCandlestickData(ticker), [apiData, ticker]);
  const sliced = period === "1M" ? data.slice(-21) : period === "3M" ? data.slice(-63) : period === "6M" ? data.slice(-126) : data;
  const stock = stockOptions.find((s) => s.ticker === ticker) || stockList.find((s) => s.ticker === ticker) || stockOptions[0] || stockList[0];
  const filteredStocks = useMemo(() => {
    const keyword = searchText.trim().toLowerCase();
    const candidates = keyword
      ? stockOptions.filter((s) =>
        s.ticker.toLowerCase().includes(keyword)
        || s.name.toLowerCase().includes(keyword)
        || s.sector.toLowerCase().includes(keyword)
      )
      : stockOptions;
    return candidates.slice(0, 80);
  }, [searchText, stockOptions]);
  const stockNews = newsSentiment.filter((n) => n.ticker === ticker);
  const last = sliced[sliced.length - 1];
  const prev = sliced[sliced.length - 2];
  if (!last || !prev || !stock) {
    return <div style={CARD}>Đang tải dữ liệu cổ phiếu...</div>;
  }
  const latestDate = last.date?.length === 10 ? last.date : dataSnapshotMeta.latestPriceDate;
  const pct = ((last.close - prev.close) / prev.close * 100).toFixed(2);
  const up = last.close >= prev.close;

  const toggleIndicator = (key: keyof typeof indicators) => {
    setIndicators((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const selectStock = (selected: StockOption) => {
    setTicker(selected.ticker);
    setSearchText("");
    setSearchOpen(false);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ ...MONO, color: "#8b5cf6", fontSize: 22, fontWeight: 700 }}>{stock.ticker}</span>
              <span style={{ background: "rgba(59,130,246,0.15)", color: "#3b82f6", fontSize: 11, padding: "2px 8px", borderRadius: 3, ...INTER }}>{stock.exchange}</span>
              <span style={{ background: "rgba(255,255,255,0.06)", color: "#6b7fa3", fontSize: 11, padding: "2px 8px", borderRadius: 3, ...INTER }}>{stock.sector}</span>
            </div>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 12, marginTop: 2 }}>{stock.name}</div>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 11, marginTop: 2 }}>
              {apiStatus} · Giá đến {latestDate}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {/* Ticker search */}
          <div style={{ position: "relative", width: 320 }}>
            <input
              value={searchOpen ? searchText : `${stock.ticker} – ${stock.name}`}
              onFocus={() => {
                setSearchOpen(true);
                setSearchText("");
              }}
              onChange={(e) => {
                setSearchText(e.target.value);
                setSearchOpen(true);
              }}
              onBlur={() => window.setTimeout(() => setSearchOpen(false), 140)}
              placeholder="Tìm mã / tên công ty..."
              style={{
                width: "100%",
                background: "#1e2535",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 5,
                color: "#e2e8f0",
                padding: "7px 10px",
                fontSize: 12,
                ...INTER,
                outline: "none",
                boxSizing: "border-box",
              }}
            />
            {searchOpen && (
              <div style={{
                position: "absolute",
                top: "calc(100% + 4px)",
                right: 0,
                width: "100%",
                maxHeight: 360,
                overflowY: "auto",
                background: "#111827",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 6,
                boxShadow: "0 18px 50px rgba(0,0,0,0.45)",
                zIndex: 30,
              }}>
                {filteredStocks.map((s) => {
                  const active = s.ticker === ticker;
                  return (
                    <button
                      key={s.ticker}
                      type="button"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        selectStock(s);
                      }}
                      style={{
                        width: "100%",
                        display: "grid",
                        gridTemplateColumns: "64px 1fr",
                        gap: 8,
                        alignItems: "center",
                        padding: "9px 10px",
                        border: "none",
                        borderBottom: "1px solid rgba(255,255,255,0.04)",
                        background: active ? "rgba(139,92,246,0.2)" : "transparent",
                        color: "#e2e8f0",
                        cursor: "pointer",
                        textAlign: "left",
                      }}
                    >
                      <span style={{ ...MONO, color: "#8b5cf6", fontSize: 12, fontWeight: 700 }}>{s.ticker}</span>
                      <span style={{ ...INTER, color: "#e2e8f0", fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {s.name}
                        <span style={{ color: "#6b7fa3" }}> · {s.exchange} · {s.sector}</span>
                      </span>
                    </button>
                  );
                })}
                {filteredStocks.length === 0 && (
                  <div style={{ padding: "12px 10px", color: "#6b7fa3", fontSize: 12, ...INTER }}>
                    Không tìm thấy mã phù hợp.
                  </div>
                )}
                {stockOptions.length > filteredStocks.length && searchText.trim() === "" && (
                  <div style={{ padding: "8px 10px", color: "#6b7fa3", fontSize: 11, ...INTER, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                    Gõ mã hoặc tên công ty để lọc trong {stockOptions.length} mã.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Period buttons */}
          {["1M", "3M", "6M", "1Y"].map((p) => (
            <button key={p} onClick={() => setPeriod(p)} style={{
              padding: "5px 12px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.1)",
              background: period === p ? "#8b5cf6" : "transparent",
              color: period === p ? "#0b0f1a" : "#6b7fa3", fontSize: 12, ...INTER, cursor: "pointer", fontWeight: period === p ? 600 : 400,
            }}>{p}</button>
          ))}
        </div>
      </div>

      {/* KPI Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
        <KPICard label="Giá đóng cửa" value={last.close.toLocaleString("vi-VN")} sub="VNĐ" color={up ? "#00d97e" : "#ff4d6d"} />
        <KPICard label="Thay đổi %" value={(up ? "+" : "") + pct + "%"} color={up ? "#00d97e" : "#ff4d6d"} />
        <KPICard label="Khối lượng" value={(last.volume / 1_000_000).toFixed(2) + "M"} sub="cổ phiếu" />
        <KPICard label="RSI (14)" value={last.rsi.toFixed(1)} color={last.rsi > 70 ? "#ff4d6d" : last.rsi < 30 ? "#00d97e" : "#e2e8f0"} sub={last.rsi > 70 ? "Quá mua" : last.rsi < 30 ? "Quá bán" : "Bình thường"} />
        <KPICard label="MACD" value={last.macd.toFixed(0)} color={last.macd > 0 ? "#00d97e" : "#ff4d6d"} />
        <KPICard label="Vốn hóa" value={(last.close * 2_800_000_000 / 1_000_000_000_000).toFixed(2) + " nghìn tỷ"} />
      </div>

      {/* Indicators toggles */}
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <span style={{ ...INTER, color: "#6b7fa3", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em" }}>Chỉ báo:</span>
        {(Object.entries(indicators) as [keyof typeof indicators, boolean][]).map(([key, active]) => {
          const labels: Record<string, string> = { sma20: "SMA20", ema12: "EMA12", bb: "Bollinger Band", rsi: "RSI14", macd: "MACD" };
          const colors: Record<string, string> = { sma20: "#8b5cf6", ema12: "#a855f7", bb: "#6b7fa3", rsi: "#3b82f6", macd: "#00d97e" };
          return (
            <button key={key} onClick={() => toggleIndicator(key)} style={{
              padding: "4px 10px", borderRadius: 4,
              border: `1px solid ${active ? colors[key] : "rgba(255,255,255,0.1)"}`,
              background: active ? `${colors[key]}18` : "transparent",
              color: active ? colors[key] : "#6b7fa3",
              fontSize: 11, ...INTER, cursor: "pointer", fontWeight: active ? 600 : 400,
            }}>{labels[key]}</button>
          );
        })}
      </div>

      {/* Main price chart */}
      <div style={CARD}>
        <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Biểu đồ giá & Khối lượng</div>
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={sliced} margin={{ left: 10, right: 20 }}>
            <XAxis dataKey="date" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} interval={Math.floor(sliced.length / 8)} tickFormatter={(v) => String(v).slice(5)} />
            <YAxis yAxisId="price" domain={["auto", "auto"]} tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} width={70} tickFormatter={(v) => v.toLocaleString("vi-VN")} />
            <YAxis yAxisId="vol" orientation="right" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} width={60} tickFormatter={(v) => (v / 1_000_000).toFixed(1) + "M"} />
            <Tooltip content={<CustomTooltip />} />
            <Bar yAxisId="vol" dataKey="volume" fill="rgba(59,130,246,0.25)" name="Volume" radius={[1, 1, 0, 0]} />
            <Line yAxisId="price" type="monotone" dataKey="close" stroke={up ? "#00d97e" : "#ff4d6d"} strokeWidth={2} dot={false} name="Giá đóng cửa" />
            {indicators.sma20 && <Line yAxisId="price" type="monotone" dataKey="sma20" stroke="#8b5cf6" strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="SMA20" />}
            {indicators.ema12 && <Line yAxisId="price" type="monotone" dataKey="ema12" stroke="#a855f7" strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="EMA12" />}
            {indicators.bb && <>
              <Line yAxisId="price" type="monotone" dataKey="bbUpper" stroke="#6b7fa3" strokeWidth={1} dot={false} strokeDasharray="2 2" name="BB Upper" />
              <Line yAxisId="price" type="monotone" dataKey="bbLower" stroke="#6b7fa3" strokeWidth={1} dot={false} strokeDasharray="2 2" name="BB Lower" />
            </>}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* RSI & MACD row */}
      <div style={{ display: "grid", gridTemplateColumns: indicators.rsi && indicators.macd ? "1fr 1fr" : "1fr", gap: 12 }}>
        {indicators.rsi && (
          <div style={CARD}>
            <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>RSI (14)</div>
            <ResponsiveContainer width="100%" height={120}>
              <ComposedChart data={sliced} margin={{ left: 10, right: 20 }}>
                <XAxis dataKey="date" tick={false} axisLine={false} tickLine={false} tickFormatter={(v) => String(v).slice(5)} />
                <YAxis domain={[0, 100]} tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} width={30} />
                <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any) => [v.toFixed(1), "RSI"]} />
                <ReferenceLine y={70} stroke="#ff4d6d" strokeDasharray="3 3" strokeWidth={1} label={{ value: "70", fill: "#ff4d6d", fontSize: 10 }} />
                <ReferenceLine y={30} stroke="#00d97e" strokeDasharray="3 3" strokeWidth={1} label={{ value: "30", fill: "#00d97e", fontSize: 10 }} />
                <Line type="monotone" dataKey="rsi" stroke="#3b82f6" strokeWidth={2} dot={false} name="RSI" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}

        {indicators.macd && (
          <div style={CARD}>
            <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>MACD</div>
            <ResponsiveContainer width="100%" height={120}>
              <ComposedChart data={sliced} margin={{ left: 10, right: 20 }}>
                <XAxis dataKey="date" tick={false} axisLine={false} tickLine={false} tickFormatter={(v) => String(v).slice(5)} />
                <YAxis tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} width={40} />
                <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" strokeWidth={1} />
                <Bar dataKey="macd" fill="#00d97e" opacity={0.6} name="MACD" />
                <Line type="monotone" dataKey="macdSignal" stroke="#8b5cf6" strokeWidth={1.5} dot={false} name="Signal" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* News table */}
      <div style={CARD}>
        <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Tin tức nổi bật</div>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
              {["Ngày", "Tiêu đề", "Nguồn", "Sentiment"].map((h) => (
                <th key={h} style={{ color: "#6b7fa3", fontSize: 11, textAlign: "left", padding: "6px 10px", ...INTER, textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {stockNews.map((row, i) => (
              <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <td style={{ padding: "9px 10px", color: "#6b7fa3", fontSize: 11, ...MONO, whiteSpace: "nowrap" }}>
                  {row.publishedAt || row.newsDate || dataSnapshotMeta.latestNewsDate}
                </td>
                <td style={{ padding: "9px 10px", color: "#e2e8f0", fontSize: 12, ...INTER }}>
                  {row.url ? (
                    <a
                      href={row.url}
                      target="_blank"
                      rel="noreferrer"
                      title={row.url}
                      style={{ color: "#e2e8f0", textDecoration: "none" }}
                    >
                      {row.headline}
                    </a>
                  ) : row.headline}
                </td>
                <td style={{ padding: "9px 10px" }}>
                  <span style={{ background: "rgba(255,255,255,0.06)", color: "#6b7fa3", fontSize: 11, padding: "2px 8px", borderRadius: 3, ...INTER }}>{row.source || `${row.sources} nguồn`}</span>
                </td>
                <td style={{ padding: "9px 10px" }}>
                  <span style={{
                    background: row.avgScore > 0.3 ? "rgba(0,217,126,0.1)" : row.avgScore < -0.1 ? "rgba(255,77,109,0.1)" : "rgba(107,127,163,0.15)",
                    color: row.avgScore > 0.3 ? "#00d97e" : row.avgScore < -0.1 ? "#ff4d6d" : "#6b7fa3",
                    fontSize: 12, padding: "2px 8px", borderRadius: 3, ...MONO, fontWeight: 600,
                  }}>
                    {row.avgScore > 0 ? "+" : ""}{row.avgScore.toFixed(2)}
                  </span>
                </td>
              </tr>
            ))}
            {stockNews.length === 0 && (
              <tr>
                <td colSpan={4} style={{ padding: "14px 10px", color: "#6b7fa3", fontSize: 12, ...INTER }}>
                  Chưa có bản ghi sentiment cho {stock.ticker} trong fact_news_sentiment_daily.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
