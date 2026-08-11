"use client";

import { useState } from "react";
import {
  nearestPoseFrame,
  type Landmark,
  type PoseSequenceArtifact,
} from "@/lib/pose-contracts";

const WIDTH = 360;
const HEIGHT = 420;
const CONNECTIONS: [number, number][] = [
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
  [11, 23],
  [12, 24],
  [23, 24],
  [23, 25],
  [25, 27],
  [27, 29],
  [29, 31],
  [24, 26],
  [26, 28],
  [28, 30],
  [30, 32],
];

type ProjectedLandmark = Landmark & { screenX: number; screenY: number; depth: number };

export function SkeletonReplay({
  artifact,
  currentTimeMs,
}: {
  artifact: PoseSequenceArtifact;
  currentTimeMs: number;
}) {
  const [yawDegrees, setYawDegrees] = useState(0);
  const frame = nearestPoseFrame(artifact, currentTimeMs);
  const pose = frame?.poses.find((item) => item.pose_index === 0);
  const points = projectLandmarks(pose?.world_landmarks ?? [], yawDegrees);
  const byIndex = new Map(points.map((point) => [point.index, point]));

  return (
    <figure className="skeleton-replay">
      <figcaption>
        <div>
          <p className="section-label">Model-relative 3D replay</p>
          <h3>World-landmark skeleton</h3>
        </div>
        <label>
          View rotation
          <input
            type="range"
            min="-90"
            max="90"
            value={yawDegrees}
            onChange={(event) => setYawDegrees(Number(event.currentTarget.value))}
          />
          <span>{yawDegrees}°</span>
        </label>
      </figcaption>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Rotatable pose skeleton">
        <line className="ground-line" x1="30" y1="380" x2="330" y2="380" />
        {CONNECTIONS.map(([startIndex, endIndex]) => {
          const start = byIndex.get(startIndex);
          const end = byIndex.get(endIndex);
          if (!start || !end) return null;
          return (
            <line
              key={`${startIndex}-${endIndex}`}
              className={startIndex >= 23 ? "lower-body-bone" : "upper-body-bone"}
              x1={start.screenX}
              y1={start.screenY}
              x2={end.screenX}
              y2={end.screenY}
              opacity={Math.max(0.25, Math.min(confidence(start), confidence(end)))}
            />
          );
        })}
        {points
          .sort((a, b) => b.depth - a.depth)
          .map((point) => (
            <circle
              key={point.index}
              className={point.index >= 23 ? "lower-body-joint" : "upper-body-joint"}
              cx={point.screenX}
              cy={point.screenY}
              r={point.index >= 23 ? 5 : 3.5}
              opacity={Math.max(0.25, confidence(point))}
            />
          ))}
        {points.length === 0 && (
          <text x={WIDTH / 2} y={HEIGHT / 2} textAnchor="middle">
            Pose unavailable at this frame
          </text>
        )}
      </svg>
      <p className="chart-note">
        Rotate the view to inspect MediaPipe world landmarks. Depth and scale are model-relative,
        not calibrated anatomical measurements.
      </p>
    </figure>
  );
}

function projectLandmarks(landmarks: Landmark[], yawDegrees: number): ProjectedLandmark[] {
  const radians = (yawDegrees * Math.PI) / 180;
  const cosine = Math.cos(radians);
  const sine = Math.sin(radians);
  return landmarks.flatMap((landmark) => {
    if (landmark.x === null || landmark.y === null || landmark.z === null) return [];
    const rotatedX = landmark.x * cosine + landmark.z * sine;
    const rotatedZ = -landmark.x * sine + landmark.z * cosine;
    const perspective = 1 / Math.max(0.7, 1 + rotatedZ * 0.35);
    return [
      {
        ...landmark,
        screenX: WIDTH / 2 + rotatedX * 190 * perspective,
        screenY: 185 + landmark.y * 190 * perspective,
        depth: rotatedZ,
      },
    ];
  });
}

function confidence(landmark: Landmark): number {
  const values = [landmark.visibility, landmark.presence].filter(
    (value): value is number => value !== null,
  );
  return values.length > 0 ? Math.min(...values) : 1;
}
