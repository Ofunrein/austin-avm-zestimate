"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from "recharts";

interface BenchmarkBar {
  name: string;
  medape: number;
  color: string;
}

export function BenchmarkChart({ data }: { data: BenchmarkBar[] }) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-zinc-700 mb-1">MedAPE Comparison</h3>
      <p className="text-xs text-zinc-400 mb-4">Lower is better · Zillow ~4.5% shown as external reference</p>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ bottom: 8 }}>
          <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#52525b" }} />
          <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} domain={[0, "auto"]} />
          <Tooltip formatter={(v) => [typeof v === "number" ? `${v.toFixed(2)}%` : v, "MedAPE"]} />
          <ReferenceLine y={4.5} stroke="#f59e0b" strokeDasharray="4 2" label={{ value: "Zillow ~4.5%", position: "right", fontSize: 11, fill: "#f59e0b" }} />
          <Bar dataKey="medape" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
