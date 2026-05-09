"use client";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { useEffect, useState } from "react";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const NAV_LINKS = [
  { href: "/",           label: "VALUATION" },
  { href: "/benchmark",  label: "BENCHMARK" },
  { href: "/scanner",    label: "SCANNER" },
  { href: "/deals",      label: "DEALS" },
  { href: "/model-card", label: "MODEL CARD" },
];

function TopNav() {
  const [theme, setTheme] = useState<"dark" | "light">("light");
  const [path, setPath] = useState("/");

  useEffect(() => {
    setPath(window.location.pathname);
    const saved = localStorage.getItem("avm-theme") as "dark" | "light" | null;
    if (saved) {
      setTheme(saved);
      document.documentElement.setAttribute("data-theme", saved);
    }
  }, []);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("avm-theme", next);
    document.documentElement.setAttribute("data-theme", next);
  };

  return (
    <nav className="topbar" style={{ position: "sticky", top: 0, zIndex: 100 }}>
      <span className="t-display" style={{ fontSize: 13, color: "var(--gold)", letterSpacing: "0.08em", flexShrink: 0 }}>AVM</span>
      <div style={{ width: 1, height: 20, background: "var(--line-2)", flexShrink: 0 }} />
      <div style={{ display: "flex", gap: 2, overflowX: "auto" }}>
        {NAV_LINKS.map(({ href, label }) => (
          <a
            key={href}
            href={href}
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 10.5,
              letterSpacing: "0.16em",
              color: path === href ? "var(--gold)" : "var(--mute)",
              padding: "0 12px",
              height: 44,
              display: "flex",
              alignItems: "center",
              borderBottom: path === href ? "2px solid var(--gold)" : "2px solid transparent",
              textDecoration: "none",
              whiteSpace: "nowrap",
              flexShrink: 0,
            }}
          >
            {label}
          </a>
        ))}
      </div>
      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
        <div className="pill" style={{ flexShrink: 0 }}>
          <div className="pill-pulse" />
          LIVE · ATX
        </div>
        <button
          onClick={toggleTheme}
          className="btn-ghost"
          style={{ padding: "6px 12px", fontSize: 10, letterSpacing: "0.14em" }}
          title="Toggle dark/light mode"
        >
          {theme === "dark" ? "☀ LIGHT" : "◑ DARK"}
        </button>
      </div>
    </nav>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <title>Austin AVM — Hyperlocal Valuation</title>
        <meta name="description" content="Bloomberg Terminal-grade home valuation for Austin, TX" />
        <script dangerouslySetInnerHTML={{ __html: `
          (function(){
            var t = localStorage.getItem('avm-theme') || 'light';
            document.documentElement.setAttribute('data-theme', t);
          })();
        `}} />
      </head>
      <body className="min-h-full flex flex-col" style={{ background: "var(--bg)" }}>
        <TopNav />
        {children}
      </body>
    </html>
  );
}
