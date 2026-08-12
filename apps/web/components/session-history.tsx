"use client";

import { useEffect, useState } from "react";
import {
  metricValue,
  parseSessionComparison,
  parseSessionList,
  type SessionComparison,
  type SessionSummary,
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
                    <th scope="row">{session.recording.original_filename}</th>
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
      <p className="chart-note">
        Change compares mean modeled ROM with the preceding stored squat session. It is not a
        clinical assessment.
      </p>
    </section>
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
