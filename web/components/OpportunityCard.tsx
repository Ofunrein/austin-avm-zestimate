import { OpportunityItem } from "@/lib/api";

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
      background: label === "LIVE SAMPLE" ? "rgba(79,179,165,0.12)" : "var(--bg-3)",
      color: label === "LIVE SAMPLE" ? "var(--teal)" : "var(--mute)",
      border: `1px solid ${label === "LIVE SAMPLE" ? "var(--teal)" : "var(--line-2)"}`,
    }}>
      {label}
    </span>
  );
}

export function OpportunityCard({ item }: { item: OpportunityItem }) {
  const gap = item.value_gap_pct;
  const isHot = gap >= 20;
  const filled = Math.round((item.confidence_score / 100) * 14);

  return (
    <div className="panel tick-corners" style={{ overflow: "hidden" }}>
      {item.photo_url && (
        <div style={{
          position: "relative",
          width: "100%",
          height: 140,
          overflow: "hidden",
          borderRadius: "4px 4px 0 0",
        }}>
          <img
            src={item.photo_url}
            alt={item.address || "Property"}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            onError={(e) => { (e.target as HTMLImageElement).parentElement!.style.display = "none"; }}
          />
          <div style={{
            position: "absolute", inset: 0,
            background: "linear-gradient(to bottom, transparent 30%, rgba(0,0,0,0.6) 100%)",
          }} />
          <div style={{
            position: "absolute", bottom: 8, left: 10, right: 10,
            fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 700,
            color: "rgba(255,255,255,0.85)", letterSpacing: "0.08em",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            {(item.address || "").toUpperCase()}
          </div>
        </div>
      )}
      <div className="panel-head">
        <div className="panel-dot" style={isHot ? { background: "var(--gold)" } : {}} />
        <span className="panel-label" style={{ maxWidth: 150, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {(item.address || "ADDR UNKNOWN").toUpperCase()}
        </span>
        <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
          <SourceChip source={item.data_source} />
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700,
            color: "#fff", background: isHot ? "var(--gold)" : "var(--mute-2)",
            padding: "2px 8px", letterSpacing: "0.06em",
          }}>
            +{gap.toFixed(1)}%
          </span>
        </span>
      </div>
      <div style={{ padding: "14px 14px 16px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
          <div>
            <div className="t-eyebrow" style={{ marginBottom: 4 }}>HISTORICAL PRICE</div>
            <div className="t-mono" style={{ fontSize: 15, color: "var(--ink-2)" }}>
              {item.list_price ? fmt(item.list_price) : "—"}
            </div>
          </div>
          <div>
            <div className="t-eyebrow" style={{ marginBottom: 4 }}>AVM ESTIMATE</div>
            <div className="t-mono" style={{ fontSize: 15, color: "var(--gold)", fontWeight: 600 }}>
              {fmt(item.predicted_price)}
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
          {item.zip_code      && <span className="t-eyebrow">{item.zip_code}</span>}
          {item.beds   != null && <span className="t-eyebrow">{item.beds}BD</span>}
          {item.baths_full != null && <span className="t-eyebrow">{item.baths_full}BA</span>}
          {item.sqft_living != null && <span className="t-eyebrow">{item.sqft_living.toLocaleString()}SF</span>}
        </div>
        {item.condition_note && (
          <p className="t-mono" style={{ fontSize: 11, color: "var(--mute)", margin: "0 0 12px", lineHeight: 1.5, borderLeft: "2px solid var(--line-2)", paddingLeft: 8 }}>
            &quot;{item.condition_note}&quot;
          </p>
        )}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
            <span className="t-eyebrow">CONFIDENCE</span>
            <span className="t-mono" style={{ fontSize: 10, color: "var(--gold)", fontWeight: 600 }}>{item.confidence_score}%</span>
          </div>
          <div className="conf-segments">
            {Array.from({ length: 14 }).map((_, i) => (
              <div key={i} className={`conf-seg${i < filled ? " on" : ""}`} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
