"use client";
import { useEffect, useCallback, useState } from "react";
import { OpportunityItem } from "@/lib/api";
import { OpportunityCard } from "@/components/OpportunityCard";

const proxyImg = (url?: string | null) =>
  url ? `/api/img-proxy?url=${encodeURIComponent(url)}` : undefined;

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

function SourceChip({ source }: { source?: string }) {
  const label = !source || source === "kaggle_historical" ? "HISTORICAL"
    : source === "active_listing" ? "LIVE SAMPLE"
    : source === "upload" ? "UPLOAD"
    : "CACHED";
  return (
    <span style={{
      fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
      letterSpacing: "0.12em", textTransform: "uppercase",
      padding: "2px 7px",
      background: label === "LIVE SAMPLE" ? "rgba(79,179,165,0.12)" : "rgba(255,255,255,0.08)",
      color: label === "LIVE SAMPLE" ? "var(--teal)" : "rgba(255,255,255,0.5)",
      border: `1px solid ${label === "LIVE SAMPLE" ? "var(--teal)" : "rgba(255,255,255,0.15)"}`,
    }}>
      {label}
    </span>
  );
}

function Lightbox({
  items,
  index,
  onClose,
  onPrev,
  onNext,
}: {
  items: OpportunityItem[];
  index: number;
  onClose: () => void;
  onPrev: () => void;
  onNext: () => void;
}) {
  const item = items[index];
  const gap = item.value_gap_pct;
  const isHot = gap >= 20;
  const filled = Math.round((item.confidence_score / 100) * 20);
  const img = proxyImg(item.photo_url);
  const hasPrev = index > 0;
  const hasNext = index < items.length - 1;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && hasPrev) onPrev();
      if (e.key === "ArrowRight" && hasNext) onNext();
    };
    window.addEventListener("keydown", handler);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handler);
      document.body.style.overflow = "";
    };
  }, [onClose, onPrev, onNext, hasPrev, hasNext]);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 200,
        background: "rgba(0,0,0,0.78)",
        backdropFilter: "blur(6px)",
        WebkitBackdropFilter: "blur(6px)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "24px 80px",
      }}
    >
      {/* Left arrow */}
      <button
        onClick={(e) => { e.stopPropagation(); onPrev(); }}
        disabled={!hasPrev}
        style={{
          position: "fixed", left: 0, top: "50%", transform: "translateY(-50%)",
          width: 64, height: "100%", border: "none", background: "transparent",
          cursor: hasPrev ? "pointer" : "default",
          display: "flex", alignItems: "center", justifyContent: "center",
          opacity: hasPrev ? 1 : 0.2,
          color: "#fff",
          fontSize: 28,
          fontFamily: "var(--font-mono)",
          transition: "opacity 0.15s",
        }}
        aria-label="Previous"
      >
        ←
      </button>

      {/* Right arrow */}
      <button
        onClick={(e) => { e.stopPropagation(); onNext(); }}
        disabled={!hasNext}
        style={{
          position: "fixed", right: 0, top: "50%", transform: "translateY(-50%)",
          width: 64, height: "100%", border: "none", background: "transparent",
          cursor: hasNext ? "pointer" : "default",
          display: "flex", alignItems: "center", justifyContent: "center",
          opacity: hasNext ? 1 : 0.2,
          color: "#fff",
          fontSize: 28,
          fontFamily: "var(--font-mono)",
          transition: "opacity 0.15s",
        }}
        aria-label="Next"
      >
        →
      </button>

      {/* Modal card */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%", maxWidth: 720,
          background: "var(--bg-1)",
          border: "1px solid var(--line-2)",
          boxShadow: "0 32px 80px rgba(0,0,0,0.6)",
          overflowY: "auto",
          maxHeight: "calc(100vh - 48px)",
          position: "relative",
        }}
      >
        {/* Close */}
        <button
          onClick={onClose}
          style={{
            position: "absolute", top: 10, right: 12, zIndex: 10,
            background: "rgba(0,0,0,0.55)", border: "1px solid rgba(255,255,255,0.1)",
            color: "#fff", fontSize: 14, fontFamily: "var(--font-mono)",
            padding: "3px 9px", cursor: "pointer", letterSpacing: "0.06em",
          }}
        >
          ✕
        </button>

        {/* Hero image */}
        {img && (
          <div style={{ position: "relative", width: "100%", background: "#000" }}>
            <img
              src={img}
              alt={item.address || "Property"}
              referrerPolicy="no-referrer"
              style={{ width: "100%", maxHeight: 480, objectFit: "contain", display: "block" }}
              onError={(e) => { (e.target as HTMLImageElement).parentElement!.style.display = "none"; }}
            />
            <div style={{
              position: "absolute", inset: 0,
              background: "linear-gradient(to bottom, transparent 40%, rgba(0,0,0,0.65) 100%)",
            }} />
            {/* Address overlay */}
            <div style={{
              position: "absolute", bottom: 14, left: 16, right: 52,
              fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 700,
              color: "#fff", letterSpacing: "0.08em",
              textShadow: "0 1px 4px rgba(0,0,0,0.8)",
            }}>
              {(item.address || "").toUpperCase()}
            </div>
            {/* Index counter */}
            <div style={{
              position: "absolute", bottom: 14, right: 16,
              fontFamily: "var(--font-mono)", fontSize: 10,
              color: "rgba(255,255,255,0.55)", letterSpacing: "0.08em",
            }}>
              {index + 1}/{items.length}
            </div>
          </div>
        )}

        {/* Header row */}
        <div className="panel-head" style={{ padding: "10px 16px" }}>
          <div className="panel-dot" style={isHot ? { background: "var(--gold)" } : {}} />
          <span className="panel-label" style={{ maxWidth: img ? 200 : "none", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {img ? (item.zip_code || "—") : (item.address || "ADDR UNKNOWN").toUpperCase()}
          </span>
          <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
            <SourceChip source={item.data_source} />
            <span style={{
              fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 700,
              color: "#fff", background: isHot ? "var(--gold)" : "var(--mute-2)",
              padding: "3px 10px", letterSpacing: "0.06em",
            }}>
              +{gap.toFixed(1)}%
            </span>
          </span>
        </div>

        {/* Prices */}
        <div style={{ padding: "18px 16px 0", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <div className="t-eyebrow" style={{ marginBottom: 6 }}>HISTORICAL PRICE</div>
            <div className="t-mono" style={{ fontSize: 22, color: "var(--ink-2)" }}>
              {item.list_price ? fmt(item.list_price) : "—"}
            </div>
          </div>
          <div>
            <div className="t-eyebrow" style={{ marginBottom: 6 }}>AVM ESTIMATE</div>
            <div className="t-mono" style={{ fontSize: 22, color: "var(--gold)", fontWeight: 600 }}>
              {fmt(item.predicted_price)}
            </div>
          </div>
        </div>

        {/* Property details */}
        <div style={{ padding: "14px 16px 0", display: "flex", flexWrap: "wrap", gap: 12 }}>
          {item.zip_code      && <span className="t-eyebrow">{item.zip_code}</span>}
          {item.beds   != null && <span className="t-eyebrow">{item.beds} BD</span>}
          {item.baths_full != null && <span className="t-eyebrow">{item.baths_full} BA</span>}
          {item.sqft_living != null && <span className="t-eyebrow">{item.sqft_living.toLocaleString()} SF</span>}
          {item.year_built != null && <span className="t-eyebrow">BUILT {item.year_built}</span>}
        </div>

        {/* Condition note */}
        {item.condition_note && (
          <p className="t-mono" style={{
            fontSize: 11, color: "var(--mute)", margin: "12px 16px 0",
            lineHeight: 1.5, borderLeft: "2px solid var(--line-2)", paddingLeft: 8,
          }}>
            &quot;{item.condition_note}&quot;
          </p>
        )}

        {/* Confidence */}
        <div style={{ padding: "16px 16px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span className="t-eyebrow">CONFIDENCE</span>
            <span className="t-mono" style={{ fontSize: 11, color: "var(--gold)", fontWeight: 600 }}>
              {item.confidence_score}/100
            </span>
          </div>
          <div className="conf-segments">
            {Array.from({ length: 20 }).map((_, i) => (
              <div key={i} className={`conf-seg${i < filled ? " on" : ""}`} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function OpportunityGallery({ items }: { items: OpportunityItem[] }) {
  const [selectedIndex, setSelected] = useState<number | null>(null);

  const close = useCallback(() => setSelected(null), []);
  const prev  = useCallback(() => setSelected(i => (i !== null && i > 0 ? i - 1 : i)), []);
  const next  = useCallback(() => setSelected(i => (i !== null && i < items.length - 1 ? i + 1 : i)), [items.length]);

  return (
    <>
      <div className="grid-deals">
        {items.map((item, idx) => (
          <div
            key={item.id}
            onClick={() => setSelected(idx)}
            style={{ cursor: "pointer" }}
          >
            <OpportunityCard item={item} />
          </div>
        ))}
      </div>

      {selectedIndex !== null && (
        <Lightbox
          items={items}
          index={selectedIndex}
          onClose={close}
          onPrev={prev}
          onNext={next}
        />
      )}
    </>
  );
}
