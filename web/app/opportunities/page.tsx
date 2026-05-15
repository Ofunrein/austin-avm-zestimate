import { getOpportunities } from "@/lib/api";
import { OpportunityGallery } from "@/components/OpportunityGallery";

export const revalidate = 120;

export default async function OpportunitiesPage() {
  let items;
  try {
    items = await getOpportunities({ limit: 50 });
  } catch {
    return (
      <main style={{ minHeight: "100vh", background: "var(--bg)", padding: "32px 28px" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto" }}>
          <a href="/" className="btn-ghost" style={{ display: "inline-block", marginBottom: 24 }}>← BACK</a>
          <p className="t-mono" style={{ color: "var(--red)", fontSize: 12 }}>ERR · COULD NOT LOAD OPPORTUNITIES · CHECK API CONNECTION</p>
        </div>
      </main>
    );
  }

  return (
    <main style={{ minHeight: "100vh", background: "var(--bg)", padding: "32px 28px 64px" }}>
      <div style={{ maxWidth: 1080, margin: "0 auto" }}>
        <a href="/" className="btn-ghost" style={{ display: "inline-block", marginBottom: 24 }}>← BACK</a>
        <div style={{ marginBottom: 28 }}>
          <div className="t-eyebrow" style={{ marginBottom: 8 }}>
            RESEARCH VIEW · HISTORICAL SALES BACKTEST · AUSTIN TX
          </div>
          <h1 className="t-display" style={{ fontSize: 36, margin: "0 0 8px", color: "var(--ink)" }}>
            Market <span style={{ color: "var(--gold)" }}>Opportunity</span> Analysis
          </h1>
          <div className="t-mono" style={{ fontSize: 12, color: "var(--mute)" }}>
            {items.length} PROPERTIES · MODEL ESTIMATE VS HISTORICAL SALE PRICE · KAGGLE 2018–2021
          </div>
          <div className="t-mono" style={{ fontSize: 11, color: "var(--gold)", marginTop: 8, padding: "6px 10px", background: "rgba(176,122,16,0.08)", borderLeft: "2px solid var(--gold)" }}>
            HISTORICAL DATA ONLY — NOT LIVE LISTINGS · FOR RESEARCH &amp; PORTFOLIO USE
          </div>
        </div>

        {items.length === 0 ? (
          <div className="panel" style={{ padding: "48px 32px", textAlign: "center" }}>
            <div className="t-eyebrow" style={{ marginBottom: 12 }}>NO DATA FOUND</div>
            <p className="t-mono" style={{ fontSize: 12, color: "var(--mute)" }}>
              BACKTEST RUNS WEEKLY · GITHUB ACTIONS · MONDAY 08:00 UTC
            </p>
          </div>
        ) : (
          <OpportunityGallery items={items} />
        )}
      </div>
    </main>
  );
}
