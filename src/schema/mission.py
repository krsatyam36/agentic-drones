from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field, model_validator


class ActionType(str, Enum):
    TAKEOFF = "TAKEOFF"
    GOTO = "GOTO"
    LOITER = "LOITER"
    RETURN_TO_LAUNCH = "RETURN_TO_LAUNCH"
    LAND = "LAND"


class Waypoint(BaseModel):
    x: float = Field(..., description="X position in meters (local NED)")
    y: float = Field(..., description="Y position in meters (local NED)")
    z: float = Field(..., description="Z altitude in meters (local NED, negative = up)")


class Action(BaseModel):
    type: ActionType
    waypoint: Optional[Waypoint] = None
    altitude: Optional[float] = Field(None, ge=1.0, le=50.0, description="Altitude in meters")
    speed: Optional[float] = Field(None, ge=0.5, le=15.0, description="Speed in m/s")
    loiter_seconds: Optional[float] = Field(None, ge=0.0, le=300.0, description="Loiter duration")
    repeat_count: Optional[int] = Field(None, ge=1, le=100, description="Repeat count")


class MissionPlan(BaseModel):
    mission_id: str = Field(default="", description="Unique mission identifier")
    target: str = Field(default="drone1", description="Target agent identifier")
    actions: List[Action] = Field(..., min_length=1, max_length=50)
    geofence: Optional[dict] = Field(
        default=None,
        description="Geofence bounding box: {min_x, max_x, min_y, max_y, min_z, max_z}"
    )

    @model_validator(mode="after")
    def validate_first_action_is_takeoff(self):
        if self.actions and self.actions[0].type != ActionType.TAKEOFF:
            raise ValueError("Mission must start with TAKEOFF")
        return self

    @model_validator(mode="after")
    def validate_last_action_is_land_or_rtl(self):
        if self.actions:
            last = self.actions[-1].type
            if last not in (ActionType.LAND, ActionType.RETURN_TO_LAUNCH):
                raise ValueError("Mission must end with LAND or RETURN_TO_LAUNCH")
        return self

    @model_validator(mode="after")
    def validate_goto_has_waypoint(self):
        for i, action in enumerate(self.actions):
            if action.type == ActionType.GOTO and action.waypoint is None:
                raise ValueError(f"Action {i}: GOTO requires a waypoint")
        return self

    @model_validator(mode="after")
    def validate_takeoff_has_altitude(self):
        for i, action in enumerate(self.actions):
            if action.type == ActionType.TAKEOFF and action.altitude is None:
                raise ValueError(f"Action {i}: TAKEOFF requires altitude")
        return self

    @model_validator(mode="after")
    def validate_waypoint_jump_distance(self):
        max_jump = 500.0
        prev_wp = None
        for i, action in enumerate(self.actions):
            if action.waypoint is not None:
                if prev_wp is not None:
                    dx = action.waypoint.x - prev_wp.x
                    dy = action.waypoint.y - prev_wp.y
                    dz = action.waypoint.z - prev_wp.z
                    dist = (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5
                    if dist > max_jump:
                        raise ValueError(
                            f"Jump distance {dist:.1f}m between actions exceeds max {max_jump}m"
                        )
                prev_wp = action.waypoint
        return self

    @model_validator(mode="after")
    def validate_geofence_compliance(self):
        gf = self.geofence
        if gf is None:
            return self
        required_keys = {"min_x", "max_x", "min_y", "max_y", "min_z", "max_z"}
        if not required_keys.issubset(gf.keys()):
            raise ValueError(f"Geofence must contain: {required_keys}")
        for i, action in enumerate(self.actions):
            if action.waypoint is not None:
                wp = action.waypoint
                if not (gf["min_x"] <= wp.x <= gf["max_x"]):
                    raise ValueError(f"Action {i}: waypoint.x {wp.x} outside geofence x-range")
                if not (gf["min_y"] <= wp.y <= gf["max_y"]):
                    raise ValueError(f"Action {i}: waypoint.y {wp.y} outside geofence y-range")
                if not (gf["min_z"] <= wp.z <= gf["max_z"]):
                    raise ValueError(f"Action {i}: waypoint.z {wp.z} outside geofence z-range")
        return self
