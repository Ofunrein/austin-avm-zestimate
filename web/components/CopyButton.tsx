"use client";
import { useState } from "react";

export function CopyButton({ text, onClick }: { text?: string | null; onClick?: (e: React.MouseEvent) => void }) {
  const [copied, setCopied] = useState(false);

  if (!text) return null;

  const handle = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClick?.(e);
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  return (
    <button
      onClick={handle}
      title={`Copy: ${text}`}
      style={{
        background: "transparent",
        border: "none",
        padding: "2px 5px",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        color: copied ? "var(--teal)" : "var(--mute)",
        transition: "color 0.15s",
        flexShrink: 0,
      }}
      aria-label="Copy address"
    >
      {copied ? (
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
          <polyline points="2,7 5,10 11,3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ) : (
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
          <rect x="4" y="1" width="8" height="9" rx="1" stroke="currentColor" strokeWidth="1.3"/>
          <path d="M2 4H1.5A.5.5 0 0 0 1 4.5v7A.5.5 0 0 0 1.5 12h7a.5.5 0 0 0 .5-.5V11" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
        </svg>
      )}
    </button>
  );
}
