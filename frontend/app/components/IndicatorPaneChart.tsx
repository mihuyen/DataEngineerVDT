import { useEffect, useRef } from "react";
import {
  createChart,
  HistogramSeries,
  IChartApi,
  ISeriesApi,
  LineSeries,
  UTCTimestamp,
} from "lightweight-charts";
import { Candle } from "./api";

function toTime(date: string): UTCTimestamp {
  return (new Date(date + "T00:00:00Z").getTime() / 1000) as UTCTimestamp;
}

const CHART_OPTIONS = {
  layout: { background: { color: "#111827" }, textColor: "#6b7fa3", fontFamily: "JetBrains Mono, monospace" },
  grid: { vertLines: { color: "rgba(255,255,255,0.04)" }, horzLines: { color: "rgba(255,255,255,0.04)" } },
  rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
  timeScale: { borderColor: "rgba(255,255,255,0.08)", timeVisible: false },
};

function observeResize(container: HTMLDivElement, chart: IChartApi): () => void {
  const resizeObserver = new ResizeObserver((entries) => {
    const width = entries[0]?.contentRect.width;
    if (width) chart.applyOptions({ width });
  });
  resizeObserver.observe(container);
  return () => resizeObserver.disconnect();
}

interface RsiPaneProps {
  data: Candle[];
}

export function RsiPane({ data }: RsiPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  // Created once on mount, not on every `data` change -- recreating the
  // whole chart object here (the previous behavior) tore down and rebuilt
  // it on every parent re-render, visible as a flicker/redraw.
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, { ...CHART_OPTIONS, width: containerRef.current.clientWidth, height: 140 });
    chartRef.current = chart;
    const series = chart.addSeries(LineSeries, { color: "#3b82f6", lineWidth: 2, priceLineVisible: false });
    series.createPriceLine({ price: 70, color: "#ff4d6d", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "70" });
    series.createPriceLine({ price: 30, color: "#00d97e", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "30" });
    chart.priceScale("right").applyOptions({ autoScale: false });
    series.priceScale().applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } });
    seriesRef.current = series;
    const stopObserving = observeResize(containerRef.current, chart);

    return () => {
      stopObserving();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current) return;
    seriesRef.current.setData(data.map((d) => ({ time: toTime(d.date), value: d.rsi })));
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} style={{ width: "100%" }} />;
}

interface MacdPaneProps {
  data: Candle[];
}

export function MacdPane({ data }: MacdPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const histogramRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const signalRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, { ...CHART_OPTIONS, width: containerRef.current.clientWidth, height: 140 });
    chartRef.current = chart;
    histogramRef.current = chart.addSeries(HistogramSeries, { color: "#00d97e", priceLineVisible: false });
    signalRef.current = chart.addSeries(LineSeries, { color: "#8b5cf6", lineWidth: 1.5, priceLineVisible: false });
    const stopObserving = observeResize(containerRef.current, chart);

    return () => {
      stopObserving();
      chart.remove();
      chartRef.current = null;
      histogramRef.current = null;
      signalRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!histogramRef.current || !signalRef.current) return;
    histogramRef.current.setData(
      data.map((d) => ({ time: toTime(d.date), value: d.macd, color: d.macd >= 0 ? "rgba(0,217,126,0.6)" : "rgba(255,77,109,0.6)" }))
    );
    signalRef.current.setData(data.map((d) => ({ time: toTime(d.date), value: d.macdSignal })));
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} style={{ width: "100%" }} />;
}
