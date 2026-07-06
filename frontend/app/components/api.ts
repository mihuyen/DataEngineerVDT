export type StockOption = {
  ticker: string;
  name: string;
  exchange: string;
  sector: string;
  marketCap?: number | null;
  sharesOutstanding?: number;
  hasPriceData?: number;
};

export type Candle = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma20: number;
  ema12: number;
  rsi: number;
  macd: number;
  macdSignal: number;
  bbUpper: number;
  bbLower: number;
  marketCap: number;
  value: number;
};

export type VwapTicker = {
  ticker: string;
  name: string;
  sector: string;
  exchange: string;
  price: number;
  sessionVwap: number;
  vwap: number;
  deviation: number;
  volume: number;
  volSma: number;
  alerts: number;
  updatedAt?: string;
  dataSource?: string;
};

export type VwapPoint = {
  time: string;
  price: number;
  vwap: number;
  sessionVwap: number;
  volume: number;
  deviation: number;
};

export type RealtimeVwapPayload = {
  count: number;
  activeCount?: number;
  universeCount?: number;
  subscribedCount?: number;
  latestMinute?: string;
  source?: string;
  marketStatus: "live" | "lunch_break" | "pre_open" | "closed";
  statusLabel: string;
  marketNow?: string;
  sessionDate?: string | null;
  staleSeconds?: number | null;
  isLive: boolean;
  isFresh: boolean;
  dataMode: "REAL" | "DEMO";
  dataProvider: string;
  data: VwapTicker[];
};

export type MarketOverviewPayload = {
  source: string;
  dataMode: "EOD" | "EOD+LIVE";
  isRealtime: boolean;
  liveTickerCount?: number;
  liveAsOf?: string | null;
  marketStatus: "live" | "lunch_break" | "pre_open" | "closed";
  statusLabel: string;
  marketNow?: string;
  dataSnapshotMeta: {
    generatedAt?: string;
    latestPriceDate?: string | null;
    label?: string;
  };
  marketIndicesAll: any[];
  marketOverviewStats: any;
  marketStatsByExchange: Record<string, any>;
  stockCountsByExchange: Record<string, number>;
  breadthData: any[];
  breadthDataByExchange: Record<string, any[]>;
  indexChangeBars: any[];
  vnIndexHistory: any[];
  indexHistoryByExchange: Record<string, any[]>;
  topGainers: any[];
  topLosers: any[];
  topLiquidity: any[];
  sectorPerformance: any[];
  sectorPerformanceByExchange: any[];
};

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function sendJson<T>(url: string, method: "POST" | "DELETE", body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function fetchStocks(): Promise<StockOption[]> {
  const payload = await getJson<{ data: StockOption[] }>("/api/stocks?limit=2000");
  return payload.data;
}

export type DailyCandlesPayload = {
  ticker: string;
  count: number;
  latestPriceDate: string;
  dataMode: "EOD";
  isRealtime: boolean;
  marketStatus: "live" | "lunch_break" | "pre_open" | "closed";
  statusLabel: string;
  data: Candle[];
};

export async function fetchCandles(ticker: string): Promise<DailyCandlesPayload> {
  return getJson<DailyCandlesPayload>(`/api/stocks/${ticker}/candles?limit=260`);
}

export type IntradayResolution = "1m" | "5m" | "15m" | "30m" | "1h";

export type IntradayCandle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type IntradayPayload = {
  ticker: string;
  resolution: IntradayResolution;
  tradingDate: string;
  latestMinute?: string;
  sources?: string[];
  dataMode: "INTRADAY";
  marketStatus: "live" | "lunch_break" | "pre_open" | "closed";
  statusLabel: string;
  count: number;
  data: IntradayCandle[];
};

export async function fetchIntraday(ticker: string, resolution: IntradayResolution): Promise<IntradayPayload> {
  return getJson<IntradayPayload>(`/api/stocks/${ticker}/intraday?resolution=${resolution}`);
}

export async function fetchRealtimeVwap(): Promise<RealtimeVwapPayload> {
  return getJson<RealtimeVwapPayload>("/api/realtime/vwap");
}

export async function fetchRealtimeVwapSeries(ticker: string): Promise<VwapPoint[]> {
  const payload = await getJson<{ data: VwapPoint[] }>(`/api/realtime/vwap/${ticker}/series`);
  return payload.data;
}

export async function fetchMarketOverview(): Promise<MarketOverviewPayload> {
  return getJson<MarketOverviewPayload>("/api/market/overview");
}

export type TechnicalSignal = {
  ticker: string;
  name: string;
  signal: string;
  rsi: number;
  macd: number;
  macdSignal: number;
  close: number;
  bbUpper: number;
  bbLower: number;
  volume: number;
  volSma20: number;
  pct: number;
};

export type TechnicalSignalsPayload = {
  trackedTickerCount: number;
  count: number;
  data: TechnicalSignal[];
};

export async function fetchTechnicalSignals(): Promise<TechnicalSignalsPayload> {
  return getJson<TechnicalSignalsPayload>("/api/technical/signals");
}

export type IntradaySignalResolution = "1m" | "5m" | "15m";

export type IntradayTechnicalSignal = {
  ticker: string;
  asOf: string;
  name: string;
  close: number;
  volume: number;
  rsi: number | null;
  bbUpper: number | null;
  bbLower: number | null;
  volSma20: number | null;
  signal: string;
};

export type IntradayTechnicalSignalsPayload = {
  resolution: IntradaySignalResolution;
  count: number;
  data: IntradayTechnicalSignal[];
};

export async function fetchIntradayTechnicalSignals(
  resolution: IntradaySignalResolution
): Promise<IntradayTechnicalSignalsPayload> {
  return getJson<IntradayTechnicalSignalsPayload>(`/api/technical/signals/intraday?resolution=${resolution}`);
}

export type NewsSentimentRow = {
  ticker: string;
  name: string;
  newsCount: number;
  sources: number;
  positive: number;
  negative: number;
  neutral: number;
  avgScore: number;
  headline: string;
  url?: string | null;
  source?: string | null;
  publishedAt?: string;
  newsDate?: string;
  avgConfidence?: number;
  lowConfidenceCount?: number;
  modelVersion?: string;
};

export type SentimentByDate = { date: string; positive: number; negative: number; neutral: number };

export type NewsArticleRow = {
  articleId: string;
  ticker: string;
  name: string;
  headline: string;
  url?: string | null;
  source?: string | null;
  publishedAt?: string;
  sentimentLabel?: string | null;
  sentimentScore?: number | null;
  confidenceScore?: number | null;
  modelVersion?: string | null;
  matchMethod?: string | null;
  matchScore?: number | null;
  isLowConfidence?: number | null;
};

export type NewsSentimentPayload = {
  count: number;
  data: NewsSentimentRow[];
  byDate: SentimentByDate[];
  articles: NewsArticleRow[];
  modelVersions: string[];
};

export async function fetchNewsSentiment(): Promise<NewsSentimentPayload> {
  return getJson<NewsSentimentPayload>("/api/news/sentiment");
}

export type AlertEvent = {
  id: string;
  triggeredAt: string;
  user: string;
  ticker: string;
  condition: string;
  threshold: number;
  actual: number;
  channel: string;
  status: string;
  /** Raw reason: sent | send_failed | channel_not_configured | unknown_channel */
  deliveryStatus?: string;
  sentAt: string | null;
  cooldown: number;
};

export type AlertByDay = { date: string; total: number };
export type AlertByCondition = { type: string; count: number; fill: string };

export type AlertsPayload = {
  count: number;
  data: AlertEvent[];
  byDay: AlertByDay[];
  byCondition: AlertByCondition[];
};

export async function fetchAlerts(): Promise<AlertsPayload> {
  return getJson<AlertsPayload>("/api/alerts");
}

export type AlertRule = {
  id: string;
  ticker: string;
  conditionType: string;
  thresholdValue: number;
  channel: string;
  cooldownMinutes: number;
  isActive: boolean;
  createdAt: string;
};

export type AlertRulesPayload = { count: number; data: AlertRule[] };

export async function fetchAlertRules(): Promise<AlertRulesPayload> {
  return getJson<AlertRulesPayload>("/api/alert-rules");
}

export async function createAlertRule(rule: {
  ticker: string;
  conditionType: string;
  thresholdValue: number;
  channel: string;
  cooldownMinutes: number;
}): Promise<{ id: string; created: boolean }> {
  return sendJson("/api/alert-rules", "POST", rule);
}

export async function setAlertRuleActive(id: string, isActive: boolean): Promise<{ id: string; isActive: boolean }> {
  const response = await fetch(`/api/alert-rules/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ isActive }),
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

export async function deleteAlertRule(id: string): Promise<{ id: string; removed: boolean }> {
  return sendJson(`/api/alert-rules/${id}`, "DELETE");
}

export type DagStatusRow = {
  dag: string;
  status: string;
  lastRun: string;
  duration: string;
  records: number;
  tasks: number;
  failed: number;
};

export type DataQualityError = { type: string; table: string; count: number; date: string };
export type IngestHistoryPoint = { date: string; records: number };
export type KafkaLagPoint = { time: string; lag: number };

export type PipelineStatusPayload = {
  dagStatus: DagStatusRow[];
  dagStatusSource: "airflow" | "clickhouse_fallback";
  dataQualityErrors: DataQualityError[];
  ingestHistory: IngestHistoryPoint[];
  kafkaLag: KafkaLagPoint[];
};

export async function fetchPipelineStatus(): Promise<PipelineStatusPayload> {
  return getJson<PipelineStatusPayload>("/api/pipeline/status");
}

export type WatchlistRow = {
  ticker: string;
  name: string;
  sector: string;
  exchange: string;
  price: number;
  change: number;
  pct: number;
  volume: number;
  value: number;
  inWatchlist: boolean;
};

export type WatchlistPayload = { count: number; data: WatchlistRow[] };

export async function fetchWatchlist(): Promise<WatchlistPayload> {
  return getJson<WatchlistPayload>("/api/watchlist");
}

export async function addToWatchlist(ticker: string): Promise<{ ticker: string; added: boolean }> {
  return sendJson("/api/watchlist", "POST", { ticker });
}

export async function removeFromWatchlist(ticker: string): Promise<{ ticker: string; removed: boolean }> {
  return sendJson(`/api/watchlist/${ticker}`, "DELETE");
}
