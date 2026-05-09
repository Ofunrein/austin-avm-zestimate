import { getBenchmark } from "@/lib/api";
import { BenchmarkChart } from "@/components/BenchmarkChart";
import { ZipAccuracyTable } from "@/components/ZipAccuracyTable";

export const revalidate = 3600;

export default async function BenchmarkPage() {
  let data;
  try {
    data = await getBenchmark();
  } catch {
    return (
      <main style={{ minHeight: '100vh', background: 'var(--bg)', padding: '32px 28px' }}>
        <p className="t-mono" style={{ color: 'var(--red)', fontSize: 12 }}>ERR · COULD NOT LOAD BENCHMARK DATA</p>
      </main>
    );
  }

  const chartData = [
    ...(data.test_medape != null
      ? [{ name: "THIS MODEL", medape: data.test_medape, color: 'var(--gold)' }]
      : []),
    ...(data.baseline_zip_median_medape != null
      ? [{ name: "ZIP MEDIAN", medape: data.baseline_zip_median_medape, color: '#4a4842' }]
      : []),
    ...(data.baseline_ppsf_medape != null
      ? [{ name: "PPSF", medape: data.baseline_ppsf_medape, color: '#3a3a45' }]
      : []),
  ];

  const stats = [
    { label: "MEDAPE", value: data.test_medape != null ? `${data.test_medape.toFixed(2)}%` : "—", gold: true },
    { label: "WITHIN 5%", value: data.test_within_5pct != null ? `${(data.test_within_5pct * 100).toFixed(1)}%` : "—" },
    { label: "WITHIN 10%", value: data.test_within_10pct != null ? `${(data.test_within_10pct * 100).toFixed(1)}%` : "—" },
    { label: "MAE", value: data.test_mae != null ? `$${(data.test_mae / 1000).toFixed(1)}K` : "—" },
    { label: "TEST N", value: data.n_test != null ? data.n_test.toLocaleString() : "—" },
    { label: "MODEL VER", value: `V${data.model_version}` },
  ];

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', padding: '32px 28px 64px' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto' }}>
        <a href="/" className="btn-ghost" style={{ display: 'inline-block', marginBottom: 24 }}>← BACK</a>
        <div style={{ marginBottom: 28 }}>
          <div className="t-eyebrow" style={{ marginBottom: 8 }}>MODEL PERFORMANCE · TEMPORAL CV · AUSTIN TX</div>
          <h1 className="t-display" style={{ fontSize: 36, margin: 0, color: 'var(--ink)' }}>
            Benchmark <span style={{ color: 'var(--gold)' }}>Dashboard</span>
          </h1>
        </div>

        {/* Stats grid */}
        <div className="grid-stats-6">
          {stats.map(({ label, value, gold }) => (
            <div key={label} className="panel" style={{ padding: '16px 14px', border: 'none', background: 'var(--bg-1)' }}>
              <div className="t-eyebrow" style={{ marginBottom: 6 }}>{label}</div>
              <div className="t-mono" style={{ fontSize: 18, color: gold ? 'var(--gold)' : 'var(--ink)' }}>{value}</div>
            </div>
          ))}
        </div>

        <BenchmarkChart data={chartData} />

        <div className="panel" style={{ padding: '12px 16px', margin: '14px 0', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 6, height: 6, background: '#e8a838', borderRadius: '50%', flexShrink: 0 }} />
          <p className="t-mono" style={{ fontSize: 11, color: 'var(--mute)', margin: 0 }}>
            ZILLOW PUBLISHED ZESTIMATE MEDAPE ~4.5% FOR AUSTIN · EXTERNAL REFERENCE ONLY · NOT A PROPERTY-LEVEL COMPARISON
          </p>
        </div>

        {data.by_zip?.length > 0 && <ZipAccuracyTable rows={data.by_zip} />}
      </div>
    </main>
  );
}
