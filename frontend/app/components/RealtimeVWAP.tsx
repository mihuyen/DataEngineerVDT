import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  ArrowUpDown,
  Bell,
  CircleAlert,
  Clock3,
  Search,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import {
  RealtimeVwapPayload,
  VwapPoint,
  VwapTicker,
  fetchRealtimeVwap,
  fetchRealtimeVwapSeries,
} from "./api";

const CARD: React.CSSProperties = {
  background: "#111827",
  border: "1px solid rgba(255,255,255,0.07)",
  borderRadius: 8,
  padding: 16,
};
const MONO: React.CSSProperties = { fontFamily: "JetBrains Mono, monospace" };
const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };

type SortKey = "ticker" | "deviation" | "volume" | "price";

const EMPTY_META: RealtimeVwapPayload = {
  count: 0,
  activeCount: 0,
  universeCount: 0,
  subscribedCount: 0,
  marketStatus: "closed",
  statusLabel: "Đang tải trạng thái phiên",
  isLive: false,
  isFresh: false,
  dataMode: "REAL",
  dataProvider: "DNSE",
  data: [],
};

function formatPrice(value: number): string {
  return value.toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatVolume(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString("vi-VN");
}

function formatTimestamp(value?: string): string {
  if (!value) return "Chưa có";
  return value.replace("T", " ").slice(0, 19);
}

function statusPresentation(meta: RealtimeVwapPayload, hasError: boolean) {
  if (hasError) return { label: "Mất kết nối", color: "#ff4d6d", bg: "rgba(255,77,109,0.12)" };
  if (meta.marketStatus === "live" && !meta.isFresh) {
    return { label: "Dữ liệu gián đoạn", color: "#ff4d6d", bg: "rgba(255,77,109,0.12)" };
  }
  if (meta.marketStatus === "live") {
    return { label: "LIVE", color: "#00d97e", bg: "rgba(0,217,126,0.12)" };
  }
  if (meta.marketStatus === "lunch_break") {
    return { label: "Nghỉ giữa phiên", color: "#f59e0b", bg: "rgba(245,158,11,0.12)" };
  }
  if (meta.marketStatus === "pre_open") {
    return { label: "Chưa mở cửa", color: "#3b82f6", bg: "rgba(59,130,246,0.12)" };
  }
  return { label: "Đã đóng cửa", color: "#94a3b8", bg: "rgba(148,163,184,0.12)" };
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "#1e2535",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 6,
        padding: "10px 14px",
        fontSize: 12,
        ...MONO,
      }}
    >
      <div style={{ color: "#6b7fa3", marginBottom: 6 }}>{label}</div>
      {payload.map((item: any) => (
        <div key={item.dataKey} style={{ color: item.color || "#e2e8f0", marginBottom: 2 }}>
          {item.name}: {typeof item.value === "number" ? item.value.toLocaleString("vi-VN") : item.value}
        </div>
      ))}
    </div>
  );
};

interface RealtimeVWAPProps {
  onNavigate: (page: string, ticker?: string) => void;
}

export function RealtimeVWAP({ onNavigate }: RealtimeVWAPProps) {
  const [search, setSearch] = useState("");
  const [selectedTicker, setSelectedTicker] = useState("");
  const [sector, setSector] = useState("Tất cả");
  const [sortKey, setSortKey] = useState<SortKey>("deviation");
  const [sortDesc, setSortDesc] = useState(true);
  const [deviationThreshold, setDeviationThreshold] = useState(0);
  const [allTickers, setAllTickers] = useState<VwapTicker[]>([]);
  const [chartData, setChartData] = useState<VwapPoint[]>([]);
  const [meta, setMeta] = useState<RealtimeVwapPayload>(EMPTY_META);
  const [connectionError, setConnectionError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    const load = async () => {
      let nextDelay = 60_000;
      try {
        const payload = await fetchRealtimeVwap();
        if (cancelled) return;
        const tickers = payload.data.filter((item) => item.exchange === "HOSE" || item.exchange === "DNSE");
        setMeta(payload);
        setAllTickers(tickers);
        setConnectionError(false);
        setSelectedTicker((current) =>
          tickers.some((item) => item.ticker === current) ? current : tickers[0]?.ticker || "",
        );
        nextDelay = payload.marketStatus === "live" ? 5_000 : 60_000;
      } catch {
        if (!cancelled) setConnectionError(true);
        nextDelay = 15_000;
      } finally {
        if (!cancelled) {
          setLoading(false);
          timer = window.setTimeout(load, nextDelay);
        }
      }
    };

    load();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    if (!selectedTicker) {
      setChartData([]);
      return;
    }
    let cancelled = false;
    let timer: number | undefined;

    const load = async () => {
      try {
        const points = await fetchRealtimeVwapSeries(selectedTicker);
        if (!cancelled) setChartData(points);
      } catch {
        if (!cancelled) setChartData([]);
      } finally {
        if (!cancelled) {
          timer = window.setTimeout(load, meta.marketStatus === "live" ? 5_000 : 60_000);
        }
      }
    };

    setChartData([]);
    load();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [selectedTicker, meta.marketStatus]);

  const sectors = useMemo(
    () => ["Tất cả", ...Array.from(new Set(allTickers.map((item) => item.sector)))],
    [allTickers],
  );

  const filtered = useMemo(() => {
    return allTickers
      .filter((item) => {
        const query = search.toLowerCase();
        if (query && !item.ticker.toLowerCase().includes(query) && !item.name.toLowerCase().includes(query)) {
          return false;
        }
        if (sector !== "Tất cả" && item.sector !== sector) return false;
        return deviationThreshold === 0 || Math.abs(item.deviation) >= deviationThreshold;
      })
      .sort((left, right) => {
        if (sortKey === "ticker") {
          return sortDesc ? right.ticker.localeCompare(left.ticker) : left.ticker.localeCompare(right.ticker);
        }
        const leftValue = sortKey === "deviation" ? Math.abs(left.deviation) : left[sortKey];
        const rightValue = sortKey === "deviation" ? Math.abs(right.deviation) : right[sortKey];
        return sortDesc ? rightValue - leftValue : leftValue - rightValue;
      });
  }, [allTickers, deviationThreshold, search, sector, sortDesc, sortKey]);

  const selected = allTickers.find((item) => item.ticker === selectedTicker);
  const aboveVwap = allTickers.filter((item) => item.deviation > 0).length;
  const belowVwap = allTickers.filter((item) => item.deviation < 0).length;
  const bigDeviation = allTickers.filter((item) => Math.abs(item.deviation) >= 2).length;
  const status = statusPresentation(meta, connectionError);
  const deviationChartData = chartData.map((item) => ({
    ...item,
    fill: item.deviation >= 0 ? "#00d97e" : "#ff4d6d",
  }));

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDesc((value) => !value);
    else {
      setSortKey(key);
      setSortDesc(true);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="vwap-header" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <h1 style={{ color: "#e2e8f0", margin: 0, fontSize: 18, fontWeight: 700, ...INTER }}>
              VWAP theo phiên
            </h1>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                background: status.bg,
                color: status.color,
                fontSize: 11,
                padding: "3px 8px",
                borderRadius: 4,
                ...INTER,
              }}
            >
              {meta.marketStatus === "live" && meta.isFresh ? <Activity size={11} /> : <Clock3 size={11} />}
              {status.label}
            </span>
          </div>
          <p style={{ color: "#6b7fa3", margin: "5px 0 0", fontSize: 12, ...INTER }}>
            Cập nhật cuối {formatTimestamp(meta.latestMinute)}
          </p>
        </div>
        {connectionError && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#ff4d6d", fontSize: 12, ...INTER }}>
            <CircleAlert size={14} /> API không phản hồi
          </div>
        )}
      </div>

      <div className="vwap-kpis" style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(120px, 1fr))", gap: 12 }}>
        {[
          { label: "Universe HOSE", value: meta.universeCount || 0, sub: "mã trong danh mục", color: "#e2e8f0" },
          { label: "Đã subscribe", value: meta.subscribedCount || 0, sub: "mã đăng ký DNSE", color: "#3b82f6" },
          { label: "Có tick trong phiên", value: meta.activeCount || allTickers.length, sub: "chỉ tính dữ liệu thật", color: "#8b5cf6" },
          { label: "Trên / dưới VWAP", value: `${aboveVwap} / ${belowVwap}`, sub: "theo giá khớp cuối", color: "#00d97e" },
          { label: "Lệch ít nhất 2%", value: bigDeviation, sub: "cần theo dõi", color: "#f59e0b" },
        ].map((item) => (
          <div key={item.label} style={CARD}>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 10, textTransform: "uppercase", marginBottom: 4 }}>
              {item.label}
            </div>
            <div style={{ ...MONO, color: item.color, fontSize: 22, fontWeight: 700 }}>{item.value}</div>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 11, marginTop: 2 }}>{item.sub}</div>
          </div>
        ))}
      </div>

      {!loading && allTickers.length === 0 ? (
        <div style={{ ...CARD, minHeight: 280, display: "grid", placeItems: "center", textAlign: "center" }}>
          <div>
            <CircleAlert size={24} color="#6b7fa3" />
            <div style={{ color: "#e2e8f0", fontSize: 14, marginTop: 10, ...INTER }}>Chưa có tick DNSE hợp lệ</div>
            <div style={{ color: "#6b7fa3", fontSize: 12, marginTop: 4, ...INTER }}>
              {meta.statusLabel || "Dữ liệu sẽ xuất hiện khi nguồn realtime hoạt động"}
            </div>
          </div>
        </div>
      ) : (
        <div className="vwap-workspace" style={{ display: "grid", gridTemplateColumns: "minmax(280px, 340px) minmax(0, 1fr)", gap: 12, alignItems: "start" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ ...CARD, padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ position: "relative" }}>
                <Search size={13} color="#6b7fa3" style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)" }} />
                <input
                  placeholder="Tìm mã hoặc tên công ty"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  style={{
                    width: "100%",
                    background: "#0b0f1a",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 5,
                    color: "#e2e8f0",
                    padding: "7px 10px 7px 28px",
                    fontSize: 12,
                    ...INTER,
                    outline: "none",
                    boxSizing: "border-box",
                  }}
                />
              </div>
              <select
                value={sector}
                onChange={(event) => setSector(event.target.value)}
                style={{ background: "#0b0f1a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 5, color: "#e2e8f0", padding: "6px 8px", fontSize: 12, ...INTER }}
              >
                {sectors.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <span style={{ ...INTER, color: "#6b7fa3", fontSize: 11 }}>Lệch tối thiểu</span>
                <div style={{ display: "flex", gap: 4 }}>
                  {[0, 1, 2, 3].map((value) => (
                    <button
                      key={value}
                      onClick={() => setDeviationThreshold(value)}
                      style={{
                        padding: "3px 8px",
                        borderRadius: 4,
                        fontSize: 11,
                        border: `1px solid ${deviationThreshold === value ? "#8b5cf6" : "rgba(255,255,255,0.08)"}`,
                        background: deviationThreshold === value ? "rgba(139,92,246,0.15)" : "transparent",
                        color: deviationThreshold === value ? "#8b5cf6" : "#6b7fa3",
                        cursor: "pointer",
                        ...INTER,
                      }}
                    >
                      {value === 0 ? "Tất cả" : `±${value}%`}
                    </button>
                  ))}
                </div>
              </div>
              <div style={{ ...INTER, color: "#6b7fa3", fontSize: 11 }}>{filtered.length} mã có dữ liệu phù hợp</div>
            </div>

            <div style={{ ...CARD, padding: 0, overflow: "hidden" }}>
              <div style={{ display: "grid", gridTemplateColumns: "52px 1fr 70px 58px", padding: "8px 10px", borderBottom: "1px solid rgba(255,255,255,0.07)", gap: 4 }}>
                {[
                  { label: "Mã", key: "ticker" as SortKey },
                  { label: "Tên", key: null },
                  { label: "Lệch", key: "deviation" as SortKey },
                  { label: "KL", key: "volume" as SortKey },
                ].map((column) => (
                  <button
                    key={column.label}
                    onClick={column.key ? () => handleSort(column.key) : undefined}
                    style={{ background: "transparent", border: "none", color: sortKey === column.key ? "#8b5cf6" : "#6b7fa3", fontSize: 10, ...INTER, textTransform: "uppercase", textAlign: "left", padding: 0, display: "flex", alignItems: "center", gap: 3, cursor: column.key ? "pointer" : "default" }}
                  >
                    {column.label}{column.key && <ArrowUpDown size={9} />}
                  </button>
                ))}
              </div>
              <div style={{ maxHeight: 460, overflowY: "auto" }}>
                {filtered.map((item) => {
                  const isSelected = item.ticker === selectedTicker;
                  return (
                    <button
                      key={item.ticker}
                      onClick={() => setSelectedTicker(item.ticker)}
                      style={{
                        width: "100%",
                        display: "grid",
                        gridTemplateColumns: "52px 1fr 70px 58px",
                        padding: "8px 10px",
                        gap: 4,
                        background: isSelected ? "rgba(139,92,246,0.12)" : "transparent",
                        border: "none",
                        borderLeft: isSelected ? "2px solid #8b5cf6" : "2px solid transparent",
                        borderBottom: "1px solid rgba(255,255,255,0.03)",
                        cursor: "pointer",
                        textAlign: "left",
                      }}
                    >
                      <span style={{ color: isSelected ? "#8b5cf6" : "#e2e8f0", fontSize: 12, fontWeight: 700, ...MONO }}>{item.ticker}</span>
                      <span style={{ color: "#6b7fa3", fontSize: 11, ...INTER, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.name}</span>
                      <span style={{ color: item.deviation >= 0 ? "#00d97e" : "#ff4d6d", fontSize: 11, ...MONO, textAlign: "right" }}>
                        {item.deviation >= 0 ? "+" : ""}{item.deviation.toFixed(2)}%
                      </span>
                      <span style={{ color: "#6b7fa3", fontSize: 10, ...MONO, textAlign: "right" }}>{formatVolume(item.volume)}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {selected && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ ...CARD, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ ...MONO, color: "#8b5cf6", fontSize: 20, fontWeight: 700 }}>{selected.ticker}</span>
                    <span style={{ background: "rgba(59,130,246,0.15)", color: "#3b82f6", fontSize: 11, padding: "2px 8px", borderRadius: 3, ...INTER }}>HOSE</span>
                    <span style={{ color: "#6b7fa3", fontSize: 11, ...INTER }}>{formatTimestamp(selected.updatedAt)}</span>
                  </div>
                  <div style={{ ...INTER, color: "#6b7fa3", fontSize: 12, marginTop: 2 }}>{selected.name}</div>
                </div>
                <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
                  {[
                    { label: "Giá khớp cuối", value: formatPrice(selected.price), color: "#e2e8f0" },
                    { label: "VWAP phiên", value: formatPrice(selected.sessionVwap), color: "#3b82f6" },
                    { label: "Lệch VWAP", value: `${selected.deviation >= 0 ? "+" : ""}${selected.deviation.toFixed(2)}%`, color: selected.deviation >= 0 ? "#00d97e" : "#ff4d6d" },
                    { label: "KL lũy kế", value: formatVolume(selected.volume), color: "#e2e8f0" },
                  ].map((item) => (
                    <div key={item.label}>
                      <div style={{ ...INTER, color: "#6b7fa3", fontSize: 10, textTransform: "uppercase" }}>{item.label}</div>
                      <div style={{ ...MONO, color: item.color, fontSize: 15, fontWeight: 700 }}>{item.value}</div>
                    </div>
                  ))}
                </div>
                <button onClick={() => onNavigate("stock", selected.ticker)} style={{ padding: "6px 12px", borderRadius: 5, border: "1px solid rgba(139,92,246,0.4)", background: "rgba(139,92,246,0.1)", color: "#8b5cf6", fontSize: 12, ...INTER, cursor: "pointer" }}>
                  Chi tiết cổ phiếu
                </button>
              </div>

              <div style={CARD}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, gap: 8, flexWrap: "wrap" }}>
                  <span style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>Giá và VWAP trong phiên</span>
                  <span style={{ ...INTER, color: "#6b7fa3", fontSize: 11 }}>Đơn vị giá: nghìn đồng</span>
                </div>
                {chartData.length ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <ComposedChart data={chartData} margin={{ left: 10, right: 20 }}>
                      <XAxis dataKey="time" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
                      <YAxis domain={["auto", "auto"]} tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} width={60} />
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey="price" stroke="#e2e8f0" strokeWidth={2} dot={false} name="Giá" />
                      <Line type="monotone" dataKey="vwap" stroke="#8b5cf6" strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="VWAP phút" />
                      <Line type="monotone" dataKey="sessionVwap" stroke="#3b82f6" strokeWidth={1.5} dot={false} strokeDasharray="3 3" name="VWAP phiên" />
                    </ComposedChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ height: 220, display: "grid", placeItems: "center", color: "#6b7fa3", fontSize: 12, ...INTER }}>Không có chuỗi phút cho mã này</div>
                )}
              </div>

              <div className="vwap-secondary-charts" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div style={CARD}>
                  <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Khối lượng theo phút</div>
                  <ResponsiveContainer width="100%" height={130}>
                    <BarChart data={chartData}>
                      <XAxis dataKey="time" tick={{ fill: "#6b7fa3", fontSize: 9, ...MONO }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: "#6b7fa3", fontSize: 9, ...MONO }} axisLine={false} tickLine={false} tickFormatter={formatVolume} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="volume" fill="#3b82f6" opacity={0.7} radius={[2, 2, 0, 0]} name="Khối lượng" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div style={CARD}>
                  <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Lệch VWAP phiên (%)</div>
                  <ResponsiveContainer width="100%" height={130}>
                    <ComposedChart data={deviationChartData}>
                      <XAxis dataKey="time" tick={{ fill: "#6b7fa3", fontSize: 9, ...MONO }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: "#6b7fa3", fontSize: 9, ...MONO }} axisLine={false} tickLine={false} tickFormatter={(value) => `${value}%`} />
                      <Tooltip content={<CustomTooltip />} />
                      <ReferenceLine y={2} stroke="#f59e0b" strokeDasharray="3 3" />
                      <ReferenceLine y={-2} stroke="#f59e0b" strokeDasharray="3 3" />
                      <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" />
                      <Bar dataKey="deviation" name="Lệch VWAP">
                        {deviationChartData.map((item) => <Cell key={`${item.time}-${item.deviation}`} fill={item.fill} opacity={0.75} />)}
                      </Bar>
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div style={CARD}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                  <Bell size={14} color="#8b5cf6" />
                  <span style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>Lệch VWAP mạnh nhất trong phiên</span>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                        {["Mã", "Tên", "Ngành", "Giá cuối", "VWAP phiên", "Lệch", "KL lũy kế", "Cập nhật"].map((heading) => (
                          <th key={heading} style={{ color: "#6b7fa3", fontSize: 10, textAlign: "left", padding: "6px 10px", ...INTER, textTransform: "uppercase", fontWeight: 500, whiteSpace: "nowrap" }}>{heading}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {[...allTickers].sort((left, right) => Math.abs(right.deviation) - Math.abs(left.deviation)).slice(0, 8).map((item) => (
                        <tr key={item.ticker} onClick={() => setSelectedTicker(item.ticker)} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }}>
                          <td style={{ padding: "8px 10px", color: "#8b5cf6", fontSize: 12, fontWeight: 700, ...MONO }}>{item.ticker}</td>
                          <td style={{ padding: "8px 10px", color: "#e2e8f0", fontSize: 11, ...INTER }}>{item.name}</td>
                          <td style={{ padding: "8px 10px", color: "#6b7fa3", fontSize: 11, ...INTER }}>{item.sector}</td>
                          <td style={{ padding: "8px 10px", color: "#e2e8f0", fontSize: 11, textAlign: "right", ...MONO }}>{formatPrice(item.price)}</td>
                          <td style={{ padding: "8px 10px", color: "#3b82f6", fontSize: 11, textAlign: "right", ...MONO }}>{formatPrice(item.sessionVwap)}</td>
                          <td style={{ padding: "8px 10px", color: item.deviation >= 0 ? "#00d97e" : "#ff4d6d", fontSize: 11, textAlign: "right", fontWeight: 700, ...MONO }}>{item.deviation >= 0 ? "+" : ""}{item.deviation.toFixed(2)}%</td>
                          <td style={{ padding: "8px 10px", color: "#6b7fa3", fontSize: 11, textAlign: "right", ...MONO }}>{formatVolume(item.volume)}</td>
                          <td style={{ padding: "8px 10px", color: "#6b7fa3", fontSize: 10, whiteSpace: "nowrap", ...MONO }}>{formatTimestamp(item.updatedAt).slice(11)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
