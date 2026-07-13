import { useEffect, useState } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import { CheckCircle, XCircle, Loader, AlertTriangle, CircleAlert } from "lucide-react";
import { fetchPipelineStatus, DagStatusRow, DataQualityError, IngestHistoryPoint, KafkaLagPoint } from "./api";

const CARD: React.CSSProperties = { background: "#111827", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: 16 };
const MONO: React.CSSProperties = { fontFamily: "JetBrains Mono, monospace" };
const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };

const StatusBadge = ({ status }: { status: string }) => {
  const cfg: Record<string, { color: string; bg: string; icon: React.ReactNode }> = {
    success: { color: "#00d97e", bg: "rgba(0,217,126,0.1)", icon: <CheckCircle size={12} /> },
    failed: { color: "#ff4d6d", bg: "rgba(255,77,109,0.1)", icon: <XCircle size={12} /> },
    running: { color: "#8b5cf6", bg: "rgba(245,158,11,0.1)", icon: <Loader size={12} /> },
  };
  const c = cfg[status] || cfg.success;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, background: c.bg, color: c.color, fontSize: 11, padding: "3px 8px", borderRadius: 4, ...INTER, fontWeight: 600 }}>
      {c.icon}{status.toUpperCase()}
    </span>
  );
};

export function PipelineMonitor() {
  const [dagStatus, setDagStatus] = useState<DagStatusRow[]>([]);
  const [dataQualityErrors, setDataQualityErrors] = useState<DataQualityError[]>([]);
  const [ingestHistory, setIngestHistory] = useState<IngestHistoryPoint[]>([]);
  const [kafkaLag, setKafkaLag] = useState<KafkaLagPoint[]>([]);
  const [apiStatus, setApiStatus] = useState("Đang tải...");
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetchPipelineStatus()
        .then((payload) => {
          if (cancelled) return;
          setDagStatus(payload.dagStatus);
          setDataQualityErrors(payload.dataQualityErrors);
          setIngestHistory(payload.ingestHistory);
          setKafkaLag(payload.kafkaLag);
          setApiStatus(
            payload.dagStatusSource === "airflow"
              ? "Airflow REST API trực tiếp"
              : "ClickHouse (Airflow không phản hồi)"
          );
          setError(false);
          setLoaded(true);
        })
        .catch(() => {
          if (cancelled) return;
          // No mock fallback here: showing stale/fake numbers when the API
          // is actually down would look identical to a healthy pipeline,
          // which defeats the point of a monitoring page.
          setError(true);
          setLoaded(true);
        });
    };
    load();
    const timer = window.setInterval(load, 60000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  if (!loaded) {
    return <div style={CARD}>Đang tải trạng thái pipeline...</div>;
  }

  if (error) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <h1 style={{ color: "#e2e8f0", margin: 0, fontSize: 18, fontWeight: 700, ...INTER }}>Giám sát pipeline dữ liệu</h1>
        </div>
        <div style={{ ...CARD, borderColor: "rgba(255,77,109,0.2)", background: "rgba(255,77,109,0.04)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#ff4d6d" }}>
            <CircleAlert size={16} />
            <span style={{ ...INTER, fontSize: 13, fontWeight: 600 }}>Không kết nối được API giám sát pipeline.</span>
          </div>
          <div style={{ ...INTER, color: "#6b7fa3", fontSize: 12, marginTop: 6 }}>
            Kiểm tra dashboard_api hoặc ClickHouse có đang chạy không. Trang sẽ tự thử lại mỗi 60 giây.
          </div>
        </div>
      </div>
    );
  }

  const successCount = dagStatus.filter((d) => d.status === "success").length;
  const failedCount = dagStatus.filter((d) => d.status === "failed").length;
  const runningCount = dagStatus.filter((d) => d.status === "running").length;
  const totalErrors = dataQualityErrors.reduce((acc, e) => acc + e.count, 0);
  const latestIngestRecords = ingestHistory[ingestHistory.length - 1]?.records ?? 0;
  const latestLag = kafkaLag[kafkaLag.length - 1]?.lag ?? 0;
  const formatRecords = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return `${n}`;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div>
        <h1 style={{ color: "#e2e8f0", margin: 0, fontSize: 18, fontWeight: 700, ...INTER }}>Giám sát pipeline dữ liệu</h1>
        <p style={{ color: "#6b7fa3", margin: 0, fontSize: 12, ...INTER }}>Giám sát pipeline & chất lượng dữ liệu · {apiStatus}</p>
      </div>

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
        {[
          { label: "DAG thành công", value: successCount, color: "#00d97e", bg: "rgba(0,217,126,0.08)" },
          { label: "DAG thất bại", value: failedCount, color: "#ff4d6d", bg: "rgba(255,77,109,0.08)" },
          { label: "DAG đang chạy", value: runningCount, color: "#8b5cf6", bg: "rgba(245,158,11,0.08)" },
          { label: "Lỗi GX Validation", value: totalErrors, color: "#ff4d6d", bg: "rgba(255,77,109,0.08)" },
          { label: "Bản ghi ingest mới nhất", value: formatRecords(latestIngestRecords), color: "#3b82f6", bg: "rgba(59,130,246,0.08)" },
          { label: "Độ trễ VWAP (proxy)", value: `${latestLag}ms`, color: "#00d97e", bg: "rgba(0,217,126,0.08)" },
        ].map((kpi) => (
          <div key={kpi.label} style={{ ...CARD, background: kpi.bg, borderColor: `${kpi.color}30` }}>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{kpi.label}</div>
            <div style={{ ...MONO, color: kpi.color, fontSize: 24, fontWeight: 700 }}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {/* Ingest volume */}
        <div style={CARD}>
          <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Bản ghi ingest theo ngày</div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={ingestHistory} margin={{ left: 10, right: 10 }}>
              <XAxis dataKey="date" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} tickFormatter={formatRecords} />
              <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any) => [formatRecords(v), "Records"]} />
              <Bar dataKey="records" fill="#3b82f6" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Kafka lag */}
        <div style={CARD}>
          <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Khoảng cách giữa các phút VWAP (ms, proxy cho độ trễ)</div>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={kafkaLag} margin={{ left: 10, right: 10 }}>
              <XAxis dataKey="time" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} interval={3} />
              <YAxis tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any) => [v + "ms", "Lag"]} />
              <Line type="monotone" dataKey="lag" stroke="#8b5cf6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* DAG table */}
      <div style={CARD}>
        <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Trạng thái DAG Pipeline</div>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
              {["DAG Name", "Status", "Last Run", "Duration", "Records", "Tasks", "Lỗi"].map((h) => (
                <th key={h} style={{ color: "#6b7fa3", fontSize: 11, textAlign: "left", padding: "6px 10px", ...INTER, textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dagStatus.map((dag) => (
              <tr key={dag.dag} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}
                onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.03)"}
                onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.background = "transparent"}
              >
                <td style={{ padding: "9px 10px" }}>
                  <span style={{ color: dag.status === "failed" ? "#ff4d6d" : "#e2e8f0", fontSize: 12, ...MONO }}>{dag.dag}</span>
                </td>
                <td style={{ padding: "9px 10px" }}><StatusBadge status={dag.status} /></td>
                <td style={{ padding: "9px 10px", color: "#6b7fa3", fontSize: 12, ...MONO }}>{dag.lastRun}</td>
                <td style={{ padding: "9px 10px", color: "#6b7fa3", fontSize: 12, ...MONO }}>{dag.duration}</td>
                <td style={{ padding: "9px 10px", color: "#3b82f6", fontSize: 12, ...MONO, textAlign: "right" }}>
                  {dag.records > 0 ? (dag.records / 1000).toFixed(0) + "K" : "—"}
                </td>
                <td style={{ padding: "9px 10px", color: "#6b7fa3", fontSize: 12, ...MONO, textAlign: "center" }}>{dag.tasks}</td>
                <td style={{ padding: "9px 10px", textAlign: "center" }}>
                  {dag.failed > 0
                    ? <span style={{ color: "#ff4d6d", fontSize: 12, ...MONO, fontWeight: 700 }}>{dag.failed}</span>
                    : <span style={{ color: "#00d97e", fontSize: 12, ...MONO }}>0</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Data Quality errors */}
      <div style={CARD}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <AlertTriangle size={16} color="#ff4d6d" />
          <span style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600 }}>Data Quality Issues (Great Expectations + dbt)</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10 }}>
          {dataQualityErrors.length === 0 && (
            <div style={{ gridColumn: "1 / -1", background: "rgba(0,217,126,0.06)", border: "1px solid rgba(0,217,126,0.2)", borderRadius: 6, padding: "12px 14px" }}>
              <div style={{ ...MONO, color: "#00d97e", fontSize: 18, fontWeight: 700, marginBottom: 4 }}>0</div>
              <div style={{ ...INTER, color: "#e2e8f0", fontSize: 12 }}>Không có lỗi chất lượng dữ liệu trong snapshot hiện tại</div>
            </div>
          )}
          {dataQualityErrors.map((e, i) => (
            <div key={i} style={{ background: "rgba(255,77,109,0.06)", border: "1px solid rgba(255,77,109,0.2)", borderRadius: 6, padding: "12px 14px" }}>
              <div style={{ ...MONO, color: "#ff4d6d", fontSize: 22, fontWeight: 700, marginBottom: 4 }}>{e.count}</div>
              <div style={{ ...INTER, color: "#e2e8f0", fontSize: 12, marginBottom: 2 }}>{e.type}</div>
              <div style={{ ...MONO, color: "#6b7fa3", fontSize: 10 }}>{e.table} · {e.date}</div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
