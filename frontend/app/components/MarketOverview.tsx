import { useState } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie,
} from "recharts";
import { TrendingUp, TrendingDown, Minus, DollarSign, Activity, BarChart2 } from "lucide-react";
import {
  vnIndexHistory, topGainers, topLosers, topLiquidity, sectorPerformance,
  marketIndices, marketIndicesAll, marketOverviewStats, breadthData, indexChangeBars, dataSnapshotMeta,
  marketStatsByExchange, breadthDataByExchange, indexHistoryByExchange,
  sectorPerformanceByExchange, stockCountsByExchange
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

type KpiItem = { label: string; value: string; sub?: string; subUp?: boolean | null };

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "8px 12px", fontSize: 12, fontFamily: "JetBrains Mono, monospace" }}>
        <div style={{ color: "#6b7fa3" }}>{label}</div>
        <div style={{ color: "#8b5cf6", fontWeight: 600 }}>{payload[0].value?.toLocaleString("vi-VN")}</div>
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
  const selectedStats = marketStatsByExchange[exchange] ?? marketOverviewStats;
  const selectedBreadthData = breadthDataByExchange[exchange] ?? breadthData;
  const selectedIndexHistory = indexHistoryByExchange[exchange] ?? vnIndexHistory;
  const selectedIndex = exchange === "HNX"
    ? marketIndicesAll.find((idx) => idx.label === "HNX-Index")
    : exchange === "UPCOM"
      ? marketIndicesAll.find((idx) => idx.label === "UPCOM-Index")
      : marketIndicesAll.find((idx) => idx.label === "VN-Index");
  const selectedIndexLabel = exchange === "HNX" ? "HNX-Index" : exchange === "UPCOM" ? "UPCOM-Index" : "VN-Index";
  const selectedIndexBars = exchange === "ALL"
    ? indexChangeBars
    : indexChangeBars.filter((idx) => {
      if (exchange === "HOSE") return idx.label === "VN-Index" || idx.label === "VN30";
      if (exchange === "HNX") return idx.label === "HNX-Index";
      return idx.label === "UPCOM-Index";
    });
  const filteredGainers = (exchange === "ALL" ? topGainers : topGainers.filter((r) => r.exchange === exchange)).slice(0, 10);
  const filteredLosers = (exchange === "ALL" ? topLosers : topLosers.filter((r) => r.exchange === exchange)).slice(0, 10);
  const filteredLiquidity = (exchange === "ALL" ? topLiquidity : topLiquidity.filter((r) => r.exchange === exchange)).slice(0, 8);
  const filteredSectorPerformance = (exchange === "ALL"
    ? sectorPerformance
    : sectorPerformanceByExchange.filter((s) => s.exchange === exchange)
  ).slice(0, 12);
  const selectedIndexCards = exchange === "ALL"
    ? []
    : marketIndicesAll.filter((idx) => {
      if (exchange === "HOSE") return idx.label === "VN-Index" || idx.label === "VN30";
      if (exchange === "HNX") return idx.label === "HNX-Index";
      return idx.label === "UPCOM-Index";
    });
  const topSector = filteredSectorPerformance[0];
  const contextLabel = exchange === "ALL" ? "Toàn thị trường" : `Sàn ${exchange}`;
  const overviewKpis: KpiItem[] = exchange === "ALL"
    ? [
      { label: "Giá trị GD", value: selectedStats.totalValue, sub: contextLabel, subUp: null },
      { label: "Khối lượng GD", value: selectedStats.totalVolume, sub: "cp toàn thị trường", subUp: null },
      { label: "Độ rộng TT", value: selectedStats.breadth, sub: selectedStats.breadthSub, subUp: null },
      { label: "Số mã có giá", value: `${stockCountsByExchange.ALL ?? 0}`, sub: "fact_daily_price mới nhất", subUp: null },
      { label: "Top ngành", value: topSector?.sector ?? "N/A", sub: topSector ? `${topSector.pct >= 0 ? "+" : ""}${topSector.pct.toFixed(2)}%` : undefined, subUp: topSector ? topSector.pct >= 0 : null },
      { label: "Sàn đang xem", value: "ALL", sub: "HOSE + HNX + UPCOM", subUp: null },
    ]
    : [
      ...selectedIndexCards.map((idx) => ({ label: idx.label, value: idx.value, sub: `${idx.chg} (${idx.pct})`, subUp: idx.up })),
      { label: "Giá trị GD", value: selectedStats.totalValue, sub: contextLabel, subUp: null },
      { label: "Khối lượng GD", value: selectedStats.totalVolume, sub: "cp toàn thị trường", subUp: null },
      { label: "Độ rộng TT", value: selectedStats.breadth, sub: selectedStats.breadthSub, subUp: null },
      { label: "Số mã có giá", value: `${stockCountsByExchange[exchange] ?? 0}`, sub: "fact_daily_price mới nhất", subUp: null },
      { label: "Top ngành", value: topSector?.sector ?? "N/A", sub: topSector ? `${topSector.pct >= 0 ? "+" : ""}${topSector.pct.toFixed(2)}%` : undefined, subUp: topSector ? topSector.pct >= 0 : null },
    ].slice(0, 6);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ color: "#e2e8f0", margin: 0, fontSize: 18, fontWeight: 700, fontFamily: "Inter, sans-serif" }}>Tổng quan thị trường</h1>
          <p style={{ color: "#6b7fa3", margin: 0, fontSize: 12, fontFamily: "Inter, sans-serif" }}>Dữ liệu ClickHouse · Phiên {dataSnapshotMeta.latestPriceDate}</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {["ALL", "HOSE", "HNX", "UPCOM"].map((ex) => (
            <button key={ex} onClick={() => setExchange(ex)} style={{
              padding: "5px 12px", borderRadius: 5, border: "1px solid rgba(255,255,255,0.1)",
              background: exchange === ex ? "#8b5cf6" : "transparent",
              color: exchange === ex ? "#0b0f1a" : "#6b7fa3",
              fontSize: 12, fontFamily: "Inter, sans-serif", cursor: "pointer", fontWeight: exchange === ex ? 600 : 400,
            }}>{ex}</button>
          ))}
        </div>
      </div>

      {/* KPI Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
        {overviewKpis.map((kpi) => (
          <KPICard key={kpi.label} label={kpi.label} value={kpi.value} sub={kpi.sub} subUp={kpi.subUp} />
        ))}
      </div>

      {/* Charts Row */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 12 }}>
        {/* VN-Index Line Chart */}
        <div style={CARD_STYLE}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <span style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 600, fontFamily: "Inter, sans-serif" }}>{selectedIndexLabel} theo ngày</span>
            <span style={{ color: (selectedIndex?.rawPct ?? 0) >= 0 ? "#00d97e" : "#ff4d6d", fontSize: 12, fontFamily: "JetBrains Mono, monospace" }}>
              {"chg" in (selectedIndex ?? {}) ? `${(selectedIndex as any).chg} (${(selectedIndex as any).pct})` : `${(selectedIndex?.pct ?? 0) >= 0 ? "+" : ""}${(selectedIndex?.pct ?? 0).toFixed(2)}%`}
            </span>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={selectedIndexHistory}>
              <XAxis dataKey="time" tick={{ fill: "#6b7fa3", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }} axisLine={false} tickLine={false} />
              <YAxis domain={["auto", "auto"]} tick={{ fill: "#6b7fa3", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }} axisLine={false} tickLine={false} width={60} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="value" stroke="#8b5cf6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Breadth Donut */}
        <div style={CARD_STYLE}>
          <div style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 600, fontFamily: "Inter, sans-serif", marginBottom: 8 }}>Độ rộng thị trường</div>
          <ResponsiveContainer width="100%" height={130}>
            <PieChart>
              <Pie data={selectedBreadthData} cx="50%" cy="50%" innerRadius={38} outerRadius={60} dataKey="value">
                {selectedBreadthData.map((entry) => <Cell key={`breadth-${entry.name}`} fill={entry.fill} />)}
              </Pie>
              <Tooltip formatter={(val: any, name: any) => [val + " mã", name]} contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 4 }}>
            {selectedBreadthData.map((d) => (
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
            {selectedIndexBars.map((idx) => (
              <div key={idx.label}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ color: "#6b7fa3", fontSize: 11, fontFamily: "Inter, sans-serif" }}>{idx.label}</span>
                  <span style={{ color: idx.pct >= 0 ? "#00d97e" : "#ff4d6d", fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}>{idx.pct >= 0 ? "+" : ""}{idx.pct.toFixed(2)}%</span>
                </div>
                <div style={{ height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ width: `${Math.min(Math.abs(idx.pct) / 3, 1) * 100}%`, height: "100%", background: idx.pct >= 0 ? "#00d97e" : "#ff4d6d", borderRadius: 2 }} />
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
          {filteredSectorPerformance.map((s) => {
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
                background: "transparent", borderBottom: activeTab === tab ? "2px solid #8b5cf6" : "2px solid transparent",
                color: activeTab === tab ? "#8b5cf6" : "#6b7fa3",
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
                {filteredGainers.map((r) => (
                  <tr key={r.ticker} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}
                    onClick={() => onNavigate("stock", r.ticker)}
                    onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.03)"}
                    onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}
                  >
                    <td style={{ padding: "8px 10px" }}>
                      <span style={{ color: "#8b5cf6", fontSize: 13, fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>{r.ticker}</span>
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
                {filteredLosers.map((r) => (
                  <tr key={r.ticker} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}
                    onClick={() => onNavigate("stock", r.ticker)}
                    onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.03)"}
                    onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}
                  >
                    <td style={{ padding: "8px 10px" }}>
                      <span style={{ color: "#8b5cf6", fontSize: 13, fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>{r.ticker}</span>
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
                <BarChart data={filteredLiquidity} layout="vertical" margin={{ left: 40, right: 20 }}>
                  <XAxis type="number" tick={{ fill: "#6b7fa3", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }} axisLine={false} tickLine={false} tickFormatter={(v) => (v / 1_000_000).toFixed(0) + "M"} />
                  <YAxis type="category" dataKey="ticker" tick={{ fill: "#8b5cf6", fontSize: 12, fontFamily: "JetBrains Mono, monospace" }} axisLine={false} tickLine={false} />
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
                  {filteredLiquidity.map((r) => (
                    <tr key={r.ticker} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}
                      onClick={() => onNavigate("stock", r.ticker)}
                      onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.03)"}
                      onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}
                    >
                      <td style={{ padding: "8px 10px" }}><span style={{ color: "#8b5cf6", fontSize: 13, fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>{r.ticker}</span></td>
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
              <BarChart data={filteredSectorPerformance} margin={{ left: 10, right: 20, top: 10 }}>
                <XAxis dataKey="sector" tick={{ fill: "#6b7fa3", fontSize: 10, fontFamily: "Inter, sans-serif" }} axisLine={false} tickLine={false} angle={-20} textAnchor="end" height={50} />
                <YAxis tick={{ fill: "#6b7fa3", fontSize: 10, fontFamily: "JetBrains Mono, monospace" }} axisLine={false} tickLine={false} tickFormatter={(v) => v + "%"} />
                <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12 }} formatter={(v: any) => [v + "%", "Thay đổi"]} />
                <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
                  {filteredSectorPerformance.map((entry) => (
                    <Cell key={`sector-${entry.sector}`} fill={entry.pct > 0 ? "#00d97e" : "#ff4d6d"} />
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
