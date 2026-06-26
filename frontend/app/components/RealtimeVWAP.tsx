import { useEffect, useState, useMemo } from "react";
import {
  ComposedChart, Line, Bar, BarChart, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell,
} from "recharts";
import { vwapData, vwapDeviations } from "./mockData";
import { VwapPoint, VwapTicker, fetchRealtimeVwap, fetchRealtimeVwapSeries } from "./api";
import { Search, Zap, Bell, TrendingUp, TrendingDown, ArrowUpDown } from "lucide-react";

const CARD: React.CSSProperties = { background: "#111827", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: 16 };
const MONO: React.CSSProperties = { fontFamily: "JetBrains Mono, monospace" };
const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };

// Generate a large realistic ticker list
function generateTickerList() {
  const tickers = [
    { ticker: "VCB", name: "Vietcombank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "BID", name: "BIDV", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "CTG", name: "VietinBank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "ACB", name: "ACB Bank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "MBB", name: "MB Bank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "TCB", name: "Techcombank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "STB", name: "Sacombank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "HDB", name: "HDBank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "VPB", name: "VPBank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "LPB", name: "LienVietPostBank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "MSB", name: "Maritime Bank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "TPB", name: "TPBank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "OCB", name: "OCB Bank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "EIB", name: "Eximbank", sector: "Ngân hàng", exchange: "HOSE" },
    { ticker: "FPT", name: "FPT Corporation", sector: "Công nghệ", exchange: "HOSE" },
    { ticker: "CMG", name: "CMC Corp", sector: "Công nghệ", exchange: "HOSE" },
    { ticker: "VGI", name: "Viettel Global", sector: "Công nghệ", exchange: "HOSE" },
    { ticker: "ITD", name: "IDT International", sector: "Công nghệ", exchange: "HOSE" },
    { ticker: "SAM", name: "SAM Holdings", sector: "Công nghệ", exchange: "HOSE" },
    { ticker: "HPG", name: "Hòa Phát Group", sector: "Thép", exchange: "HOSE" },
    { ticker: "HSG", name: "Hoa Sen Group", sector: "Thép", exchange: "HOSE" },
    { ticker: "NKG", name: "Nam Kim Steel", sector: "Thép", exchange: "HOSE" },
    { ticker: "POM", name: "Pomina Steel", sector: "Thép", exchange: "HOSE" },
    { ticker: "VIC", name: "Vingroup", sector: "Bất động sản", exchange: "HOSE" },
    { ticker: "VHM", name: "Vinhomes", sector: "Bất động sản", exchange: "HOSE" },
    { ticker: "NVL", name: "Novaland", sector: "Bất động sản", exchange: "HOSE" },
    { ticker: "PDR", name: "Phát Đạt", sector: "Bất động sản", exchange: "HOSE" },
    { ticker: "DXG", name: "Đất Xanh Group", sector: "Bất động sản", exchange: "HOSE" },
    { ticker: "KDH", name: "Khang Điền", sector: "Bất động sản", exchange: "HOSE" },
    { ticker: "DIG", name: "DIC Corp", sector: "Bất động sản", exchange: "HOSE" },
    { ticker: "VRE", name: "Vincom Retail", sector: "Bất động sản", exchange: "HOSE" },
    { ticker: "CEO", name: "CEO Group", sector: "Bất động sản", exchange: "HOSE" },
    { ticker: "AGG", name: "An Gia Corp", sector: "Bất động sản", exchange: "HOSE" },
    { ticker: "MWG", name: "Thế Giới Di Động", sector: "Bán lẻ", exchange: "HOSE" },
    { ticker: "PNJ", name: "Phú Nhuận Jewelry", sector: "Bán lẻ", exchange: "HOSE" },
    { ticker: "FRT", name: "FPT Retail", sector: "Bán lẻ", exchange: "HOSE" },
    { ticker: "DGW", name: "Digiworld", sector: "Bán lẻ", exchange: "HOSE" },
    { ticker: "MSN", name: "Masan Group", sector: "Tiêu dùng", exchange: "HOSE" },
    { ticker: "VNM", name: "Vinamilk", sector: "Tiêu dùng", exchange: "HOSE" },
    { ticker: "SAB", name: "Sabeco", sector: "Tiêu dùng", exchange: "HOSE" },
    { ticker: "MCH", name: "Masan Consumer", sector: "Tiêu dùng", exchange: "HOSE" },
    { ticker: "QNS", name: "Quảng Ngãi Sugar", sector: "Tiêu dùng", exchange: "HOSE" },
    { ticker: "GAS", name: "PV Gas", sector: "Dầu khí", exchange: "HOSE" },
    { ticker: "PLX", name: "Petrolimex", sector: "Dầu khí", exchange: "HOSE" },
    { ticker: "PVD", name: "PV Drilling", sector: "Dầu khí", exchange: "HOSE" },
    { ticker: "GVR", name: "Vietnam Rubber", sector: "Nông nghiệp", exchange: "HOSE" },
    { ticker: "HNG", name: "HAGL Agrico", sector: "Nông nghiệp", exchange: "HOSE" },
    { ticker: "BAF", name: "BA F Animal Husbandry", sector: "Nông nghiệp", exchange: "HOSE" },
    { ticker: "HAG", name: "HAGL Group", sector: "Nông nghiệp", exchange: "HOSE" },
    { ticker: "VIC", name: "Vingroup", sector: "Đa ngành", exchange: "HOSE" },
    { ticker: "BVH", name: "Bảo Việt Holdings", sector: "Bảo hiểm", exchange: "HOSE" },
    { ticker: "BMI", name: "Bảo Minh Insurance", sector: "Bảo hiểm", exchange: "HOSE" },
    { ticker: "HBC", name: "Hòa Bình Construction", sector: "Xây dựng", exchange: "HOSE" },
    { ticker: "CTD", name: "Coteccons", sector: "Xây dựng", exchange: "HOSE" },
    { ticker: "VCG", name: "Vinaconex", sector: "Xây dựng", exchange: "HOSE" },
    { ticker: "FCN", name: "FECON Corp", sector: "Xây dựng", exchange: "HOSE" },
    { ticker: "DHC", name: "Đông Hải Bến Tre", sector: "Xây dựng", exchange: "HOSE" },
    { ticker: "DHG", name: "DHG Pharma", sector: "Dược phẩm", exchange: "HOSE" },
    { ticker: "IMP", name: "IMEXPHARM", sector: "Dược phẩm", exchange: "HOSE" },
    { ticker: "DBD", name: "Danapha Pharma", sector: "Dược phẩm", exchange: "HOSE" },
    { ticker: "VFS", name: "VinFast Auto", sector: "Ô tô", exchange: "HOSE" },
    { ticker: "HHS", name: "Hoàng Huy Investment", sector: "Ô tô", exchange: "HOSE" },
    { ticker: "VOS", name: "Vietnam Ocean Ship", sector: "Vận tải", exchange: "HOSE" },
    { ticker: "HAH", name: "Hải An Transport", sector: "Vận tải", exchange: "HOSE" },
    { ticker: "GMD", name: "Gemadept", sector: "Vận tải", exchange: "HOSE" },
    { ticker: "VSC", name: "Vietnam Container", sector: "Vận tải", exchange: "HOSE" },
    { ticker: "HVN", name: "Vietnam Airlines", sector: "Hàng không", exchange: "HOSE" },
    { ticker: "VJC", name: "VietJet Air", sector: "Hàng không", exchange: "HOSE" },
    { ticker: "BWE", name: "Binh Duong Water", sector: "Tiện ích", exchange: "HOSE" },
    { ticker: "POW", name: "PV Power", sector: "Năng lượng", exchange: "HOSE" },
    { ticker: "PC1", name: "Power Construction 1", sector: "Năng lượng", exchange: "HOSE" },
    { ticker: "REE", name: "Refrigeration Elec Eng", sector: "Năng lượng", exchange: "HOSE" },
    { ticker: "GEG", name: "Gia Lai Electricity", sector: "Năng lượng", exchange: "HOSE" },
  ];

  // Generate synthetic volume/price/deviation data for each
  return tickers.map((t) => {
    const price = Math.round((20000 + Math.random() * 120000) / 100) * 100;
    const vwap = Math.round(price * (0.96 + Math.random() * 0.08) / 100) * 100;
    const deviation = +((price - vwap) / vwap * 100).toFixed(2);
    const volume = Math.floor(Math.random() * 15_000_000) + 200_000;
    const volSma = Math.floor(volume * (0.5 + Math.random()));
    const alerts = Math.abs(deviation) > 2 ? Math.floor(Math.random() * 4) + 1 : 0;
    return { ...t, price, vwap, deviation, volume, volSma, alerts };
  });
}

const EXCHANGES = ["ALL", "HOSE"];

type SortKey = "ticker" | "deviation" | "volume" | "price";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "10px 14px", fontSize: 12, ...MONO }}>
        <div style={{ color: "#6b7fa3", marginBottom: 6 }}>{label}</div>
        {payload.map((p: any) => (
          <div key={p.dataKey} style={{ color: p.color || "#e2e8f0", marginBottom: 2 }}>
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
  const [search, setSearch] = useState("");
  const [selectedTicker, setSelectedTicker] = useState("VCB");
  const [sector, setSector] = useState("Tất cả");
  const [exchange, setExchange] = useState("HOSE");
  const [sortKey, setSortKey] = useState<SortKey>("deviation");
  const [sortDesc, setSortDesc] = useState(true);
  const [deviationThreshold, setDeviationThreshold] = useState(0);
  const [allTickers, setAllTickers] = useState<VwapTicker[]>(vwapDeviations.filter((item) => item.exchange === "HOSE"));
  const [chartData, setChartData] = useState<VwapPoint[]>(vwapData);
  const [apiStatus, setApiStatus] = useState("Đang đọc realtime API...");
  const [universeCount, setUniverseCount] = useState(vwapDeviations.filter((item) => item.exchange === "HOSE").length);
  const SECTORS = useMemo(() => ["Tất cả", ...Array.from(new Set(allTickers.map((t) => t.sector)))], [allTickers]);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetchRealtimeVwap()
        .then((payload) => {
          if (cancelled) return;
          const tickers = payload.data.filter((item) => item.exchange === "HOSE" || item.exchange === "DNSE");
          setAllTickers(tickers);
          setUniverseCount(payload.universeCount || tickers.length);
          const source = payload.source === "dnse_bronze" ? "DNSE Bronze" : "API polling";
          setApiStatus(`${source} · ${tickers.length}/${payload.universeCount || tickers.length} mã có tick`);
          if (!tickers.find((item) => item.ticker === selectedTicker) && tickers[0]) {
            setSelectedTicker(tickers[0].ticker);
          }
        })
        .catch(() => {
          if (!cancelled) setApiStatus(`Snapshot · ${vwapDeviations.filter((item) => item.exchange === "HOSE").length} mã`);
        });
    };
    load();
    const timer = window.setInterval(load, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [selectedTicker]);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetchRealtimeVwapSeries(selectedTicker)
        .then((points) => {
          if (!cancelled) setChartData(points);
        })
        .catch(() => {
          if (!cancelled) setChartData(vwapData);
        });
    };
    load();
    const timer = window.setInterval(load, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [selectedTicker]);

  const filtered = useMemo(() => {
    return allTickers
      .filter((t) => {
        if (search && !t.ticker.toLowerCase().includes(search.toLowerCase()) && !t.name.toLowerCase().includes(search.toLowerCase())) return false;
        if (sector !== "Tất cả" && t.sector !== sector) return false;
        if (exchange !== "ALL" && t.exchange !== exchange) return false;
        if (deviationThreshold > 0 && Math.abs(t.deviation) < deviationThreshold) return false;
        return true;
      })
      .sort((a, b) => {
        const av = sortKey === "deviation" ? Math.abs(a.deviation) : sortKey === "volume" ? a.volume : sortKey === "price" ? a.price : a.ticker.localeCompare(b.ticker);
        const bv = sortKey === "deviation" ? Math.abs(b.deviation) : sortKey === "volume" ? b.volume : sortKey === "price" ? b.price : b.ticker.localeCompare(a.ticker);
        if (typeof av === "string") return 0;
        return sortDesc ? (bv as number) - (av as number) : (av as number) - (bv as number);
      });
  }, [search, sector, exchange, sortKey, sortDesc, deviationThreshold]);

  const selected = allTickers.find((t) => t.ticker === selectedTicker) || allTickers[0];
  const last = chartData[chartData.length - 1];

  // Stats
  const trackedCount = Math.max(universeCount, allTickers.length);
  const aboveVwap = allTickers.filter((t) => t.deviation > 0).length;
  const belowVwap = allTickers.filter((t) => t.deviation < 0).length;
  const bigDeviation = allTickers.filter((t) => Math.abs(t.deviation) >= 2).length;
  const totalAlerts = allTickers.reduce((a, t) => a + t.alerts, 0);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDesc(!sortDesc);
    else { setSortKey(key); setSortDesc(true); }
  };

  const deviationChartData = chartData.map((d) => ({
    ...d,
    fill: d.deviation >= 0 ? "#00d97e" : "#ff4d6d",
  }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h1 style={{ color: "#e2e8f0", margin: 0, fontSize: 18, fontWeight: 700, ...INTER }}>Realtime VWAP Monitoring</h1>
            <span style={{ display: "flex", alignItems: "center", gap: 4, background: "rgba(0,217,126,0.1)", color: "#00d97e", fontSize: 11, padding: "3px 8px", borderRadius: 4, ...INTER }}>
              <Zap size={11} /> LIVE · {trackedCount} mã
            </span>
          </div>
          <p style={{ color: "#6b7fa3", margin: 0, fontSize: 12, ...INTER }}>Theo dõi VWAP intraday toàn thị trường · {apiStatus}</p>
        </div>
      </div>

      {/* Market KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
        {[
          { label: "Tổng mã theo dõi", value: trackedCount + "", color: "#e2e8f0", sub: `${allTickers.length} mã có tick` },
          { label: "Giá > VWAP", value: aboveVwap + "", color: "#00d97e", sub: `${((aboveVwap / allTickers.length) * 100).toFixed(0)}%` },
          { label: "Giá < VWAP", value: belowVwap + "", color: "#ff4d6d", sub: `${((belowVwap / allTickers.length) * 100).toFixed(0)}%` },
          { label: "Lệch > ±2%", value: bigDeviation + "", color: "#8b5cf6", sub: "cần chú ý" },
          { label: "Alerts phiên này", value: totalAlerts + "", color: "#f59e0b" },
        ].map((kpi) => (
          <div key={kpi.label} style={CARD}>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{kpi.label}</div>
            <div style={{ ...MONO, color: kpi.color, fontSize: 22, fontWeight: 700 }}>{kpi.value}</div>
            {kpi.sub && <div style={{ ...INTER, color: "#6b7fa3", fontSize: 11, marginTop: 2 }}>{kpi.sub}</div>}
          </div>
        ))}
      </div>

      {/* Main layout: Ticker list left | Chart right */}
      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 12, alignItems: "start" }}>

        {/* === LEFT: Ticker list panel === */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {/* Search & filters */}
          <div style={{ ...CARD, padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
            {/* Search */}
            <div style={{ position: "relative" }}>
              <Search size={13} color="#6b7fa3" style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)" }} />
              <input
                placeholder="Tìm mã / tên công ty..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{
                  width: "100%", background: "#0b0f1a", border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 5, color: "#e2e8f0", padding: "7px 10px 7px 28px",
                  fontSize: 12, ...INTER, outline: "none", boxSizing: "border-box",
                }}
              />
            </div>

            {/* Exchange filter */}
            <div style={{ display: "flex", gap: 4 }}>
              {EXCHANGES.map((ex) => (
                <button key={ex} onClick={() => setExchange(ex)} style={{
                  flex: 1, padding: "4px 0", borderRadius: 4,
                  border: `1px solid ${exchange === ex ? "#8b5cf6" : "rgba(255,255,255,0.08)"}`,
                  background: exchange === ex ? "rgba(139,92,246,0.15)" : "transparent",
                  color: exchange === ex ? "#8b5cf6" : "#6b7fa3",
                  fontSize: 11, ...INTER, cursor: "pointer", fontWeight: exchange === ex ? 600 : 400,
                }}>{ex}</button>
              ))}
            </div>

            {/* Sector filter */}
            <select value={sector} onChange={(e) => setSector(e.target.value)} style={{
              background: "#0b0f1a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 5,
              color: "#e2e8f0", padding: "6px 8px", fontSize: 12, ...INTER, cursor: "pointer",
            }}>
              {SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>

            {/* Deviation threshold */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ ...INTER, color: "#6b7fa3", fontSize: 11, whiteSpace: "nowrap" }}>Lệch tối thiểu:</span>
              <div style={{ display: "flex", gap: 4 }}>
                {[0, 1, 2, 3].map((v) => (
                  <button key={v} onClick={() => setDeviationThreshold(v)} style={{
                    padding: "3px 8px", borderRadius: 4, fontSize: 11,
                    border: `1px solid ${deviationThreshold === v ? "#8b5cf6" : "rgba(255,255,255,0.08)"}`,
                    background: deviationThreshold === v ? "rgba(139,92,246,0.15)" : "transparent",
                    color: deviationThreshold === v ? "#8b5cf6" : "#6b7fa3",
                    cursor: "pointer", ...INTER,
                  }}>{v === 0 ? "All" : `±${v}%`}</button>
                ))}
              </div>
            </div>

            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 11 }}>{filtered.length} mã phù hợp</div>
          </div>

          {/* Table header */}
          <div style={{ ...CARD, padding: "0 0 8px 0", overflow: "hidden" }}>
            {/* Sort header */}
            <div style={{
              display: "grid", gridTemplateColumns: "52px 1fr 72px 64px",
              padding: "8px 10px", borderBottom: "1px solid rgba(255,255,255,0.07)", gap: 4,
            }}>
              {[
                { label: "Mã", key: "ticker" as SortKey },
                { label: "Tên", key: null },
                { label: "Lệch%", key: "deviation" as SortKey },
                { label: "Vol", key: "volume" as SortKey },
              ].map((col) => (
                <button key={col.label} onClick={col.key ? () => handleSort(col.key!) : undefined} style={{
                  background: "transparent", border: "none", cursor: col.key ? "pointer" : "default",
                  color: sortKey === col.key ? "#8b5cf6" : "#6b7fa3",
                  fontSize: 10, ...INTER, textTransform: "uppercase", letterSpacing: "0.05em",
                  fontWeight: 500, textAlign: "left", padding: 0,
                  display: "flex", alignItems: "center", gap: 3,
                }}>
                  {col.label}
                  {col.key && <ArrowUpDown size={9} />}
                </button>
              ))}
            </div>

            {/* Ticker rows — scrollable */}
            <div style={{ maxHeight: 460, overflowY: "auto", overflowX: "hidden" }}>
              {filtered.map((t) => {
                const isSelected = t.ticker === selectedTicker;
                return (
                  <div key={`${t.ticker}-${t.sector}`}
                    onClick={() => setSelectedTicker(t.ticker)}
                    style={{
                      display: "grid", gridTemplateColumns: "52px 1fr 72px 64px",
                      padding: "7px 10px", gap: 4, cursor: "pointer",
                      background: isSelected ? "rgba(139,92,246,0.12)" : "transparent",
                      borderLeft: isSelected ? "2px solid #8b5cf6" : "2px solid transparent",
                      borderBottom: "1px solid rgba(255,255,255,0.03)",
                      transition: "background 0.1s",
                    }}
                    onMouseEnter={(e) => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.03)"; }}
                    onMouseLeave={(e) => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                  >
                    <span style={{ color: isSelected ? "#8b5cf6" : "#e2e8f0", fontSize: 12, fontWeight: 700, ...MONO }}>{t.ticker}</span>
                    <span style={{ color: "#6b7fa3", fontSize: 11, ...INTER, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.name}</span>
                    <span style={{
                      color: t.deviation >= 0 ? "#00d97e" : "#ff4d6d",
                      fontSize: 11, ...MONO, fontWeight: 600, textAlign: "right",
                      display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 2,
                    }}>
                      {t.deviation >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                      {t.deviation >= 0 ? "+" : ""}{t.deviation.toFixed(2)}%
                    </span>
                    <span style={{ color: "#6b7fa3", fontSize: 10, ...MONO, textAlign: "right" }}>
                      {(t.volume / 1_000_000).toFixed(1)}M
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* === RIGHT: Chart panel === */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Selected ticker header */}
          <div style={{ ...CARD, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ ...MONO, color: "#8b5cf6", fontSize: 20, fontWeight: 700 }}>{selected.ticker}</span>
                  <span style={{ background: "rgba(59,130,246,0.15)", color: "#3b82f6", fontSize: 11, padding: "2px 8px", borderRadius: 3, ...INTER }}>{selected.exchange}</span>
                  <span style={{ background: "rgba(255,255,255,0.06)", color: "#6b7fa3", fontSize: 11, padding: "2px 8px", borderRadius: 3, ...INTER }}>{selected.sector}</span>
                </div>
                <div style={{ ...INTER, color: "#6b7fa3", fontSize: 12, marginTop: 2 }}>{selected.name}</div>
              </div>
            </div>
            <div style={{ display: "flex", gap: 20 }}>
              {[
                { label: "Giá hiện tại", value: selected.price.toLocaleString("vi-VN") + "đ", color: "#e2e8f0" },
                { label: "Session VWAP", value: selected.vwap.toLocaleString("vi-VN") + "đ", color: "#3b82f6" },
                { label: "Lệch VWAP", value: (selected.deviation >= 0 ? "+" : "") + selected.deviation.toFixed(2) + "%", color: selected.deviation >= 0 ? "#00d97e" : "#ff4d6d" },
                { label: "Volume", value: (selected.volume / 1_000_000).toFixed(2) + "M", color: "#e2e8f0" },
              ].map((k) => (
                <div key={k.label}>
                  <div style={{ ...INTER, color: "#6b7fa3", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>{k.label}</div>
                  <div style={{ ...MONO, color: k.color, fontSize: 15, fontWeight: 700 }}>{k.value}</div>
                </div>
              ))}
            </div>
            <button onClick={() => onNavigate("stock", selected.ticker)} style={{
              padding: "6px 14px", borderRadius: 5, border: "1px solid rgba(139,92,246,0.4)",
              background: "rgba(139,92,246,0.1)", color: "#8b5cf6",
              fontSize: 12, ...INTER, cursor: "pointer",
            }}>Xem Stock Detail →</button>
          </div>

          {/* Price vs VWAP chart */}
          <div style={CARD}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <span style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>Giá theo phút vs Session VWAP</span>
              <div style={{ display: "flex", gap: 16 }}>
                {[{ label: "Giá", color: "#e2e8f0" }, { label: "VWAP 1min", color: "#8b5cf6" }, { label: "Session VWAP", color: "#3b82f6" }].map((l) => (
                  <div key={l.label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <div style={{ width: 20, height: 2, background: l.color }} />
                    <span style={{ ...INTER, color: "#6b7fa3", fontSize: 11 }}>{l.label}</span>
                  </div>
                ))}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <ComposedChart data={chartData} margin={{ left: 10, right: 20 }}>
                <XAxis dataKey="time" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
                <YAxis domain={["auto", "auto"]} tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} width={70} tickFormatter={(v) => v.toLocaleString("vi-VN")} />
                <Tooltip content={<CustomTooltip />} />
                <Line type="monotone" dataKey="price" stroke="#e2e8f0" strokeWidth={2} dot={false} name="Giá" />
                <Line type="monotone" dataKey="vwap" stroke="#8b5cf6" strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="VWAP 1min" />
                <Line type="monotone" dataKey="sessionVwap" stroke="#3b82f6" strokeWidth={1.5} dot={false} strokeDasharray="3 3" name="Session VWAP" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Volume + Deviation row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div style={CARD}>
              <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Khối lượng theo phút</div>
              <ResponsiveContainer width="100%" height={120}>
                <BarChart data={chartData} margin={{ left: 10, right: 10 }}>
                  <XAxis dataKey="time" tick={{ fill: "#6b7fa3", fontSize: 9, ...MONO }} axisLine={false} tickLine={false} interval={3} />
                  <YAxis tick={{ fill: "#6b7fa3", fontSize: 9, ...MONO }} axisLine={false} tickLine={false} tickFormatter={(v) => (v / 1000).toFixed(0) + "K"} />
                  <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 11, ...MONO }} formatter={(v: any) => [(v / 1000).toFixed(0) + "K", "Volume"]} />
                  <Bar dataKey="volume" fill="#3b82f6" opacity={0.7} radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div style={CARD}>
              <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                Lệch Session VWAP (%)
                <span style={{ marginLeft: 8, ...INTER, color: "#6b7fa3", fontSize: 11, fontWeight: 400 }}>Ngưỡng cảnh báo: ±2%</span>
              </div>
              <ResponsiveContainer width="100%" height={120}>
                <ComposedChart data={deviationChartData} margin={{ left: 10, right: 10 }}>
                  <XAxis dataKey="time" tick={{ fill: "#6b7fa3", fontSize: 9, ...MONO }} axisLine={false} tickLine={false} interval={3} />
                  <YAxis tick={{ fill: "#6b7fa3", fontSize: 9, ...MONO }} axisLine={false} tickLine={false} tickFormatter={(v) => v + "%"} />
                  <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 11, ...MONO }} formatter={(v: any) => [v.toFixed(2) + "%", "Lệch"]} />
                  <ReferenceLine y={2} stroke="#ff4d6d" strokeDasharray="3 3" strokeWidth={1} />
                  <ReferenceLine y={-2} stroke="#ff4d6d" strokeDasharray="3 3" strokeWidth={1} />
                  <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeWidth={1} />
                  <Bar dataKey="deviation" radius={[2, 2, 0, 0]}>
                    {deviationChartData.map((d, i) => <Cell key={`dev-${i}-${d.time}`} fill={d.deviation >= 0 ? "#00d97e" : "#ff4d6d"} opacity={0.75} />)}
                  </Bar>
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top deviations mini table */}
          <div style={CARD}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <Bell size={14} color="#8b5cf6" />
              <span style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>Top lệch VWAP mạnh nhất toàn thị trường</span>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                    {["Mã CK", "Tên", "Ngành", "Giá", "VWAP", "Lệch %", "Volume", "Alerts"].map((h) => (
                      <th key={h} style={{ color: "#6b7fa3", fontSize: 10, textAlign: "left", padding: "5px 10px", ...INTER, textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 500, whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...allTickers].sort((a, b) => Math.abs(b.deviation) - Math.abs(a.deviation)).slice(0, 8).map((r) => (
                    <tr key={r.ticker} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}
                      onClick={() => setSelectedTicker(r.ticker)}
                      onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.03)"}
                      onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}
                    >
                      <td style={{ padding: "8px 10px" }}><span style={{ color: "#8b5cf6", fontSize: 12, fontWeight: 700, ...MONO }}>{r.ticker}</span></td>
                      <td style={{ padding: "8px 10px", color: "#e2e8f0", fontSize: 11, ...INTER }}>{r.name}</td>
                      <td style={{ padding: "8px 10px" }}>
                        <span style={{ background: "rgba(59,130,246,0.1)", color: "#3b82f6", fontSize: 10, padding: "2px 6px", borderRadius: 3, ...INTER }}>{r.sector}</span>
                      </td>
                      <td style={{ padding: "8px 10px", color: "#e2e8f0", fontSize: 11, ...MONO, textAlign: "right" }}>{r.price.toLocaleString("vi-VN")}</td>
                      <td style={{ padding: "8px 10px", color: "#3b82f6", fontSize: 11, ...MONO, textAlign: "right" }}>{r.vwap.toLocaleString("vi-VN")}</td>
                      <td style={{ padding: "8px 10px", textAlign: "right" }}>
                        <span style={{
                          background: r.deviation >= 0 ? "rgba(0,217,126,0.1)" : "rgba(255,77,109,0.1)",
                          color: r.deviation >= 0 ? "#00d97e" : "#ff4d6d",
                          fontSize: 12, ...MONO, padding: "2px 8px", borderRadius: 4, fontWeight: 700,
                        }}>{r.deviation >= 0 ? "+" : ""}{r.deviation.toFixed(2)}%</span>
                      </td>
                      <td style={{ padding: "8px 10px", color: "#6b7fa3", fontSize: 11, ...MONO, textAlign: "right" }}>{(r.volume / 1_000_000).toFixed(2)}M</td>
                      <td style={{ padding: "8px 10px", textAlign: "center" }}>
                        {r.alerts > 0
                          ? <span style={{ background: "rgba(245,158,11,0.1)", color: "#f59e0b", fontSize: 11, ...MONO, padding: "2px 8px", borderRadius: 3, fontWeight: 600 }}>{r.alerts}</span>
                          : <span style={{ color: "#6b7fa3", fontSize: 11, ...MONO }}>—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
