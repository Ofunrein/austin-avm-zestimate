"use client";
interface ZipRow { zip_code: string; medape: number; n_sales: number; mae: number }

export function ZipAccuracyTable({ rows }: { rows: ZipRow[] }) {
  const fmt = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-100">
        <h3 className="text-sm font-semibold text-zinc-700">Accuracy by ZIP Code</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 text-zinc-500 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">ZIP</th>
              <th className="px-4 py-3 text-right">MedAPE</th>
              <th className="px-4 py-3 text-right">MAE</th>
              <th className="px-4 py-3 text-right">N Sales</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {rows.map((r) => (
              <tr key={r.zip_code} className="hover:bg-zinc-50">
                <td className="px-4 py-3 font-mono text-zinc-700">{r.zip_code}</td>
                <td className="px-4 py-3 text-right">
                  <span className={`font-medium ${r.medape < 4 ? "text-emerald-600" : r.medape < 6 ? "text-amber-600" : "text-red-600"}`}>
                    {r.medape.toFixed(2)}%
                  </span>
                </td>
                <td className="px-4 py-3 text-right text-zinc-600">{fmt(r.mae)}</td>
                <td className="px-4 py-3 text-right text-zinc-500">{r.n_sales.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
