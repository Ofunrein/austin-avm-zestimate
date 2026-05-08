"use client";
import { useState, FormEvent } from "react";

interface Props {
  onSearch: (query: string) => void;
  loading: boolean;
}

export function SearchBar({ onSearch, loading }: Props) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim()) onSearch(query.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className="flex items-center gap-3 rounded-2xl border border-zinc-200 bg-white px-4 py-3 shadow-sm focus-within:ring-2 focus-within:ring-emerald-500">
        <span className="text-emerald-500 text-lg flex-shrink-0">✦</span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Try "3BR under $400k in 78704" or "undervalued homes near downtown"'
          className="flex-1 bg-transparent text-sm text-zinc-800 placeholder:text-zinc-400 focus:outline-none"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="flex-shrink-0 rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-40 transition-colors"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>
    </form>
  );
}
