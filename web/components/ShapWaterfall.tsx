"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { ShapFeature } from "@/lib/api";

const LABELS: Record<string, string> = {
  sqft_living:             "Living Area",
  lot_sqft:                "Lot Size",
  beds:                    "Bedrooms",
  baths_full:              "Full Baths",
  baths_half:              "Half Baths",
  bath_total:              "Total Baths",
  year_built:              "Year Built",
  age:                     "Property Age",
  effective_age:           "Effective Age",
  stories:                 "Stories",
  has_pool:                "Pool Present",
  has_garage:              "Garage Present",
  garage_spaces:           "Garage Spaces",
  sqft_per_bed:            "Sqft per Bedroom",
  lot_to_living_ratio:     "Lot/Living Ratio",
  dist_downtown_miles:     "Distance to Downtown",
  zip_income_score:        "ZIP Income Score",
  zip_encoded:             "Neighborhood Signal",
  median_zip_price_90d:    "Recent ZIP Median Price",
  median_zip_ppsf_90d:     "Recent ZIP Price/Sqft",
  price_per_sqft_assessed: "Assessed $/Sqft",
  assessed_ratio:          "Assessed Value Ratio",
  is_covid_period:         "Covid Period Flag",
};

export function ShapWaterfall({ features }: { features: ShapFeature[] }) {
  const data = features.map((f) => ({
    name: LABELS[f.feature] ?? f.feature.toUpperCase(),
    value: f.shap_value,
    direction: f.direction,
  }));

  return (
    <div className="panel tick-corners scanlines">
      <div className="panel-head">
        <div className="panel-dot" />
        <span className="panel-label">SHAP · VALUE DRIVERS</span>
        <span className="panel-meta">XGB + LGB ENSEMBLE</span>
      </div>
      <div style={{ padding: '16px 16px 12px' }}>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} layout="vertical" margin={{ left: 0 }}>
            <XAxis
              type="number"
              tickFormatter={(v: number) => {
                const abs = Math.abs(v);
                if (abs >= 1000) return `$${(v / 1000).toFixed(0)}k`;
                if (abs >= 100)  return `$${v.toFixed(0)}`;
                return `$${v.toFixed(1)}`;
              }}
              tick={{ fontSize: 10, fill: 'var(--mute)', fontFamily: 'var(--font-mono)' }}
              axisLine={{ stroke: 'var(--line)' }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={112}
              tick={{ fontSize: 9.5, fill: 'var(--mute)', fontFamily: 'var(--font-mono)', letterSpacing: '0.1em' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{ background: 'var(--bg-2)', border: '1px solid var(--line)', borderRadius: 0, fontFamily: 'var(--font-mono)', fontSize: 11 }}
              labelStyle={{ color: 'var(--ink-2)' }}
              formatter={(v) => {
                if (typeof v !== "number") return [String(v), ""];
                const abs = Math.abs(v);
                const label = abs >= 1000
                  ? `${v > 0 ? "+" : ""}$${(v / 1000).toFixed(1)}k`
                  : `${v > 0 ? "+" : ""}$${v.toFixed(0)}`;
                return [label, "Impact"];
              }}
            />
            <Bar dataKey="value" radius={0} barSize={12}>
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.direction === "increases" ? 'var(--gold)' : 'var(--red)'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 10, height: 10, background: 'var(--gold)' }} />
            <span className="t-eyebrow">INCREASES VALUE</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 10, height: 10, background: 'var(--red)' }} />
            <span className="t-eyebrow">DECREASES VALUE</span>
          </div>
        </div>
      </div>
    </div>
  );
}
