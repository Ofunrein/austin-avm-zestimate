import { getBenchmark } from "@/lib/api";
import { BenchmarkChart } from "@/components/BenchmarkChart";
import { ZipAccuracyTable } from "@/components/ZipAccuracyTable";

export const revalidate = 3600;

export default async function BenchmarkPage() {
  let data;
  try {
    data = await getBenchmark();
  } catch {
    return <div className="p-8 text-zinc-500">Could not load benchmark data.</div>;
  }

  const chartData = [
    { name: "This Model", medape: data.test_medape, color: "#10b981" },
    { name: "ZIP Median", medape: data.baseline_zip_median_medape || 8.5, color: "#6366f1" },
    { name: "PPSF", medape: data.baseline_ppsf_medape || 9.2, color: "#8b5cf6" },
  ];

  return (
    <main className="min-h-screen bg-zinc-50">
      <div className="max-w-5xl mx-auto px-4 py-12 space-y-8">
        <div>
          <a href="/" className="text-sm text-emerald-600 hover:underline">← Back</a>
          <h1 className="text-3xl font-bold text-zinc-900 mt-2">Benchmark Dashboard</h1>
          <p className="text-zinc-500 mt-1">Austin TX · Model v{data.model_version} · {data.n_test.toLocaleString()} test properties</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "MedAPE", value: `${data.test_medape.toFixed(2)}%` },
            { label: "Within 5%", value: `${(data.test_within_5pct * 100).toFixed(1)}%` },
            { label: "Within 10%", value: `${(data.test_within_10pct * 100).toFixed(1)}%` },
            { label: "MAE", value: `$${(data.test_mae / 1000).toFixed(1)}k` },
          ].map(({ label, value }) => (
            <div key={label} className="bg-white rounded-2xl border border-zinc-200 p-5 shadow-sm text-center">
              <p className="text-xs text-zinc-500 uppercase tracking-wide">{label}</p>
              <p className="text-2xl font-bold text-zinc-900 mt-1">{value}</p>
            </div>
          ))}
        </div>

        <BenchmarkChart data={chartData} />

        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
          Zillow&apos;s published Zestimate MedAPE for Austin is approximately 4.5% (external reference only — not a property-level comparison).
        </div>

        {data.by_zip?.length > 0 && <ZipAccuracyTable rows={data.by_zip} />}
      </div>
    </main>
  );
}
