export default function ModelCardPage() {
  const sections = [
    {
      label: "01",
      title: "Model Details",
      content: `Primary model: XGBoost + LightGBM ensemble with Optuna hyperparameter tuning.
Prediction intervals: XGBoost quantile regression at α=0.05 and α=0.95 (90% CI).
Explanations: SHAP TreeExplainer, top 5 features per prediction.
Version: 1.0.0`,
    },
    {
      label: "02",
      title: "Training Data",
      content: `Sources: Kaggle Austin Housing Prices (ericpierce/austinhousingprices) + Travis County CAD bulk export + Compass Austin listings.
Date range: January 2018 – December 2023 (training), January 2024 – December 2024 (test).
Records after cleaning: ~40,000–47,000 Austin TX sales.
Geographic scope: Travis County, TX (ZIP codes 786xx–787xx).
COVID period (2020-Q2 to 2021-Q2) flagged as feature, not excluded.`,
    },
    {
      label: "03",
      title: "Validation",
      content: `Walk-forward temporal cross-validation: 5 folds, each fold trains on all data before its validation window (6-month windows). No random shuffle — prevents future data leakage.
Final test set: held-out 2024 sales (not seen during training or tuning).`,
    },
    {
      label: "04",
      title: "Intended Use",
      content: `Portfolio demonstration of production ML engineering practices. Suitable for: rough valuation reference, undervalued property screening, educational AVM benchmarking.
Not suitable for: mortgage underwriting, tax assessment disputes, legal valuation.`,
    },
    {
      label: "05",
      title: "Known Limitations",
      content: `Luxury homes (>$2M): underrepresented in training data, higher error expected.
New construction (<2 years old): often lacks comparable sales, may undervalue.
Interior quality: model cannot see renovation quality, condition upgrades, or custom finishes.
Market shifts: model trained on 2018–2023 data; rapid 2024+ market changes may degrade accuracy.
Geographic scope: Travis County only. Not valid for suburbs outside ZIP 786xx–787xx.`,
    },
    {
      label: "06",
      title: "Bias Analysis",
      content: `MedAPE reported by ZIP code. ZIPs in lowest median income quartile are flagged if error exceeds 2x the overall MedAPE — see Benchmark Dashboard for current values.`,
    },
    {
      label: "07",
      title: "Benchmark Reference",
      content: `Zillow's published Zestimate MedAPE for Austin TX is approximately 4.5% (as of their public accuracy report). This is an external contextual reference — not a property-level comparison against Zillow predictions.
Internal baselines: ZIP median and price-per-square-foot baselines measured on the same held-out test set.`,
    },
  ];

  return (
    <main style={{ minHeight: "100vh", background: "var(--bg)", padding: "32px 28px 64px" }}>
      <div className="page-container">
        <div style={{ marginBottom: 28 }}>
          <div className="t-eyebrow" style={{ marginBottom: 8 }}>SECTION 05 · MODEL CARD · XGB + LGB ENSEMBLE</div>
          <h1 className="t-display" style={{ fontSize: 36, margin: 0, color: "var(--ink)" }}>
            Model <span style={{ color: "var(--gold)" }}>Card</span>
          </h1>
        </div>
        {sections.map((s) => (
          <div key={s.title} className="panel tick-corners" style={{ marginBottom: 14 }}>
            <div className="panel-head">
              <div className="panel-dot" />
              <span className="t-mono" style={{ fontSize: 10, color: "var(--gold)", opacity: 0.6, marginRight: 4 }}>{s.label}</span>
              <span className="panel-label">{s.title.toUpperCase()}</span>
            </div>
            <div style={{ padding: "14px 18px 16px" }}>
              <pre className="t-mono" style={{
                fontSize: 12, color: "var(--ink-2)", lineHeight: 1.7,
                margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word"
              }}>
                {s.content}
              </pre>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
