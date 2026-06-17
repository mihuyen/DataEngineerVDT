import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import { dagStatus, dataQualityErrors, ingestHistory, kafkaLag } from "./mockData";
import { CheckCircle, XCircle, Loader, AlertTriangle, Database, Server, Activity, HardDrive } from "lucide-react";

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

const ServiceCard = ({ name, status, metric, unit, icon }: { name: string; status: string; metric: string; unit: string; icon: React.ReactNode }) => {
  const up = status === "healthy";
  return (
    <div style={{ ...CARD, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#6b7fa3" }}>{icon}<span style={{ ...INTER, fontSize: 12 }}>{name}</span></div>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: up ? "#00d97e" : "#ff4d6d" }} />
      </div>
      <div style={{ ...MONO, color: up ? "#00d97e" : "#ff4d6d", fontSize: 20, fontWeight: 700 }}>{metric}</div>
      <div style={{ ...INTER, color: "#6b7fa3", fontSize: 11 }}>{unit}</div>
    </div>
  );
};

export function PipelineMonitor() {
  const successCount = dagStatus.filter((d) => d.status === "success").length;
  const failedCount = dagStatus.filter((d) => d.status === "failed").length;
  const runningCount = dagStatus.filter((d) => d.status === "running").length;
  const totalErrors = dataQualityErrors.reduce((acc, e) => acc + e.count, 0);
  const latestIngestRecords = ingestHistory[ingestHistory.length - 1]?.records ?? 0;
  const latestLag = kafkaLag[kafkaLag.length - 1]?.lag ?? 0;
  const formatRecords = (n: number) => n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : `${(n / 1000).toFixed(0)}K`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div>
        <h1 style={{ color: "#e2e8f0", margin: 0, fontSize: 18, fontWeight: 700, ...INTER }}>Data Pipeline Monitor</h1>
        <p style={{ color: "#6b7fa3", margin: 0, fontSize: 12, ...INTER }}>Giám sát pipeline & chất lượng dữ liệu từ ClickHouse snapshot</p>
      </div>

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
        {[
          { label: "DAG thành công", value: successCount, color: "#00d97e", bg: "rgba(0,217,126,0.08)" },
          { label: "DAG thất bại", value: failedCount, color: "#ff4d6d", bg: "rgba(255,77,109,0.08)" },
          { label: "DAG đang chạy", value: runningCount, color: "#8b5cf6", bg: "rgba(245,158,11,0.08)" },
          { label: "Lỗi GX Validation", value: totalErrors, color: "#ff4d6d", bg: "rgba(255,77,109,0.08)" },
          { label: "Bản ghi ingest mới nhất", value: formatRecords(latestIngestRecords), color: "#3b82f6", bg: "rgba(59,130,246,0.08)" },
          { label: "Kafka Consumer Lag", value: `${latestLag}ms`, color: "#00d97e", bg: "rgba(0,217,126,0.08)" },
        ].map((kpi) => (
          <div key={kpi.label} style={{ ...CARD, background: kpi.bg, borderColor: `${kpi.color}30` }}>
            <div style={{ ...INTER, color: "#6b7fa3", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{kpi.label}</div>
            <div style={{ ...MONO, color: kpi.color, fontSize: 24, fontWeight: 700 }}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Service health */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
        <ServiceCard name="Kafka" status="healthy" metric={`${latestLag}ms`} icon={<Activity size={14} />} unit="lag từ bảng realtime VWAP" />
        <ServiceCard name="ClickHouse" status="healthy" metric={`${dagStatus.reduce((acc, d) => acc + d.records, 0).toLocaleString("vi-VN")}`} icon={<Database size={14} />} unit="bản ghi trong Gold snapshot" />
        <ServiceCard name="MinIO" status="healthy" metric="OK" icon={<HardDrive size={14} />} unit="raw/silver objects đã ingest" />
        <ServiceCard name="Airflow" status="healthy" metric={`${dagStatus.length}/${dagStatus.length}`} icon={<Server size={14} />} unit="pipeline snapshot" />
        <ServiceCard name="Realtime" status="healthy" metric={formatRecords(latestIngestRecords)} icon={<Activity size={14} />} unit="records phiên mới nhất" />
      </div>

      {/* Charts row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {/* Ingest volume */}
        <div style={CARD}>
          <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Bản ghi ingest theo ngày</div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={ingestHistory} margin={{ left: 10, right: 10 }}>
              <XAxis dataKey="date" tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#6b7fa3", fontSize: 10, ...MONO }} axisLine={false} tickLine={false} tickFormatter={(v) => (v / 1000).toFixed(0) + "K"} />
              <Tooltip contentStyle={{ background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", fontSize: 12, ...MONO }} formatter={(v: any) => [(v / 1000).toFixed(0) + "K", "Records"]} />
              <Bar dataKey="records" fill="#3b82f6" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Kafka lag */}
        <div style={CARD}>
          <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Kafka Consumer Lag (ms)</div>
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

      {/* Storage health */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        {[
          { layer: "Bronze (Raw)", used: 850, total: 3000, color: "#8b5cf6" },
          { layer: "Silver (Cleaned)", used: 420, total: 2000, color: "#3b82f6" },
          { layer: "Gold (Aggregated)", used: 180, total: 1000, color: "#00d97e" },
        ].map((s) => (
          <div key={s.layer} style={CARD}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ ...INTER, color: "#e2e8f0", fontSize: 12, fontWeight: 600 }}>{s.layer}</span>
              <span style={{ ...MONO, color: "#6b7fa3", fontSize: 12 }}>{s.used}GB / {s.total}GB</span>
            </div>
            <div style={{ height: 8, background: "rgba(255,255,255,0.06)", borderRadius: 4, overflow: "hidden", marginBottom: 6 }}>
              <div style={{ width: `${(s.used / s.total) * 100}%`, height: "100%", background: s.color, borderRadius: 4, transition: "width 0.5s" }} />
            </div>
            <div style={{ ...MONO, color: s.color, fontSize: 11 }}>{((s.used / s.total) * 100).toFixed(1)}% used</div>
          </div>
        ))}
      </div>
    </div>
  );
}
