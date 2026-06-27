from __future__ import annotations

import logging
import math
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("sim_camera")

CIRCLE_COLORS = {
    "red": (0, 0, 255),
    "green": (0, 255, 0),
    "blue": (255, 0, 0),
    "yellow": (0, 255, 255),
    "orange": (0, 165, 255),
    "purple": (255, 0, 255),
    "cyan": (255, 255, 0),
}


class SimulatedCamera:
    def __init__(self, width: int = 640, height: int = 480,
                 pattern: str = "circle", color: str = "red",
                 target_speed: float = 30.0, fps: float = 30.0):
        self.width = width
        self.height = height
        self.pattern = pattern
        self.color = CIRCLE_COLORS.get(color, (0, 0, 255))
        self.target_speed = target_speed
        self.fps = fps
        self.frame_count = 0
        self.t0 = time.time()

        cx, cy = width // 2, height // 2
        self.target_x = float(cx)
        self.target_y = float(cy)
        self.target_vx = target_speed * 0.7
        self.target_vy = target_speed * 0.5
        self.target_radius = 25

    def _update_position(self):
        dt = 1.0 / self.fps
        self.target_x += self.target_vx * dt
        self.target_y += self.target_vy * dt

        if self.target_x - self.target_radius < 50:
            self.target_vx = abs(self.target_vx)
        elif self.target_x + self.target_radius > self.width - 50:
            self.target_vx = -abs(self.target_vx)

        if self.target_y - self.target_radius < 50:
            self.target_vy = abs(self.target_vy)
        elif self.target_y + self.target_radius > self.height - 50:
            self.target_vy = -abs(self.target_vy)

    def read(self) -> tuple[bool, Optional[np.ndarray]]:
        self.frame_count += 1
        self._update_position()

        frame = np.ones((self.height, self.width, 3), dtype=np.uint8) * 200

        cv2.circle(
            frame,
            (int(self.target_x), int(self.target_y)),
            self.target_radius,
            self.color,
            -1,
        )

        cv2.circle(
            frame,
            (int(self.target_x), int(self.target_y)),
            self.target_radius,
            (0, 0, 0),
            2,
        )

        overlay_text = (
            f"SIM CAMERA | Target: ({int(self.target_x)}, {int(self.target_y)})"
            f" | Frame: {self.frame_count}"
        )
        cv2.putText(frame, overlay_text, (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

        return True, frame

    def release(self):
        pass

    def isOpened(self) -> bool:
        return True
