import { useEffect, useRef } from "react";
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  IChartApi,
  ISeriesApi,
  UTCTimestamp,
} from "lightweight-charts";
// Structurally compatible with both Candle (daily) and a mapped IntradayCandle
// (date <- time) -- the chart only ever needs OHLCV plus the optional overlay
// fields, so it doesn't need the full Candle shape (marketCap, value, etc).
export type OhlcPoint = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma20?: number;
  ema12?: number;
  bbUpper?: number;
  bbLower?: number;
};

function baseChartOptions(timeVisible: boolean) {
  return {
    layout: {
      background: { color: "#111827" },
      textColor: "#6b7fa3",
      fontFamily: "JetBrains Mono, monospace",
    },
    grid: {
      vertLines: { color: "rgba(255,255,255,0.04)" },
      horzLines: { color: "rgba(255,255,255,0.04)" },
    },
    rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
    timeScale: { borderColor: "rgba(255,255,255,0.08)", timeVisible },
    crosshair: { mode: 0 },
  };
}

// Accepts either a pure date ("YYYY-MM-DD", from the daily candles API) or a
// full minute timestamp ("YYYY-MM-DD HH:mm", from the intraday API) -- both
// are UTC-naive strings produced by ClickHouse's formatDateTime, so treating
// them as UTC here keeps candles aligned to the actual exchange timestamp
// instead of shifting by the browser's local offset.
function toTime(value: string): UTCTimestamp {
  const iso = value.length === 10 ? `${value}T00:00:00Z` : `${value.replace(" ", "T")}:00Z`;
  return (new Date(iso).getTime() / 1000) as UTCTimestamp;
}

interface CandlestickChartProps {
  data: OhlcPoint[];
  indicators: { sma20: boolean; ema12: boolean; bb: boolean };
  timeVisible?: boolean;
}

export function CandlestickChart({ data, indicators, timeVisible = false }: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const overlaySeriesRef = useRef<Record<string, ISeriesApi<"Line">>>({});

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      ...baseChartOptions(timeVisible),
      width: containerRef.current.clientWidth,
      height: 360,
    });
    chartRef.current = chart;

    candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
      upColor: "#00d97e",
      downColor: "#ff4d6d",
      borderUpColor: "#00d97e",
      borderDownColor: "#ff4d6d",
      wickUpColor: "#00d97e",
      wickDownColor: "#ff4d6d",
      priceScaleId: "right",
    });
    candleSeriesRef.current.priceScale().applyOptions({ scaleMargins: { top: 0.05, bottom: 0.25 } });

    volumeSeriesRef.current = chart.addSeries(HistogramSeries, {
      color: "rgba(59,130,246,0.35)",
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    volumeSeriesRef.current.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

    // A browser-window resize is not the only thing that changes this
    // container's width -- collapsing the sidebar or any other flex-layout
    // shift resizes it too, without firing a window "resize" event. Watching
    // the container itself is what actually keeps the chart width correct.
    const resizeObserver = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width;
      if (width) chart.applyOptions({ width });
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      overlaySeriesRef.current = {};
    };
  }, [timeVisible]);

  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return;
    candleSeriesRef.current.setData(
      data.map((d) => ({ time: toTime(d.date), open: d.open, high: d.high, low: d.low, close: d.close }))
    );
    volumeSeriesRef.current.setData(
      data.map((d) => ({
        time: toTime(d.date),
        value: d.volume,
        color: d.close >= d.open ? "rgba(0,217,126,0.35)" : "rgba(255,77,109,0.35)",
      }))
    );
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    const overlayConfig: { key: keyof typeof indicators; field: keyof OhlcPoint; color: string }[] = [
      { key: "sma20", field: "sma20", color: "#8b5cf6" },
      { key: "ema12", field: "ema12", color: "#a855f7" },
    ];

    for (const { key, field, color } of overlayConfig) {
      const wanted = indicators[key];
      const existing = overlaySeriesRef.current[key];
      if (wanted && !existing) {
        const series = chart.addSeries(LineSeries, { color, lineWidth: 1, priceLineVisible: false });
        series.setData(data.map((d) => ({ time: toTime(d.date), value: d[field] as number })));
        overlaySeriesRef.current[key] = series;
      } else if (wanted && existing) {
        existing.setData(data.map((d) => ({ time: toTime(d.date), value: d[field] as number })));
      } else if (!wanted && existing) {
        chart.removeSeries(existing);
        delete overlaySeriesRef.current[key];
      }
    }

    const bbWanted = indicators.bb;
    for (const bbKey of ["bbUpper", "bbLower"] as const) {
      const existing = overlaySeriesRef.current[bbKey];
      if (bbWanted && !existing) {
        const series = chart.addSeries(LineSeries, {
          color: "rgba(107,127,163,0.7)",
          lineWidth: 1,
          lineStyle: 2,
          priceLineVisible: false,
        });
        series.setData(data.map((d) => ({ time: toTime(d.date), value: d[bbKey] })));
        overlaySeriesRef.current[bbKey] = series;
      } else if (bbWanted && existing) {
        existing.setData(data.map((d) => ({ time: toTime(d.date), value: d[bbKey] })));
      } else if (!bbWanted && existing) {
        chart.removeSeries(existing);
        delete overlaySeriesRef.current[bbKey];
      }
    }
  }, [data, indicators]);

  return <div ref={containerRef} style={{ width: "100%" }} />;
}
