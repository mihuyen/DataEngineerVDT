import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { alertHistory as mockAlertHistory, alertsByDay as mockAlertsByDay, alertsByCondition as mockAlertsByCondition } from "./mockData";
import { Bell, CheckCircle, XCircle, Clock } from "lucide-react";
import { fetchAlerts, AlertEvent, AlertByDay, AlertByCondition } from "./api";
import { AlertRules } from "./AlertRules";

const CARD: React.CSSProperties = { background: "#111827", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: 16 };
const MONO: React.CSSProperties = { fontFamily: "JetBrains Mono, monospace" };
const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };

const CONDITION_LABELS: Record<string, string> = {
  RSI_ABOVE: "RSI Quá mua", RSI_BELOW: "RSI Quá bán",
  BB_BREAK: "Bollinger Break", VWAP_DEVIATION: "VWAP Lệch",
  PRICE_ABOVE: "Giá vượt ngưỡng", PRICE_BELOW: "Giá dưới ngưỡng",
  INTRADAY_VOLUME_SPIKE: "KL đột biến", INTRADAY_BREAKOUT: "Breakout phiên",
  STOP_LOSS: "Cắt lỗ", TAKE_PROFIT: "Chốt lời",
  VWAP_CROSS_UP: "Cắt lên VWAP", VWAP_CROSS_DOWN: "Cắt xuống VWAP",
  RSI_CROSS_UP: "RSI cắt lên", RSI_CROSS_DOWN: "RSI cắt xuống",
};
const CONDITION_COLORS: Record<string, string> = {
  RSI_ABOVE: "#ff4d6d", RSI_BELOW: "#00d97e",
  BB_BREAK: "#8b5cf6", VWAP_DEVIATION: "#a855f7",
  PRICE_ABOVE: "#3b82f6", PRICE_BELOW: "#06b6d4",
  INTRADAY_VOLUME_SPIKE: "#06b6d4", INTRADAY_BREAKOUT: "#f59e0b",
  STOP_LOSS: "#ff4d6d", TAKE_PROFIT: "#00d97e",
  VWAP_CROSS_UP: "#00d97e", VWAP_CROSS_DOWN: "#ff4d6d",
  RSI_CROSS_UP: "#00d97e", RSI_CROSS_DOWN: "#ff4d6d",
};

const StatusIcon = ({ status }: { status: string }) => {
  if (status === "sent") return <CheckCircle size={13} color="#00d97e" />;
  if (status === "failed") return <XCircle size={13} color="#ff4d6d" />;
  return <Clock size={13} color="#6b7fa3" />;
};

interface AlertHistoryProps { onNavigate: (page: string, ticker?: string) => void; initialTicker?: string; }

export function AlertHistory({ onNavigate, initialTicker }: AlertHistoryProps) {
  const [tab, setTab] = useState<"rules" | "history">("rules");
  const [filterCondition, setFilterCondition] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterChannel, setFilterChannel] = useState("all");
  const [alertHistory, setAlertHistory] = useState<AlertEvent[]>(mockAlertHistory);
  const [alertsByDay, setAlertsByDay] = useState<AlertByDay[]>(mockAlertsByDay);
  const [alertsByCondition, setAlertsByCondition] = useState<AlertByCondition[]>(mockAlertsByCondition);
  const [apiStatus, setApiStatus] = useState("Snapshot local");

  useEffect(() => {
    let cancelled = false;
    fetchAlerts()
      .then((payload) => {
        if (cancelled) return;
        setAlertHistory(payload.data);
        setAlertsByDay(payload.byDay);
        setAlertsByCondition(payload.byCondition);
        setApiStatus("ClickHouse live query");
      })
      .catch(() => {
        if (!cancelled) setApiStatus("Snapshot local");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = alertHistory.filter((a) => {
    if (filterCondition !== "all" && a.condition !== filterCondition) return false;
    if (filterStatus !== "all" && a.status !== filterStatus) return false;
    if (filterChannel !== "all" && a.channel !== filterChannel) return false;
    return true;
  });

  const totalSent = alertHistory.filter((a) => a.status === "sent").length;
  const totalFailed = alertHistory.filter((a) => a.status === "failed").length;
  const totalSkipped = alertHistory.filter((a) => a.status === "skipped").length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <h1 style={{ color: "#e2e8f0", margin: 0, fontSize: 18, fontWeight: 700, ...INTER }}>Quản lý cảnh báo</h1>
          <Bell size={16} color="#8b5cf6" />
        </div>
        <p style={{ color: "#6b7fa3", margin: 0, fontSize: 12, ...INTER }}>Tạo quy tắc và xem lịch sử gửi · {apiStatus}</p>
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        {[{ id: "rules" as const, label: "Quy tắc đang theo dõi" }, { id: "history" as const, label: "Lịch sử gửi" }].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "6px 16px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.1)",
              background: tab === t.id ? "#8b5cf6" : "transparent",
              color: tab === t.id ? "#0b0f1a" : "#6b7fa3", fontSize: 13, ...INTER, cursor: "pointer",
              fontWeight: tab === t.id ? 600 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "rules" && <AlertRules onNavigate={onNavigate} initialTicker={initialTicker} />}

      {tab === "history" && <>
      {alertHistory.length === 0 && apiStatus === "ClickHouse live query" && (
        <div style={{ ...CARD, borderColor: "rgba(245,158,11,0.2)", background: "rgba(245,158,11,0.04)" }}>
          <div style={{ ...INTER, color: "#6b7fa3", fontSize: 12, lineHeight: 1.6 }}>
            Bảng <span style={{ color: "#e2e8f0", ...MONO }}>fact_alert_event</span> hiện chưa có dữ liệu — Alert Engine chưa được vận hành (chỉ mới có schema).
          </div>
        </div>
      )}

      {/* KPI */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
        {[
          { label: "Tổng cảnh báo", value: alertHistory.length, color: "#e2e8f0" },
          { label: "Đã gửi", value: totalSent, color: "#00d97e" },
          { label: "Lỗi gửi", value: totalFailed, color: "#ff4d6d" },
          { label: "Bỏ qua (spam)", value: totalSkipped, color: "#6b7fa3" },
          { label: "Mã active", value: new Set(alertHistory.map((a) => a.ticker)).size, color: "#8b5cf6" },
        ].map((kpi) => (
          <div key={kpi.label} style={CARD}>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{kpi.label}</div>
            <div style={{ ...MONO, color: kpi.color, fontSize: 24, fontWeight: 700 }}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
        <div style={CARD}>
          <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Số cảnh báo theo ngày</div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={alertsByDay} margin={{ left: 10, right: 10 }}>
              <XAxis dataKey="date" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any) => [v, "Cảnh báo"]} />
              <Bar dataKey="total" fill="#8b5cf6" radius={[3, 3, 0, 0]} opacity={0.85} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={CARD}>
          <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Phân loại theo điều kiện</div>
          <ResponsiveContainer width="100%" height={140}>
            <PieChart>
              <Pie data={alertsByCondition} cx="50%" cy="50%" outerRadius={58} innerRadius={32} dataKey="count">
                {alertsByCondition.map((entry) => <Cell key={`alert-cond-${entry.type}`} fill={entry.fill} />)}
              </Pie>
              <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any, name: any) => [v, name]} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
            {alertsByCondition.map((c) => (
              <div key={c.type} style={{ display: "flex", alignItems: "center", gap: 3 }}>
                <div style={{ width: 7, height: 7, borderRadius: 1, background: c.fill, flexShrink: 0 }} />
                <span style={{ color: "#6b7fa3", fontSize: 10, ...INTER }}>{c.type.replace("_", " ")}: <span style={{ color: c.fill }}>{c.count}</span></span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        {/* Condition filter */}
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ ...INTER, color: "#6b7fa3", fontSize: 11, whiteSpace: "nowrap" }}>Điều kiện:</span>
          <select value={filterCondition} onChange={(e) => setFilterCondition(e.target.value)}
            style={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 5, color: "#e2e8f0", padding: "5px 8px", fontSize: 12, ...INTER, cursor: "pointer" }}>
            <option value="all">Tất cả</option>
            {Object.entries(CONDITION_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>

        {/* Status filter */}
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ ...INTER, color: "#6b7fa3", fontSize: 11, whiteSpace: "nowrap" }}>Trạng thái:</span>
          {["all", "sent", "failed", "skipped"].map((s) => {
            const labels: Record<string, string> = { all: "Tất cả", sent: "Đã gửi", failed: "Lỗi", skipped: "Bỏ qua" };
            const colors: Record<string, string> = { all: "#6b7fa3", sent: "#00d97e", failed: "#ff4d6d", skipped: "#6b7fa3" };
            return (
              <button key={s} onClick={() => setFilterStatus(s)} style={{
                padding: "4px 10px", borderRadius: 4,
                border: `1px solid ${filterStatus === s ? colors[s] : "rgba(255,255,255,0.1)"}`,
                background: filterStatus === s ? `${colors[s]}18` : "transparent",
                color: filterStatus === s ? colors[s] : "#6b7fa3",
                fontSize: 11, ...INTER, cursor: "pointer", fontWeight: filterStatus === s ? 600 : 400,
              }}>{labels[s]}</button>
            );
          })}
        </div>

        {/* Channel filter */}
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ ...INTER, color: "#6b7fa3", fontSize: 11, whiteSpace: "nowrap" }}>Kênh:</span>
          {["all", "TELEGRAM", "EMAIL"].map((c) => (
            <button key={c} onClick={() => setFilterChannel(c)} style={{
              padding: "4px 10px", borderRadius: 4,
              border: `1px solid ${filterChannel === c ? "#8b5cf6" : "rgba(255,255,255,0.1)"}`,
              background: filterChannel === c ? "rgba(245,158,11,0.1)" : "transparent",
              color: filterChannel === c ? "#8b5cf6" : "#6b7fa3",
              fontSize: 11, ...INTER, cursor: "pointer", fontWeight: filterChannel === c ? 600 : 400,
            }}>{c === "all" ? "Tất cả" : c}</button>
          ))}
        </div>

        <span style={{ marginLeft: "auto", ...INTER, color: "#6b7fa3", fontSize: 12 }}>{filtered.length} cảnh báo</span>
      </div>

      {/* Alert table */}
      <div style={CARD}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                {["#", "Thời điểm KT", "User", "Mã CK", "Điều kiện", "Ngưỡng", "Giá trị TT", "Kênh", "Trạng thái", "Sent At", "Cooldown"].map((h) => (
                  <th key={h} style={{ color: "#6b7fa3", fontSize: 10, textAlign: "left", padding: "6px 10px", ...INTER, textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 500, whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((a) => {
                const condColor = CONDITION_COLORS[a.condition] || "#6b7fa3";
                return (
                  <tr key={a.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}
                    onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.03)"}
                    onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}
                  >
                    <td style={{ padding: "9px 10px", color: "#6b7fa3", fontSize: 11, ...MONO }}>{a.id}</td>
                    <td style={{ padding: "9px 10px", color: "#e2e8f0", fontSize: 12, ...MONO, whiteSpace: "nowrap" }}>{a.triggeredAt}</td>
                    <td style={{ padding: "9px 10px" }}>
                      <span style={{ background: "rgba(255,255,255,0.06)", color: "#6b7fa3", fontSize: 11, padding: "2px 8px", borderRadius: 3, ...MONO }}>{a.user}</span>
                    </td>
                    <td style={{ padding: "9px 10px", cursor: "pointer" }} onClick={() => onNavigate("stock", a.ticker)}>
                      <span style={{ color: "#8b5cf6", fontSize: 13, fontWeight: 700, ...MONO }}>{a.ticker}</span>
                    </td>
                    <td style={{ padding: "9px 10px" }}>
                      <span style={{ background: `${condColor}18`, color: condColor, fontSize: 11, padding: "2px 8px", borderRadius: 3, ...INTER, fontWeight: 600, whiteSpace: "nowrap" }}>
                        {CONDITION_LABELS[a.condition] || a.condition}
                      </span>
                    </td>
                    <td style={{ padding: "9px 10px", color: "#6b7fa3", fontSize: 12, ...MONO, textAlign: "right" }}>
                      {a.threshold !== 0 ? a.threshold.toLocaleString("vi-VN") : "—"}
                    </td>
                    <td style={{ padding: "9px 10px", textAlign: "right" }}>
                      <span style={{ color: condColor, fontSize: 12, ...MONO, fontWeight: 600 }}>
                        {typeof a.actual === "number" ? (Math.abs(a.actual) < 10 ? a.actual.toFixed(1) : a.actual.toLocaleString("vi-VN")) : a.actual}
                      </span>
                    </td>
                    <td style={{ padding: "9px 10px" }}>
                      <span style={{
                        background: a.channel === "TELEGRAM" ? "rgba(59,130,246,0.1)" : "rgba(245,158,11,0.1)",
                        color: a.channel === "TELEGRAM" ? "#3b82f6" : "#8b5cf6",
                        fontSize: 11, padding: "2px 8px", borderRadius: 3, ...INTER,
                      }}>{a.channel}</span>
                    </td>
                    <td style={{ padding: "9px 10px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <StatusIcon status={a.status} />
                        <span style={{
                          color: a.status === "sent" ? "#00d97e" : a.status === "failed" ? "#ff4d6d" : "#6b7fa3",
                          fontSize: 11, ...INTER, fontWeight: 600, textTransform: "capitalize",
                        }}>
                          {a.status === "sent" ? "Đã gửi" : a.status === "failed" ? "Lỗi" : "Bỏ qua"}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: "9px 10px", color: "#6b7fa3", fontSize: 11, ...MONO }}>{a.sentAt || "—"}</td>
                    <td style={{ padding: "9px 10px", color: "#6b7fa3", fontSize: 11, ...MONO, textAlign: "center" }}>{a.cooldown}min</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Anti-spam explanation */}
      <div style={{ ...CARD, borderColor: "rgba(245,158,11,0.2)", background: "rgba(245,158,11,0.04)" }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
          <Bell size={16} color="#8b5cf6" style={{ marginTop: 2, flexShrink: 0 }} />
          <div>
            <div style={{ ...INTER, color: "#8b5cf6", fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Cơ chế chống spam Alert Engine</div>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 12, lineHeight: 1.6 }}>
              Mỗi cảnh báo được kiểm tra điều kiện <span style={{ color: "#e2e8f0", ...MONO }}>user_id + ticker + condition_type</span> trong vòng <span style={{ color: "#e2e8f0", ...MONO }}>cooldown_minutes</span> gần nhất trước khi gửi.
              Nếu đã tồn tại bản ghi tương tự trong <span style={{ color: "#e2e8f0", ...MONO }}>fact_alert_event</span>, cảnh báo sẽ bị bỏ qua và ghi trạng thái <span style={{ color: "#6b7fa3", ...MONO }}>skipped</span>.
              Điều này giúp ngăn spam mà vẫn giữ đầy đủ lịch sử kiểm toán.
            </div>
          </div>
        </div>
      </div>
      </>}
    </div>
  );
}
