import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { AlertRule, createAlertRule, deleteAlertRule, fetchAlertRules, setAlertRuleActive } from "./api";

const CARD: React.CSSProperties = { background: "#111827", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: 16 };
const MONO: React.CSSProperties = { fontFamily: "JetBrains Mono, monospace" };
const INTER: React.CSSProperties = { fontFamily: "Inter, sans-serif" };

const CONDITION_LABELS: Record<string, string> = {
  PRICE_ABOVE: "Giá vượt ngưỡng",
  PRICE_BELOW: "Giá dưới ngưỡng",
  RSI_ABOVE: "RSI quá mua",
  RSI_BELOW: "RSI quá bán",
  BB_BREAK: "Vượt Bollinger Band",
  VWAP_DEVIATION: "Lệch VWAP (%)",
  INTRADAY_VOLUME_SPIKE: "Khối lượng đột biến (x lần TB 20p)",
  INTRADAY_BREAKOUT: "Breakout trong phiên (% vượt biên 20p)",
};

const FIELD_INPUT: React.CSSProperties = {
  background: "#1e2535", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 5,
  color: "#e2e8f0", padding: "7px 10px", fontSize: 12, ...INTER, outline: "none",
};

interface AlertRulesProps {
  onNavigate: (page: string, ticker?: string) => void;
  initialTicker?: string;
}

export function AlertRules({ onNavigate, initialTicker }: AlertRulesProps) {
  const [rules, setRules] = useState<AlertRule[] | null>(null);
  const [error, setError] = useState(false);
  const [form, setForm] = useState({
    ticker: initialTicker || "",
    conditionType: "PRICE_ABOVE",
    thresholdValue: "",
    channel: "TELEGRAM",
    cooldownMinutes: "60",
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = () => {
    fetchAlertRules()
      .then((payload) => {
        setRules(payload.data);
        setError(false);
      })
      .catch(() => {
        setRules([]);
        setError(true);
      });
  };

  useEffect(load, []);

  const submit = () => {
    const ticker = form.ticker.trim().toUpperCase();
    const thresholdValue = Number(form.thresholdValue);
    const cooldownMinutes = Number(form.cooldownMinutes);
    if (!ticker || !Number.isFinite(thresholdValue) || !Number.isFinite(cooldownMinutes) || cooldownMinutes <= 0) {
      setFormError("Nhập mã, ngưỡng và cooldown hợp lệ.");
      return;
    }
    setFormError(null);
    setSaving(true);
    createAlertRule({ ticker, conditionType: form.conditionType, thresholdValue, channel: form.channel, cooldownMinutes })
      .then(() => {
        setForm({ ...form, ticker: "", thresholdValue: "" });
        load();
      })
      .catch(() => setFormError("Không tạo được cảnh báo."))
      .finally(() => setSaving(false));
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={CARD}>
        <div style={{ ...INTER, color: "#e2e8f0", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Tạo cảnh báo mới</div>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
          <input
            value={form.ticker}
            onChange={(e) => setForm({ ...form, ticker: e.target.value })}
            placeholder="Mã CK (hoặc ALL)"
            style={{ ...FIELD_INPUT, width: 130 }}
          />
          <select value={form.conditionType} onChange={(e) => setForm({ ...form, conditionType: e.target.value })} style={{ ...FIELD_INPUT, width: 180, cursor: "pointer" }}>
            {Object.entries(CONDITION_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <input
            value={form.thresholdValue}
            onChange={(e) => setForm({ ...form, thresholdValue: e.target.value })}
            placeholder="Ngưỡng"
            type="number"
            style={{ ...FIELD_INPUT, width: 100 }}
          />
          <select value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value })} style={{ ...FIELD_INPUT, width: 110, cursor: "pointer" }}>
            <option value="TELEGRAM">Telegram</option>
            <option value="EMAIL">Email</option>
          </select>
          <input
            value={form.cooldownMinutes}
            onChange={(e) => setForm({ ...form, cooldownMinutes: e.target.value })}
            placeholder="Cooldown (phút)"
            type="number"
            style={{ ...FIELD_INPUT, width: 130 }}
          />
          <button
            onClick={submit}
            disabled={saving}
            style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 14px", borderRadius: 5, border: "none", background: "#8b5cf6", color: "#0b0f1a", fontSize: 12, ...INTER, cursor: "pointer", fontWeight: 600 }}
          >
            <Plus size={14} /> Tạo
          </button>
        </div>
        {formError && <div style={{ color: "#ff4d6d", fontSize: 11, marginTop: 8, ...INTER }}>{formError}</div>}
      </div>

      {error && (
        <div style={{ ...CARD, borderColor: "rgba(255,77,109,0.2)", background: "rgba(255,77,109,0.04)" }}>
          <span style={{ color: "#ff4d6d", fontSize: 12, ...INTER }}>Không kết nối được API cảnh báo.</span>
        </div>
      )}

      <div style={CARD}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
              {["Mã", "Điều kiện", "Ngưỡng", "Kênh", "Cooldown", "Trạng thái", ""].map((h) => (
                <th key={h} style={{ color: "#6b7fa3", fontSize: 11, textAlign: h === "Mã" ? "left" : "right", padding: "6px 10px", ...INTER, textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(rules ?? []).map((rule) => (
              <tr key={rule.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <td style={{ padding: "9px 10px", ...MONO, color: "#8b5cf6", fontWeight: 700, fontSize: 12, cursor: rule.ticker !== "ALL" ? "pointer" : "default" }} onClick={() => rule.ticker !== "ALL" && onNavigate("stock", rule.ticker)}>
                  {rule.ticker}
                </td>
                <td style={{ padding: "9px 10px", textAlign: "right", ...INTER, color: "#e2e8f0", fontSize: 12 }}>{CONDITION_LABELS[rule.conditionType] || rule.conditionType}</td>
                <td style={{ padding: "9px 10px", textAlign: "right", ...MONO, color: "#6b7fa3", fontSize: 12 }}>{rule.thresholdValue}</td>
                <td style={{ padding: "9px 10px", textAlign: "right" }}>
                  <span style={{ background: rule.channel === "TELEGRAM" ? "rgba(59,130,246,0.1)" : "rgba(245,158,11,0.1)", color: rule.channel === "TELEGRAM" ? "#3b82f6" : "#8b5cf6", fontSize: 11, padding: "2px 8px", borderRadius: 3, ...INTER }}>{rule.channel}</span>
                </td>
                <td style={{ padding: "9px 10px", textAlign: "right", ...MONO, color: "#6b7fa3", fontSize: 12 }}>{rule.cooldownMinutes}min</td>
                <td style={{ padding: "9px 10px", textAlign: "right" }}>
                  <button
                    onClick={() => setAlertRuleActive(rule.id, !rule.isActive).then(load)}
                    style={{
                      padding: "3px 10px", borderRadius: 4, border: "none", cursor: "pointer",
                      background: rule.isActive ? "rgba(0,217,126,0.12)" : "rgba(107,127,163,0.12)",
                      color: rule.isActive ? "#00d97e" : "#6b7fa3", fontSize: 11, ...INTER, fontWeight: 600,
                    }}
                  >
                    {rule.isActive ? "Đang chạy" : "Tạm dừng"}
                  </button>
                </td>
                <td style={{ padding: "9px 10px", textAlign: "right" }}>
                  <button
                    onClick={() => deleteAlertRule(rule.id).then(load)}
                    style={{ background: "none", border: "none", cursor: "pointer", color: "#6b7fa3", display: "inline-flex" }}
                    title="Xoá cảnh báo"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
            {rules && rules.length === 0 && (
              <tr>
                <td colSpan={7} style={{ padding: "20px 10px", color: "#6b7fa3", fontSize: 12, ...INTER, textAlign: "center" }}>
                  Chưa có quy tắc cảnh báo nào. Tạo ở form phía trên.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
