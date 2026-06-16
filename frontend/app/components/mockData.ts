// Mock data for Vietnam Stock Market Dashboard

export const vnIndexHistory = [
  { time: "09:15", value: 1248.5 }, { time: "09:30", value: 1251.2 },
  { time: "09:45", value: 1249.8 }, { time: "10:00", value: 1255.3 },
  { time: "10:15", value: 1260.1 }, { time: "10:30", value: 1258.7 },
  { time: "10:45", value: 1263.4 }, { time: "11:00", value: 1267.9 },
  { time: "11:15", value: 1265.2 }, { time: "11:30", value: 1270.5 },
  { time: "13:00", value: 1268.3 }, { time: "13:15", value: 1272.1 },
  { time: "13:30", value: 1275.8 }, { time: "13:45", value: 1273.4 },
  { time: "14:00", value: 1278.2 }, { time: "14:15", value: 1281.6 },
  { time: "14:30", value: 1279.3 }, { time: "14:45", value: 1283.7 },
];

export const topGainers = [
  { ticker: "VCB", name: "Vietcombank", price: 88200, change: 4200, pct: 5.0, volume: 3450000, sector: "Ngân hàng" },
  { ticker: "FPT", name: "FPT Corporation", price: 115600, change: 5200, pct: 4.71, volume: 2980000, sector: "Công nghệ" },
  { ticker: "HPG", name: "Hòa Phát Group", price: 26800, change: 1100, pct: 4.28, volume: 12500000, sector: "Thép" },
  { ticker: "MWG", name: "Thế Giới Di Động", price: 49700, change: 1900, pct: 3.98, volume: 1870000, sector: "Bán lẻ" },
  { ticker: "VIC", name: "Vingroup", price: 41500, change: 1500, pct: 3.75, volume: 4100000, sector: "Bất động sản" },
  { ticker: "GVR", name: "VRG", price: 17200, change: 600, pct: 3.62, volume: 6700000, sector: "Nông nghiệp" },
  { ticker: "BVH", name: "Bảo Việt", price: 51300, change: 1700, pct: 3.43, volume: 890000, sector: "Bảo hiểm" },
  { ticker: "PNJ", name: "Phú Nhuận Jewelry", price: 72400, change: 2300, pct: 3.28, volume: 750000, sector: "Bán lẻ" },
  { ticker: "ACB", name: "ACB Bank", price: 24100, change: 700, pct: 2.99, volume: 8200000, sector: "Ngân hàng" },
  { ticker: "STB", name: "Sacombank", price: 28600, change: 800, pct: 2.88, volume: 7300000, sector: "Ngân hàng" },
];

export const topLosers = [
  { ticker: "DXG", name: "Đất Xanh Group", price: 15300, change: -800, pct: -4.97, volume: 3200000, sector: "Bất động sản" },
  { ticker: "NVL", name: "Novaland", price: 14200, change: -700, pct: -4.70, volume: 9800000, sector: "Bất động sản" },
  { ticker: "PDR", name: "Phát Đạt", price: 28400, change: -1300, pct: -4.38, volume: 2400000, sector: "Bất động sản" },
  { ticker: "DIG", name: "DIC Corp", price: 22100, change: -900, pct: -3.91, volume: 4100000, sector: "Xây dựng" },
  { ticker: "KDH", name: "Khang Điền", price: 31700, change: -1200, pct: -3.65, volume: 1700000, sector: "Bất động sản" },
  { ticker: "VHM", name: "Vinhomes", price: 38200, change: -1400, pct: -3.53, volume: 5600000, sector: "Bất động sản" },
  { ticker: "MSN", name: "Masan Group", price: 67800, change: -2300, pct: -3.28, volume: 1900000, sector: "Tiêu dùng" },
  { ticker: "VRE", name: "Vincom Retail", price: 22500, change: -700, pct: -3.02, volume: 3800000, sector: "Bất động sản" },
  { ticker: "HBC", name: "Hòa Bình Construction", price: 18900, change: -550, pct: -2.83, volume: 2100000, sector: "Xây dựng" },
  { ticker: "CEO", name: "CEO Group", price: 19600, change: -550, pct: -2.73, volume: 1500000, sector: "Bất động sản" },
];

export const topLiquidity = [
  { ticker: "HPG", name: "Hòa Phát Group", volume: 12500000, value: 335000000000, price: 26800 },
  { ticker: "STB", name: "Sacombank", volume: 9800000, value: 280280000000, price: 28600 },
  { ticker: "NVL", name: "Novaland", volume: 9800000, value: 139160000000, price: 14200 },
  { ticker: "ACB", name: "ACB Bank", volume: 8200000, value: 197620000000, price: 24100 },
  { ticker: "VIC", name: "Vingroup", volume: 4100000, value: 170150000000, price: 41500 },
  { ticker: "VCB", name: "Vietcombank", volume: 3450000, value: 304290000000, price: 88200 },
  { ticker: "DXG", name: "Đất Xanh Group", volume: 3200000, value: 48960000000, price: 15300 },
  { ticker: "MBB", name: "MB Bank", volume: 2980000, value: 62878000000, price: 21100 },
];

export const sectorPerformance = [
  { sector: "Ngân hàng", pct: 2.1, value: 15200 },
  { sector: "Công nghệ", pct: 3.8, value: 4500 },
  { sector: "Thép", pct: 2.9, value: 8900 },
  { sector: "Bất động sản", pct: -2.4, value: 12300 },
  { sector: "Bán lẻ", pct: 1.7, value: 3200 },
  { sector: "Dầu khí", pct: 0.8, value: 5600 },
  { sector: "Dược phẩm", pct: 1.2, value: 2100 },
  { sector: "Xây dựng", pct: -1.8, value: 4800 },
  { sector: "Tiêu dùng", pct: -0.5, value: 3900 },
  { sector: "Bảo hiểm", pct: 1.5, value: 1700 },
];

// Stock Detail mock data
export const generateCandlestickData = () => {
  const data = [];
  let price = 88000;
  for (let i = 60; i >= 0; i--) {
    const open = price + (Math.random() - 0.5) * 2000;
    const close = open + (Math.random() - 0.5) * 3000;
    const high = Math.max(open, close) + Math.random() * 1500;
    const low = Math.min(open, close) - Math.random() * 1500;
    const volume = Math.floor(Math.random() * 5000000) + 500000;
    const date = new Date();
    date.setDate(date.getDate() - i);
    data.push({
      date: date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" }),
      open: Math.round(open / 100) * 100,
      close: Math.round(close / 100) * 100,
      high: Math.round(high / 100) * 100,
      low: Math.round(low / 100) * 100,
      volume,
      sma20: Math.round((price + 500) / 100) * 100,
      ema12: Math.round((price + 200) / 100) * 100,
      rsi: 40 + Math.random() * 40,
      macd: (Math.random() - 0.4) * 500,
      macdSignal: (Math.random() - 0.4) * 400,
      bbUpper: Math.round((price + 3000) / 100) * 100,
      bbLower: Math.round((price - 3000) / 100) * 100,
    });
    price = price + (Math.random() - 0.45) * 1500;
  }
  return data;
};

export const stockList = [
  { ticker: "VCB", name: "Ngân hàng TMCP Ngoại thương Việt Nam", exchange: "HOSE", sector: "Ngân hàng" },
  { ticker: "FPT", name: "Công ty CP FPT", exchange: "HOSE", sector: "Công nghệ" },
  { ticker: "HPG", name: "Công ty CP Tập đoàn Hòa Phát", exchange: "HOSE", sector: "Thép" },
  { ticker: "VIC", name: "Tập đoàn Vingroup – CTCP", exchange: "HOSE", sector: "Bất động sản" },
  { ticker: "MWG", name: "CTCP Đầu tư Thế Giới Di Động", exchange: "HOSE", sector: "Bán lẻ" },
  { ticker: "BID", name: "Ngân hàng TMCP Đầu tư và Phát triển VN", exchange: "HOSE", sector: "Ngân hàng" },
  { ticker: "CTG", name: "Ngân hàng TMCP Công thương Việt Nam", exchange: "HOSE", sector: "Ngân hàng" },
  { ticker: "ACB", name: "Ngân hàng TMCP Á Châu", exchange: "HOSE", sector: "Ngân hàng" },
  { ticker: "MBB", name: "Ngân hàng TMCP Quân đội", exchange: "HOSE", sector: "Ngân hàng" },
  { ticker: "TCB", name: "Ngân hàng TMCP Kỹ thương Việt Nam", exchange: "HOSE", sector: "Ngân hàng" },
];

// Technical Scanner
export const technicalSignals = [
  { ticker: "VCB", name: "Vietcombank", rsi: 72.3, macd: 420, macdSignal: 310, close: 88200, bbUpper: 86000, bbLower: 74000, volume: 3450000, volSma20: 2100000, signal: "overbought", pct: 5.0 },
  { ticker: "FPT", name: "FPT Corp", rsi: 68.5, macd: 380, macdSignal: 290, close: 115600, bbUpper: 114000, bbLower: 98000, volume: 2980000, volSma20: 1800000, signal: "macd_positive", pct: 4.71 },
  { ticker: "HPG", name: "Hòa Phát", rsi: 28.4, macd: -180, macdSignal: -120, close: 26800, bbUpper: 29500, bbLower: 24200, volume: 12500000, volSma20: 7200000, signal: "oversold", pct: 4.28 },
  { ticker: "MBB", name: "MB Bank", rsi: 31.2, macd: -95, macdSignal: -60, close: 21100, bbUpper: 23800, bbLower: 19400, volume: 2980000, volSma20: 2500000, signal: "oversold", pct: -1.2 },
  { ticker: "STB", name: "Sacombank", rsi: 74.1, macd: 220, macdSignal: 150, close: 28600, bbUpper: 27800, bbLower: 23400, volume: 9800000, volSma20: 5100000, signal: "breakout", pct: 2.88 },
  { ticker: "NVL", name: "Novaland", rsi: 22.8, macd: -310, macdSignal: -210, close: 14200, bbUpper: 17200, bbLower: 14500, volume: 9800000, volSma20: 4900000, signal: "breakdown", pct: -4.70 },
  { ticker: "DXG", name: "Đất Xanh", rsi: 25.1, macd: -240, macdSignal: -180, close: 15300, bbUpper: 17800, bbLower: 15800, volume: 3200000, volSma20: 1800000, signal: "breakdown", pct: -4.97 },
  { ticker: "ACB", name: "ACB Bank", rsi: 55.3, macd: 120, macdSignal: 80, close: 24100, bbUpper: 26400, bbLower: 21200, volume: 8200000, volSma20: 4800000, signal: "volume_spike", pct: 2.99 },
  { ticker: "GVR", name: "VRG", rsi: 71.8, macd: 88, macdSignal: 62, close: 17200, bbUpper: 16900, bbLower: 14100, signal: "breakout", volume: 6700000, volSma20: 3200000, pct: 3.62 },
  { ticker: "TCB", name: "Techcombank", rsi: 63.4, macd: 195, macdSignal: 140, close: 32400, bbUpper: 34200, bbLower: 28600, volume: 5100000, volSma20: 2800000, signal: "macd_positive", pct: 1.85 },
  { ticker: "PDR", name: "Phát Đạt", rsi: 24.7, macd: -275, macdSignal: -190, close: 28400, bbUpper: 33200, bbLower: 29100, volume: 2400000, volSma20: 1600000, signal: "oversold", pct: -4.38 },
  { ticker: "VIC", name: "Vingroup", rsi: 44.2, macd: 88, macdSignal: 70, close: 41500, bbUpper: 45200, bbLower: 37800, volume: 4100000, volSma20: 2400000, signal: "volume_spike", pct: 3.75 },
];

// Pipeline Monitor
export const dagStatus = [
  { dag: "ingest_ohlcv_hose", status: "success", lastRun: "06:30", duration: "4m 12s", records: 482000, tasks: 8, failed: 0 },
  { dag: "ingest_ohlcv_hnx", status: "success", lastRun: "06:32", duration: "2m 48s", records: 198000, tasks: 6, failed: 0 },
  { dag: "ingest_ohlcv_upcom", status: "success", lastRun: "06:35", duration: "3m 05s", records: 287000, tasks: 6, failed: 0 },
  { dag: "process_technical_indicators", status: "success", lastRun: "07:15", duration: "8m 32s", records: 967000, tasks: 12, failed: 0 },
  { dag: "ingest_news_sentiment", status: "running", lastRun: "14:00", duration: "1m 20s", records: 12400, tasks: 4, failed: 0 },
  { dag: "dbt_transform_silver", status: "success", lastRun: "08:00", duration: "6m 15s", records: 1240000, tasks: 15, failed: 0 },
  { dag: "gx_validation_daily", status: "failed", lastRun: "08:20", duration: "2m 45s", records: 0, tasks: 10, failed: 3 },
  { dag: "clickhouse_load_gold", status: "success", lastRun: "09:00", duration: "3m 18s", records: 845000, tasks: 8, failed: 0 },
  { dag: "realtime_vwap_consumer", status: "running", lastRun: "09:00", duration: "5h 22m", records: 4820000, tasks: 2, failed: 0 },
  { dag: "alert_checker", status: "success", lastRun: "14:20", duration: "0m 45s", records: 48, tasks: 3, failed: 0 },
];

export const dataQualityErrors = [
  { type: "high < low", count: 3, table: "fact_daily_price", date: "2026-06-14" },
  { type: "null close price", count: 7, table: "fact_daily_price", date: "2026-06-14" },
  { type: "duplicate (ticker, date)", count: 2, table: "fact_daily_price", date: "2026-06-13" },
  { type: "volume < 0", count: 1, table: "fact_daily_price", date: "2026-06-14" },
  { type: "missing ticker ref", count: 4, table: "fact_news_sentiment_daily", date: "2026-06-14" },
];

export const ingestHistory = [
  { date: "06-08", records: 820000 }, { date: "06-09", records: 945000 },
  { date: "06-10", records: 867000 }, { date: "06-11", records: 912000 },
  { date: "06-12", records: 889000 }, { date: "06-13", records: 978000 },
  { date: "06-14", records: 967000 },
];

export const kafkaLag = [
  { time: "09:00", lag: 120 }, { time: "09:15", lag: 85 }, { time: "09:30", lag: 62 },
  { time: "09:45", lag: 110 }, { time: "10:00", lag: 45 }, { time: "10:15", lag: 38 },
  { time: "10:30", lag: 220 }, { time: "10:45", lag: 180 }, { time: "11:00", lag: 95 },
  { time: "11:15", lag: 62 }, { time: "11:30", lag: 48 }, { time: "13:00", lag: 72 },
  { time: "13:15", lag: 55 }, { time: "13:30", lag: 41 }, { time: "13:45", lag: 88 },
  { time: "14:00", lag: 65 }, { time: "14:15", lag: 50 }, { time: "14:30", lag: 35 },
];

// VWAP Monitoring
export const vwapData = [
  { time: "09:15", price: 88100, vwap: 88050, sessionVwap: 88050, volume: 145000, deviation: 0.06 },
  { time: "09:20", price: 88200, vwap: 88120, sessionVwap: 88090, volume: 220000, deviation: 0.13 },
  { time: "09:25", price: 88400, vwap: 88200, sessionVwap: 88150, volume: 310000, deviation: 0.28 },
  { time: "09:30", price: 88300, vwap: 88230, sessionVwap: 88170, volume: 180000, deviation: 0.15 },
  { time: "09:35", price: 88600, vwap: 88310, sessionVwap: 88220, volume: 420000, deviation: 0.43 },
  { time: "09:40", price: 88500, vwap: 88350, sessionVwap: 88260, volume: 280000, deviation: 0.27 },
  { time: "09:45", price: 88700, vwap: 88420, sessionVwap: 88310, volume: 390000, deviation: 0.44 },
  { time: "09:50", price: 88200, vwap: 88400, sessionVwap: 88320, volume: 210000, deviation: -0.14 },
  { time: "09:55", price: 88000, vwap: 88360, sessionVwap: 88300, volume: 160000, deviation: -0.34 },
  { time: "10:00", price: 87900, vwap: 88310, sessionVwap: 88260, volume: 125000, deviation: -0.41 },
  { time: "10:05", price: 87800, vwap: 88250, sessionVwap: 88210, volume: 180000, deviation: -0.46 },
  { time: "10:10", price: 88100, vwap: 88240, sessionVwap: 88200, volume: 215000, deviation: -0.11 },
  { time: "10:15", price: 88300, vwap: 88250, sessionVwap: 88210, volume: 245000, deviation: 0.10 },
  { time: "10:20", price: 88500, vwap: 88280, sessionVwap: 88230, volume: 340000, deviation: 0.31 },
  { time: "10:25", price: 88700, vwap: 88330, sessionVwap: 88260, volume: 410000, deviation: 0.50 },
  { time: "10:30", price: 88900, vwap: 88410, sessionVwap: 88310, volume: 520000, deviation: 0.56 },
];

export const vwapDeviations = [
  { ticker: "STB", price: 28600, sessionVwap: 27400, deviation: 4.38, volume: 9800000, alerts: 3 },
  { ticker: "HPG", price: 26800, sessionVwap: 25900, deviation: 3.47, volume: 12500000, alerts: 2 },
  { ticker: "NVL", price: 14200, sessionVwap: 14900, deviation: -4.70, volume: 9800000, alerts: 4 },
  { ticker: "DXG", price: 15300, sessionVwap: 15900, deviation: -3.77, volume: 3200000, alerts: 2 },
  { ticker: "VCB", price: 88200, sessionVwap: 86500, deviation: 1.97, volume: 3450000, alerts: 1 },
  { ticker: "FPT", price: 115600, sessionVwap: 113800, deviation: 1.58, volume: 2980000, alerts: 0 },
];

// News & Sentiment
export const newsSentiment = [
  { ticker: "VCB", name: "Vietcombank", newsCount: 18, sources: 8, positive: 12, negative: 2, neutral: 4, avgScore: 0.72, headline: "Vietcombank dự kiến tăng vốn điều lệ lên 83.000 tỷ đồng trong 2026" },
  { ticker: "FPT", name: "FPT Corp", newsCount: 15, sources: 7, positive: 10, negative: 1, neutral: 4, avgScore: 0.68, headline: "FPT ký hợp đồng AI với tập đoàn Nhật Bản trị giá 50 triệu USD" },
  { ticker: "HPG", name: "Hòa Phát", newsCount: 12, sources: 6, positive: 7, negative: 3, neutral: 2, avgScore: 0.41, headline: "Xuất khẩu thép Hòa Phát tháng 6 tăng 28% so với cùng kỳ" },
  { ticker: "NVL", name: "Novaland", newsCount: 22, sources: 9, positive: 2, negative: 16, neutral: 4, avgScore: -0.58, headline: "Novaland đàm phán gia hạn nợ trái phiếu thêm 12 tháng" },
  { ticker: "VIC", name: "Vingroup", newsCount: 20, sources: 10, positive: 11, negative: 5, neutral: 4, avgScore: 0.32, headline: "VinFast giao thêm 3.200 xe trong tháng 6, đạt mục tiêu quý 2" },
  { ticker: "MWG", name: "Thế Giới Di Động", newsCount: 8, sources: 5, positive: 6, negative: 0, neutral: 2, avgScore: 0.78, headline: "Thế Giới Di Động báo lãi quý 2 tăng 45% nhờ phục hồi tiêu dùng" },
  { ticker: "DXG", name: "Đất Xanh", newsCount: 10, sources: 4, positive: 1, negative: 8, neutral: 1, avgScore: -0.62, headline: "Đất Xanh bị kiểm toán nêu ý kiến ngoại trừ về dự án tồn đọng" },
  { ticker: "STB", name: "Sacombank", newsCount: 9, sources: 5, positive: 7, negative: 1, neutral: 1, avgScore: 0.65, headline: "Sacombank hoàn thành xử lý toàn bộ nợ xấu tồn đọng từ VAMC" },
  { ticker: "BVH", name: "Bảo Việt", newsCount: 6, sources: 4, positive: 5, negative: 0, neutral: 1, avgScore: 0.80, headline: "Bảo Việt ký hợp đồng tái bảo hiểm với Swiss Re trị giá 120 triệu USD" },
  { ticker: "PDR", name: "Phát Đạt", newsCount: 7, sources: 3, positive: 0, negative: 6, neutral: 1, avgScore: -0.71, headline: "Phát Đạt đối mặt kiện tụng liên quan dự án Bình Dương chậm tiến độ" },
];

export const sentimentByDate = [
  { date: "06-08", positive: 45, negative: 22, neutral: 38 },
  { date: "06-09", positive: 52, negative: 18, neutral: 35 },
  { date: "06-10", positive: 38, negative: 31, neutral: 42 },
  { date: "06-11", positive: 61, negative: 15, neutral: 29 },
  { date: "06-12", positive: 48, negative: 25, neutral: 37 },
  { date: "06-13", positive: 55, negative: 20, neutral: 32 },
  { date: "06-14", positive: 63, negative: 28, neutral: 35 },
];

// Alert History
export const alertHistory = [
  { id: 1, user: "user_001", ticker: "VCB", condition: "RSI_ABOVE", threshold: 70, actual: 72.3, channel: "TELEGRAM", status: "sent", sentAt: "14:28:32", triggeredAt: "14:28:30", cooldown: 30 },
  { id: 2, user: "user_002", ticker: "NVL", condition: "BB_BREAK", threshold: 0, actual: -4.2, channel: "EMAIL", status: "sent", sentAt: "14:15:12", triggeredAt: "14:15:10", cooldown: 60 },
  { id: 3, user: "user_001", ticker: "STB", condition: "VWAP_DEVIATION", threshold: 3, actual: 4.38, channel: "TELEGRAM", status: "sent", sentAt: "13:52:08", triggeredAt: "13:52:05", cooldown: 30 },
  { id: 4, user: "user_003", ticker: "HPG", condition: "RSI_BELOW", threshold: 30, actual: 28.4, channel: "TELEGRAM", status: "sent", sentAt: "11:32:45", triggeredAt: "11:32:44", cooldown: 30 },
  { id: 5, user: "user_002", ticker: "DXG", condition: "PRICE_BELOW", threshold: 16000, actual: 15300, channel: "EMAIL", status: "failed", sentAt: null, triggeredAt: "10:45:22", cooldown: 60 },
  { id: 6, user: "user_001", ticker: "FPT", condition: "PRICE_ABOVE", threshold: 115000, actual: 115600, channel: "TELEGRAM", status: "sent", sentAt: "09:55:11", triggeredAt: "09:55:10", cooldown: 30 },
  { id: 7, user: "user_004", ticker: "VIC", condition: "RSI_ABOVE", threshold: 65, actual: 69.2, channel: "EMAIL", status: "sent", sentAt: "09:32:18", triggeredAt: "09:32:15", cooldown: 30 },
  { id: 8, user: "user_003", ticker: "NVL", condition: "BB_BREAK", threshold: 0, actual: -5.1, channel: "TELEGRAM", status: "sent", sentAt: "09:28:40", triggeredAt: "09:28:38", cooldown: 60 },
  { id: 9, user: "user_001", ticker: "STB", condition: "VWAP_DEVIATION", threshold: 3, actual: 3.85, channel: "TELEGRAM", status: "skipped", sentAt: null, triggeredAt: "09:18:22", cooldown: 30 },
  { id: 10, user: "user_002", ticker: "HPG", condition: "RSI_BELOW", threshold: 30, actual: 29.1, channel: "EMAIL", status: "sent", sentAt: "09:10:05", triggeredAt: "09:10:03", cooldown: 30 },
];

export const alertsByDay = [
  { date: "06-08", total: 18 }, { date: "06-09", total: 24 },
  { date: "06-10", total: 15 }, { date: "06-11", total: 31 },
  { date: "06-12", total: 22 }, { date: "06-13", total: 28 },
  { date: "06-14", total: 35 },
];

export const alertsByCondition = [
  { type: "RSI_ABOVE", count: 42, fill: "#f59e0b" },
  { type: "RSI_BELOW", count: 35, fill: "#3b82f6" },
  { type: "VWAP_DEVIATION", count: 28, fill: "#a855f7" },
  { type: "BB_BREAK", count: 31, fill: "#00d97e" },
  { type: "PRICE_ABOVE", count: 18, fill: "#ff4d6d" },
  { type: "PRICE_BELOW", count: 12, fill: "#6b7fa3" },
];
