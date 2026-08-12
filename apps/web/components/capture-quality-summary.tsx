import type { CaptureQualityReport, CaptureQualitySignal } from "@/lib/quality-contracts";

export function CaptureQualitySummary({ report }: { report: CaptureQualityReport }) {
  return (
    <section className={`capture-quality quality-${report.status}`} aria-labelledby="quality-title">
      <div className="result-heading">
        <div>
          <p className="section-label">Capture quality</p>
          <h3 id="quality-title">{report.status.toUpperCase()}</h3>
        </div>
        <p className="frame-count">{report.analysis_version}</p>
      </div>
      <div className="quality-grid">
        {report.signals.map((signal) => (
          <article className="metric-card" key={signal.name}>
            <span>{signal.name.replaceAll("_", " ")}</span>
            <strong>{formatSignal(signal)}</strong>
            <small>{signal.status} · {signal.explanation}</small>
          </article>
        ))}
      </div>
      {report.guidance.length > 0 && (
        <div>
          <h4>Recording guidance</h4>
          <ul>{report.guidance.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      )}
      <p className="chart-note">{report.interpretation}</p>
    </section>
  );
}

function formatSignal(signal: CaptureQualitySignal): string {
  if (signal.value === null) return "Unavailable";
  if (typeof signal.value === "boolean") return signal.value ? "Yes" : "No";
  if (signal.unit === "ratio") return `${Math.round(signal.value * 100)}%`;
  if (signal.unit === "millisecond") return `${Math.round(signal.value)} ms`;
  return String(signal.value);
}
