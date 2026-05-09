import { UploadCanvas } from "@/components/UploadCanvas";

export default function UploadPage() {
  return (
    <main style={{ minHeight: "100vh", background: "var(--bg)", padding: "32px 28px 64px" }}>
      <div style={{ maxWidth: 1080, margin: "0 auto" }}>
        <a href="/" className="btn-ghost" style={{ display: "inline-block", marginBottom: 24 }}>← BACK</a>
        <div style={{ marginBottom: 24 }}>
          <div className="t-eyebrow" style={{ marginBottom: 8 }}>LISTING ANALYSIS · CSV UPLOAD</div>
          <h1 className="t-display" style={{ fontSize: 36, margin: "0 0 8px", color: "var(--ink)" }}>
            Upload <span style={{ color: "var(--gold)" }}>Listings</span>
          </h1>
          <p className="t-mono" style={{ fontSize: 12, color: "var(--mute)" }}>
            Score your own listing CSV. AVM predicts each property, ranks by model estimate vs list price.
          </p>
        </div>
        <div className="panel">
          <UploadCanvas />
        </div>
      </div>
    </main>
  );
}
