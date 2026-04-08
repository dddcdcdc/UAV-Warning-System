from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from config import HISTORY_LEN, STATUS_GREEN


@dataclass(frozen=True)  #不可变配置对象，绘制无人机的依据
class DroneBlueprint:
    drone_id: str
    drone_type: str
    speed: float
    waypoints: list[tuple[float, float, float]]


def _scenario_catalog() -> dict[str, dict[str, Any]]:
    return {
        "safe_patrol": {
            "description": "四机中心城区平稳巡航，避开核心障碍并保持顺滑机动",
            "drones": [
                DroneBlueprint(
                    "UAV-001",
                    "Logistics",
                    4.0,
                    [
                        (-42, 40, 14),
                        (-38, 44, 14),
                        (-30, 46, 14),
                        (-22, 44, 14),
                        (-18, 40, 14),
                        (-20, 34, 14),
                        (-28, 32, 14),
                        (-36, 34, 14),
                    ],
                ),
                DroneBlueprint(
                    "UAV-002",
                    "Mapping",
                    4.1,
                    [
                        (18, 42, 16),
                        (24, 46, 16),
                        (32, 46, 16),
                        (38, 42, 16),
                        (40, 34, 16),
                        (34, 30, 16),
                        (26, 30, 16),
                        (20, 34, 16),
                    ],
                ),
                DroneBlueprint(
                    "UAV-003",
                    "Inspection",
                    3.9,
                    [
                        (-46, -6, 13),
                        (-40, -2, 13),
                        (-32, -2, 13),
                        (-28, -6, 13),
                        (-28, -14, 13),
                        (-32, -18, 13),
                        (-40, -18, 13),
                        (-46, -14, 13),
                    ],
                ),
                DroneBlueprint(
                    "UAV-004",
                    "Security",
                    4.0,
                    [
                        (30, -34, 15),
                        (36, -30, 15),
                        (44, -30, 15),
                        (48, -34, 15),
                        (48, -42, 15),
                        (44, -46, 15),
                        (36, -46, 15),
                        (30, -42, 15),
                    ],
                ),
            ],
        },
        "crossing_conflict": {
            "description": "两机十字交汇，突出动态防撞告警（平滑往返）",
            "drones": [
                DroneBlueprint(
                    "UAV-101",
                    "Logistics",
                    5.4,
                    [
                        (-50, -30, 12),
                        (-44, -32, 12),
                        (-36, -33, 12),
                        (-28, -33, 12),
                        (-20, -32, 12),
                        (-12, -30, 12),
                        (-20, -28, 12),
                        (-28, -27, 12),
                        (-36, -27, 12),
                        (-44, -28, 12),
                    ],
                ),
                DroneBlueprint(
                    "UAV-102",
                    "Inspection",
                    5.4,
                    [
                        (-30, -50, 12),
                        (-32, -44, 12),
                        (-33, -36, 12),
                        (-33, -28, 12),
                        (-32, -20, 12),
                        (-30, -12, 12),
                        (-28, -20, 12),
                        (-27, -28, 12),
                        (-27, -36, 12),
                        (-28, -44, 12),
                    ],
                ),
                DroneBlueprint(
                    "UAV-103",
                    "Patrol",
                    5.6,
                    [
                        (34, 30, 18),
                        (40, 34, 18),
                        (48, 34, 18),
                        (52, 30, 18),
                        (52, 22, 18),
                        (48, 18, 18),
                        (40, 18, 18),
                        (34, 22, 18),
                    ],
                ),
            ],
        },
        "building_conflict": {
            "description": "单机逼近核心建筑，演示静态障碍高危告警与应急悬停",
            "drones": [
                DroneBlueprint(
                    "UAV-201",
                    "Express",
                    5.2,
                    [
                        (-48, 20, 12),
                        (-40, 20, 12),
                        (-32, 20, 12),
                        (-24, 20, 12),
                        (-16, 20, 12),
                        (-8, 20, 12),
                        (0, 20, 12),
                        (8, 20, 12),
                        (14, 20, 12),
                        (20, 20, 12),
                        (26, 20, 12),
                        (32, 20, 12),
                    ],
                ),
                DroneBlueprint(
                    "UAV-202",
                    "Survey",
                    4.2,
                    [
                        (-58, 58, 16),
                        (-52, 62, 16),
                        (-44, 62, 16),
                        (-40, 58, 16),
                        (-40, 50, 16),
                        (-44, 46, 16),
                        (-52, 46, 16),
                        (-58, 50, 16),
                    ],
                ),
                DroneBlueprint(
                    "UAV-203",
                    "Cargo",
                    4.6,
                    [
                        (34, -22, 12),
                        (26, -20, 12),
                        (18, -18, 12),
                        (10, -18, 12),
                        (2, -20, 12),
                        (-6, -22, 12),
                        (2, -24, 12),
                        (10, -26, 12),
                        (18, -26, 12),
                        (26, -24, 12),
                    ],
                ),
            ],
        },
        "restricted_zone_demo": {
            "description": "单机进入限飞区，仅触发黄色违规预警",
            "drones": [
                DroneBlueprint(
                    "UAV-301",
                    "Training",
                    4.8,
                    [
                        (12, -10, 12),
                        (18, -8, 12),
                        (24, -7, 12),
                        (30, -6, 12),
                        (36, -2, 12),
                        (36, 2, 12),
                        (30, 6, 12),
                        (24, 7, 12),
                        (18, 8, 12),
                        (12, 10, 12),
                        (10, 0, 12),
                    ],
                ),
                DroneBlueprint(
                    "UAV-302",
                    "Escort",
                    4.2,
                    [
                        (-56, 40, 18),
                        (-50, 44, 18),
                        (-42, 44, 18),
                        (-38, 40, 18),
                        (-38, 32, 18),
                        (-42, 28, 18),
                        (-50, 28, 18),
                        (-56, 32, 18),
                    ],
                ),
            ],
        },
    }

#模拟了四种情形下的无人机状态

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
        speed = float(sim["speed"]) #speed就是每个文件中设置的速度
        speed_phase = float(sim.get("speed_phase", 0.0))

        current = np.array(drone["current_pos"], dtype=np.float32)
        target = waypoints[target_idx]

        direction = target - current
        horizontal_dir = direction[:2]
        distance_xy = float(np.linalg.norm(horizontal_dir)) #计算方向和平面距离
        if distance_xy < 0.8: #距离小于0.8后自动切换下一航点
            target_idx = (target_idx + 1) % len(waypoints)
            sim["target_idx"] = target_idx
            target = waypoints[target_idx]
            direction = target - current
            horizontal_dir = direction[:2]
            distance_xy = float(np.linalg.norm(horizontal_dir)) 

        sim["phase"] = float(sim["phase"]) + dt * (1.0 + speed * 0.05)
        speed_scale = 0.88 + 0.16 * math.sin(float(sim["phase"]) * 0.45 + speed_phase)
        effective_speed = max(1.2, speed * speed_scale) 
        #使用相位的方式让速度尺度上下浮动进而让速度上下浮动


        if distance_xy > 1e-6:
            desired_xy = horizontal_dir / distance_xy * effective_speed
        else:
            desired_xy = np.zeros(2, dtype=np.float32)
        #如果距离太小，则将目标速度设为0

        current_vel = np.array(drone.get("current_vel", [0.0, 0.0, 0.0]), dtype=np.float32)
        current_xy_vel = current_vel[:2]
        turn_alpha = min(0.85, dt * 2.1)
        next_xy_vel = (1.0 - turn_alpha) * current_xy_vel + turn_alpha * desired_xy

        #做了位置限制和速度限制

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
        #此外还有进行高度更新


        new_vel = (new_pos - current) / max(dt, 1e-6)
        drone["current_pos"] = new_pos.round(4).tolist()
        drone["current_vel"] = new_vel.round(4).tolist()
        drone["history_pos"].append(drone["current_pos"])
