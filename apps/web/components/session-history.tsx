"use client";

import { useEffect, useState } from "react";
import {
  metricValue,
  parseSessionComparison,
  parseSessionList,
  parseSelectedSessionComparison,
  type SessionComparison,
  type SessionSummary,
  type SelectedSessionComparison,
} from "@/lib/session-contracts";

type HistoryState =
  | { status: "loading" }
  | { status: "ready"; sessions: SessionSummary[]; comparisons: Map<string, SessionComparison> }
  | { status: "error" };

export function SessionHistory({ refreshKey }: { refreshKey: string }) {
  const [state, setState] = useState<HistoryState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const [sessionsResponse, comparisonResponse] = await Promise.all([
          fetch("/api/sessions", { cache: "no-store" }),
          fetch("/api/sessions/comparison", { cache: "no-store" }),
        ]);
        const sessions = sessionsResponse.ok ? parseSessionList(await sessionsResponse.json()) : null;
        const comparison = comparisonResponse.ok
          ? parseSessionComparison(await comparisonResponse.json())
          : null;
        if (!active) return;
        if (!sessions || !comparison) {
          setState({ status: "error" });
          return;
        }
        setState({
          status: "ready",
          sessions: sessions.sessions,
          comparisons: new Map(comparison.sessions.map((item) => [item.session_id, item])),
        });
      } catch {
        if (active) setState({ status: "error" });
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [refreshKey]);

  return (
    <section className="session-history" aria-labelledby="session-history-title">
      <div>
        <p className="section-label">Longitudinal record</p>
        <h2 id="session-history-title">Session history</h2>
      </div>
      {state.status === "loading" && <p className="chart-note">Loading sessions…</p>}
      {state.status === "error" && (
        <p className="upload-message error">Session history is currently unavailable.</p>
      )}
      {state.status === "ready" && state.sessions.length === 0 && (
        <p className="chart-note">Complete an analysis to create the first session.</p>
      )}
      {state.status === "ready" && state.sessions.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Recorded</th>
                <th scope="col">Recording</th>
                <th scope="col">Reps</th>
                <th scope="col">Mean ROM</th>
                <th scope="col">Change</th>
                <th scope="col">Confidence</th>
                <th scope="col">Quality</th>
              </tr>
            </thead>
            <tbody>
              {state.sessions.map((session) => {
                const comparison = state.comparisons.get(session.id);
                return (
                  <tr key={session.id}>
                    <td>{new Date(session.recorded_at).toLocaleString()}</td>
                    <th scope="row">
                      <a href={`/sessions/${session.id}`}>{session.recording.original_filename}</a>
                    </th>
                    <td>{format(metricValue(session, "repetition_count"), 0)}</td>
                    <td>{format(metricValue(session, "mean_rom_degrees"), 1, "°")}</td>
                    <td>
                      {format(comparison?.mean_rom_change_from_previous_degrees ?? null, 1, "°", true)}
                    </td>
                    <td>{formatPercent(metricValue(session, "mean_confidence"))}</td>
                    <td>{session.capture_quality_status ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {state.status === "ready" && state.sessions.length > 1 && (
        <SelectedComparisonPanel sessions={state.sessions} />
      )}
      <p className="chart-note">
        The table change is a convenience view against the preceding stored squat session. Use the
        selector for explicit, compatibility-checked comparisons. This is not a clinical assessment.
      </p>
    </section>
  );
}

function SelectedComparisonPanel({ sessions }: { sessions: SessionSummary[] }) {
  const [baselineId, setBaselineId] = useState(sessions.at(-1)?.id ?? "");
  const [currentId, setCurrentId] = useState(sessions[0]?.id ?? "");
  const [comparison, setComparison] = useState<SelectedSessionComparison | null>(null);
  const [error, setError] = useState(false);

  async function compare() {
    setError(false);
    const query = new URLSearchParams({ baseline_id: baselineId, current_id: currentId });
    try {
      const response = await fetch(`/api/sessions/selected-comparison?${query}`, {
        cache: "no-store",
      });
      const parsed = response.ok ? parseSelectedSessionComparison(await response.json()) : null;
      setComparison(parsed);
      setError(parsed === null);
    } catch {
      setComparison(null);
      setError(true);
    }
  }

  return (
    <section className="comparison-selector" aria-labelledby="selected-comparison-title">
      <h3 id="selected-comparison-title">Compare selected sessions</h3>
      <div className="comparison-controls">
        <label>
          Baseline
          <select value={baselineId} onChange={(event) => setBaselineId(event.target.value)}>
            {sessions.map((session) => <SessionOption key={session.id} session={session} />)}
          </select>
        </label>
        <label>
          Current
          <select value={currentId} onChange={(event) => setCurrentId(event.target.value)}>
            {sessions.map((session) => <SessionOption key={session.id} session={session} />)}
          </select>
        </label>
        <button type="button" onClick={compare}>Compare</button>
      </div>
      {error && <p className="upload-message error">The selected comparison is unavailable.</p>}
      {comparison && !comparison.compatible && (
        <div className="compatibility-warning">
          <strong>These sessions are not compatible.</strong>
          <ul>{comparison.incompatibilities.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      )}
      {comparison?.compatible && (
        <div className="table-scroll">
          <table>
            <thead><tr><th>Metric</th><th>Baseline</th><th>Current</th><th>Change</th></tr></thead>
            <tbody>
              {comparison.metrics.map((metric) => (
                <tr key={metric.name}>
                  <th scope="row">{metric.name.replaceAll("_", " ")}</th>
                  <td>{metric.baseline_value.toFixed(2)} {metric.unit}</td>
                  <td>{metric.current_value.toFixed(2)} {metric.unit}</td>
                  <td>{metric.change > 0 ? "+" : ""}{metric.change.toFixed(2)} {metric.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function SessionOption({ session }: { session: SessionSummary }) {
  return (
    <option value={session.id}>
      {new Date(session.recorded_at).toLocaleString()} · {session.recording.original_filename}
    </option>
  );
}

function format(value: number | null, digits: number, suffix = "", signed = false): string {
  if (value === null) return "—";
  const prefix = signed && value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(digits)}${suffix}`;
}

function formatPercent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}
