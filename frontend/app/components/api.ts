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
  latestMinute?: string;
  source?: string;
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
