from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("slam_navigator")


class SLAMNavigator:
    def __init__(self, use_sim_time: bool = True):
        self.use_sim_time = use_sim_time
        self.map_topic = "/map"
        self.scan_topic = "/scan"
        self.odom_topic = "/odom"
        self.map_received = False
        self.robot_pose = None

    def start_slam_toolbox(self):
        logger.info("Starting SLAM Toolbox...")
        logger.info(f"  Input: {self.scan_topic}")
        logger.info(f"  Odometry: {self.odom_topic}")
        logger.info(f"  Output: {self.map_topic}")
        self.map_received = False

    def start_nav2(self):
        logger.info("Starting Nav2 stack...")
        logger.info("  Planner: NavFn")
        logger.info("  Controller: DWB")
        logger.info("  Costmap layers: obstacle_layer, inflation_layer, static_layer")

    def navigate_to_pose(self, x: float, y: float, yaw: float = 0.0) -> bool:
        logger.info(f"Navigating to pose ({x:.1f}, {y:.1f}, {yaw:.2f})")
        logger.info("  Sending goal to Nav2 action server...")
        logger.info("  Goal reached (simulated)")
        return True

    def get_current_map(self) -> Optional[dict]:
        if not self.map_received:
            logger.warning("No map received yet")
            return None
        return {"width": 20.0, "height": 20.0, "resolution": 0.05}


class PathPlanner:
    def __init__(self):
        self.waypoints = []
        self.current_index = 0
        self.obstacle_avoidance = True

    def plan_route(self, start: tuple, end: tuple, obstacles: list = None) -> list:
        logger.info(f"Planning route from {start} to {end}")
        path = [start]

        dx = end[0] - start[0]
        dy = end[1] - start[1]
        steps = max(int(((dx ** 2 + dy ** 2) ** 0.5) / 2.0), 5)

        for i in range(1, steps + 1):
            t = i / steps
            px = start[0] + dx * t
            py = start[1] + dy * t
            path.append((px, py))

        path.append(end)
        logger.info(f"Planned path with {len(path)} waypoints")
        return path


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    import sys
    if len(sys.argv) > 1:
        mission_path = sys.argv[1]
        with open(mission_path) as f:
            mission = json.load(f)
    else:
        mission = {
            "actions": [
                {"type": "NAVIGATE_TO", "pose": {"x": 5.0, "y": 3.0, "yaw": 0.0}},
                {"type": "NAVIGATE_TO", "pose": {"x": 2.0, "y": 8.0, "yaw": 1.57}},
                {"type": "NAVIGATE_TO", "pose": {"x": 0.0, "y": 0.0, "yaw": 0.0}},
            ]
        }
        logger.info("Using default SLAM demo mission")

    navigator = SLAMNavigator()
    navigator.start_slam_toolbox()
    navigator.start_nav2()

    for action in mission.get("actions", []):
        if action["type"] == "NAVIGATE_TO":
            pose = action.get("pose", {})
            navigator.navigate_to_pose(
                x=pose.get("x", 0.0),
                y=pose.get("y", 0.0),
                yaw=pose.get("yaw", 0.0),
            )
            time.sleep(1.0)

    logger.info("SLAM navigation mission complete")


if __name__ == "__main__":
    main()
