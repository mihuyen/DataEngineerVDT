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

export async function fetchRealtimeVwap(): Promise<VwapTicker[]> {
  const payload = await getJson<{ data: VwapTicker[] }>("/api/realtime/vwap");
  return payload.data;
}

export async function fetchRealtimeVwapSeries(ticker: string): Promise<VwapPoint[]> {
  const payload = await getJson<{ data: VwapPoint[] }>(`/api/realtime/vwap/${ticker}/series`);
  return payload.data;
}
