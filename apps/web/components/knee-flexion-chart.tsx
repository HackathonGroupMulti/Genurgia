import {
  sampleDisplayValue,
  type KneeFlexionAnalysis,
  type KneeFlexionSeries,
} from "@/lib/knee-flexion-contracts";

const WIDTH = 760;
const HEIGHT = 280;
const PADDING = 42;

export function KneeFlexionChart({ analysis }: { analysis: KneeFlexionAnalysis }) {
  const allSamples = analysis.series.flatMap((series) => series.samples);
  const maxTime = Math.max(1, ...allSamples.map((sample) => sample.timestamp_ms));
  const validValues = allSamples
    .map(sampleDisplayValue)
    .filter((value): value is number => value !== null);
  const maxAngle = Math.max(120, Math.ceil(Math.max(0, ...validValues) / 30) * 30);

  return (
    <figure className="angle-chart">
      <figcaption>
        <div>
          <p className="section-label">Modeled knee flexion</p>
          <h3>Left / right through time</h3>
        </div>
        <div className="chart-legend" aria-label="Chart legend">
          <span className="left-series">Left</span>
          <span className="right-series">Right</span>
        </div>
      </figcaption>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Knee flexion line graph">
        <line x1={PADDING} y1={PADDING} x2={PADDING} y2={HEIGHT - PADDING} />
        <line
          x1={PADDING}
          y1={HEIGHT - PADDING}
          x2={WIDTH - PADDING}
          y2={HEIGHT - PADDING}
        />
        {[0, maxAngle / 2, maxAngle].map((angle) => {
          const y = scaleY(angle, maxAngle);
          return (
            <g key={angle}>
              <line className="grid-line" x1={PADDING} y1={y} x2={WIDTH - PADDING} y2={y} />
              <text x={PADDING - 8} y={y + 4} textAnchor="end">
                {angle}°
              </text>
            </g>
          );
        })}
        {analysis.series.map((series) => (
          <path
            key={series.side}
            className={`chart-series ${series.side}`}
            d={seriesPath(series, maxTime, maxAngle)}
          />
        ))}
        <text x={WIDTH - PADDING} y={HEIGHT - 12} textAnchor="end">
          {(maxTime / 1000).toFixed(1)} s
        </text>
      </svg>
      <p className="chart-note">
        Filtered world-landmark estimates are shown. Missing and low-confidence samples appear as
        gaps and are not interpolated.
      </p>
    </figure>
  );
}

function seriesPath(series: KneeFlexionSeries, maxTime: number, maxAngle: number): string {
  let drawing = false;
  return series.samples
    .map((sample) => {
      const value = sampleDisplayValue(sample);
      if (value === null) {
        drawing = false;
        return "";
      }
      const x = PADDING + (sample.timestamp_ms / maxTime) * (WIDTH - PADDING * 2);
      const y = scaleY(value, maxAngle);
      const command = drawing ? "L" : "M";
      drawing = true;
      return `${command}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .filter(Boolean)
    .join(" ");
}

function scaleY(value: number, maxAngle: number): number {
  return HEIGHT - PADDING - (value / maxAngle) * (HEIGHT - PADDING * 2);
}
