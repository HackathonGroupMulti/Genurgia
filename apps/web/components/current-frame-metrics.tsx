import {
  sampleAtTimestamp,
  sampleDisplayValue,
  type KneeFlexionAnalysis,
} from "@/lib/knee-flexion-contracts";
import type { SquatRepetitionAnalysis } from "@/lib/repetition-contracts";

export function CurrentFrameMetrics({
  analysis,
  repetitions,
  currentTimeMs,
}: {
  analysis: KneeFlexionAnalysis;
  repetitions: SquatRepetitionAnalysis | null;
  currentTimeMs: number;
}) {
  const leftSeries = analysis.series.find((series) => series.side === "left");
  const rightSeries = analysis.series.find((series) => series.side === "right");
  const left = leftSeries ? sampleAtTimestamp(leftSeries, currentTimeMs) : null;
  const right = rightSeries ? sampleAtTimestamp(rightSeries, currentTimeMs) : null;
  const repetition = repetitions?.repetitions.find(
    (item) => currentTimeMs >= item.start_timestamp_ms && currentTimeMs <= item.end_timestamp_ms,
  );

  return (
    <section className="current-metrics" aria-label="Current playback measurements">
      <div className="metric-card">
        <span>Playback</span>
        <strong>{(currentTimeMs / 1000).toFixed(2)} s</strong>
      </div>
      <Measurement label="Left flexion" value={left ? sampleDisplayValue(left) : null} />
      <Measurement label="Right flexion" value={right ? sampleDisplayValue(right) : null} />
      <div className="metric-card">
        <span>Repetition</span>
        <strong>{repetition ? `Rep ${repetition.repetition_index}` : "Between reps"}</strong>
      </div>
    </section>
  );
}

function Measurement({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value === null ? "Unavailable" : `${value.toFixed(1)}°`}</strong>
    </div>
  );
}
