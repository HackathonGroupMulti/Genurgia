"""MediaPipe Pose Landmarker adapter for timestamped video inference."""

from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp

from analysis.pose import (
    LandmarkObservation,
    PoseExtraction,
    PoseExtractionError,
    PoseFrameObservation,
    PoseObservation,
    VideoMetadata,
)

MODEL_NAME = "mediapipe-pose-landmarker"
MODEL_VARIANT = "full-float16-v1"


class MediaPipePoseProvider:
    def __init__(self, model_path: Path) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(f"MediaPipe model not found: {model_path}")
        self._model_path = model_path

    @property
    def model_name(self) -> str:
        return MODEL_NAME

    @property
    def model_version(self) -> str:
        return f"mediapipe-{mp.__version__}:{MODEL_VARIANT}"

    def extract(self, video_path: Path, annotated_video_path: Path) -> PoseExtraction:
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise PoseExtractionError("The uploaded file could not be opened as a video.")

        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if fps <= 0 or width <= 0 or height <= 0:
            capture.release()
            raise PoseExtractionError("The video is missing valid FPS or frame dimensions.")

        annotated_video_path.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            str(annotated_video_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            capture.release()
            raise PoseExtractionError("The annotated MP4 output could not be created.")

        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(self._model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            output_segmentation_masks=False,
        )

        frames: list[PoseFrameObservation] = []
        try:
            with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
                frame_index = 0
                while True:
                    decoded, bgr_frame = capture.read()
                    if not decoded:
                        break

                    timestamp_ms = round(frame_index * 1000 / fps)
                    rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
                    media_pipe_image = mp.Image(
                        image_format=mp.ImageFormat.SRGB,
                        data=rgb_frame,
                    )
                    result = landmarker.detect_for_video(media_pipe_image, timestamp_ms)
                    poses = self._convert_poses(result)
                    frames.append(
                        PoseFrameObservation(
                            frame_index=frame_index,
                            timestamp_ms=timestamp_ms,
                            poses=poses,
                        )
                    )
                    self._draw_overlay(bgr_frame, result)
                    writer.write(bgr_frame)
                    frame_index += 1
        except (RuntimeError, ValueError) as error:
            raise PoseExtractionError(f"MediaPipe pose extraction failed: {error}") from error
        finally:
            capture.release()
            writer.release()

        if not frames:
            raise PoseExtractionError("The uploaded video contained no decodable frames.")

        duration_ms = round(len(frames) * 1000 / fps)
        return PoseExtraction(
            video=VideoMetadata(
                duration_ms=duration_ms,
                fps=fps,
                width=width,
                height=height,
                decoded_frame_count=len(frames),
            ),
            frames=tuple(frames),
        )

    @staticmethod
    def _convert_poses(result: Any) -> tuple[PoseObservation, ...]:
        poses: list[PoseObservation] = []
        for pose_index, image_landmarks in enumerate(result.pose_landmarks):
            world_landmarks = (
                result.pose_world_landmarks[pose_index]
                if pose_index < len(result.pose_world_landmarks)
                else []
            )
            poses.append(
                PoseObservation(
                    pose_index=pose_index,
                    image_landmarks=MediaPipePoseProvider._convert_landmarks(image_landmarks),
                    world_landmarks=MediaPipePoseProvider._convert_landmarks(world_landmarks),
                )
            )
        return tuple(poses)

    @staticmethod
    def _convert_landmarks(landmarks: list[Any]) -> tuple[LandmarkObservation, ...]:
        return tuple(
            LandmarkObservation(
                index=index,
                name=mp.tasks.vision.PoseLandmark(index).name.lower(),
                x=landmark.x,
                y=landmark.y,
                z=landmark.z,
                visibility=landmark.visibility,
                presence=landmark.presence,
            )
            for index, landmark in enumerate(landmarks)
        )

    @staticmethod
    def _draw_overlay(bgr_frame: Any, result: Any) -> None:
        landmark_style = mp.tasks.vision.drawing_styles.get_default_pose_landmarks_style()
        connection_style = mp.tasks.vision.drawing_utils.DrawingSpec(
            color=(46, 204, 113),
            thickness=2,
        )
        for landmarks in result.pose_landmarks:
            mp.tasks.vision.drawing_utils.draw_landmarks(
                image=bgr_frame,
                landmark_list=landmarks,
                connections=mp.tasks.vision.PoseLandmarksConnections.POSE_LANDMARKS,
                landmark_drawing_spec=landmark_style,
                connection_drawing_spec=connection_style,
            )
