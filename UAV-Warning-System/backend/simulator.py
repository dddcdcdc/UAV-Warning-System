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
            "description": "四机在路口周边安全巡航，持续避障且不触发冲突告警",
            "drones": [
                DroneBlueprint(
                    "UAV-001",
                    "Logistics",
                    4.0,
                    [
                        (-18, 30, 14),
                        (-12, 36, 14),
                        (-4, 41, 14),
                        (6, 45, 14),
                        (14, 46, 14),
                        (18, 42, 14),
                        (18, 35, 14),
                        (13, 30, 14),
                        (5, 27, 14),
                        (-4, 26, 14),
                        (-12, 27, 14),
                        (-18, 29, 14),
                    ],
                ),
                DroneBlueprint(
                    "UAV-002",
                    "Mapping",
                    4.0,
                    [
                        (-62, 2, 16),
                        (-58, 7, 16),
                        (-52, 10, 16),
                        (-44, 10, 16),
                        (-38, 7, 16),
                        (-36, 2, 16),
                        (-38, -5, 16),
                        (-44, -10, 16),
                        (-52, -12, 16),
                        (-58, -11, 16),
                        (-62, -7, 16),
                        (-64, -2, 16),
                    ],
                ),
                DroneBlueprint(
                    "UAV-003",
                    "Inspection",
                    3.8,
                    [
                        (-8, -26, 13),
                        (-2, -32, 13),
                        (6, -37, 13),
                        (14, -40, 13),
                        (20, -38, 13),
                        (20, -32, 13),
                        (17, -26, 13),
                        (11, -22, 13),
                        (3, -20, 13),
                        (-4, -20, 13),
                        (-10, -23, 13),
                        (-12, -30, 13),
                    ],
                ),
                DroneBlueprint(
                    "UAV-004",
                    "Security",
                    3.9,
                    [
                        (44, 8, 15),
                        (49, 11, 15),
                        (56, 12, 15),
                        (62, 10, 15),
                        (66, 6, 15),
                        (66, 1, 15),
                        (63, -5, 15),
                        (57, -10, 15),
                        (50, -12, 15),
                        (44, -9, 15),
                        (42, -4, 15),
                        (42, 2, 15),
                    ],
                ),
            ],
        },
        "crossing_conflict": {
            "description": "四机弧线交汇演示：一组稳定红色防撞告警，另一组稳定黄色近距预警（节奏不同）",
            "drones": [
                DroneBlueprint(
                    "UAV-101",
                    "Logistics",
                    5.5,
                    [
                        (-32.0, 14.2, 12.0),
                        (-26.0, 14.9, 12.0),
                        (-20.0, 15.6, 12.0),
                        (-15.0, 16.0, 12.0),
                        (-12.0, 16.0, 12.0),
                        (-8.0, 15.8, 12.0),
                        (-2.0, 15.2, 12.0),
                        (6.0, 14.9, 12.0),
                        (14.0, 15.3, 12.0),
                        (22.0, 16.0, 12.0),
                        (28.0, 18.4, 12.0),
                        (30.0, 22.6, 12.0),
                        (28.0, 27.2, 12.0),
                        (22.0, 30.0, 12.0),
                        (14.0, 30.4, 12.0),
                        (6.0, 28.8, 12.0),
                        (-2.0, 25.8, 12.0),
                        (-8.0, 21.4, 12.0),
                        (-12.0, 16.0, 12.0),
                        (-16.0, 11.4, 12.0),
                        (-24.0, 9.6, 12.0),
                        (-30.0, 11.0, 12.0),
                    ],
                ),
                DroneBlueprint(
                    "UAV-102",
                    "Inspection",
                    5.4,
                    [
                        (-14.0, 36.0, 12.0),
                        (-13.2, 30.0, 12.0),
                        (-12.6, 24.0, 12.0),
                        (-12.2, 20.0, 12.0),
                        (-12.0, 17.4, 12.0),
                        (-12.0, 16.0, 12.0),
                        (-12.2, 14.2, 12.0),
                        (-12.8, 10.2, 12.0),
                        (-13.5, 4.2, 12.0),
                        (-14.2, -1.8, 12.0),
                        (-16.0, -7.6, 12.0),
                        (-20.2, -9.8, 12.0),
                        (-24.0, -8.2, 12.0),
                        (-26.0, -2.2, 12.0),
                        (-24.2, 5.8, 12.0),
                        (-20.0, 11.8, 12.0),
                        (-16.0, 14.8, 12.0),
                        (-12.0, 16.0, 12.0),
                        (-8.2, 18.2, 12.0),
                        (-4.2, 22.2, 12.0),
                        (-2.0, 28.0, 12.0),
                        (-4.2, 33.0, 12.0),
                        (-8.4, 36.0, 12.0),
                        (-12.4, 37.0, 12.0),
                    ],
                ),
                DroneBlueprint(
                    "UAV-103",
                    "Patrol",
                    4.5,
                    [
                        (2.0, 18.2, 14.2),
                        (7.0, 18.8, 14.2),
                        (12.0, 19.3, 14.2),
                        (16.0, 19.7, 14.2),
                        (20.2, 19.8, 14.2),
                        (24.8, 19.7, 14.2),
                        (30.0, 19.3, 14.2),
                        (35.0, 18.7, 14.2),
                        (40.0, 18.2, 14.2),
                        (44.0, 20.4, 14.2),
                        (45.0, 23.8, 14.2),
                        (43.0, 27.2, 14.2),
                        (38.0, 29.1, 14.2),
                        (32.0, 30.0, 14.2),
                        (26.0, 29.4, 14.2),
                        (20.8, 28.0, 14.2),
                        (15.0, 26.0, 14.2),
                        (9.0, 23.6, 14.2),
                        (4.0, 20.8, 14.2),
                    ],
                ),
                DroneBlueprint(
                    "UAV-104",
                    "Relay",
                    3.9,
                    [
                        (22.0, 34.0, 15.2),
                        (21.9, 30.0, 15.2),
                        (21.8, 26.0, 15.2),
                        (21.7, 22.0, 15.2),
                        (21.6, 19.2, 15.2),
                        (21.7, 16.6, 15.2),
                        (21.9, 14.0, 15.2),
                        (22.1, 11.0, 15.2),
                        (20.0, 8.8, 15.2),
                        (17.4, 9.6, 15.2),
                        (15.6, 12.2, 15.2),
                        (15.0, 16.0, 15.2),
                        (15.2, 20.0, 15.2),
                        (16.4, 24.0, 15.2),
                        (18.2, 27.4, 15.2),
                        (20.0, 30.2, 15.2),
                        (21.2, 32.6, 15.2),
                    ],
                ),
            ],
        },
        "building_conflict": {
            "description": "单机弧线逼近核心建筑，演示静态障碍红色告警与应急悬停",
            "drones": [
                DroneBlueprint(
                    "UAV-201",
                    "Express",
                    5.2,
                    [
                        (2.0, -38.0, 12.0),
                        (8.0, -35.2, 12.0),
                        (14.0, -33.0, 12.0),
                        (20.0, -31.2, 12.0),
                        (25.0, -29.9, 12.0),
                        (29.0, -28.8, 12.0),
                        (32.0, -28.1, 12.0),
                        (34.0, -28.3, 12.0),
                        (36.0, -29.0, 12.0),
                        (39.0, -30.4, 12.0),
                        (43.0, -32.6, 12.0),
                        (48.0, -34.8, 12.0),
                        (54.0, -36.4, 12.0),
                        (60.0, -36.8, 12.0),
                    ],
                ),
                DroneBlueprint(
                    "UAV-202",
                    "Survey",
                    4.2,
                    [
                        (-78.0, 32.0, 16.0),
                        (-73.0, 37.0, 16.0),
                        (-66.0, 40.0, 16.0),
                        (-59.0, 39.2, 16.0),
                        (-54.0, 35.4, 16.0),
                        (-52.0, 29.2, 16.0),
                        (-54.0, 23.2, 16.0),
                        (-59.0, 19.4, 16.0),
                        (-66.0, 18.8, 16.0),
                        (-73.0, 21.4, 16.0),
                        (-77.0, 26.2, 16.0),
                    ],
                ),
                DroneBlueprint(
                    "UAV-203",
                    "Cargo",
                    4.6,
                    [
                        (42.0, 9.0, 13.0),
                        (47.0, 12.6, 13.0),
                        (53.0, 14.6, 13.0),
                        (60.0, 14.0, 13.0),
                        (65.0, 10.4, 13.0),
                        (67.0, 4.6, 13.0),
                        (66.0, -1.8, 13.0),
                        (62.0, -6.4, 13.0),
                        (56.0, -8.2, 13.0),
                        (50.0, -7.2, 13.0),
                        (45.0, -3.6, 13.0),
                        (42.0, 1.8, 13.0),
                    ],
                ),
            ],
        },
        "restricted_zone_demo": {
            "description": "单机进入限飞区，仅触发黄色违规预警，不触发建筑碰撞",
            "drones": [
                DroneBlueprint(
                    "UAV-301",
                    "Training",
                    4.8,
                    [
                        (14, -6, 12),
                        (20, -4, 12),
                        (24, -2, 12),
                        (28, -1, 12),
                        (31, 0, 12),
                        (34, 1, 12),
                        (36, 4, 12),
                        (34, 7, 12),
                        (30, 8, 12),
                        (24, 7, 12),
                        (18, 4, 12),
                        (14, 0, 12),
                    ],
                ),
                DroneBlueprint(
                    "UAV-302",
                    "Escort",
                    4.2,
                    [
                        (-70, 18, 18),
                        (-64, 22, 18),
                        (-56, 22, 18),
                        (-50, 18, 18),
                        (-50, 10, 18),
                        (-56, 6, 18),
                        (-64, 6, 18),
                        (-70, 10, 18),
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
        turn_alpha = min(0.72, dt * 1.6)
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
