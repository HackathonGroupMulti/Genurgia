import type { SquatRepetitionAnalysis } from "@/lib/repetition-contracts";

export function RepetitionSummary({ analysis }: { analysis: SquatRepetitionAnalysis }) {
  return (
    <section className="repetition-summary" aria-labelledby="repetition-title">
      <div className="result-heading">
        <div>
          <p className="section-label">Squat segmentation</p>
          <h3 id="repetition-title">{analysis.repetitions.length} complete repetitions</h3>
        </div>
        <p className="frame-count">Bilateral filtered estimates</p>
      </div>
      {analysis.repetitions.length > 0 ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Rep</th>
                <th scope="col">Start / bottom / end</th>
                <th scope="col">Duration</th>
                <th scope="col">Left ROM</th>
                <th scope="col">Right ROM</th>
                <th scope="col">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {analysis.repetitions.map((repetition) => (
                <tr key={repetition.repetition_index}>
                  <th scope="row">{repetition.repetition_index}</th>
                  <td>
                    {seconds(repetition.start_timestamp_ms)} / {seconds(repetition.bottom_timestamp_ms)} /{" "}
                    {seconds(repetition.end_timestamp_ms)}
                  </td>
                  <td>{(repetition.duration_ms / 1000).toFixed(2)} s</td>
                  <td>{repetition.left_rom_degrees.toFixed(1)}°</td>
                  <td>{repetition.right_rom_degrees.toFixed(1)}°</td>
                  <td>{Math.round(repetition.confidence * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="chart-note">
          No complete squat crossed the configured phase, duration, bilateral-quality, and ROM
          thresholds.
        </p>
      )}
      <p className="chart-note">
        ROM is the within-repetition maximum minus minimum modeled flexion for each knee. These
        monocular estimates are not diagnostic measurements.
      </p>
    </section>
  );
}

function seconds(timestampMs: number): string {
  return `${(timestampMs / 1000).toFixed(2)} s`;
}
