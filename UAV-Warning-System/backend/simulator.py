from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from config import BUILDINGS, HISTORY_LEN, STATUS_GREEN


@dataclass(frozen=True)
class DroneBlueprint:
    drone_id: str
    drone_type: str
    speed: float
    waypoints: list[tuple[float, float, float]]


def _scenario_catalog() -> dict[str, dict[str, Any]]:
    return {
        "safe_patrol": {
            "description": "四机中心城区平稳巡航，路径避障且保持连续机动",
            "drones": [
                DroneBlueprint(
                    "UAV-001",
                    "Logistics",
                    5.2,
                    [(-8, 46, 14), (8, 46, 14), (8, 34, 14), (-8, 34, 14)],
                ),
                DroneBlueprint(
                    "UAV-002",
                    "Mapping",
                    5.3,
                    [(-8, -34, 16), (8, -34, 16), (8, -46, 16), (-8, -46, 16)],
                ),
                DroneBlueprint(
                    "UAV-003",
                    "Inspection",
                    5.1,
                    [(-58, 10, 13), (-46, 10, 13), (-46, -10, 13), (-58, -10, 13)],
                ),
                DroneBlueprint(
                    "UAV-004",
                    "Security",
                    5.2,
                    [(50, 12, 15), (62, 12, 15), (62, -12, 15), (50, -12, 15)],
                ),
            ],
        },
        "crossing_conflict": {
            "description": "两机十字交汇，突出动态防撞告警",
            "drones": [
                DroneBlueprint(
                    "UAV-101",
                    "Logistics",
                    6.8,
                    [(-56, -34, 12), (-16, -34, 12), (-56, -34, 12)],
                ),
                DroneBlueprint(
                    "UAV-102",
                    "Inspection",
                    6.8,
                    [(-36, -56, 12), (-36, -16, 12), (-36, -56, 12)],
                ),
                DroneBlueprint(
                    "UAV-103",
                    "Patrol",
                    5.6,
                    [(48, 36, 18), (62, 36, 18), (62, 22, 18), (48, 22, 18)],
                ),
            ],
        },
        "building_conflict": {
            "description": "单机逼近核心建筑，演示静态障碍高危告警与应急悬停",
            "drones": [
                DroneBlueprint(
                    "UAV-201",
                    "Express",
                    6.8,
                    [(-34, 20, 12), (34, 20, 12), (-34, 20, 12)],
                ),
                DroneBlueprint(
                    "UAV-202",
                    "Survey",
                    5.8,
                    [(-58, 58, 16), (-42, 58, 16), (-42, 42, 16), (-58, 42, 16)],
                ),
                DroneBlueprint(
                    "UAV-203",
                    "Cargo",
                    6.2,
                    [(34, -22, 12), (-34, -22, 12), (34, -22, 12)],
                ),
            ],
        },
        "restricted_zone_demo": {
            "description": "单机进入限飞区，仅触发黄色违规预警",
            "drones": [
                DroneBlueprint(
                    "UAV-301",
                    "Training",
                    6.0,
                    [(12, -6, 12), (38, -6, 12), (38, 6, 12), (12, 6, 12), (12, -6, 12)],
                ),
                DroneBlueprint(
                    "UAV-302",
                    "Escort",
                    5.5,
                    [(-56, 40, 18), (-40, 40, 18), (-40, 24, 18), (-56, 24, 18)],
                ),
            ],
        },
    }


class ScenarioSimulator:
    def __init__(self, bootstrap_dt: float = 0.2) -> None:
        self.bootstrap_dt = bootstrap_dt
        self.active_drones: dict[str, dict[str, Any]] = {}
        self.current_scenario: str | None = None

    @staticmethod
    def available_scenarios() -> dict[str, str]:
        catalog = _scenario_catalog()
        return {name: item["description"] for name, item in catalog.items()}

    def load_scenario(self, scenario_name: str) -> dict[str, dict[str, Any]]:
        catalog = _scenario_catalog()
        if scenario_name not in catalog:
            raise ValueError(f"Unknown scenario: {scenario_name}")

        self.active_drones = {}
        self.current_scenario = scenario_name
        for blueprint in catalog[scenario_name]["drones"]:
            self.active_drones[blueprint.drone_id] = self._build_drone_record(blueprint)
        return self.active_drones

    def update(self, dt: float) -> None:
        for drone in self.active_drones.values():
            self._advance_drone(drone, dt)

    def _build_drone_record(self, blueprint: DroneBlueprint) -> dict[str, Any]:
        start = np.array(blueprint.waypoints[0], dtype=np.float32)
        second = np.array(blueprint.waypoints[1], dtype=np.float32)
        heading = second - start
        norm = float(np.linalg.norm(heading))
        direction = np.array([1.0, 0.0, 0.0], dtype=np.float32) if norm < 1e-6 else heading / norm
        initial_vel = direction * blueprint.speed

        history_pos: deque[list[float]] = deque(maxlen=HISTORY_LEN)
        for idx in range(HISTORY_LEN):
            backward_steps = HISTORY_LEN - idx
            hist = start - direction * blueprint.speed * self.bootstrap_dt * backward_steps
            hist[2] = start[2]
            history_pos.append(hist.round(4).tolist())

        return {
            "id": blueprint.drone_id,
            "type": blueprint.drone_type,
            "history_pos": history_pos,
            "current_pos": start.round(4).tolist(),
            "current_vel": initial_vel.round(4).tolist(),
            "predict_traj": [],
            "status": STATUS_GREEN,
            "warning_msg": "",
            "_sim": {
                "waypoints": [list(point) for point in blueprint.waypoints],
                "target_idx": 1 % len(blueprint.waypoints),
                "speed": blueprint.speed,
                "phase": 0.0,
                "speed_phase": (sum(ord(ch) for ch in blueprint.drone_id) % 37) / 37.0 * 2.0 * math.pi,
                "halted": False,
                "halt_reason": "",
            },
        }

    def _advance_drone(self, drone: dict[str, Any], dt: float) -> None:
        sim = drone["_sim"]
        if sim.get("halted"):
            drone["current_vel"] = [0.0, 0.0, 0.0]
            drone["history_pos"].append(drone["current_pos"])
            return

        waypoints = np.array(sim["waypoints"], dtype=np.float32)
        target_idx = int(sim["target_idx"])
        speed = float(sim["speed"])
        speed_phase = float(sim.get("speed_phase", 0.0))

        current = np.array(drone["current_pos"], dtype=np.float32)
        target = waypoints[target_idx]

        direction = target - current
        horizontal_dir = direction[:2]
        distance_xy = float(np.linalg.norm(horizontal_dir))
        if distance_xy < 0.8:
            target_idx = (target_idx + 1) % len(waypoints)
            sim["target_idx"] = target_idx
            target = waypoints[target_idx]
            direction = target - current
            horizontal_dir = direction[:2]
            distance_xy = float(np.linalg.norm(horizontal_dir))

        sim["phase"] = float(sim["phase"]) + dt * (1.0 + speed * 0.05)
        speed_scale = 0.88 + 0.16 * math.sin(float(sim["phase"]) * 0.45 + speed_phase)
        effective_speed = max(1.2, speed * speed_scale)

        if distance_xy > 1e-6:
            desired_xy = horizontal_dir / distance_xy * effective_speed
        else:
            desired_xy = np.zeros(2, dtype=np.float32)

        current_vel = np.array(drone.get("current_vel", [0.0, 0.0, 0.0]), dtype=np.float32)
        current_xy_vel = current_vel[:2]
        turn_alpha = min(0.9, dt * 2.6)
        next_xy_vel = (1.0 - turn_alpha) * current_xy_vel + turn_alpha * desired_xy

        next_speed = float(np.linalg.norm(next_xy_vel))
        if next_speed > effective_speed and next_speed > 1e-6:
            next_xy_vel = next_xy_vel / next_speed * effective_speed

        move_xy = next_xy_vel * dt
        new_xy = current[:2] + move_xy
        if distance_xy > 1e-6:
            overshoot = float(np.dot(move_xy, horizontal_dir)) >= distance_xy * distance_xy
            if overshoot:
                new_xy = target[:2]
                sim["target_idx"] = (target_idx + 1) % len(waypoints)

        new_pos = np.array([new_xy[0], new_xy[1], current[2]], dtype=np.float32)
        target_z = max(2.0, target[2] + 0.28 * math.sin(float(sim["phase"]) * 0.9 + speed_phase))
        z_alpha = min(1.0, dt * 2.4)
        new_pos[2] = current[2] + (target_z - current[2]) * z_alpha

        if self._inside_any_building(new_pos):
            sim["halted"] = True
            sim["halt_reason"] = "hard_building_block"
            drone["current_vel"] = [0.0, 0.0, 0.0]
            drone["history_pos"].append(drone["current_pos"])
            return

        new_vel = (new_pos - current) / max(dt, 1e-6)
        drone["current_pos"] = new_pos.round(4).tolist()
        drone["current_vel"] = new_vel.round(4).tolist()
        drone["history_pos"].append(drone["current_pos"])

    @staticmethod
    def _inside_any_building(point: np.ndarray) -> bool:
        x, y, z = float(point[0]), float(point[1]), float(point[2])
        for building in BUILDINGS:
            center_x, center_y, base_z = building.center
            if not (base_z <= z <= base_z + building.height):
                continue
            if math.hypot(x - center_x, y - center_y) <= building.radius + 0.15:
                return True
        return False
