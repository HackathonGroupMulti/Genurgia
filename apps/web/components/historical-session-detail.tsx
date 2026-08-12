"use client";

import { useEffect, useRef, useState } from "react";
import { CaptureQualitySummary } from "@/components/capture-quality-summary";
import { CurrentFrameMetrics } from "@/components/current-frame-metrics";
import { KneeFlexionChart } from "@/components/knee-flexion-chart";
import { RepetitionSummary } from "@/components/repetition-summary";
import { SkeletonReplay } from "@/components/skeleton-replay";
import {
  parseKneeFlexionAnalysis,
  type KneeFlexionAnalysis,
} from "@/lib/knee-flexion-contracts";
import {
  artifactProxyUrl,
  parsePoseSequenceArtifact,
  type PoseSequenceArtifact,
} from "@/lib/pose-contracts";
import {
  parseCaptureQualityReport,
  type CaptureQualityReport,
} from "@/lib/quality-contracts";
import {
  parseSquatRepetitionAnalysis,
  type SquatRepetitionAnalysis,
} from "@/lib/repetition-contracts";
import { parseSession, type SessionSummary } from "@/lib/session-contracts";

type DetailState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      session: SessionSummary;
      pose: PoseSequenceArtifact | null;
      knee: KneeFlexionAnalysis | null;
      repetitions: SquatRepetitionAnalysis | null;
      quality: CaptureQualityReport | null;
    };

export function HistoricalSessionDetail({ sessionId }: { sessionId: string }) {
  const [state, setState] = useState<DetailState>({ status: "loading" });
  const [revision, setRevision] = useState(0);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [currentTimeMs, setCurrentTimeMs] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      setState({ status: "loading" });
      try {
        const response = await fetch(`/api/sessions/${sessionId}`, { cache: "no-store" });
        const session = response.ok ? parseSession(await response.json()) : null;
        if (!session) throw new Error("The stored session could not be loaded.");
        const latest = (type: string) =>
          session.analyses.filter((item) => item.analysis_type === type).at(-1)?.artifact_reference;
        const [poseResponse, kneeResponse, repetitionResponse, qualityResponse] = await Promise.all([
          fetch(artifactProxyUrl(session.pose_sequence.raw_landmarks_reference)),
          fetchOptional(latest("knee_flexion")),
          fetchOptional(latest("squat_repetitions")),
          fetchOptional(latest("capture_quality")),
        ]);
        const pose = poseResponse.ok ? parsePoseSequenceArtifact(await poseResponse.json()) : null;
        const knee = kneeResponse?.ok ? parseKneeFlexionAnalysis(await kneeResponse.json()) : null;
        const repetitions = repetitionResponse?.ok
          ? parseSquatRepetitionAnalysis(await repetitionResponse.json())
          : null;
        const quality = qualityResponse?.ok
          ? parseCaptureQualityReport(await qualityResponse.json())
          : null;
        if (active) setState({ status: "ready", session, pose, knee, repetitions, quality });
      } catch (error) {
        if (active) {
          setState({
            status: "error",
            message: error instanceof Error ? error.message : "The session could not be loaded.",
          });
        }
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [sessionId, revision]);

  async function reanalyze() {
    setReanalyzing(true);
    try {
      const response = await fetch(`/api/sessions/${sessionId}/reanalysis`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "{}",
      });
      if (!response.ok) throw new Error();
      setRevision((value) => value + 1);
    } finally {
      setReanalyzing(false);
    }
  }

  if (state.status === "loading") return <p className="chart-note">Loading stored session…</p>;
  if (state.status === "error") return <p className="upload-message error">{state.message}</p>;

  const { session, pose, knee, repetitions, quality } = state;
  function seekVideo(timestampMs: number) {
    if (!videoRef.current) return;
    videoRef.current.currentTime = timestampMs / 1000;
    setCurrentTimeMs(timestampMs);
  }

  return (
    <section className="analysis-result historical-detail">
      <div className="result-heading">
        <div>
          <p className="section-label">Stored session</p>
          <h2>{session.recording.original_filename}</h2>
          <p className="chart-note">{new Date(session.recorded_at).toLocaleString()}</p>
        </div>
        <div className="session-actions">
          <button type="button" onClick={reanalyze} disabled={reanalyzing}>
            {reanalyzing ? "Reanalyzing…" : "Derive missing current analyses"}
          </button>
          <a className="artifact-link" href={`/api/sessions/${session.id}/export-manifest`}>
            Export integrity manifest
          </a>
        </div>
      </div>
      <dl className="capture-metadata">
        <div><dt>View</dt><dd>{session.recording.camera_view ?? "unknown"}</dd></div>
        <div><dt>Orientation</dt><dd>{session.recording.orientation ?? "unknown"}</dd></div>
        <div><dt>Knee context</dt><dd>{session.recording.laterality_context ?? "unknown"}</dd></div>
        <div><dt>Quality</dt><dd>{session.capture_quality_status ?? "not analyzed"}</dd></div>
      </dl>
      <video
        ref={videoRef}
        controls
        preload="metadata"
        src={artifactProxyUrl(session.pose_sequence.annotated_video_reference)}
        onTimeUpdate={(event) => setCurrentTimeMs(event.currentTarget.currentTime * 1000)}
        onSeeked={(event) => setCurrentTimeMs(event.currentTarget.currentTime * 1000)}
      />
      {knee && <CurrentFrameMetrics analysis={knee} repetitions={repetitions} currentTimeMs={currentTimeMs} />}
      {knee && (
        <KneeFlexionChart
          analysis={knee}
          repetitions={repetitions}
          currentTimeMs={currentTimeMs}
          onSeek={seekVideo}
        />
      )}
      {pose && <SkeletonReplay artifact={pose} currentTimeMs={currentTimeMs} />}
      {repetitions && <RepetitionSummary analysis={repetitions} />}
      {quality && <CaptureQualitySummary report={quality} />}
      {(!knee || !repetitions || !quality) && (
        <p className="upload-message error">
          One or more current analysis versions are missing. Use reanalysis to derive them from preserved raw observations.
        </p>
      )}
    </section>
  );
}

async function fetchOptional(reference: string | undefined): Promise<Response | null> {
  return reference ? fetch(artifactProxyUrl(reference)) : null;
}
