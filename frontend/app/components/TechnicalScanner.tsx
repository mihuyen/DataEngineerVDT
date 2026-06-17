import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { technicalSignals } from "./mockData";

const CARD: React.CSSProperties = { background: "#111827", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: 16 };
const MONO: React.CSSProperties = { fontFamily: "JetBrains Mono, monospace" };
const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };

const SIGNAL_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  overbought: { label: "Quá mua", color: "#ff4d6d", bg: "rgba(255,77,109,0.1)" },
  oversold: { label: "Quá bán", color: "#00d97e", bg: "rgba(0,217,126,0.1)" },
  breakout: { label: "Breakout", color: "#8b5cf6", bg: "rgba(245,158,11,0.1)" },
  breakdown: { label: "Breakdown", color: "#a855f7", bg: "rgba(168,85,247,0.1)" },
  macd_positive: { label: "MACD+", color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  volume_spike: { label: "Vol Spike", color: "#06b6d4", bg: "rgba(6,182,212,0.1)" },
};

interface TechnicalScannerProps { onNavigate: (page: string, ticker?: string) => void; }

export function TechnicalScanner({ onNavigate }: TechnicalScannerProps) {
  const [filterSignal, setFilterSignal] = useState<string>("all");
  const [filterExchange, setFilterExchange] = useState("ALL");

  const filtered = technicalSignals.filter((s) =>
    filterSignal === "all" || s.signal === filterSignal
  );

  const counts = {
    overbought: technicalSignals.filter((s) => s.signal === "overbought").length,
    oversold: technicalSignals.filter((s) => s.signal === "oversold").length,
    breakout: technicalSignals.filter((s) => s.signal === "breakout").length,
    breakdown: technicalSignals.filter((s) => s.signal === "breakdown").length,
    macd_positive: technicalSignals.filter((s) => s.signal === "macd_positive").length,
    volume_spike: technicalSignals.filter((s) => s.signal === "volume_spike").length,
  };

  const topRsiHigh = [...technicalSignals].sort((a, b) => b.rsi - a.rsi).slice(0, 8);
  const topRsiLow = [...technicalSignals].sort((a, b) => a.rsi - b.rsi).slice(0, 8);
  const topVolSpike = [...technicalSignals].sort((a, b) => (b.volume / b.volSma20) - (a.volume / a.volSma20)).slice(0, 8);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ color: "#e2e8f0", margin: 0, fontSize: 18, fontWeight: 700, ...INTER }}>Technical Signal Scanner</h1>
          <p style={{ color: "#6b7fa3", margin: 0, fontSize: 12, ...INTER }}>Quét tín hiệu kỹ thuật toàn thị trường · Phiên 14/06/2026</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {["ALL", "HOSE", "HNX", "UPCOM"].map((ex) => (
            <button key={ex} onClick={() => setFilterExchange(ex)} style={{
              padding: "5px 12px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.1)",
              background: filterExchange === ex ? "#8b5cf6" : "transparent",
              color: filterExchange === ex ? "#0b0f1a" : "#6b7fa3",
              fontSize: 12, ...INTER, cursor: "pointer", fontWeight: filterExchange === ex ? 600 : 400,
            }}>{ex}</button>
          ))}
        </div>
      </div>

      {/* Signal KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
        {Object.entries(counts).map(([key, count]) => {
          const cfg = SIGNAL_CONFIG[key];
          const active = filterSignal === key;
          return (
            <div key={key} onClick={() => setFilterSignal(active ? "all" : key)}
              style={{
                ...CARD, cursor: "pointer",
                borderColor: active ? cfg.color : "rgba(255,255,255,0.07)",
                background: active ? cfg.bg : "#111827",
                transition: "all 0.15s",
              }}>
              <div style={{ color: "#6b7fa3", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", ...INTER, marginBottom: 4 }}>{cfg.label}</div>
              <div style={{ color: cfg.color, fontSize: 28, fontWeight: 700, ...MONO }}>{count}</div>
              <div style={{ color: "#6b7fa3", fontSize: 11, ...INTER, marginTop: 2 }}>mã</div>
            </div>
          );
        })}
      </div>

      {/* Charts row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
        <div style={CARD}>
          <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>RSI cao nhất (quá mua)</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={topRsiHigh} layout="vertical" margin={{ left: 10, right: 20 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="ticker" tick={{ fill: "#8b5cf6", fontSize: 11, ...MONO }} axisLine={false} tickLine={false} width={35} />
              <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any) => [v.toFixed(1), "RSI"]} />
              <Bar dataKey="rsi" radius={[0, 3, 3, 0]}>
                {topRsiHigh.map((entry, i) => <Cell key={`rsi-high-${entry.ticker}`} fill={entry.rsi > 70 ? "#ff4d6d" : "#8b5cf6"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={CARD}>
          <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>RSI thấp nhất (quá bán)</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={topRsiLow} layout="vertical" margin={{ left: 10, right: 20 }}>
              <XAxis type="number" domain={[0, 60]} tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="ticker" tick={{ fill: "#8b5cf6", fontSize: 11, ...MONO }} axisLine={false} tickLine={false} width={35} />
              <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any) => [v.toFixed(1), "RSI"]} />
              <Bar dataKey="rsi" radius={[0, 3, 3, 0]}>
                {topRsiLow.map((entry, i) => <Cell key={`rsi-low-${entry.ticker}`} fill={entry.rsi < 30 ? "#00d97e" : "#3b82f6"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={CARD}>
          <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Volume spike (so với SMA20)</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={topVolSpike.map((s) => ({ ...s, ratio: +(s.volume / s.volSma20).toFixed(2) }))} layout="vertical" margin={{ left: 10, right: 20 }}>
              <XAxis type="number" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} tickFormatter={(v) => v + "x"} />
              <YAxis type="category" dataKey="ticker" tick={{ fill: "#8b5cf6", fontSize: 11, ...MONO }} axisLine={false} tickLine={false} width={35} />
              <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any) => [v + "x SMA20", "Vol ratio"]} />
              <Bar dataKey="ratio" fill="#06b6d4" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Signal filter table */}
      <div style={CARD}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <span style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>
            Danh sách tín hiệu
            {filterSignal !== "all" && (
              <span style={{ marginLeft: 8, ...INTER, color: SIGNAL_CONFIG[filterSignal]?.color, fontSize: 12 }}>
                · {SIGNAL_CONFIG[filterSignal]?.label}
              </span>
            )}
          </span>
          <span style={{ ...INTER, color: "#6b7fa3", fontSize: 12 }}>{filtered.length} mã</span>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                {["Mã CK", "Tên", "Tín hiệu", "RSI14", "MACD", "Giá đóng", "BB Upper", "BB Lower", "Vol/SMA20", "% Ngày"].map((h) => (
                  <th key={h} style={{ color: "#6b7fa3", fontSize: 10, textAlign: "left", padding: "6px 10px", ...INTER, textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500, whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => {
                const cfg = SIGNAL_CONFIG[s.signal];
                const volRatio = (s.volume / s.volSma20).toFixed(2);
                return (
                  <tr key={s.ticker} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}
                    onClick={() => onNavigate("stock", s.ticker)}
                    onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.03)"}
                    onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}
                  >
                    <td style={{ padding: "9px 10px" }}>
                      <span style={{ color: "#8b5cf6", fontSize: 13, fontWeight: 700, ...MONO }}>{s.ticker}</span>
                    </td>
                    <td style={{ padding: "9px 10px", color: "#e2e8f0", fontSize: 12, ...INTER }}>{s.name}</td>
                    <td style={{ padding: "9px 10px" }}>
                      <span style={{ background: cfg.bg, color: cfg.color, fontSize: 11, padding: "2px 10px", borderRadius: 3, ...INTER, fontWeight: 600, whiteSpace: "nowrap" }}>{cfg.label}</span>
                    </td>
                    <td style={{ padding: "9px 10px", color: s.rsi > 70 ? "#ff4d6d" : s.rsi < 30 ? "#00d97e" : "#e2e8f0", fontSize: 12, ...MONO, textAlign: "right" }}>{s.rsi.toFixed(1)}</td>
                    <td style={{ padding: "9px 10px", color: s.macd > 0 ? "#00d97e" : "#ff4d6d", fontSize: 12, ...MONO, textAlign: "right" }}>{s.macd > 0 ? "+" : ""}{s.macd}</td>
                    <td style={{ padding: "9px 10px", color: "#e2e8f0", fontSize: 12, ...MONO, textAlign: "right" }}>{s.close.toLocaleString("vi-VN")}</td>
                    <td style={{ padding: "9px 10px", color: "#6b7fa3", fontSize: 11, ...MONO, textAlign: "right" }}>{s.bbUpper.toLocaleString("vi-VN")}</td>
                    <td style={{ padding: "9px 10px", color: "#6b7fa3", fontSize: 11, ...MONO, textAlign: "right" }}>{s.bbLower.toLocaleString("vi-VN")}</td>
                    <td style={{ padding: "9px 10px", textAlign: "right" }}>
                      <span style={{
                        background: parseFloat(volRatio) > 1.5 ? "rgba(6,182,212,0.1)" : "transparent",
                        color: parseFloat(volRatio) > 1.5 ? "#06b6d4" : "#6b7fa3",
                        fontSize: 12, ...MONO, padding: "2px 6px", borderRadius: 3, fontWeight: parseFloat(volRatio) > 1.5 ? 600 : 400,
                      }}>{volRatio}x</span>
                    </td>
                    <td style={{ padding: "9px 10px", textAlign: "right" }}>
                      <span style={{ color: s.pct >= 0 ? "#00d97e" : "#ff4d6d", fontSize: 12, ...MONO, fontWeight: 600 }}>
                        {s.pct >= 0 ? "+" : ""}{s.pct}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
