"use client";

import { FormEvent, useRef, useState } from "react";
import { CaptureQualitySummary } from "@/components/capture-quality-summary";
import { CurrentFrameMetrics } from "@/components/current-frame-metrics";
import { KneeFlexionChart } from "@/components/knee-flexion-chart";
import { RepetitionSummary } from "@/components/repetition-summary";
import { SessionHistory } from "@/components/session-history";
import { SkeletonReplay } from "@/components/skeleton-replay";
import {
  parseKneeFlexionAnalysis,
  type KneeFlexionAnalysis,
} from "@/lib/knee-flexion-contracts";
import {
  artifactProxyUrl,
  parsePoseAnalysisResponse,
  parsePoseSequenceArtifact,
  type PoseAnalysisResponse,
  type PoseSequenceArtifact,
} from "@/lib/pose-contracts";
import {
  parseSquatRepetitionAnalysis,
  type SquatRepetitionAnalysis,
} from "@/lib/repetition-contracts";
import {
  parseCaptureQualityReport,
  type CaptureQualityReport,
} from "@/lib/quality-contracts";

type UploadState =
  | { status: "idle" }
  | { status: "uploading" }
  | { status: "analyzing"; result: PoseAnalysisResponse }
  | {
      status: "complete";
      result: PoseAnalysisResponse;
      analysis: KneeFlexionAnalysis | null;
      repetitions: SquatRepetitionAnalysis | null;
      quality: CaptureQualityReport | null;
      poseArtifact: PoseSequenceArtifact | null;
      analysisError: string | null;
    }
  | { status: "error"; message: string };

export function VideoUpload() {
  const [state, setState] = useState<UploadState>({ status: "idle" });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const capturedAt = formData.get("captured_at");
    if (typeof capturedAt === "string" && capturedAt.length > 0) {
      formData.set("captured_at", new Date(capturedAt).toISOString());
    } else {
      formData.delete("captured_at");
    }
    setState({ status: "uploading" });

    try {
      const response = await fetch("/api/pose-sequences", {
        method: "POST",
        body: formData,
      });
      const payload: unknown = await response.json();
      if (!response.ok) {
        const message =
          typeof payload === "object" && payload !== null && "detail" in payload
            ? String(payload.detail)
            : `Upload failed with HTTP ${response.status}.`;
        setState({ status: "error", message });
        return;
      }

      const result = parsePoseAnalysisResponse(payload);
      if (!result) {
        setState({ status: "error", message: "The API returned an unexpected response." });
        return;
      }
      setState({ status: "analyzing", result });
      let analysis: KneeFlexionAnalysis | null = null;
      let repetitions: SquatRepetitionAnalysis | null = null;
      let quality: CaptureQualityReport | null = null;
      let poseArtifact: PoseSequenceArtifact | null = null;
      try {
        const analysisResponse = await fetch(
          `/api/pose-sequences/${result.pose_sequence.id}/knee-flexion`,
          { method: "POST" },
        );
        const analysisPayload: unknown = await analysisResponse.json();
        analysis = analysisResponse.ok ? parseKneeFlexionAnalysis(analysisPayload) : null;
        if (analysis) {
          const repetitionResponse = await fetch(
            `/api/pose-sequences/${result.pose_sequence.id}/squat-repetitions`,
            { method: "POST" },
          );
          const repetitionPayload: unknown = await repetitionResponse.json();
          repetitions = repetitionResponse.ok
            ? parseSquatRepetitionAnalysis(repetitionPayload)
            : null;
          if (repetitions) {
            const qualityResponse = await fetch(
              `/api/pose-sequences/${result.pose_sequence.id}/capture-quality`,
              { method: "POST" },
            );
            const qualityPayload: unknown = await qualityResponse.json();
            quality = qualityResponse.ok ? parseCaptureQualityReport(qualityPayload) : null;
          }
        }
      } catch {
        analysis = null;
        repetitions = null;
        quality = null;
      }
      try {
        const rawResponse = await fetch(artifactProxyUrl(result.pose_sequence.raw_landmarks_reference));
        poseArtifact = rawResponse.ok ? parsePoseSequenceArtifact(await rawResponse.json()) : null;
      } catch {
        poseArtifact = null;
      }
      setState({
        status: "complete",
        result,
        analysis,
        repetitions,
        quality,
        poseArtifact,
        analysisError: analysis && repetitions && quality
          ? null
          : "Pose landmarks were preserved, but one or more derived analyses were unavailable.",
      });
    } catch {
      setState({ status: "error", message: "The upload service could not be reached." });
    }
  }

  return (
    <section className="upload-panel" aria-labelledby="upload-title">
      <div>
        <p className="section-label">Video → raw landmarks</p>
        <h2 id="upload-title">Create a pose sequence</h2>
        <p className="section-copy">
          Upload an MP4, MOV, or WebM squat recording to preserve raw observations, estimate
          bilateral knee flexion, and segment complete repetitions.
        </p>
      </div>

      <form onSubmit={submit}>
        <label className="file-field">
          <span>Movement video</span>
          <input name="video" type="file" accept="video/mp4,video/quicktime,video/webm" required />
        </label>
        <label className="metadata-field">
          <span>Captured at</span>
          <input name="captured_at" type="datetime-local" />
        </label>
        <label className="metadata-field">
          <span>Camera view</span>
          <select name="camera_view" defaultValue="unknown">
            <option value="unknown">Unknown</option>
            <option value="front">Front</option>
            <option value="rear">Rear</option>
            <option value="left_side">Left side</option>
            <option value="right_side">Right side</option>
            <option value="oblique">Oblique</option>
          </select>
        </label>
        <label className="metadata-field">
          <span>Orientation</span>
          <select name="orientation" defaultValue="unknown">
            <option value="unknown">Unknown</option>
            <option value="landscape">Landscape</option>
            <option value="portrait">Portrait</option>
          </select>
        </label>
        <label className="metadata-field">
          <span>Knee context</span>
          <select name="laterality_context" defaultValue="bilateral">
            <option value="bilateral">Bilateral</option>
            <option value="left">Left</option>
            <option value="right">Right</option>
            <option value="unknown">Unknown</option>
          </select>
        </label>
        <label className="notes-field">
          <span>Capture notes</span>
          <input name="capture_notes" type="text" maxLength={1000} />
        </label>
        <button
          type="submit"
          disabled={state.status === "uploading" || state.status === "analyzing"}
        >
          {state.status === "uploading" || state.status === "analyzing"
            ? "Analyzing movement…"
            : "Analyze video"}
        </button>
      </form>

      {state.status === "error" && (
        <p className="upload-message error" role="alert">
          {state.message}
        </p>
      )}

      {state.status === "analyzing" && (
        <p className="upload-message" role="status">
          Pose observations preserved. Calculating knee flexion and squat repetitions…
        </p>
      )}

      {state.status === "complete" && (
        <AnalysisResult
          result={state.result}
          analysis={state.analysis}
          repetitions={state.repetitions}
          quality={state.quality}
          poseArtifact={state.poseArtifact}
          analysisError={state.analysisError}
        />
      )}
      <SessionHistory
        refreshKey={state.status === "complete" ? state.result.pose_sequence.id : "initial"}
      />
    </section>
  );
}

function AnalysisResult({
  result,
  analysis,
  repetitions,
  quality,
  poseArtifact,
  analysisError,
}: {
  result: PoseAnalysisResponse;
  analysis: KneeFlexionAnalysis | null;
  repetitions: SquatRepetitionAnalysis | null;
  quality: CaptureQualityReport | null;
  poseArtifact: PoseSequenceArtifact | null;
  analysisError: string | null;
}) {
  const sequence = result.pose_sequence;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTimeMs, setCurrentTimeMs] = useState(0);

  function seekVideo(timestampMs: number) {
    if (!videoRef.current) return;
    videoRef.current.currentTime = timestampMs / 1000;
    setCurrentTimeMs(timestampMs);
  }

  return (
    <div className="analysis-result" aria-live="polite">
      <div className="result-heading">
        <div>
          <p className="section-label">Extraction complete</p>
          <h3>{result.recording.original_filename}</h3>
        </div>
        <p className="frame-count">
          {sequence.detected_frame_count} / {sequence.frame_count} frames detected
        </p>
      </div>
      <p className="section-label">Annotated pose overlay · synchronized playback source</p>
      <video
        ref={videoRef}
        controls
        preload="metadata"
        src={artifactProxyUrl(sequence.annotated_video_reference)}
        onTimeUpdate={(event) => setCurrentTimeMs(event.currentTarget.currentTime * 1000)}
        onSeeked={(event) => setCurrentTimeMs(event.currentTarget.currentTime * 1000)}
      >
        Your browser does not support video playback.
      </video>
      {analysis && (
        <CurrentFrameMetrics
          analysis={analysis}
          repetitions={repetitions}
          currentTimeMs={currentTimeMs}
        />
      )}
      {analysis && (
        <KneeFlexionChart
          analysis={analysis}
          repetitions={repetitions}
          currentTimeMs={currentTimeMs}
          onSeek={seekVideo}
        />
      )}
      {poseArtifact ? (
        <SkeletonReplay artifact={poseArtifact} currentTimeMs={currentTimeMs} />
      ) : (
        <p className="chart-note">The model-relative skeleton replay is unavailable.</p>
      )}
      {repetitions && <RepetitionSummary analysis={repetitions} />}
      {quality && <CaptureQualitySummary report={quality} />}
      {analysisError && <p className="upload-message error">{analysisError}</p>}
      <a
        className="artifact-link"
        href={artifactProxyUrl(sequence.raw_landmarks_reference)}
        target="_blank"
        rel="noreferrer"
      >
        Open preserved raw landmark JSON
      </a>
    </div>
  );
}
