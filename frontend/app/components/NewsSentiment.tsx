import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  LineChart, Line,
} from "recharts";
import { fetchNewsSentiment, NewsSentimentRow, SentimentByDate } from "./api";

const CARD: React.CSSProperties = { background: "#111827", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: 16 };
const MONO: React.CSSProperties = { fontFamily: "JetBrains Mono, monospace" };
const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };

function SentimentBar({ positive, negative, neutral }: { positive: number; negative: number; neutral: number }) {
  const total = positive + negative + neutral || 1;
  return (
    <div style={{ display: "flex", height: 6, borderRadius: 3, overflow: "hidden", gap: 1 }}>
      <div style={{ width: `${(positive / total) * 100}%`, background: "#00d97e" }} />
      <div style={{ width: `${(neutral / total) * 100}%`, background: "#6b7fa3" }} />
      <div style={{ width: `${(negative / total) * 100}%`, background: "#ff4d6d" }} />
    </div>
  );
}

interface NewsSentimentProps { onNavigate: (page: string, ticker?: string) => void; }

export function NewsSentiment({ onNavigate }: NewsSentimentProps) {
  const [filterSentiment, setFilterSentiment] = useState<"all" | "positive" | "negative" | "neutral">("all");
  const [search, setSearch] = useState("");
  const [newsSentiment, setNewsSentiment] = useState<NewsSentimentRow[]>([]);
  const [sentimentByDate, setSentimentByDate] = useState<SentimentByDate[]>([]);
  const [apiStatus, setApiStatus] = useState<"loading" | "ok" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    fetchNewsSentiment()
      .then((payload) => {
        if (cancelled) return;
        setNewsSentiment(payload.data);
        setSentimentByDate(payload.byDate);
        setApiStatus("ok");
      })
      .catch(() => {
        if (!cancelled) setApiStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = newsSentiment.filter((n) => {
    if (search && !n.ticker.toLowerCase().includes(search.toLowerCase()) && !n.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterSentiment === "positive" && n.avgScore <= 0.3) return false;
    if (filterSentiment === "negative" && n.avgScore >= -0.1) return false;
    if (filterSentiment === "neutral" && (n.avgScore > 0.3 || n.avgScore < -0.1)) return false;
    return true;
  });

  const totalNews = newsSentiment.reduce((a, n) => a + n.newsCount, 0);
  const totalPositive = newsSentiment.reduce((a, n) => a + n.positive, 0);
  const totalNegative = newsSentiment.reduce((a, n) => a + n.negative, 0);
  const topByNews = [...newsSentiment].sort((a, b) => b.newsCount - a.newsCount).slice(0, 8);

  const sentimentScoreData = sentimentByDate.map((d) => ({
    ...d,
    score: +((d.positive - d.negative) / (d.positive + d.negative + d.neutral || 1) * 100).toFixed(1),
  }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ color: "#e2e8f0", margin: 0, fontSize: 18, fontWeight: 700, ...INTER }}>Tin tức & cảm xúc thị trường</h1>
          <p style={{ color: apiStatus === "error" ? "#ff4d6d" : "#6b7fa3", margin: 0, fontSize: 12, ...INTER }}>
            {apiStatus === "loading" ? "Đang tải dữ liệu..." : apiStatus === "error" ? "Không thể tải dữ liệu — kiểm tra API" : `ClickHouse live · ${newsSentiment.length} mã`}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            placeholder="Tìm mã CK..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 5,
              color: "#e2e8f0", padding: "6px 10px", fontSize: 12, ...INTER, outline: "none",
            }}
          />
          {(["all", "positive", "negative", "neutral"] as const).map((s) => {
            const labels = { all: "Tất cả", positive: "Tích cực", negative: "Tiêu cực", neutral: "Trung lập" };
            const colors = { all: "#6b7fa3", positive: "#00d97e", negative: "#ff4d6d", neutral: "#6b7fa3" };
            return (
              <button key={s} onClick={() => setFilterSentiment(s)} style={{
                padding: "5px 12px", borderRadius: 5,
                border: `1px solid ${filterSentiment === s ? colors[s] : "rgba(255,255,255,0.1)"}`,
                background: filterSentiment === s ? `${colors[s]}18` : "transparent",
                color: filterSentiment === s ? colors[s] : "#6b7fa3",
                fontSize: 12, ...INTER, cursor: "pointer", fontWeight: filterSentiment === s ? 600 : 400,
              }}>{labels[s]}</button>
            );
          })}
        </div>
      </div>

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
        {[
          { label: "Tổng tin hôm nay", value: totalNews + "", color: "#e2e8f0" },
          { label: "Tin tích cực", value: totalPositive + "", color: "#00d97e" },
          { label: "Tin tiêu cực", value: totalNegative + "", color: "#ff4d6d" },
          { label: "Mã được nhắc đến", value: newsSentiment.length + "", color: "#3b82f6" },
          { label: "Avg Sentiment Score", value: (newsSentiment.reduce((a, n) => a + n.avgScore, 0) / (newsSentiment.length || 1)).toFixed(2), color: "#8b5cf6" },
        ].map((kpi) => (
          <div key={kpi.label} style={CARD}>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{kpi.label}</div>
            <div style={{ ...MONO, color: kpi.color, fontSize: 24, fontWeight: 700 }}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {/* Top news by ticker */}
        <div style={CARD}>
          <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Top mã có nhiều tin nhất</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={topByNews} layout="vertical" margin={{ left: 10, right: 20 }}>
              <XAxis type="number" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="ticker" tick={{ fill: "#8b5cf6", fontSize: 11, ...MONO }} axisLine={false} tickLine={false} width={35} />
              <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any) => [v + " tin", "Số tin"]} />
              <Bar dataKey="newsCount" fill="#3b82f6" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Sentiment score trend */}
        <div style={CARD}>
          <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Market Sentiment Score theo ngày</div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={sentimentScoreData} margin={{ left: 10, right: 20 }}>
              <XAxis dataKey="date" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} tickFormatter={(v) => v + "%"} />
              <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any) => [v + "%", "Score"]} />
              <Line type="monotone" dataKey="score" stroke="#8b5cf6" strokeWidth={2} dot={{ fill: "#8b5cf6", r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Stacked bar by day */}
      <div style={CARD}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <span style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>Phân bố tin tức theo ngày</span>
          <div style={{ display: "flex", gap: 16 }}>
            {[{ label: "Tích cực", color: "#00d97e" }, { label: "Tiêu cực", color: "#ff4d6d" }, { label: "Trung lập", color: "#6b7fa3" }].map((l) => (
              <div key={l.label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: l.color }} />
                <span style={{ ...INTER, color: "#6b7fa3", fontSize: 11 }}>{l.label}</span>
              </div>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={sentimentByDate} margin={{ left: 10, right: 20 }}>
            <XAxis dataKey="date" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} />
            <Bar dataKey="positive" stackId="a" fill="#00d97e" name="Tích cực" />
            <Bar dataKey="neutral" stackId="a" fill="#6b7fa3" name="Trung lập" />
            <Bar dataKey="negative" stackId="a" fill="#ff4d6d" name="Tiêu cực" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* News table */}
      <div style={CARD}>
        <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>
          Chi tiết tin tức & sentiment · {filtered.length} mã
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                {["Mã CK", "Tên công ty", "Số tin", "Nguồn", "Positive / Negative / Neutral", "Phân bố", "Avg Score", "Tin nổi bật"].map((h) => (
                  <th key={h} style={{ color: "#6b7fa3", fontSize: 10, textAlign: "left", padding: "6px 10px", ...INTER, textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 500, whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((n) => (
                <tr key={n.ticker} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}
                  onClick={() => onNavigate("stock", n.ticker)}
                  onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.03)"}
                  onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}
                >
                  <td style={{ padding: "10px 10px" }}><span style={{ color: "#8b5cf6", fontSize: 13, fontWeight: 700, ...MONO }}>{n.ticker}</span></td>
                  <td style={{ padding: "10px 10px", color: "#e2e8f0", fontSize: 12, ...INTER }}>{n.name}</td>
                  <td style={{ padding: "10px 10px", color: "#3b82f6", fontSize: 13, fontWeight: 600, ...MONO, textAlign: "right" }}>{n.newsCount}</td>
                  <td style={{ padding: "10px 10px", color: "#6b7fa3", fontSize: 12, ...MONO, textAlign: "center" }}>{n.sources}</td>
                  <td style={{ padding: "10px 10px" }}>
                    <div style={{ display: "flex", gap: 6, ...MONO, fontSize: 11 }}>
                      <span style={{ color: "#00d97e" }}>{n.positive}</span>
                      <span style={{ color: "#6b7fa3" }}>/</span>
                      <span style={{ color: "#ff4d6d" }}>{n.negative}</span>
                      <span style={{ color: "#6b7fa3" }}>/</span>
                      <span style={{ color: "#6b7fa3" }}>{n.neutral}</span>
                    </div>
                  </td>
                  <td style={{ padding: "10px 10px", minWidth: 100 }}>
                    <SentimentBar positive={n.positive} negative={n.negative} neutral={n.neutral} />
                  </td>
                  <td style={{ padding: "10px 10px", textAlign: "right" }}>
                    <span style={{
                      background: n.avgScore > 0.3 ? "rgba(0,217,126,0.1)" : n.avgScore < -0.1 ? "rgba(255,77,109,0.1)" : "rgba(107,127,163,0.1)",
                      color: n.avgScore > 0.3 ? "#00d97e" : n.avgScore < -0.1 ? "#ff4d6d" : "#6b7fa3",
                      fontSize: 12, ...MONO, padding: "3px 8px", borderRadius: 3, fontWeight: 700,
                    }}>{n.avgScore > 0 ? "+" : ""}{n.avgScore.toFixed(2)}</span>
                  </td>
                  <td style={{ padding: "10px 10px", color: "#6b7fa3", fontSize: 11, ...INTER, maxWidth: 280 }}>
                    {n.url ? (
                      <a
                        href={n.url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        title={n.url}
                        style={{ color: "#e2e8f0", textDecoration: "none" }}
                      >
                        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {n.headline}
                        </div>
                      </a>
                    ) : (
                      <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{n.headline}</div>
                    )}
                    {n.source && <div style={{ color: "#6b7fa3", fontSize: 10, marginTop: 2 }}>{n.source}</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
