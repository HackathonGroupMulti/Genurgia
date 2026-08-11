# Fixture provenance

`pose-person.mp4` was generated on 2026-08-10 from the image used by Google's official MediaPipe Pose Landmarker Python example:

* Source image: <https://cdn.pixabay.com/photo/2019/03/12/20/39/girl-4051811_960_720.jpg>
* Source page: <https://pixabay.com/photos/girl-woman-fitness-beautiful-smile-4051811/>
* MediaPipe example: <https://github.com/google-ai-edge/mediapipe-samples/blob/main/examples/pose_landmarker/python/%5BMediaPipe_Python_Tasks%5D_Pose_Landmarker.ipynb>

The source is provided under the Pixabay Content License. The fixture applies minor deterministic scale changes to the source image and encodes twelve frames as MP4. It exists only to verify video decoding, timestamp preservation, pose extraction, and overlay export; it is not a biomechanical ground-truth fixture and is not a squat recording.

## `squat-real.webm`

Downloaded on 2026-08-10 from Wikimedia Commons:

* File page: <https://commons.wikimedia.org/wiki/File:Squat_-_exercise_demonstration_video.webm>
* Original author: FitnessScape
* License: [Creative Commons Attribution 3.0 Unported](https://creativecommons.org/licenses/by/3.0/)

The committed file is Wikimedia's 480p VP9 transcode of the source excerpt. No content changes were made. The fixture is used only as a repeatable integration example and is not biomechanical ground truth.
