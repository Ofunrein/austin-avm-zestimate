"use client";
import { SearchResult } from "@/lib/api";

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

function SourceChip({ source }: { source?: string }) {
  const label = !source || source === "kaggle_historical" ? "HISTORICAL"
    : source === "active_listing" ? "LIVE SAMPLE"
    : "CACHED";
  return (
    <span style={{
      fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
      letterSpacing: "0.12em", textTransform: "uppercase",
      padding: "2px 7px",
      background: "var(--bg-3)",
      color: "var(--mute)",
      border: "1px solid var(--line-2)",
    }}>
      {label}
    </span>
  );
}

interface Props {
  results: SearchResult[];
  total: number;
  query: string;
  onClear: () => void;
}

export function SearchResults({ results, total, query, onClear }: Props) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div>
          <span className="t-mono" style={{ fontSize: 11, color: 'var(--gold)' }}>{total} RESULTS</span>
          <span className="t-mono" style={{ fontSize: 11, color: 'var(--mute)', marginLeft: 8 }}>FOR &quot;{query.toUpperCase()}&quot;</span>
        </div>
        <button onClick={onClear} className="btn-ghost" style={{ fontSize: 10 }}>← CLEAR QUERY</button>
      </div>

      {results.length === 0 ? (
        <div className="panel" style={{ padding: '32px', textAlign: 'center' }}>
          <p className="t-eyebrow">NO MATCHING PROPERTIES · TRY ADJUSTING QUERY</p>
        </div>
      ) : (
        <div className="grid-search-results">
          {results.map((r) => (
            <div key={r.id} className="panel tick-corners" style={{ padding: 0 }}>
              <div style={{ padding: '14px 14px 12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <p className="t-mono" style={{ fontSize: 11, color: 'var(--ink-2)', margin: 0, maxWidth: 160, lineHeight: 1.4 }}>
                    {(r.address || 'ADDR UNAVAILABLE').toUpperCase()}
                  </p>
                  {r.value_gap_pct != null && r.value_gap_pct > 0 && (
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: 10.5, fontWeight: 700,
                      color: '#fff', background: 'var(--gold)',
                      padding: '2px 7px', letterSpacing: '0.06em', flexShrink: 0
                    }}>
                      +{r.value_gap_pct.toFixed(1)}%
                    </span>
                  )}
                </div>
                <div style={{ marginBottom: 8 }}>
                  <SourceChip source={r.data_source} />
                </div>
                <div className="t-mono glitch-in" style={{ fontSize: 22, color: 'var(--ink)', letterSpacing: '-0.01em' }}>
                  {fmt(r.predicted_price)}
                </div>
                <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                  {r.zip_code && <span className="t-eyebrow">{r.zip_code}</span>}
                  {r.beds != null && <span className="t-eyebrow">{r.beds}BD</span>}
                  {r.baths_full != null && <span className="t-eyebrow">{r.baths_full}BA</span>}
                  {r.sqft_living != null && <span className="t-eyebrow">{r.sqft_living.toLocaleString()}SF</span>}
                </div>
                <div style={{ marginTop: 10 }}>
                  <div className="conf-segments">
                    {Array.from({ length: 16 }).map((_, i) => (
                      <div key={i} className={`conf-seg${i < Math.round(r.confidence_score / 100 * 16) ? ' on' : ''}`} />
                    ))}
                  </div>
                </div>
                {r.neighborhood_summary && (
                  <div className="t-mono" style={{ fontSize: 10, color: 'var(--mute)', marginTop: 6 }}>
                    {r.neighborhood_summary}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
