from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("vision_node")

TARGET_CLASSES = {
    "person": 0,
    "bicycle": 1,
    "car": 2,
    "motorcycle": 3,
    "airplane": 4,
    "bus": 5,
    "train": 6,
    "truck": 7,
    "boat": 8,
    "dog": 16,
    "cat": 15,
}


@dataclass
class DetectionResult:
    detected: bool
    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float]
    center_x: float
    center_y: float
    frame_width: int
    frame_height: int
    pixel_error_x: float
    pixel_error_y: float
    area_fraction: float


class VisionNode:
    def __init__(self, model_path: str = "yolov8n.pt",
                 target_class: str = "person",
                 confidence_threshold: float = 0.5,
                 save_dir: str = "output/detections"):
        self.target_class_name = target_class
        self.target_class_id = TARGET_CLASSES.get(target_class, 0)
        self.confidence_threshold = confidence_threshold
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            if os.path.exists(self.model_path):
                self.model = YOLO(self.model_path)
                logger.info(f"Loaded YOLO model from {self.model_path}")
            else:
                logger.info(f"Model {self.model_path} not found locally, downloading...")
                self.model = YOLO(self.model_path)
                logger.info("YOLO model loaded")
        except ImportError:
            logger.warning("ultralytics not installed — using mock detection")
            self.model = None

    def detect(self, frame: np.ndarray) -> Optional[DetectionResult]:
        if frame is None or frame.size == 0:
            return None

        h, w = frame.shape[:2]

        if self.model is None:
            return self._mock_detection(frame, w, h)

        results = self.model(frame, verbose=False)[0]
        boxes = results.boxes

        if boxes is None or len(boxes) == 0:
            return None

        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            conf = boxes.conf[i].item()

            if cls_id != self.target_class_id:
                continue
            if conf < self.confidence_threshold:
                continue

            x1, y1, x2, y2 = boxes.xyxy[i].tolist()
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0

            class_name = self.target_class_name
            for name, cid in TARGET_CLASSES.items():
                if cid == cls_id:
                    class_name = name
                    break

            result = DetectionResult(
                detected=True,
                class_name=class_name,
                confidence=conf,
                bbox=(x1, y1, x2, y2),
                center_x=cx,
                center_y=cy,
                frame_width=w,
                frame_height=h,
                pixel_error_x=cx - (w / 2.0),
                pixel_error_y=cy - (h / 2.0),
                area_fraction=((x2 - x1) * (y2 - y1)) / (w * h),
            )
            return result

        return None

    def _mock_detection(self, frame: np.ndarray, w: int, h: int) -> Optional[DetectionResult]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower = np.array([0, 100, 100])
        upper = np.array([10, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            if area > 500:
                M = cv2.moments(largest)
                if M["m00"] > 0:
                    cx = M["m10"] / M["m00"]
                    cy = M["m01"] / M["m00"]
                    return DetectionResult(
                        detected=True,
                        class_name=self.target_class_name,
                        confidence=0.85,
                        bbox=(cx - 20, cy - 20, cx + 20, cy + 20),
                        center_x=cx,
                        center_y=cy,
                        frame_width=w,
                        frame_height=h,
                        pixel_error_x=cx - (w / 2.0),
                        pixel_error_y=cy - (h / 2.0),
                        area_fraction=area / (w * h),
                    )
        return None

    def save_detection(self, frame: np.ndarray, result: DetectionResult) -> str:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = self.save_dir / f"detection_{timestamp}.jpg"
        annotated = frame.copy()
        x1, y1, x2, y2 = map(int, result.bbox)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{result.class_name} {result.confidence:.2f}"
        cv2.putText(annotated, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.imwrite(str(path), annotated)
        logger.info(f"Detection image saved to {path}")
        return str(path)

    def draw_error_overlay(self, frame: np.ndarray, result: DetectionResult) -> np.ndarray:
        annotated = frame.copy()
        h, w = frame.shape[:2]
        cv2.line(annotated, (w // 2, h // 2), (int(result.center_x), int(result.center_y)),
                 (0, 255, 255), 2)
        cv2.circle(annotated, (w // 2, h // 2), 5, (0, 0, 255), -1)
        cv2.circle(annotated, (int(result.center_x), int(result.center_y)), 5, (0, 255, 0), -1)
        return annotated


class VisualServoController:
    def __init__(self, kp_x: float = 0.005, kp_y: float = 0.005,
                 kp_z: float = 0.0001, max_speed: float = 5.0):
        self.kp_x = kp_x
        self.kp_y = kp_y
        self.kp_z = kp_z
        self.max_speed = max_speed

    def compute_velocity(self, error: DetectionResult) -> dict:
        vx = -self.kp_x * error.pixel_error_x
        vy = -self.kp_y * error.pixel_error_y
        vz = 0.0

        area_target = 0.05
        area_error = area_target - error.area_fraction
        vz = self.kp_z * area_error * 100

        vx = max(-self.max_speed, min(self.max_speed, vx))
        vy = max(-self.max_speed, min(self.max_speed, vy))
        vz = max(-self.max_speed, min(self.max_speed, vz))

        return {"vx": vx, "vy": vy, "vz": vz}

    def compute_yaw_rate(self, error: DetectionResult, kp_yaw: float = 0.01) -> float:
        yaw_rate = -kp_yaw * error.pixel_error_x
        return max(-30.0, min(30.0, yaw_rate))


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "person"
    source = sys.argv[2] if len(sys.argv) > 2 else "0"

    node = VisionNode(target_class=target)
    controller = VisualServoController()

    if source.isdigit():
        cap = cv2.VideoCapture(int(source))
    else:
        cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        logger.error("Cannot open video source")
        sys.exit(1)

    first_detection_saved = False
    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % 3 != 0:
                continue

            result = node.detect(frame)

            if result and result.detected:
                logger.info(f"Detected {result.class_name} at "
                           f"cx={result.center_x:.1f}, cy={result.center_y:.1f}, "
                           f"error=({result.pixel_error_x:.1f}, {result.pixel_error_y:.1f})")

                if not first_detection_saved:
                    path = node.save_detection(frame, result)
                    print(f"[OPERATOR ALERT] Target '{target}' acquired. Image saved: {path}")
                    first_detection_saved = True

                velocity = controller.compute_velocity(result)
                logger.debug(f"Follow velocity: {velocity}")

                display = node.draw_error_overlay(frame, result)
                cv2.putText(display,
                            f"Target: {result.class_name} ({result.confidence:.2f})",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display,
                            f"Follow cmd: vx={velocity['vx']:.2f} vy={velocity['vy']:.2f}",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                display = frame.copy()
                cv2.putText(display, f"Searching for '{target}'...",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.imshow("Vision AI - Target Detection & Follow", display)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
