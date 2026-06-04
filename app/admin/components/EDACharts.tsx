'use client';

import React, { useRef, useEffect, useState } from 'react';

const CHART_COLORS = [
  '#0ea5e9', '#6366f1', '#8b5cf6', '#10b981', '#f59e0b',
  '#ef4444', '#ec4899', '#14b8a6', '#f97316', '#06b6d4',
];

function useInView(ref: React.RefObject<HTMLElement | null>) {
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setInView(true); obs.unobserve(el); }
    }, { threshold: 0.2 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [ref]);
  return inView;
}

/* ═══ EMPTY STATE ═══ */
const EmptyChart = React.forwardRef<HTMLDivElement, { title: string }>(({ title }, ref) => (
  <div ref={ref} className="glass-card-static rounded-3xl p-6 border border-sky-100/20 dark:border-sky-850/10" style={{ boxShadow: '0 4px 20px rgba(14,165,233,0.02)' }}>
    <h4 className="text-sm font-black text-sky-950 dark:text-sky-50 mb-5">{title}</h4>
    <div className="flex items-center justify-center h-48">
      <p className="text-sm text-sky-400/50 font-bold">Belum ada data analitis</p>
    </div>
  </div>
));
EmptyChart.displayName = 'EmptyChart';

/* ═══ PIE CHART ═══ */
interface PieChartProps {
  data: { label: string; value: number; color?: string }[];
  title: string;
  size?: number;
}

export function PieChart({ data, title, size = 240 }: PieChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref);
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return <EmptyChart title={title} ref={ref} />;

  const cx = size / 2, cy = size / 2, r = size / 2 - 10;
  let cumAngle = -90;

  const slices = data.map((d, i) => {
    const angle = (d.value / total) * 360;
    const startAngle = cumAngle;
    cumAngle += angle;
    const endAngle = cumAngle;
    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;
    const x1 = cx + r * Math.cos(startRad);
    const y1 = cy + r * Math.sin(startRad);
    const x2 = cx + r * Math.cos(endRad);
    const y2 = cy + r * Math.sin(endRad);
    const largeArc = angle > 180 ? 1 : 0;
    const pathD = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;
    const color = d.color || CHART_COLORS[i % CHART_COLORS.length];
    return { pathD, color, label: d.label, value: d.value, pct: ((d.value / total) * 100).toFixed(1) };
  });

  return (
    <div ref={ref} className="glass-card-static rounded-3xl p-6 border border-sky-100/20 dark:border-sky-850/10" style={{ boxShadow: '0 8px 30px rgba(14,165,233,0.02)' }}>
      <h4 className="text-sm font-black text-sky-950 dark:text-sky-50 mb-5">{title}</h4>
      <div className="flex flex-col items-center gap-6">
        <svg width="100%" height="100%" viewBox={`0 0 ${size} ${size}`} className="max-w-[240px] mx-auto transition-all duration-700" style={{ opacity: inView ? 1 : 0, transform: inView ? 'scale(1)' : 'scale(0.7)' }}>
          {slices.map((s, i) => (
            <path key={i} d={s.pathD} fill={s.color} stroke="white" strokeWidth="2.5" className="hover:opacity-85 transition-opacity cursor-default">
              <title>{s.label}: {s.value} ({s.pct}%)</title>
            </path>
          ))}
          <circle cx={cx} cy={cy} r={r * 0.55} fill="white" className="dark:fill-[#0f172a]" />
          <text x={cx} y={cy - 6} textAnchor="middle" className="fill-sky-950 dark:fill-sky-50" fontSize="24" fontWeight="900">{total}</text>
          <text x={cx} y={cy + 14} textAnchor="middle" className="fill-sky-500/60" fontSize="10" fontWeight="800" style={{ letterSpacing: '0.05em' }}>TOTAL</text>
        </svg>
        <div className="flex flex-wrap justify-center gap-x-5 gap-y-2.5">
          {slices.map((s, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: s.color }} />
              <span className="text-xs font-bold text-sky-800/80 dark:text-sky-300/70">{s.label} ({s.pct}%)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ═══ BAR CHART ═══ */
interface BarChartProps {
  data: { label: string; value: number; color?: string }[];
  title: string;
  height?: number;
}

export function BarChart({ data, title, height = 280 }: BarChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref);
  if (data.length === 0) return <EmptyChart title={title} ref={ref} />;

  const maxVal = Math.max(...data.map(d => d.value), 1);
  const barWidth = Math.min(48, Math.max(20, (360 / data.length) - 10));
  const chartWidth = data.length * (barWidth + 14) + 40;

  return (
    <div ref={ref} className="glass-card-static rounded-3xl p-6 border border-sky-100/20 dark:border-sky-850/10" style={{ boxShadow: '0 8px 30px rgba(14,165,233,0.02)' }}>
      <h4 className="text-sm font-black text-sky-950 dark:text-sky-50 mb-5">{title}</h4>
      <div className="overflow-x-auto">
        <svg width="100%" height="100%" viewBox={`0 0 ${Math.max(chartWidth, 320)} ${height + 40}`} className="w-full h-auto max-h-[300px] mx-auto">
          {[0, 0.25, 0.5, 0.75, 1].map((f, i) => (
            <g key={i}>
              <line x1="38" y1={height - f * (height - 30)} x2={chartWidth} y2={height - f * (height - 30)} stroke="rgba(14,165,233,0.08)" strokeWidth="1.5" strokeDasharray="4,4" />
              <text x="32" y={height - f * (height - 30) + 4} textAnchor="end" className="fill-sky-500/60 font-bold" fontSize="11">{Math.round(maxVal * f)}</text>
            </g>
          ))}
          {data.map((d, i) => {
            const barH = (d.value / maxVal) * (height - 30);
            const x = 48 + i * (barWidth + 14);
            const y = height - barH;
            const color = d.color || CHART_COLORS[i % CHART_COLORS.length];
            return (
              <g key={i}>
                <rect x={x} y={inView ? y : height} width={barWidth} height={inView ? barH : 0} rx="5" fill={color} className="transition-all duration-750 ease-out hover:opacity-85" style={{ transitionDelay: `${i * 60}ms` }}>
                  <title>{d.label}: {d.value}</title>
                </rect>
                <text x={x + barWidth / 2} y={inView ? y - 8 : height - 8} textAnchor="middle" className="fill-sky-850 dark:fill-sky-200 font-extrabold transition-all duration-750" fontSize="11" style={{ transitionDelay: `${i * 60}ms`, opacity: inView ? 1 : 0 }}>{d.value}</text>
                <text x={x + barWidth / 2} y={height + 18} textAnchor="middle" className="fill-sky-500/60 font-bold" fontSize="10">{d.label.length > 10 ? d.label.slice(0, 9) + '…' : d.label}</text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

/* ═══ LINE CHART ═══ */
interface LineChartProps {
  data: { label: string; value: number }[];
  title: string;
  color?: string;
  height?: number;
}

export function LineChart({ data, title, color = '#0ea5e9', height = 240 }: LineChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref);
  if (data.length === 0) return <EmptyChart title={title} ref={ref} />;

  const maxVal = Math.max(...data.map(d => d.value), 1);
  const pad = { top: 15, right: 25, bottom: 35, left: 45 };
  const w = Math.max(data.length * 60, 360);
  const plotW = w - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const points = data.map((d, i) => ({
    x: pad.left + (i / Math.max(data.length - 1, 1)) * plotW,
    y: pad.top + plotH - (d.value / maxVal) * plotH,
    ...d,
  }));

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${height - pad.bottom} L ${points[0].x} ${height - pad.bottom} Z`;

  return (
    <div ref={ref} className="glass-card-static rounded-3xl p-6 border border-sky-100/20 dark:border-sky-850/10" style={{ boxShadow: '0 8px 30px rgba(14,165,233,0.02)' }}>
      <h4 className="text-sm font-black text-sky-950 dark:text-sky-50 mb-5">{title}</h4>
      <div className="overflow-x-auto">
        <svg width="100%" height="100%" viewBox={`0 0 ${w} ${height}`} className="w-full h-auto max-h-[260px] mx-auto">
          {[0, 0.25, 0.5, 0.75, 1].map((f, i) => (
            <g key={i}>
              <line x1={pad.left} y1={pad.top + plotH - f * plotH} x2={w - pad.right} y2={pad.top + plotH - f * plotH} stroke="rgba(14,165,233,0.06)" strokeWidth="1.5" />
              <text x={pad.left - 8} y={pad.top + plotH - f * plotH + 4} textAnchor="end" className="fill-sky-500/60 font-bold" fontSize="10">{Math.round(maxVal * f)}</text>
            </g>
          ))}
          <path d={areaPath} fill={`${color}15`} className="transition-opacity duration-1000" style={{ opacity: inView ? 1 : 0 }} />
          <path d={linePath} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="transition-all duration-1000" strokeDasharray={inView ? '0' : '2000'} strokeDashoffset={inView ? '0' : '2000'} />
          {points.map((p, i) => (
            <g key={i}>
              <circle cx={p.x} cy={p.y} r={inView ? 5 : 0} fill={color} stroke="white" strokeWidth="2.5" className="transition-all duration-500 hover:scale-125" style={{ transitionDelay: `${i * 60}ms` }}>
                <title>{p.label}: {p.value}</title>
              </circle>
              <text x={p.x} y={height - pad.bottom + 18} textAnchor="middle" className="fill-sky-500/60 font-bold" fontSize="9">{p.label.length > 8 ? p.label.slice(0, 7) + '…' : p.label}</text>
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}

/* ═══ HISTOGRAM CHART ═══ */
interface HistogramProps {
  data: { label: string; value: number }[];
  title: string;
  color?: string;
  height?: number;
}

export function HistogramChart({ data, title, color = '#6366f1', height = 260 }: HistogramProps) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref);
  if (data.length === 0) return <EmptyChart title={title} ref={ref} />;

  const maxVal = Math.max(...data.map(d => d.value), 1);
  const barW = Math.max(26, Math.min(60, 360 / data.length));
  const chartW = data.length * (barW + 2) + 60;

  return (
    <div ref={ref} className="glass-card-static rounded-3xl p-6 border border-sky-100/20 dark:border-sky-850/10" style={{ boxShadow: '0 8px 30px rgba(14,165,233,0.02)' }}>
      <h4 className="text-sm font-black text-sky-950 dark:text-sky-50 mb-5">{title}</h4>
      <div className="overflow-x-auto">
        <svg width="100%" height="100%" viewBox={`0 0 ${Math.max(chartW, 320)} ${height + 30}`} className="w-full h-auto max-h-[280px] mx-auto">
          {data.map((d, i) => {
            const barH = (d.value / maxVal) * (height - 30);
            const x = 50 + i * (barW + 2);
            const y = height - barH;
            return (
              <g key={i}>
                <rect x={x} y={inView ? y : height} width={barW} height={inView ? barH : 0} fill={color} opacity="0.8" className="transition-all duration-500 hover:opacity-100" style={{ transitionDelay: `${i * 50}ms` }}>
                  <title>{d.label}: {d.value}</title>
                </rect>
                <text x={x + barW / 2} y={inView ? y - 6 : height - 6} textAnchor="middle" className="fill-sky-850 dark:fill-sky-200 font-extrabold transition-all duration-500" fontSize="10" style={{ transitionDelay: `${i * 50}ms`, opacity: inView ? 1 : 0 }}>{d.value}</text>
                <text x={x + barW / 2} y={height + 16} textAnchor="middle" className="fill-sky-500/60 font-bold" fontSize="9">{d.label}</text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
