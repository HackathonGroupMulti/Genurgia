"use client";

import { FormEvent, useState } from "react";
import {
  artifactProxyUrl,
  parsePoseAnalysisResponse,
  type PoseAnalysisResponse,
} from "@/lib/pose-contracts";

type UploadState =
  | { status: "idle" }
  | { status: "uploading" }
  | { status: "complete"; result: PoseAnalysisResponse }
  | { status: "error"; message: string };

export function VideoUpload() {
  const [state, setState] = useState<UploadState>({ status: "idle" });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
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
      setState({ status: "complete", result });
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
          Upload an MP4, MOV, or WebM recording. Milestone 1 preserves raw observations and
          exports a pose overlay; it does not calculate knee angles yet.
        </p>
      </div>

      <form onSubmit={submit}>
        <label className="file-field">
          <span>Movement video</span>
          <input name="video" type="file" accept="video/mp4,video/quicktime,video/webm" required />
        </label>
        <button type="submit" disabled={state.status === "uploading"}>
          {state.status === "uploading" ? "Extracting landmarks…" : "Analyze video"}
        </button>
      </form>

      {state.status === "error" && (
        <p className="upload-message error" role="alert">
          {state.message}
        </p>
      )}

      {state.status === "complete" && <AnalysisResult result={state.result} />}
    </section>
  );
}

function AnalysisResult({ result }: { result: PoseAnalysisResponse }) {
  const sequence = result.pose_sequence;
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
      <video
        controls
        preload="metadata"
        src={artifactProxyUrl(sequence.annotated_video_reference)}
      >
        Your browser does not support video playback.
      </video>
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
