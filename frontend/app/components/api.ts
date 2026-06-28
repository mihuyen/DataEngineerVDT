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
  dataSnapshotMeta: {
    generatedAt?: string;
    latestPriceDate?: string | null;
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

export async function fetchStocks(): Promise<StockOption[]> {
  const payload = await getJson<{ data: StockOption[] }>("/api/stocks?limit=2000");
  return payload.data;
}

export async function fetchCandles(ticker: string): Promise<Candle[]> {
  const payload = await getJson<{ data: Candle[] }>(`/api/stocks/${ticker}/candles?limit=260`);
  return payload.data;
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
};

export type SentimentByDate = { date: string; positive: number; negative: number; neutral: number };

export type NewsSentimentPayload = {
  count: number;
  data: NewsSentimentRow[];
  byDate: SentimentByDate[];
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
