"use client";
import { PredictionResponse } from "@/lib/api";
import { CopyButton } from "@/components/CopyButton";

const proxyImg = (url?: string) =>
  url ? `/api/img-proxy?url=${encodeURIComponent(url)}` : undefined;

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

const fmtApprox = (n: number) =>
  "~" + new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(
    Math.round(n / 1000) * 1000
  );

function tier(score: number): "high" | "medium" | "low" {
  if (score >= 70) return "high";
  if (score >= 40) return "medium";
  return "low";
}

const TIER_CONFIG = {
  high:   { label: "AVM ESTIMATE · AUSTIN TX",       badge: null,                     color: "var(--gold)" },
  medium: { label: "DIRECTIONAL ESTIMATE",            badge: "USE AS GUIDANCE",        color: "var(--gold)" },
  low:    { label: "LOW-CONFIDENCE ESTIMATE",         badge: "⚠ DIRECTIONAL ONLY",    color: "var(--mute)" },
};

export function PredictionCard({ result, imageUrl, address: addr }: { result: PredictionResponse; imageUrl?: string; address?: string }) {
  const t = tier(result.confidence_score);
  const cfg = TIER_CONFIG[t];
  const segs = 20;
  const filled = Math.round((result.confidence_score / 100) * segs);
  const priceDisplay = t === "low" ? fmtApprox(result.predicted_price) : fmt(result.predicted_price);

  return (
    <div className="panel tick-corners" style={{ background: "var(--bg-1)" }}>
      {proxyImg(imageUrl) && (
        <div style={{
          position: "relative",
          width: "100%",
          height: 160,
          overflow: "hidden",
          borderRadius: "4px 4px 0 0",
        }}>
          <img
            src={proxyImg(imageUrl)}
            alt="Property"
            referrerPolicy="no-referrer"
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
          <div style={{
            position: "absolute", inset: 0,
            background: "linear-gradient(to bottom, transparent 40%, rgba(0,0,0,0.55) 100%)",
          }} />
        </div>
      )}
      <div className="panel-head">
        <div className="panel-dot" style={t === "low" ? { background: "var(--mute-2)" } : {}} />
        <span className="panel-label">{cfg.label}</span>
        <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4 }}>
          <CopyButton text={addr} />
          <span className="panel-meta">MODEL v{result.model_version} · 90% CI</span>
        </span>
      </div>

      {t === "low" && (
        <div style={{
          background: "rgba(192,57,43,0.07)", borderBottom: "1px solid var(--red-soft)",
          padding: "8px 20px",
        }}>
          <span style={{ color: "var(--red)", fontSize: 10, fontFamily: "var(--font-mono)", fontWeight: 700, letterSpacing: "0.1em" }}>
            LOW CONFIDENCE — WIDE RANGE — TREAT AS DIRECTIONAL ONLY
          </span>
        </div>
      )}

      <div style={{ padding: "20px 20px 12px", textAlign: "center" }}>
        {cfg.badge && (
          <div className="t-eyebrow" style={{ marginBottom: 8, color: t === "low" ? "var(--red)" : "var(--mute)" }}>
            {cfg.badge}
          </div>
        )}
        <div className={`t-mono${t !== "low" ? " glitch-in" : ""}`} style={{
          fontSize: t === "low" ? 38 : 48,
          color: cfg.color, letterSpacing: "-0.02em", lineHeight: 1, fontWeight: 600,
          opacity: t === "low" ? 0.75 : 1,
        }}>
          {priceDisplay}
        </div>
        <div className="t-mono" style={{ fontSize: 12, color: "var(--ink-2)", marginTop: 8, letterSpacing: "0.04em" }}>
          {fmt(result.lower_bound)} <span style={{ color: "var(--mute)" }}>→</span> {fmt(result.upper_bound)}
        </div>
      </div>

      <div style={{ padding: "0 20px 16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
          <span className="t-eyebrow">CONFIDENCE</span>
          <span className="t-mono" style={{
            fontSize: 11, fontWeight: 700,
            color: t === "high" ? "var(--gold)" : t === "medium" ? "var(--ink-2)" : "var(--mute)",
          }}>
            {result.confidence_score}/100
          </span>
        </div>
        <div className="conf-segments">
          {Array.from({ length: segs }).map((_, i) => (
            <div
              key={i}
              className={`conf-seg${i < filled ? " on" : ""}`}
              style={i < filled && t === "low" ? { background: "var(--mute-2)", borderColor: "var(--mute)" } : {}}
            />
          ))}
        </div>
      </div>

      {t === "low" && (
        <div style={{ margin: "0 16px 16px", padding: "10px 14px", background: "var(--bg-2)", border: "1px solid var(--line-2)" }}>
          <div className="t-eyebrow" style={{ marginBottom: 6 }}>IMPROVE THIS ESTIMATE</div>
          {["Add property details manually", "Review comparable sales", "Upload a listings CSV"].map(s => (
            <div key={s} className="t-mono" style={{ fontSize: 11, color: "var(--mute)", marginBottom: 3 }}>· {s}</div>
          ))}
        </div>
      )}
    </div>
  );
}
