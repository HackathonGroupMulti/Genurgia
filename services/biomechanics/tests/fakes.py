from pathlib import Path

from analysis.pose import (
    LandmarkObservation,
    PoseExtraction,
    PoseFrameObservation,
    PoseObservation,
    VideoMetadata,
)


class FakePoseProvider:
    model_name = "fake-pose-provider"
    model_version = "test-v1"

    def extract(self, video_path: Path, annotated_video_path: Path) -> PoseExtraction:
        annotated_video_path.write_bytes(video_path.read_bytes())
        nose = LandmarkObservation(
            index=0,
            name="nose",
            x=0.5,
            y=0.25,
            z=-0.1,
            visibility=0.9,
            presence=0.8,
        )
        joint_landmarks = tuple(
            LandmarkObservation(
                index=index,
                name=name,
                x=x,
                y=y,
                z=0.0,
                visibility=0.9,
                presence=0.9,
            )
            for index, name, x, y in (
                (23, "left_hip", 0.4, 1.0),
                (24, "right_hip", 0.6, 1.0),
                (25, "left_knee", 0.4, 0.5),
                (26, "right_knee", 0.6, 0.5),
                (27, "left_ankle", 0.4, 0.0),
                (28, "right_ankle", 0.6, 0.0),
            )
        )
        landmarks = (nose, *joint_landmarks)
        return PoseExtraction(
            video=VideoMetadata(
                duration_ms=100,
                fps=10.0,
                width=480,
                height=360,
                decoded_frame_count=1,
            ),
            frames=(
                PoseFrameObservation(
                    frame_index=0,
                    timestamp_ms=0,
                    poses=(
                        PoseObservation(
                            pose_index=0,
                            image_landmarks=landmarks,
                            world_landmarks=landmarks,
                        ),
                    ),
                ),
            ),
        )
