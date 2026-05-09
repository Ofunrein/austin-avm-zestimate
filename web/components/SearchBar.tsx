"use client";
import { useState, FormEvent } from "react";

interface Props {
  onSearch: (query: string) => void;
  loading: boolean;
}

const SUGGESTIONS = [
  "3BR under $500k in 78744",
  "undervalued homes in 78725",
  "pool homes 78750 built after 2010",
];

export function SearchBar({ onSearch, loading }: Props) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim()) onSearch(query.trim());
  };

  return (
    <div className="panel tick-corners scanlines" style={{ background: 'var(--bg-1)' }}>
      <div className="panel-head">
        <div className="panel-dot" />
        <span className="panel-label">NL · QUERY</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--gold)', letterSpacing: '0.16em' }}>· /</span>
        <span className="panel-meta">CLAUDE PARSE → SUPABASE SQL</span>
      </div>
      <form onSubmit={handleSubmit}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '16px 20px' }}>
          <span className="t-mono" style={{ fontSize: 14, color: 'var(--gold)' }}>$</span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='QUERY → "3BR under $400K in 78704" · "undervalued homes near downtown"'
            disabled={loading}
            style={{
              flex: 1, background: 'transparent', border: 'none', outline: 'none',
              fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--ink)',
              letterSpacing: '0.02em',
            }}
          />
          {!loading && (
            <span style={{ width: 7, height: 14, background: 'var(--gold)' }} className="blink" />
          )}
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="btn-gold"
            style={{ width: 'auto', padding: '10px 20px' }}
          >
            {loading ? "SEARCHING…" : "EXECUTE ↵"}
          </button>
        </div>
        <div style={{ display: 'flex', gap: 8, padding: '0 20px 14px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span className="t-eyebrow" style={{ marginRight: 4 }}>SUGGEST →</span>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setQuery(s)}
              style={{
                background: 'transparent',
                border: '1px solid var(--line-2)',
                color: 'var(--ink-2)',
                fontFamily: 'var(--font-mono)',
                fontSize: 10.5, letterSpacing: '0.04em',
                padding: '4px 10px', cursor: 'pointer',
              }}
            >{s}</button>
          ))}
        </div>
      </form>
    </div>
  );
}
