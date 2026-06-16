import { useState } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie,
} from "recharts";
import { TrendingUp, TrendingDown, Minus, DollarSign, Activity, BarChart2 } from "lucide-react";
import {
  vnIndexHistory, topGainers, topLosers, topLiquidity, sectorPerformance
} from "./mockData";

const CARD_STYLE: React.CSSProperties = {
  background: "#111827",
  border: "1px solid rgba(255,255,255,0.07)",
  borderRadius: 8,
  padding: 16,
};

const LABEL_STYLE: React.CSSProperties = {
  color: "#6b7fa3", fontSize: 11, fontFamily: "Inter, sans-serif", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.06em",
};

const VALUE_STYLE: React.CSSProperties = {
  color: "#e2e8f0", fontSize: 22, fontWeight: 700, fontFamily: "JetBrains Mono, monospace",
};

function KPICard({ label, value, sub, subUp }: { label: string; value: string; sub?: string; subUp?: boolean | null }) {
  return (
    <div style={CARD_STYLE}>
      <div style={LABEL_STYLE}>{label}</div>
      <div style={VALUE_STYLE}>{value}</div>
      {sub && (
        <div style={{ color: subUp === null ? "#6b7fa3" : subUp ? "#00d97e" : "#ff4d6d", fontSize: 12, fontFamily: "JetBrains Mono, monospace", marginTop: 2 }}>
          {sub}
        </div>
      )}
    </div>
  );
}

const breadthData = [
  { name: "Tăng", value: 248, fill: "#00d97e" },
  { name: "Giảm", value: 187, fill: "#ff4d6d" },
  { name: "Đứng", value: 81, fill: "#6b7fa3" },
];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "8px 12px", fontSize: 12, fontFamily: "JetBrains Mono, monospace" }}>
        <div style={{ color: "#6b7fa3" }}>{label}</div>
        <div style={{ color: "#f59e0b", fontWeight: 600 }}>{payload[0].value?.toLocaleString("vi-VN")}</div>
      </div>
    );
  }
  return null;
};

interface MarketOverviewProps { onNavigate: (page: string, ticker?: string) => void; }

export function MarketOverview({ onNavigate }: MarketOverviewProps) {
  const [activeTab, setActiveTab] = useState<"gainers" | "losers" | "liquidity" | "sector">("gainers");
  const [exchange, setExchange] = useState("ALL");

  const formatBillion = (n: number) => (n / 1_000_000_000).toFixed(1) + " tỷ";
  const formatMillion = (n: number) => (n / 1_000_000).toFixed(2) + "M";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ color: "#e2e8f0", margin: 0, fontSize: 18, fontWeight: 700, fontFamily: "Inter, sans-serif" }}>Market Overview</h1>
          <p style={{ color: "#6b7fa3", margin: 0, fontSize: 12, fontFamily: "Inter, sans-serif" }}>Tổng quan thị trường · Phiên 14/06/2026</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {["ALL", "HOSE", "HNX", "UPCOM"].map((ex) => (
            <button key={ex} onClick={() => setExchange(ex)} style={{
              padding: "5px 12px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.1)",
              background: exchange === ex ? "#f59e0b" : "transparent",
              color: exchange === ex ? "#0b0f1a" : "#6b7fa3",
              fontSize: 12, fontFamily: "Inter, sans-serif", cursor: "pointer", fontWeight: exchange === ex ? 600 : 400,
            }}>{ex}</button>
          ))}
        </div>
      </div>

      {/* KPI Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
        <KPICard label="VN-Index" value="1.283,7" sub="+35,2 (+2,82%)" subUp={true} />
        <KPICard label="HNX-Index" value="228,4" sub="+4,1 (+1,83%)" subUp={true} />
        <KPICard label="VN30" value="1.341,5" sub="+28,6 (+2,18%)" subUp={true} />
        <KPICard label="Giá trị GD" value="18.425 tỷ" sub="HOSE+HNX+UPCOM" subUp={null} />
        <KPICard label="Khối lượng GD" value="856,3 M" sub="cp toàn thị trường" subUp={null} />
        <KPICard label="Độ rộng TT" value="248 / 187" sub="Tăng / Giảm / Đứng: 81" subUp={null} />
      </div>

      {/* Charts Row */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 12 }}>
        {/* VN-Index Line Chart */}
        <div style={CARD_STYLE}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <span style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 600, fontFamily: "Inter, sans-serif" }}>VN-Index intraday</span>
            <span style={{ color: "#00d97e", fontSize: 12, fontFamily: "JetBrains Mono, monospace" }}>▲ +35,2 (+2,82%)</span>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={vnIndexHistory}>
              <XAxis dataKey="time" tick={{ fill: "#6b7fa3", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }} axisLine={false} tickLine={false} />
              <YAxis domain={["auto", "auto"]} tick={{ fill: "#6b7fa3", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }} axisLine={false} tickLine={false} width={60} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="value" stroke="#f59e0b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Breadth Donut */}
        <div style={CARD_STYLE}>
          <div style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 600, fontFamily: "Inter, sans-serif", marginBottom: 8 }}>Độ rộng thị trường</div>
          <ResponsiveContainer width="100%" height={130}>
            <PieChart>
              <Pie data={breadthData} cx="50%" cy="50%" innerRadius={38} outerRadius={60} dataKey="value">
                {breadthData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Pie>
              <Tooltip formatter={(val: any, name: any) => [val + " mã", name]} contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 4 }}>
            {breadthData.map((d) => (
              <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <div style={{ width: 8, height: 8, borderRadius: 2, background: d.fill }} />
                <span style={{ color: "#6b7fa3", fontSize: 11, fontFamily: "Inter, sans-serif" }}>{d.name}: <span style={{ color: d.fill, fontWeight: 600 }}>{d.value}</span></span>
              </div>
            ))}
          </div>
        </div>

        {/* Indices change bars */}
        <div style={CARD_STYLE}>
          <div style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 600, fontFamily: "Inter, sans-serif", marginBottom: 8 }}>Chỉ số % hôm nay</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
            {[
              { label: "VN-Index", pct: 2.82 },
              { label: "VN30", pct: 2.18 },
              { label: "HNX", pct: 1.83 },
              { label: "UPCOM", pct: 0.94 },
            ].map((idx) => (
              <div key={idx.label}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ color: "#6b7fa3", fontSize: 11, fontFamily: "Inter, sans-serif" }}>{idx.label}</span>
                  <span style={{ color: "#00d97e", fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}>+{idx.pct}%</span>
                </div>
                <div style={{ height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ width: `${(idx.pct / 3) * 100}%`, height: "100%", background: "#00d97e", borderRadius: 2 }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sector heatmap */}
      <div style={CARD_STYLE}>
        <div style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 600, fontFamily: "Inter, sans-serif", marginBottom: 12 }}>Hiệu suất theo ngành</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
          {sectorPerformance.map((s) => {
            const intensity = Math.min(Math.abs(s.pct) / 4, 1);
            const bg = s.pct > 0
              ? `rgba(0, 217, 126, ${0.1 + intensity * 0.35})`
              : `rgba(255, 77, 109, ${0.1 + intensity * 0.35})`;
            return (
              <div key={s.sector} style={{ background: bg, borderRadius: 6, padding: "10px 12px", border: `1px solid ${s.pct > 0 ? "rgba(0,217,126,0.2)" : "rgba(255,77,109,0.2)"}` }}>
                <div style={{ color: "#e2e8f0", fontSize: 12, fontFamily: "Inter, sans-serif", marginBottom: 4 }}>{s.sector}</div>
                <div style={{ color: s.pct > 0 ? "#00d97e" : "#ff4d6d", fontSize: 14, fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>
                  {s.pct > 0 ? "+" : ""}{s.pct}%
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Tab tables */}
      <div style={CARD_STYLE}>
        <div style={{ display: "flex", gap: 0, marginBottom: 16, borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
          {(["gainers", "losers", "liquidity", "sector"] as const).map((tab) => {
            const labels = { gainers: "Top Tăng giá", losers: "Top Giảm giá", liquidity: "Top Thanh khoản", sector: "Ngành dẫn dắt" };
            return (
              <button key={tab} onClick={() => setActiveTab(tab)} style={{
                padding: "8px 16px", border: "none", cursor: "pointer",
                background: "transparent", borderBottom: activeTab === tab ? "2px solid #f59e0b" : "2px solid transparent",
                color: activeTab === tab ? "#f59e0b" : "#6b7fa3",
                fontSize: 12, fontFamily: "Inter, sans-serif", fontWeight: activeTab === tab ? 600 : 400,
                marginBottom: -1, transition: "all 0.15s",
              }}>{labels[tab]}</button>
            );
          })}
        </div>

        {/* Table */}
        <div style={{ overflowX: "auto" }}>
          {activeTab === "gainers" && (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                  {["Mã CK", "Tên công ty", "Ngành", "Giá (đ)", "Thay đổi", "%", "Khối lượng"].map((h) => (
                    <th key={h} style={{ color: "#6b7fa3", fontSize: 11, textAlign: "left", padding: "6px 10px", fontFamily: "Inter, sans-serif", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {topGainers.map((r, i) => (
                  <tr key={r.ticker} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}
                    onClick={() => onNavigate("stock", r.ticker)}
                    onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.03)"}
                    onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}
                  >
                    <td style={{ padding: "8px 10px" }}>
                      <span style={{ color: "#f59e0b", fontSize: 13, fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>{r.ticker}</span>
                    </td>
                    <td style={{ padding: "8px 10px", color: "#e2e8f0", fontSize: 12, fontFamily: "Inter, sans-serif" }}>{r.name}</td>
                    <td style={{ padding: "8px 10px" }}>
                      <span style={{ background: "rgba(59,130,246,0.15)", color: "#3b82f6", fontSize: 11, padding: "2px 8px", borderRadius: 3, fontFamily: "Inter, sans-serif" }}>{r.sector}</span>
                    </td>
                    <td style={{ padding: "8px 10px", color: "#e2e8f0", fontSize: 12, fontFamily: "JetBrains Mono, monospace", textAlign: "right" }}>{r.price.toLocaleString("vi-VN")}</td>
                    <td style={{ padding: "8px 10px", color: "#00d97e", fontSize: 12, fontFamily: "JetBrains Mono, monospace", textAlign: "right" }}>+{r.change.toLocaleString("vi-VN")}</td>
                    <td style={{ padding: "8px 10px", textAlign: "right" }}>
                      <span style={{ background: "rgba(0,217,126,0.1)", color: "#00d97e", fontSize: 12, fontFamily: "JetBrains Mono, monospace", padding: "2px 8px", borderRadius: 3, fontWeight: 600 }}>+{r.pct}%</span>
                    </td>
                    <td style={{ padding: "8px 10px", color: "#6b7fa3", fontSize: 12, fontFamily: "JetBrains Mono, monospace", textAlign: "right" }}>{formatMillion(r.volume)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {activeTab === "losers" && (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                  {["Mã CK", "Tên công ty", "Ngành", "Giá (đ)", "Thay đổi", "%", "Khối lượng"].map((h) => (
                    <th key={h} style={{ color: "#6b7fa3", fontSize: 11, textAlign: "left", padding: "6px 10px", fontFamily: "Inter, sans-serif", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {topLosers.map((r) => (
                  <tr key={r.ticker} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}
                    onClick={() => onNavigate("stock", r.ticker)}
                    onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.03)"}
                    onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}
                  >
                    <td style={{ padding: "8px 10px" }}>
                      <span style={{ color: "#f59e0b", fontSize: 13, fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>{r.ticker}</span>
                    </td>
                    <td style={{ padding: "8px 10px", color: "#e2e8f0", fontSize: 12, fontFamily: "Inter, sans-serif" }}>{r.name}</td>
                    <td style={{ padding: "8px 10px" }}>
                      <span style={{ background: "rgba(59,130,246,0.15)", color: "#3b82f6", fontSize: 11, padding: "2px 8px", borderRadius: 3, fontFamily: "Inter, sans-serif" }}>{r.sector}</span>
                    </td>
                    <td style={{ padding: "8px 10px", color: "#e2e8f0", fontSize: 12, fontFamily: "JetBrains Mono, monospace", textAlign: "right" }}>{r.price.toLocaleString("vi-VN")}</td>
                    <td style={{ padding: "8px 10px", color: "#ff4d6d", fontSize: 12, fontFamily: "JetBrains Mono, monospace", textAlign: "right" }}>{r.change.toLocaleString("vi-VN")}</td>
                    <td style={{ padding: "8px 10px", textAlign: "right" }}>
                      <span style={{ background: "rgba(255,77,109,0.1)", color: "#ff4d6d", fontSize: 12, fontFamily: "JetBrains Mono, monospace", padding: "2px 8px", borderRadius: 3, fontWeight: 600 }}>{r.pct}%</span>
                    </td>
                    <td style={{ padding: "8px 10px", color: "#6b7fa3", fontSize: 12, fontFamily: "JetBrains Mono, monospace", textAlign: "right" }}>{(r.volume / 1_000_000).toFixed(2)}M</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {activeTab === "liquidity" && (
            <div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={topLiquidity} layout="vertical" margin={{ left: 40, right: 20 }}>
                  <XAxis type="number" tick={{ fill: "#6b7fa3", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }} axisLine={false} tickLine={false} tickFormatter={(v) => (v / 1_000_000).toFixed(0) + "M"} />
                  <YAxis type="category" dataKey="ticker" tick={{ fill: "#f59e0b", fontSize: 12, fontFamily: "JetBrains Mono, monospace" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12 }} formatter={(v: any) => [(v / 1_000_000).toFixed(2) + "M cp", "Khối lượng"]} />
                  <Bar dataKey="volume" fill="#3b82f6" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                    {["Mã CK", "Tên công ty", "Giá (đ)", "Khối lượng", "Giá trị"].map((h) => (
                      <th key={h} style={{ color: "#6b7fa3", fontSize: 11, textAlign: "left", padding: "6px 10px", fontFamily: "Inter, sans-serif", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {topLiquidity.map((r) => (
                    <tr key={r.ticker} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}
                      onClick={() => onNavigate("stock", r.ticker)}
                      onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.03)"}
                      onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}
                    >
                      <td style={{ padding: "8px 10px" }}><span style={{ color: "#f59e0b", fontSize: 13, fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>{r.ticker}</span></td>
                      <td style={{ padding: "8px 10px", color: "#e2e8f0", fontSize: 12, fontFamily: "Inter, sans-serif" }}>{r.name}</td>
                      <td style={{ padding: "8px 10px", color: "#e2e8f0", fontSize: 12, fontFamily: "JetBrains Mono, monospace", textAlign: "right" }}>{r.price.toLocaleString("vi-VN")}</td>
                      <td style={{ padding: "8px 10px", color: "#3b82f6", fontSize: 12, fontFamily: "JetBrains Mono, monospace", textAlign: "right" }}>{(r.volume / 1_000_000).toFixed(2)}M</td>
                      <td style={{ padding: "8px 10px", color: "#6b7fa3", fontSize: 12, fontFamily: "JetBrains Mono, monospace", textAlign: "right" }}>{formatBillion(r.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === "sector" && (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={sectorPerformance} margin={{ left: 10, right: 20, top: 10 }}>
                <XAxis dataKey="sector" tick={{ fill: "#6b7fa3", fontSize: 10, fontFamily: "Inter, sans-serif" }} axisLine={false} tickLine={false} angle={-20} textAnchor="end" height={50} />
                <YAxis tick={{ fill: "#6b7fa3", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }} axisLine={false} tickLine={false} tickFormatter={(v) => v + "%"} />
                <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12 }} formatter={(v: any) => [v + "%", "Thay đổi"]} />
                <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
                  {sectorPerformance.map((entry, i) => (
                    <Cell key={i} fill={entry.pct > 0 ? "#00d97e" : "#ff4d6d"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
