import { useState } from "react";
import {
  ComposedChart, Line, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell,
} from "recharts";
import { vwapData, vwapDeviations } from "./mockData";
import { Zap, Bell } from "lucide-react";

const CARD: React.CSSProperties = { background: "#111827", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: 16 };
const MONO: React.CSSProperties = { fontFamily: "JetBrains Mono, monospace" };
const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };

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

interface RealtimeVWAPProps { onNavigate: (page: string, ticker?: string) => void; }

export function RealtimeVWAP({ onNavigate }: RealtimeVWAPProps) {
  const [selectedTicker, setSelectedTicker] = useState("VCB");
  const tickers = ["VCB", "HPG", "STB", "NVL", "FPT", "ACB"];
  const last = vwapData[vwapData.length - 1];

  const deviationChartData = vwapData.map((d) => ({
    ...d,
    devColor: d.deviation >= 0 ? "#00d97e" : "#ff4d6d",
  }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h1 style={{ color: "#e2e8f0", margin: 0, fontSize: 18, fontWeight: 700, ...INTER }}>Realtime VWAP Monitoring</h1>
            <span style={{ display: "flex", alignItems: "center", gap: 4, background: "rgba(0,217,126,0.1)", color: "#00d97e", fontSize: 11, padding: "3px 8px", borderRadius: 4, ...INTER }}>
              <Zap size={11} /> LIVE
            </span>
          </div>
          <p style={{ color: "#6b7fa3", margin: 0, fontSize: 12, ...INTER }}>Theo dõi VWAP intraday · 09:15 – 14:30 phiên 14/06/2026</p>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          {tickers.map((t) => (
            <button key={t} onClick={() => setSelectedTicker(t)} style={{
              padding: "5px 12px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.1)",
              background: selectedTicker === t ? "#f59e0b" : "transparent",
              color: selectedTicker === t ? "#0b0f1a" : "#6b7fa3",
              fontSize: 12, ...MONO, cursor: "pointer", fontWeight: selectedTicker === t ? 700 : 400,
            }}>{t}</button>
          ))}
        </div>
      </div>

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
        {[
          { label: "Giá hiện tại", value: last.price.toLocaleString("vi-VN"), unit: "VNĐ", color: "#e2e8f0" },
          { label: "Session VWAP", value: last.sessionVwap.toLocaleString("vi-VN"), unit: "VNĐ", color: "#3b82f6" },
          { label: "Lệch VWAP", value: (last.deviation >= 0 ? "+" : "") + last.deviation.toFixed(2) + "%", unit: "so với Session VWAP", color: last.deviation >= 0 ? "#00d97e" : "#ff4d6d" },
          { label: "Session Volume", value: (vwapData.reduce((acc, d) => acc + d.volume, 0) / 1_000_000).toFixed(2) + "M", unit: "cổ phiếu", color: "#e2e8f0" },
          { label: "Alerts trong phiên", value: "3", unit: "lần kích hoạt", color: "#f59e0b" },
        ].map((kpi) => (
          <div key={kpi.label} style={CARD}>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{kpi.label}</div>
            <div style={{ ...MONO, color: kpi.color, fontSize: 20, fontWeight: 700 }}>{kpi.value}</div>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 11, marginTop: 2 }}>{kpi.unit}</div>
          </div>
        ))}
      </div>

      {/* Price vs VWAP chart */}
      <div style={CARD}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <span style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>Giá theo phút vs Session VWAP — {selectedTicker}</span>
          <div style={{ display: "flex", gap: 16 }}>
            {[
              { label: "Giá", color: "#e2e8f0" },
              { label: "VWAP 1min", color: "#f59e0b" },
              { label: "Session VWAP", color: "#3b82f6" },
            ].map((l) => (
              <div key={l.label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <div style={{ width: 20, height: 2, background: l.color }} />
                <span style={{ ...INTER, color: "#6b7fa3", fontSize: 11 }}>{l.label}</span>
              </div>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={vwapData} margin={{ left: 10, right: 20 }}>
            <XAxis dataKey="time" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
            <YAxis domain={["auto", "auto"]} tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} width={70} tickFormatter={(v) => v.toLocaleString("vi-VN")} />
            <Tooltip content={<CustomTooltip />} />
            <Line type="monotone" dataKey="price" stroke="#e2e8f0" strokeWidth={2} dot={false} name="Giá" />
            <Line type="monotone" dataKey="vwap" stroke="#f59e0b" strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="VWAP 1min" />
            <Line type="monotone" dataKey="sessionVwap" stroke="#3b82f6" strokeWidth={1.5} dot={false} strokeDasharray="3 3" name="Session VWAP" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Volume chart */}
      <div style={CARD}>
        <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Khối lượng theo phút</div>
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={vwapData} margin={{ left: 10, right: 20 }}>
            <XAxis dataKey="time" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} tickFormatter={(v) => (v / 1000).toFixed(0) + "K"} />
            <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any) => [(v / 1000).toFixed(0) + "K cp", "Volume"]} />
            <Bar dataKey="volume" fill="#3b82f6" opacity={0.7} radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Deviation chart */}
      <div style={CARD}>
        <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>
          Độ lệch so với Session VWAP (%)
          <span style={{ marginLeft: 12, ...INTER, color: "#6b7fa3", fontSize: 11, fontWeight: 400 }}>Ngưỡng cảnh báo: ±2%</span>
        </div>
        <ResponsiveContainer width="100%" height={130}>
          <ComposedChart data={deviationChartData} margin={{ left: 10, right: 20 }}>
            <XAxis dataKey="time" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} tickFormatter={(v) => v + "%"} />
            <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any) => [v.toFixed(2) + "%", "Deviation"]} />
            <ReferenceLine y={2} stroke="#ff4d6d" strokeDasharray="3 3" strokeWidth={1} />
            <ReferenceLine y={-2} stroke="#ff4d6d" strokeDasharray="3 3" strokeWidth={1} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeWidth={1} />
            <Bar dataKey="deviation" radius={[2, 2, 0, 0]}>
              {deviationChartData.map((d, i) => <Cell key={i} fill={d.deviation >= 0 ? "#00d97e" : "#ff4d6d"} opacity={0.75} />)}
            </Bar>
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Deviation table */}
      <div style={CARD}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <Bell size={14} color="#f59e0b" />
          <span style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>Mã lệch VWAP mạnh nhất trong phiên</span>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
              {["Mã CK", "Giá hiện tại", "Session VWAP", "Lệch %", "Volume", "Alerts"].map((h) => (
                <th key={h} style={{ color: "#6b7fa3", fontSize: 11, textAlign: "left", padding: "6px 10px", ...INTER, textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {vwapDeviations.map((r) => (
              <tr key={r.ticker} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}
                onClick={() => onNavigate("stock", r.ticker)}
                onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.03)"}
                onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}
              >
                <td style={{ padding: "9px 10px" }}><span style={{ color: "#f59e0b", fontSize: 13, fontWeight: 700, ...MONO }}>{r.ticker}</span></td>
                <td style={{ padding: "9px 10px", color: "#e2e8f0", fontSize: 12, ...MONO, textAlign: "right" }}>{r.price.toLocaleString("vi-VN")}</td>
                <td style={{ padding: "9px 10px", color: "#3b82f6", fontSize: 12, ...MONO, textAlign: "right" }}>{r.sessionVwap.toLocaleString("vi-VN")}</td>
                <td style={{ padding: "9px 10px", textAlign: "right" }}>
                  <span style={{
                    background: r.deviation >= 0 ? "rgba(0,217,126,0.1)" : "rgba(255,77,109,0.1)",
                    color: r.deviation >= 0 ? "#00d97e" : "#ff4d6d",
                    fontSize: 13, ...MONO, padding: "3px 10px", borderRadius: 4, fontWeight: 700,
                  }}>{r.deviation >= 0 ? "+" : ""}{r.deviation.toFixed(2)}%</span>
                </td>
                <td style={{ padding: "9px 10px", color: "#6b7fa3", fontSize: 12, ...MONO, textAlign: "right" }}>{(r.volume / 1_000_000).toFixed(2)}M</td>
                <td style={{ padding: "9px 10px", textAlign: "right" }}>
                  {r.alerts > 0
                    ? <span style={{ background: "rgba(245,158,11,0.1)", color: "#f59e0b", fontSize: 12, ...MONO, padding: "2px 8px", borderRadius: 3, fontWeight: 600 }}>{r.alerts}</span>
                    : <span style={{ color: "#6b7fa3", fontSize: 12, ...MONO }}>—</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
