"""Eye tracking collector using MediaPipe."""

import base64
import cv2
import numpy as np
import mediapipe as mp
from scipy.spatial import distance
from config.logging_config import get_logger
from config.thresholds import EAR_THRESHOLD

logger = get_logger(__name__)

mp_face_mesh = mp.solutions.face_mesh

LEFT_EYE  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]


def eye_aspect_ratio(landmarks, eye_idxs, w, h):
    pts = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in eye_idxs]
    A = distance.euclidean(pts[1], pts[5])
    B = distance.euclidean(pts[2], pts[4])
    C = distance.euclidean(pts[0], pts[3])
    return (A + B) / (2.0 * C)


class EyeCollector:
    def __init__(self):
        self.face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)
        self.blink_count   = 0
        self.frames_closed = 0
        self.total_frames  = 0
        self.prev_ear_below = False

    def process_frame(self, frame_b64: str) -> dict:
        """Decode a base64 JPEG frame and return eye metrics."""
        try:
            img_data = base64.b64decode(frame_b64.split(',')[1])
            arr   = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w  = frame.shape[:2]

            results = self.face_mesh.process(rgb)

            if not results.multi_face_landmarks:
                return {"blink_rate": 0.0, "perclos": 0.0, "face_detected": False}

            lm        = results.multi_face_landmarks[0].landmark
            left_ear  = eye_aspect_ratio(lm, LEFT_EYE,  w, h)
            right_ear = eye_aspect_ratio(lm, RIGHT_EYE, w, h)
            ear       = (left_ear + right_ear) / 2.0

            self.total_frames += 1

            if ear < EAR_THRESHOLD:
                self.frames_closed += 1
                if not self.prev_ear_below:
                    self.blink_count += 1
                self.prev_ear_below = True
            else:
                self.prev_ear_below = False

            perclos    = self.frames_closed / max(self.total_frames, 1)
            blink_rate = self.blink_count   / max(self.total_frames / 20, 1)

            return {
                "blink_rate":    round(blink_rate, 1),
                "perclos":       round(perclos, 4),
                "face_detected": True,
                "ear":           round(ear, 3),
            }

        except Exception as e:
            logger.error(f"EyeCollector frame error: {e}")
            return {"blink_rate": 0.0, "perclos": 0.0, "face_detected": False}

    def reset(self):
        self.blink_count    = 0
        self.frames_closed  = 0
        self.total_frames   = 0
        self.prev_ear_below = False