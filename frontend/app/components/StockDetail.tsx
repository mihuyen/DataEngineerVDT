import { useState, useMemo } from "react";
import {
  ComposedChart, Line, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";
import { generateCandlestickData, stockList } from "./mockData";

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

  const data = useMemo(() => generateCandlestickData(), [ticker]);
  const sliced = period === "1M" ? data.slice(-21) : period === "3M" ? data.slice(-63) : period === "6M" ? data.slice(-126) : data;
  const stock = stockList.find((s) => s.ticker === ticker) || stockList[0];
  const last = sliced[sliced.length - 1];
  const prev = sliced[sliced.length - 2];
  const pct = ((last.close - prev.close) / prev.close * 100).toFixed(2);
  const up = last.close >= prev.close;

  const toggleIndicator = (key: keyof typeof indicators) => {
    setIndicators((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ ...MONO, color: "#f59e0b", fontSize: 22, fontWeight: 700 }}>{stock.ticker}</span>
              <span style={{ background: "rgba(59,130,246,0.15)", color: "#3b82f6", fontSize: 11, padding: "2px 8px", borderRadius: 3, ...INTER }}>{stock.exchange}</span>
              <span style={{ background: "rgba(255,255,255,0.06)", color: "#6b7fa3", fontSize: 11, padding: "2px 8px", borderRadius: 3, ...INTER }}>{stock.sector}</span>
            </div>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 12, marginTop: 2 }}>{stock.name}</div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {/* Ticker selector */}
          <select
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            style={{
              background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 5,
              color: "#e2e8f0", padding: "6px 10px", fontSize: 12, ...INTER, cursor: "pointer",
            }}
          >
            {stockList.map((s) => (
              <option key={s.ticker} value={s.ticker}>{s.ticker} – {s.name.slice(0, 30)}</option>
            ))}
          </select>

          {/* Period buttons */}
          {["1M", "3M", "6M", "1Y"].map((p) => (
            <button key={p} onClick={() => setPeriod(p)} style={{
              padding: "5px 12px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.1)",
              background: period === p ? "#f59e0b" : "transparent",
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
          const colors: Record<string, string> = { sma20: "#f59e0b", ema12: "#a855f7", bb: "#6b7fa3", rsi: "#3b82f6", macd: "#00d97e" };
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
            <XAxis dataKey="date" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} interval={Math.floor(sliced.length / 8)} />
            <YAxis yAxisId="price" domain={["auto", "auto"]} tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} width={70} tickFormatter={(v) => v.toLocaleString("vi-VN")} />
            <YAxis yAxisId="vol" orientation="right" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} width={60} tickFormatter={(v) => (v / 1_000_000).toFixed(1) + "M"} />
            <Tooltip content={<CustomTooltip />} />
            <Bar yAxisId="vol" dataKey="volume" fill="rgba(59,130,246,0.25)" name="Volume" radius={[1, 1, 0, 0]} />
            <Line yAxisId="price" type="monotone" dataKey="close" stroke={up ? "#00d97e" : "#ff4d6d"} strokeWidth={2} dot={false} name="Giá đóng cửa" />
            {indicators.sma20 && <Line yAxisId="price" type="monotone" dataKey="sma20" stroke="#f59e0b" strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="SMA20" />}
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
                <XAxis dataKey="date" tick={false} axisLine={false} tickLine={false} />
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
                <XAxis dataKey="date" tick={false} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} width={40} />
                <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" strokeWidth={1} />
                <Bar dataKey="macd" fill="#00d97e" opacity={0.6} name="MACD" />
                <Line type="monotone" dataKey="macdSignal" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="Signal" />
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
            {[
              { date: "14/06/2026", title: `${stock.ticker} ghi nhận kết quả kinh doanh Q2 tích cực, vượt kỳ vọng thị trường`, source: "CafeF", sentiment: 0.78 },
              { date: "13/06/2026", title: `Dòng tiền ngoại mua ròng ${stock.ticker} phiên thứ 5 liên tiếp`, source: "VnDirect", sentiment: 0.65 },
              { date: "12/06/2026", title: `Phân tích kỹ thuật ${stock.ticker}: Breakout khỏi kháng cự quan trọng`, source: "SSI", sentiment: 0.52 },
              { date: "11/06/2026", title: `${stock.ticker} thông báo kế hoạch chia cổ tức bằng tiền mặt 1.500đ/cp`, source: "HNX", sentiment: 0.88 },
              { date: "10/06/2026", title: `Nhận định: ${stock.ticker} có thể điều chỉnh ngắn hạn trước khi tăng trở lại`, source: "VCSC", sentiment: -0.15 },
            ].map((row, i) => (
              <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <td style={{ padding: "9px 10px", color: "#6b7fa3", fontSize: 11, ...MONO, whiteSpace: "nowrap" }}>{row.date}</td>
                <td style={{ padding: "9px 10px", color: "#e2e8f0", fontSize: 12, ...INTER }}>{row.title}</td>
                <td style={{ padding: "9px 10px" }}>
                  <span style={{ background: "rgba(255,255,255,0.06)", color: "#6b7fa3", fontSize: 11, padding: "2px 8px", borderRadius: 3, ...INTER }}>{row.source}</span>
                </td>
                <td style={{ padding: "9px 10px" }}>
                  <span style={{
                    background: row.sentiment > 0.3 ? "rgba(0,217,126,0.1)" : row.sentiment < -0.1 ? "rgba(255,77,109,0.1)" : "rgba(107,127,163,0.15)",
                    color: row.sentiment > 0.3 ? "#00d97e" : row.sentiment < -0.1 ? "#ff4d6d" : "#6b7fa3",
                    fontSize: 12, padding: "2px 8px", borderRadius: 3, ...MONO, fontWeight: 600,
                  }}>
                    {row.sentiment > 0 ? "+" : ""}{row.sentiment.toFixed(2)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
