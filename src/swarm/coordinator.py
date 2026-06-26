from __future__ import annotations

import json
import logging
import math
import time
from enum import Enum
from typing import Optional

from src.schema.mission import MissionPlan

logger = logging.getLogger("swarm_coordinator")


class FormationType(str, Enum):
    LINE = "LINE"
    WEDGE = "WEDGE"
    DIAMOND = "DIAMOND"
    COLUMN = "COLUMN"


class DroneAgent:
    def __init__(self, drone_id: str, mavlink_port: int = 14540):
        self.drone_id = drone_id
        self.mavlink_port = mavlink_port
        self.position = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.yaw = 0.0
        self.armed = False
        self.mode = "GROUND"

    def __repr__(self) -> str:
        return f"DroneAgent({self.drone_id}, port={self.mavlink_port})"


class SwarmCoordinator:
    def __init__(self):
        self.drones: dict[str, DroneAgent] = {}
        self.formation_type: Optional[FormationType] = None
        self.leader_id: Optional[str] = None

    def add_drone(self, drone_id: str, mavlink_port: int = 14540):
        drone = DroneAgent(drone_id, mavlink_port)
        self.drones[drone_id] = drone
        logger.info(f"Added {drone}")
        return drone

    def set_formation(self, formation: FormationType, leader_id: str = "drone1"):
        self.formation_type = formation
        self.leader_id = leader_id
        logger.info(f"Set formation to {formation.value}, leader: {leader_id}")

    def get_follower_offset(self, drone_id: str) -> tuple[float, float, float]:
        if self.formation_type is None:
            return (0.0, 0.0, 0.0)

        drone_ids = sorted(self.drones.keys())
        try:
            idx = drone_ids.index(drone_id)
        except ValueError:
            return (0.0, 0.0, 0.0)

        spacing = 5.0
        altitude_offset = 0.0

        if self.formation_type == FormationType.LINE:
            return (0.0, spacing * idx, 0.0)

        elif self.formation_type == FormationType.WEDGE:
            if idx == 0:
                return (0.0, 0.0, 0.0)
            return (-spacing, spacing * (idx - 1) - spacing / 2, altitude_offset)

        elif self.formation_type == FormationType.DIAMOND:
            positions = [(0.0, 0.0, 0.0), (-spacing, 0.0, 0.0),
                         (spacing, 0.0, 0.0), (0.0, spacing, 0.0)]
            return positions[idx % len(positions)]

        elif self.formation_type == FormationType.COLUMN:
            return (-spacing * idx, 0.0, 0.0)

        return (0.0, 0.0, 0.0)

    def compute_follower_setpoints(self, leader_pose: dict) -> dict[str, dict]:
        setpoints = {}
        lx = leader_pose.get("x", 0.0)
        ly = leader_pose.get("y", 0.0)
        lz = leader_pose.get("z", 0.0)
        lyaw = leader_pose.get("yaw", 0.0)

        for drone_id, _drone in self.drones.items():
            if drone_id == self.leader_id:
                setpoints[drone_id] = {"x": lx, "y": ly, "z": lz, "yaw": lyaw}
                continue

            ox, oy, oz = self.get_follower_offset(drone_id)

            cos_yaw = math.cos(lyaw)
            sin_yaw = math.sin(lyaw)
            wx = lx + ox * cos_yaw - oy * sin_yaw
            wy = ly + ox * sin_yaw + oy * cos_yaw
            wz = lz + oz

            setpoints[drone_id] = {"x": wx, "y": wy, "z": wz, "yaw": lyaw}

        return setpoints

    def dispatch_mission(self, mission: dict) -> list[dict]:
        missions = []
        target = mission.get("target", "all")

        if target == "all" or target == "swarm":
            for drone_id in self.drones:
                missions.append({**mission, "target": drone_id})
        elif target in self.drones:
            missions.append(mission)
        else:
            for drone_id in self.drones:
                missions.append({**mission, "target": drone_id})

        logger.info(f"Dispatched {len(missions)} missions across {len(self.drones)} drones")
        return missions

    def run_formation_demo(self):
        self.add_drone("drone1", 14540)
        self.add_drone("drone2", 14541)
        self.add_drone("drone3", 14542)

        self.set_formation(FormationType.WEDGE, leader_id="drone1")

        waypoints = [
            (0, 0, -10),
            (20, 0, -10),
            (20, 20, -10),
            (0, 20, -10),
            (0, 0, -10),
        ]

        logger.info(f"Formation: {self.formation_type.value}")
        logger.info(f"Drones: {list(self.drones.keys())}")

        for i, (x, y, z) in enumerate(waypoints):
            leader_pose = {"x": x, "y": y, "z": z, "yaw": 0.0}
            setpoints = self.compute_follower_setpoints(leader_pose)

            logger.info(f"Waypoint {i}: leader=({x},{y},{z})")
            for did, sp in setpoints.items():
                logger.info(f"  {did}: ({sp['x']:.1f}, {sp['y']:.1f}, {sp['z']:.1f})")
            time.sleep(0.5)

        logger.info("Formation demo complete")


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    import sys

    coordinator = SwarmCoordinator()

    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            mission = json.load(f)
        missions = coordinator.dispatch_mission(mission)
        logger.info(f"Dispatched {len(missions)} missions")
    else:
        coordinator.run_formation_demo()


if __name__ == "__main__":
    main()
