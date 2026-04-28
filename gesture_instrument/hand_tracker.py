import os
import urllib.request
import mediapipe as mp
from mediapipe.tasks.python.vision.hand_landmarker import (
    HandLandmarker,
    HandLandmarkerOptions,
    vision_task_running_mode,
)
from mediapipe.tasks.python import BaseOptions
import cv2

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

# Landmark indices for the three tracked fingertips
TRACKED_TIPS = [4, 8, 12]  # thumb, index, middle


def _ensure_model():
    if not os.path.exists(_MODEL_PATH):
        print("Downloading hand landmark model (~8 MB)...")
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        print("Model downloaded.")


class HandTracker:
    def __init__(self):
        _ensure_model()
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=_MODEL_PATH),
            running_mode=vision_task_running_mode.VisionTaskRunningMode.IMAGE,
            num_hands=2,
            min_hand_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )
        self._landmarker = HandLandmarker.create_from_options(options)

    def get_hands(self, frame) -> dict:
        """Return {"Left": [(x,y), ...] | None, "Right": [(x,y), ...] | None}
        Each list contains normalized positions of thumb, index and middle tips."""
        flipped = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(flipped, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(mp_image)

        output = {"Left": None, "Right": None}

        if not result.hand_landmarks:
            return output

        for landmarks, handedness_list in zip(result.hand_landmarks, result.handedness):
            raw_label = handedness_list[0].display_name
            # MediaPipe labels are mirrored after horizontal flip — swap them
            label = "Right" if raw_label == "Left" else "Left"
            tips = [(landmarks[i].x, landmarks[i].y) for i in TRACKED_TIPS]
            output[label] = tips

        return output
