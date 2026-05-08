"use client";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { fetchRecentPredictions, PredictionRow } from "@/lib/supabase";

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

const fmtDate = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
};

export function RecentValuations() {
  const [rows, setRows] = useState<PredictionRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentPredictions(5).then(setRows).finally(() => setLoading(false));
  }, []);

  if (!loading && rows.length === 0) return null;

  return (
    <div className="rounded-xl border mt-6" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
      <div className="px-5 py-3 border-b" style={{ borderColor: "var(--border)" }}>
        <p className="text-xs uppercase tracking-widest" style={{ color: "var(--text-subtle)" }}>Recent Valuations</p>
      </div>
      {loading ? (
        <div className="px-5 py-4 space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-4 rounded animate-pulse" style={{ background: "var(--surface-raised)", width: `${60 + i * 10}%` }} />
          ))}
        </div>
      ) : (
        <AnimatePresence>
          <ul className="divide-y" style={{ borderColor: "var(--border)" }}>
            {rows.map((row, i) => (
              <motion.li key={row.id} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: i * 0.05 }}
                className="px-5 py-3 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate tabular-nums" style={{ color: "var(--accent)" }}>
                    {fmt(row.predicted_price)}
                  </p>
                  <p className="text-xs mt-0.5 truncate" style={{ color: "var(--text-muted)" }}>
                    {row.sqft_living.toLocaleString()} sqft · {row.beds}bd · ZIP {row.zip_code}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs tabular-nums" style={{ color: "var(--text-subtle)" }}>{fmtDate(row.created_at)}</p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--text-subtle)" }}>
                    conf <span style={{ color: row.confidence_score >= 70 ? "var(--accent)" : row.confidence_score >= 40 ? "#f59e0b" : "var(--red)" }}>
                      {row.confidence_score}
                    </span>/100
                  </p>
                </div>
              </motion.li>
            ))}
          </ul>
        </AnimatePresence>
      )}
    </div>
  );
}
