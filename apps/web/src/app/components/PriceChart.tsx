"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Point = { date: string; value: number };

const RANGES: [string, number][] = [
  ["1Y", 12],
  ["5Y", 60],
  ["10Y", 120],
  ["Max", 0],
];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export default function PriceChart({ points, unit }: { points: Point[]; unit: string }) {
  const [range, setRange] = useState("10Y");
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const data = useMemo(() => {
    const months = RANGES.find((r) => r[0] === range)?.[1] ?? 0;
    return months ? points.slice(-months) : points;
  }, [points, range]);

  // One tick per label, no repeats: every 2nd month for 1Y, otherwise one January per N years.
  const ticks = useMemo(() => {
    if (range === "1Y") return data.filter((_, i) => i % 2 === 0).map((p) => p.date);
    const years = data.length / 12;
    const step = range === "5Y" ? 1 : range === "10Y" ? 2 : Math.max(1, Math.ceil(years / 8));
    const out: string[] = [];
    let last = -Infinity;
    for (const p of data) {
      const y = Number(p.date.slice(0, 4));
      if (p.date.slice(5, 7) === "01" && y - last >= step) {
        out.push(p.date);
        last = y;
      }
    }
    return out;
  }, [data, range]);

  const tickLabel = (d: string) =>
    range === "1Y" ? `${MONTHS[Number(d.slice(5, 7)) - 1]} ${d.slice(2, 4)}` : d.slice(0, 4);

  return (
    <div>
      <div className="mb-3 flex gap-1">
        {RANGES.map(([label]) => {
          const active = range === label;
          return (
            <button
              key={label}
              type="button"
              aria-pressed={active}
              onClick={() => setRange(label)}
              className={`meta border px-3 py-1 ${
                active ? "border-ink bg-ink" : "border-rule hover:border-ink"
              }`}
              style={active ? { color: "#f6f3ec", background: "#1c1b19" } : undefined}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div className="border-t border-ink" style={{ width: "100%", height: 320 }}>
        {!mounted ? (
          <p className="meta pt-3">Loading chart…</p>
        ) : data.length < 2 ? (
          <p className="meta pt-3">Not enough data for this range.</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 16, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#d9d3c4" vertical={false} />
              <XAxis
                dataKey="date"
                ticks={ticks}
                tickFormatter={tickLabel}
                tick={{ fontSize: 11 }}
                stroke="#55524b"
              />
              <YAxis width={56} tick={{ fontSize: 11 }} stroke="#55524b" domain={["auto", "auto"]} />
              <Tooltip
                formatter={(v) =>
                  [`${Number(v).toLocaleString()} ${unit}`, "Monthly average"] as [string, string]
                }
                labelFormatter={(l) => String(l).slice(0, 7)}
                contentStyle={{ background: "#f6f3ec", border: "1px solid #1c1b19", borderRadius: 0, fontSize: 12 }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#1c1b19"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}