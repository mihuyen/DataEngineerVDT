import { useEffect, useState, useMemo } from "react";
import { dataSnapshotMeta, newsSentiment as mockNewsSentiment, stockList } from "./mockData";
import {
  Candle, DailyCandlesPayload, IntradayCandle, IntradayPayload, IntradayResolution, NewsArticleRow, NewsSentimentRow, StockOption,
  fetchCandles, fetchIntraday, fetchNewsSentiment, fetchStocks,
} from "./api";
import { CandlestickChart } from "./CandlestickChart";
import { RsiPane, MacdPane } from "./IndicatorPaneChart";

const INTRADAY_RESOLUTIONS: IntradayResolution[] = ["1m", "5m", "15m", "30m", "1h"];

const CARD: React.CSSProperties = {
  background: "#111827", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: 16,
};
const MONO: React.CSSProperties = { fontFamily: "JetBrains Mono, monospace" };
const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };
const NEWS_REFRESH_MS = 5 * 60 * 1000;

function sentimentStyle(score: number | null | undefined) {
  if (score == null) {
    return { background: "rgba(107,127,163,0.15)", color: "#6b7fa3" };
  }
  if (score > 0.3) {
    return { background: "rgba(0,217,126,0.1)", color: "#00d97e" };
  }
  if (score < -0.1) {
    return { background: "rgba(255,77,109,0.1)", color: "#ff4d6d" };
  }
  return { background: "rgba(107,127,163,0.15)", color: "#6b7fa3" };
}

function KPICard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div style={CARD}>
      <div style={{ ...INTER, color: "#6b7fa3", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{label}</div>
      <div style={{ ...MONO, color: color || "#e2e8f0", fontSize: 20, fontWeight: 700 }}>{value}</div>
      {sub && <div style={{ ...MONO, color: "#6b7fa3", fontSize: 11, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

interface StockDetailProps { initialTicker?: string; onNavigate?: (page: string, ticker?: string) => void; }

export function StockDetail({ initialTicker = "VCB", onNavigate }: StockDetailProps) {
  const [ticker, setTicker] = useState(initialTicker);
  const [period, setPeriod] = useState("3M");
  const [viewMode, setViewMode] = useState<"daily" | "intraday">("daily");
  const [intradayResolution, setIntradayResolution] = useState<IntradayResolution>("5m");
  const [intradayData, setIntradayData] = useState<IntradayCandle[] | null>(null);
  const [intradayMeta, setIntradayMeta] = useState<IntradayPayload | null>(null);
  const [intradayError, setIntradayError] = useState(false);
  const [indicators, setIndicators] = useState({ sma20: true, ema12: false, bb: true, rsi: true, macd: false });
  const [stockOptions, setStockOptions] = useState<StockOption[]>(stockList);
  const [apiData, setApiData] = useState<Candle[] | null>(null);
  const [dailyMeta, setDailyMeta] = useState<DailyCandlesPayload | null>(null);
  const [candleError, setCandleError] = useState(false);
  const [apiStatus, setApiStatus] = useState("Đang đọc API...");
  const [searchText, setSearchText] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [newsSentiment, setNewsSentiment] = useState<NewsSentimentRow[]>(mockNewsSentiment);
  const [newsArticles, setNewsArticles] = useState<NewsArticleRow[]>([]);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetchNewsSentiment()
        .then((payload) => {
          if (!cancelled) {
            setNewsSentiment(payload.data);
            setNewsArticles(payload.articles || []);
          }
        })
        .catch(() => {
          if (!cancelled) setNewsSentiment(mockNewsSentiment);
        });
    };
    load();
    const timer = window.setInterval(load, NEWS_REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

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
    setCandleError(false);
    fetchCandles(ticker)
      .then((payload) => {
        if (!cancelled) {
          setApiData(payload.data);
          setDailyMeta(payload);
        }
      })
      .catch(() => {
        if (cancelled) return;
        setApiData([]);
        setCandleError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  useEffect(() => {
    if (viewMode !== "intraday") return;
    let cancelled = false;
    setIntradayData(null);
    setIntradayMeta(null);
    setIntradayError(false);
    fetchIntraday(ticker, intradayResolution)
      .then((payload) => {
        if (!cancelled) {
          setIntradayData(payload.data);
          setIntradayMeta(payload);
        }
      })
      .catch(() => {
        if (cancelled) return;
        setIntradayData([]);
        setIntradayError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [ticker, viewMode, intradayResolution]);

  const data = useMemo(() => apiData ?? [], [apiData]);
  const intradayPoints = useMemo(
    () => (intradayData ?? []).map((d) => ({ date: d.time, open: d.open, high: d.high, low: d.low, close: d.close, volume: d.volume })),
    [intradayData]
  );
  // Memoized: this array is passed straight into chart components whose
  // data-update effects key off it by reference, so a fresh array every
  // render (the previous behavior here) made every unrelated re-render of
  // this page -- typing in the ticker search, hovering a button -- redraw
  // the candlestick/RSI/MACD charts from scratch.
  const sliced = useMemo(
    () => (period === "1M" ? data.slice(-21) : period === "3M" ? data.slice(-63) : period === "6M" ? data.slice(-126) : data),
    [data, period]
  );
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
  const stockArticles = newsArticles.filter((article) => article.ticker === ticker);
  const last = sliced[sliced.length - 1];
  const prev = sliced[sliced.length - 2];
  if (apiData === null) {
    return <div style={CARD}>Đang tải dữ liệu cổ phiếu...</div>;
  }
  if (candleError || !last || !prev || !stock) {
    return <div style={CARD}>Không có dữ liệu cho mã {ticker}.</div>;
  }
  const latestDate = last.date?.length === 10 ? last.date : dataSnapshotMeta.latestPriceDate;
  const intradayLast = intradayData?.[intradayData.length - 1];
  const intradaySameAsLatestDaily = intradayMeta?.tradingDate === latestDate;
  const referenceClose = intradaySameAsLatestDaily ? prev.close : last.close;
  const displayedClose = viewMode === "intraday" && intradayLast ? intradayLast.close : last.close;
  const displayedPct = ((displayedClose - (viewMode === "intraday" ? referenceClose : prev.close))
    / (viewMode === "intraday" ? referenceClose : prev.close) * 100).toFixed(2);
  const up = displayedClose >= (viewMode === "intraday" ? referenceClose : prev.close);
  const intradayVolume = intradayData?.reduce((total, candle) => total + candle.volume, 0) ?? 0;
  const displayedVolume = viewMode === "intraday" && intradayData?.length ? intradayVolume : last.volume;
  const displayedHigh = viewMode === "intraday" && intradayData?.length
    ? Math.max(...intradayData.map((candle) => candle.high))
    : last.high;
  const displayedLow = viewMode === "intraday" && intradayData?.length
    ? Math.min(...intradayData.map((candle) => candle.low))
    : last.low;
  const displayedValue = viewMode === "intraday" && intradayData?.length
    ? intradayData.reduce((total, candle) => total + candle.close * candle.volume * 1_000, 0)
    : last.value * 1_000;
  const sourceLabel = intradayMeta?.sources?.length ? intradayMeta.sources.join(" + ") : "DNSE / Vnstock";

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
              {viewMode === "intraday" && intradayMeta
                ? `Trong phiên ${intradayMeta.tradingDate} · ${sourceLabel} · ${intradayMeta.statusLabel} · cập nhật ${intradayMeta.latestMinute || "chưa có"}`
                : `Dữ liệu EOD · phiên gần nhất ${dailyMeta?.latestPriceDate || latestDate} · ${dailyMeta?.statusLabel || apiStatus}`}
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

          {/* Daily / intraday toggle */}
          {([["daily", "Theo ngày"], ["intraday", "Trong phiên"]] as const).map(([mode, label]) => (
            <button key={mode} onClick={() => setViewMode(mode)} style={{
              padding: "5px 12px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.1)",
              background: viewMode === mode ? "#3b82f6" : "transparent",
              color: viewMode === mode ? "#0b0f1a" : "#6b7fa3", fontSize: 12, ...INTER, cursor: "pointer", fontWeight: viewMode === mode ? 600 : 400,
            }}>{label}</button>
          ))}

          {/* Period buttons (daily) / resolution buttons (intraday) */}
          {viewMode === "daily"
            ? ["1M", "3M", "6M", "1Y"].map((p) => (
              <button key={p} onClick={() => setPeriod(p)} style={{
                padding: "5px 12px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.1)",
                background: period === p ? "#8b5cf6" : "transparent",
                color: period === p ? "#0b0f1a" : "#6b7fa3", fontSize: 12, ...INTER, cursor: "pointer", fontWeight: period === p ? 600 : 400,
              }}>{p}</button>
            ))
            : INTRADAY_RESOLUTIONS.map((r) => (
              <button key={r} onClick={() => setIntradayResolution(r)} style={{
                padding: "5px 12px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.1)",
                background: intradayResolution === r ? "#8b5cf6" : "transparent",
                color: intradayResolution === r ? "#0b0f1a" : "#6b7fa3", fontSize: 12, ...INTER, cursor: "pointer", fontWeight: intradayResolution === r ? 600 : 400,
              }}>{r}</button>
            ))}

          {onNavigate && (
            <button
              onClick={() => onNavigate("alerts", ticker)}
              style={{
                padding: "5px 12px", borderRadius: 5, border: "1px solid rgba(139,92,246,0.4)",
                background: "rgba(139,92,246,0.1)", color: "#8b5cf6", fontSize: 12, ...INTER,
                cursor: "pointer", fontWeight: 600,
              }}
            >
              + Tạo cảnh báo
            </button>
          )}
        </div>
      </div>

      {/* KPI Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
        <KPICard label={viewMode === "intraday" ? "Giá gần nhất" : "Giá đóng cửa"} value={displayedClose.toLocaleString("vi-VN")} sub="nghìn đồng" color={up ? "#00d97e" : "#ff4d6d"} />
        <KPICard label="Thay đổi %" value={(up ? "+" : "") + displayedPct + "%"} color={up ? "#00d97e" : "#ff4d6d"} />
        <KPICard label="Khối lượng" value={(displayedVolume / 1_000_000).toFixed(2) + "M"} sub="cổ phiếu" />
        <KPICard label="Giá trị ước tính" value={(displayedValue / 1_000_000_000).toFixed(1) + " tỷ"} sub="VNĐ" />
        <KPICard label="Cao / Thấp" value={displayedHigh.toLocaleString("vi-VN") + " / " + displayedLow.toLocaleString("vi-VN")} sub="nghìn đồng" />
        <KPICard label="Vốn hóa" value={last.marketCap ? (last.marketCap / 1_000_000_000).toFixed(2) + " nghìn tỷ" : "—"} />
      </div>

      {/* Indicators toggles */}
      {viewMode === "daily" && (
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
      )}

      {/* Main price chart */}
      <div style={CARD}>
        <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>
          {viewMode === "daily" ? "Biểu đồ nến & Khối lượng" : `Biểu đồ trong phiên (${intradayResolution})`}
        </div>
        {viewMode === "daily" ? (
          <CandlestickChart data={sliced} indicators={indicators} />
        ) : intradayData === null ? (
          <div style={{ color: "#6b7fa3", fontSize: 12, ...INTER, padding: "40px 0", textAlign: "center" }}>Đang tải dữ liệu trong phiên...</div>
        ) : intradayError || intradayPoints.length === 0 ? (
          <div style={{ color: "#6b7fa3", fontSize: 12, ...INTER, padding: "40px 0", textAlign: "center" }}>
            Chưa có dữ liệu trong phiên cho mã {ticker} (cần backfill hoặc DNSE realtime).
          </div>
        ) : (
          <CandlestickChart data={intradayPoints} indicators={{ sma20: false, ema12: false, bb: false }} timeVisible />
        )}
      </div>

      {/* RSI & MACD row */}
      {viewMode === "daily" && (
      <div style={{ display: "grid", gridTemplateColumns: indicators.rsi && indicators.macd ? "1fr 1fr" : "1fr", gap: 12 }}>
        {indicators.rsi && (
          <div style={CARD}>
            <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>RSI (14)</div>
            <RsiPane data={sliced} />
          </div>
        )}

        {indicators.macd && (
          <div style={CARD}>
            <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>MACD</div>
            <MacdPane data={sliced} />
          </div>
        )}
      </div>
      )}

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

      <div style={CARD}>
        <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>
          Bài báo gần đây của {stock.ticker}
        </div>
        <div style={{ display: "grid", gap: 10 }}>
          {stockArticles.slice(0, 10).map((article) => {
            const tone = sentimentStyle(article.sentimentScore);
            return (
              <div
                key={article.articleId}
                style={{
                  border: "1px solid rgba(255,255,255,0.06)",
                  borderRadius: 8,
                  padding: 12,
                  background: "rgba(255,255,255,0.02)",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {article.url ? (
                    <a href={article.url} target="_blank" rel="noreferrer" style={{ color: "#e2e8f0", textDecoration: "none" }}>
                      <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>{article.headline}</div>
                    </a>
                  ) : (
                    <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>{article.headline}</div>
                  )}
                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <span style={{ color: "#6b7fa3", fontSize: 11, ...MONO }}>{article.publishedAt || dataSnapshotMeta.latestNewsDate}</span>
                    {article.source && <span style={{ color: "#6b7fa3", fontSize: 11, ...INTER }}>{article.source}</span>}
                    <span
                      style={{
                        ...tone,
                        fontSize: 11,
                        padding: "2px 8px",
                        borderRadius: 3,
                        ...MONO,
                        fontWeight: 700,
                      }}
                    >
                      {article.sentimentLabel || "unknown"} · {(article.sentimentScore ?? 0) > 0 ? "+" : ""}{(article.sentimentScore ?? 0).toFixed(2)}
                    </span>
                    {article.confidenceScore != null && (
                      <span style={{ color: "#6b7fa3", fontSize: 11, ...MONO }}>
                        confidence {(article.confidenceScore * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
          {stockArticles.length === 0 && (
            <div style={{ color: "#6b7fa3", fontSize: 12, ...INTER }}>
              Chưa có bài báo sentiment chi tiết cho {stock.ticker} trong 7 ngày gần đây.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
