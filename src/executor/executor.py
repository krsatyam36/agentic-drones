from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger("executor")


class ExecutorState(Enum):
    IDLE = "IDLE"
    ARMING = "ARMING"
    TAKEOFF = "TAKEOFF"
    EXECUTING = "EXECUTING"
    LANDING = "LANDING"
    DONE = "DONE"
    FAILSAFE = "FAILSAFE"


class ActionType:
    TAKEOFF = "TAKEOFF"
    GOTO = "GOTO"
    LOITER = "LOITER"
    RETURN_TO_LAUNCH = "RETURN_TO_LAUNCH"
    LAND = "LAND"


class DeterministicExecutor:
    def __init__(self, connection_string: str = "udp://:14540"):
        self.connection_string = connection_string
        self.state = ExecutorState.IDLE
        self.drone = None
        self.audit_log: list[dict] = []
        self.telemetry = {}

    def log_command(self, action: str, detail: dict):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "detail": detail,
        }
        self.audit_log.append(entry)
        logger.info(f"[CMD] {action}: {json.dumps(detail)}")

    def save_audit_log(self, path: str = "audit_log.json"):
        with open(path, "w") as f:
            json.dump(self.audit_log, f, indent=2)
        logger.info(f"Audit log saved to {path}")

    def connect(self):
        logger.info(f"Connecting to drone at {self.connection_string} ...")
        try:
            from mavsdk import System
            self.drone = System(mavsdk_server_address=self.connection_string)
        except ImportError:
            logger.warning("MAVSDK not available — running in simulation mode")
            self.drone = None
            return
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._do_connect(loop))

    async def _do_connect(self, loop):
        try:
            await asyncio.wait_for(self.drone.connect(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Drone connection timed out — running in simulation mode")
            self.drone = None
            return
        logger.info("Connecting...")
        try:
            async for state in asyncio.wait_for(
                self.drone.core.connection_state(), timeout=5.0
            ):
                if state.is_connected:
                    logger.info("Drone connected")
                    break
        except asyncio.TimeoutError:
            logger.warning("No connection state received — running in simulation mode")
            self.drone = None

    def arm(self):
        self.state = ExecutorState.ARMING
        self.log_command("ARM", {})
        logger.info("Arming...")

    def takeoff(self, altitude: float = 10.0):
        self.state = ExecutorState.TAKEOFF
        self.log_command("TAKEOFF", {"altitude": altitude})
        logger.info(f"Taking off to {altitude}m...")

    def goto(self, x: float, y: float, z: float, speed: Optional[float] = None):
        self.log_command("GOTO", {"x": x, "y": y, "z": z, "speed": speed})
        logger.info(f"Going to ({x}, {y}, {z}) at speed {speed or 'default'}")

    def loiter(self, seconds: float):
        self.log_command("LOITER", {"seconds": seconds})
        logger.info(f"Loitering for {seconds}s...")
        time.sleep(seconds)

    def return_to_launch(self):
        self.log_command("RETURN_TO_LAUNCH", {})
        logger.info("Returning to launch...")

    def land(self):
        self.state = ExecutorState.LANDING
        self.log_command("LAND", {})
        logger.info("Landing...")

    def set_velocity_body(self, vx: float, vy: float, vz: float,
                          yaw_rate: float = 0.0):
        self.log_command("SET_VELOCITY_BODY", {
            "vx": round(vx, 2), "vy": round(vy, 2),
            "vz": round(vz, 2), "yaw_rate": round(yaw_rate, 2),
        })
        logger.info(f"Body velocity: vx={vx:.2f} vy={vy:.2f} vz={vz:.2f} yaw_rate={yaw_rate:.2f}")

    def failsafe(self, reason: str):
        self.state = ExecutorState.FAILSAFE
        self.log_command("FAILSAFE", {"reason": reason})
        logger.error(f"FAILSAFE: {reason}")

    def execute_mission(self, mission: dict) -> bool:
        actions = mission.get("actions", [])
        logger.info(f"Executing mission with {len(actions)} actions")

        self.state = ExecutorState.ARMING
        self.arm()

        for i, action in enumerate(actions):
            if self.state == ExecutorState.FAILSAFE:
                break

            atype = action["type"]
            detail = {}

            if atype == ActionType.TAKEOFF:
                alt = action.get("altitude", 10.0)
                self.takeoff(alt)

            elif atype == ActionType.GOTO:
                wp = action.get("waypoint")
                if wp:
                    self.goto(
                        x=wp["x"],
                        y=wp["y"],
                        z=wp.get("z", -10.0),
                        speed=action.get("speed"),
                    )
                else:
                    self.failsafe(f"GOTO at index {i} missing waypoint")
                    break

            elif atype == ActionType.LOITER:
                secs = action.get("loiter_seconds", 10.0)
                self.loiter(secs)

            elif atype == ActionType.RETURN_TO_LAUNCH:
                self.return_to_launch()

            elif atype == ActionType.LAND:
                self.land()

            else:
                self.failsafe(f"Unknown action type: {atype}")
                break

        if self.state != ExecutorState.FAILSAFE:
            self.state = ExecutorState.DONE

        logger.info(f"Mission complete. Final state: {self.state.value}")
        return self.state == ExecutorState.DONE


def load_mission(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Deterministic drone mission executor")
    parser.add_argument("--mission", "-m", type=str, required=True,
                        help="Path to validated mission JSON file")
    parser.add_argument("--connection", "-c", type=str, default="udp://:14540",
                        help="MAVSDK connection string")
    parser.add_argument("--log", "-l", type=str, default="audit_log.json",
                        help="Path to save audit log")
    args = parser.parse_args()

    mission = load_mission(args.mission)
    executor = DeterministicExecutor(connection_string=args.connection)
    executor.connect()
    success = executor.execute_mission(mission)
    executor.save_audit_log(args.log)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
