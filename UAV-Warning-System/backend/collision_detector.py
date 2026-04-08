from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np

from config import (
    BUILDING_RED_BUFFER,
    BUILDING_YELLOW_BUFFER,
    BUILDINGS,
    DYNAMIC_RED_DISTANCE,
    DYNAMIC_YELLOW_DISTANCE,
    NO_FLY_ZONES,
    PREDICT_DT,
    RESTRICTED_WARN_BUFFER,
    RESTRICTED_ZONES,
    STATIC_RED_BUFFER,
    STATIC_YELLOW_BUFFER,
    STATUS_GREEN,
    STATUS_PRIORITY,
    STATUS_RED,
    STATUS_YELLOW,
)


Zone = dict[str, Any]


def _rect_points(center_x: float, center_y: float, width: float, depth: float) -> list[list[float]]:
    half_w = width / 2.0
    half_d = depth / 2.0
    return [
        [center_x - half_w, center_y - half_d],
        [center_x + half_w, center_y - half_d],
        [center_x + half_w, center_y + half_d],
        [center_x - half_w, center_y + half_d],
    ]


def _default_zones() -> tuple[list[Zone], list[Zone], list[Zone]]:
    buildings = [
        {
            "zone_id": item.zone_id,
            "shape": "polygon",
            "zone_kind": "building",
            "points": _rect_points(item.center[0], item.center[1], float(item.width), float(item.depth)),
            "height": float(item.height),
            "base_z": float(item.center[2]),
        }
        for item in BUILDINGS
    ]
    no_fly = [
        {
            "zone_id": item.zone_id,
            "shape": "cylinder",
            "zone_kind": "no_fly",
            "center": list(item.center),
            "radius": float(item.radius),
            "height": float(item.height),
        }
        for item in NO_FLY_ZONES
    ]
    restricted = [
        {
            "zone_id": item.zone_id,
            "shape": "cylinder",
            "zone_kind": "restricted",
            "center": list(item.center),
            "radius": float(item.radius),
            "height": float(item.height),
        }
        for item in RESTRICTED_ZONES
    ]
    return buildings, no_fly, restricted


def _height_overlap(point: list[float], base_z: float, height: float) -> bool:
    return base_z <= point[2] <= (base_z + height)


def _clearance_to_cylinder(point: list[float], zone: Zone) -> float:
    point_xy = np.array(point[:2], dtype=np.float32)
    center = zone.get("center", [0.0, 0.0, 0.0])
    center_xy = np.array(center[:2], dtype=np.float32)
    radius = float(zone.get("radius", 0.0))
    return float(np.linalg.norm(point_xy - center_xy) - radius)


def _point_in_polygon(point_xy: np.ndarray, polygon: np.ndarray) -> bool:
    x, y = point_xy
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / max((yj - yi), 1e-9) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _distance_to_segment(point: np.ndarray, seg_a: np.ndarray, seg_b: np.ndarray) -> float:
    ab = seg_b - seg_a
    denom = float(np.dot(ab, ab))
    if denom < 1e-9:
        return float(np.linalg.norm(point - seg_a))
    t = float(np.dot(point - seg_a, ab) / denom)
    t = max(0.0, min(1.0, t))
    nearest = seg_a + t * ab
    return float(np.linalg.norm(point - nearest))


def _clearance_to_polygon(point: list[float], zone: Zone) -> float:
    pts = zone.get("points", [])
    if len(pts) < 3:
        return 1e9
    polygon = np.array(pts, dtype=np.float32)
    query = np.array(point[:2], dtype=np.float32)

    inside = _point_in_polygon(query, polygon)
    edge_min = 1e9
    for idx in range(len(polygon)):
        seg_a = polygon[idx]
        seg_b = polygon[(idx + 1) % len(polygon)]
        edge_min = min(edge_min, _distance_to_segment(query, seg_a, seg_b))
    if inside:
        return -edge_min
    return edge_min


def _zone_clearance(point: list[float], zone: Zone) -> float:
    shape = zone.get("shape", "cylinder")
    if shape == "polygon":
        return _clearance_to_polygon(point, zone)
    return _clearance_to_cylinder(point, zone)


def _zone_height_overlap(point: list[float], zone: Zone) -> bool:
    center = zone.get("center", [0.0, 0.0, 0.0])
    base_z = float(zone.get("base_z", center[2] if len(center) > 2 else 0.0))
    height = float(zone.get("height", 50.0))
    return _height_overlap(point, base_z, height)


def _upgrade_alert(drone: dict[str, Any], status: str, msg: str) -> None:
    current = drone.get("status", STATUS_GREEN)
    if STATUS_PRIORITY[status] > STATUS_PRIORITY[current]:
        drone["status"] = status
        drone["warning_msg"] = msg
        drone["warning_category"] = drone.get("_pending_warning_category", "general")
        return
    if STATUS_PRIORITY[status] == STATUS_PRIORITY[current] and not drone.get("warning_msg"):
        drone["warning_msg"] = msg
        drone["warning_category"] = drone.get("_pending_warning_category", "general")


def _evaluate_static_conflict(
    drone_id: str, drone: dict[str, Any], static_zones: list[Zone]
) -> tuple[str, str, str]:
    trajectory = drone.get("predict_traj", [])
    best_yellow = ""
    best_yellow_category = "general"

    for step_idx, point in enumerate(trajectory):
        t = (step_idx + 1) * PREDICT_DT
        for zone in static_zones:
            if not _zone_height_overlap(point, zone):
                continue
            clearance = _zone_clearance(point, zone)
            zone_kind = str(zone.get("zone_kind", "static"))
            zone_id = zone.get("zone_id", "STATIC-ZONE")
            red_buffer = BUILDING_RED_BUFFER if zone_kind == "building" else STATIC_RED_BUFFER
            yellow_buffer = BUILDING_YELLOW_BUFFER if zone_kind == "building" else STATIC_YELLOW_BUFFER

            if clearance <= red_buffer:
                if zone_kind == "building":
                    return (
                        STATUS_RED,
                        f"[{drone_id}] 建筑碰撞警报：预测 {t:.1f}s 后撞击 {zone_id}",
                        "building_collision",
                    )
                if zone_kind == "no_fly":
                    return (
                        STATUS_RED,
                        f"[{drone_id}] 禁飞区侵入警报：预测 {t:.1f}s 后进入 {zone_id}",
                        "no_fly_intrusion",
                    )
                return (
                    STATUS_RED,
                    f"[{drone_id}] 战术告警：预测 {t:.1f}s 后撞击 {zone_id}",
                    "static_collision",
                )

            if clearance <= yellow_buffer and not best_yellow:
                if zone_kind == "building":
                    best_yellow = f"[{drone_id}] 建筑接近预警：预测轨迹逼近 {zone_id}"
                    best_yellow_category = "building_near"
                elif zone_kind == "no_fly":
                    best_yellow = f"[{drone_id}] 禁飞区接近预警：预测轨迹逼近 {zone_id}"
                    best_yellow_category = "no_fly_near"
                else:
                    best_yellow = f"[{drone_id}] 接近警告：预测轨迹逼近 {zone_id}"
                    best_yellow_category = "static_near"

    if best_yellow:
        return STATUS_YELLOW, best_yellow, best_yellow_category
    return STATUS_GREEN, "", "general"


def _evaluate_restricted_zone(
    drone_id: str, drone: dict[str, Any], restricted_zones: list[Zone]
) -> tuple[str, str, str]:
    trajectory = drone.get("predict_traj", [])
    for step_idx, point in enumerate(trajectory):
        t = (step_idx + 1) * PREDICT_DT
        for zone in restricted_zones:
            if not _zone_height_overlap(point, zone):
                continue
            clearance = _zone_clearance(point, zone)
            zone_id = zone.get("zone_id", "RZ")
            if clearance <= 0.0:
                return (
                    STATUS_YELLOW,
                    f"[{drone_id}] 违规预警：预测 {t:.1f}s 后将进入限飞区 {zone_id}",
                    "restricted_intrusion",
                )
            if clearance <= RESTRICTED_WARN_BUFFER:
                return (
                    STATUS_YELLOW,
                    f"[{drone_id}] 限飞区接近预警：预测 {t:.1f}s 后逼近 {zone_id}",
                    "restricted_near",
                )
    return STATUS_GREEN, "", "general"


def _evaluate_dynamic_conflicts(active_drones: dict[str, dict[str, Any]]) -> None:
    items = list(active_drones.items())
    for (id_a, drone_a), (id_b, drone_b) in combinations(items, 2):
        traj_a = drone_a.get("predict_traj", [])
        traj_b = drone_b.get("predict_traj", [])
        steps = min(len(traj_a), len(traj_b))
        if steps == 0:
            continue

        yellow_time: float | None = None
        for idx in range(steps):
            point_a = np.array(traj_a[idx], dtype=np.float32)
            point_b = np.array(traj_b[idx], dtype=np.float32)
            distance = float(np.linalg.norm(point_a - point_b))
            t = (idx + 1) * PREDICT_DT

            if distance <= DYNAMIC_RED_DISTANCE:
                drone_a["_pending_warning_category"] = "dynamic_collision"
                _upgrade_alert(
                    drone_a,
                    STATUS_RED,
                    f"[{id_a}] 与 [{id_b}] 极度危险：预测 {t:.1f}s 后可能发生空中碰撞",
                )
                drone_b["_pending_warning_category"] = "dynamic_collision"
                _upgrade_alert(
                    drone_b,
                    STATUS_RED,
                    f"[{id_b}] 与 [{id_a}] 极度危险：预测 {t:.1f}s 后可能发生空中碰撞",
                )
                yellow_time = None
                break

            if distance <= DYNAMIC_YELLOW_DISTANCE and yellow_time is None:
                yellow_time = t

        if yellow_time is not None:
            drone_a["_pending_warning_category"] = "dynamic_near"
            _upgrade_alert(
                drone_a,
                STATUS_YELLOW,
                f"[{id_a}] 与 [{id_b}] 冲突预警：预测 {yellow_time:.1f}s 后距离过近",
            )
            drone_b["_pending_warning_category"] = "dynamic_near"
            _upgrade_alert(
                drone_b,
                STATUS_YELLOW,
                f"[{id_b}] 与 [{id_a}] 冲突预警：预测 {yellow_time:.1f}s 后距离过近",
            )


def run_collision_detection(
    active_drones: dict[str, dict[str, Any]],
    buildings: list[Zone] | None = None,
    no_fly_zones: list[Zone] | None = None,
    restricted_zones: list[Zone] | None = None,
) -> dict[str, int]:
    default_buildings, default_no_fly, default_restricted = _default_zones()
    used_buildings = buildings if buildings is not None else default_buildings
    used_no_fly = no_fly_zones if no_fly_zones is not None else default_no_fly
    used_restricted = restricted_zones if restricted_zones is not None else default_restricted

    for drone in active_drones.values():
        drone["status"] = STATUS_GREEN
        drone["warning_msg"] = ""
        drone["warning_category"] = "none"
        drone["_pending_warning_category"] = "general"

    static_zones = [*used_buildings, *used_no_fly]
    for drone_id, drone in active_drones.items():
        status, msg, category = _evaluate_static_conflict(drone_id, drone, static_zones)
        if status != STATUS_GREEN:
            drone["_pending_warning_category"] = category
            _upgrade_alert(drone, status, msg)

        rz_status, rz_msg, rz_category = _evaluate_restricted_zone(drone_id, drone, used_restricted)
        if rz_status != STATUS_GREEN:
            drone["_pending_warning_category"] = rz_category
            _upgrade_alert(drone, rz_status, rz_msg)

    _evaluate_dynamic_conflicts(active_drones)

    counts = {STATUS_GREEN: 0, STATUS_YELLOW: 0, STATUS_RED: 0}
    for drone in active_drones.values():
        counts[drone["status"]] += 1
        drone.pop("_pending_warning_category", None)
    return counts


def estimate_building_collision_time(
    drone: dict[str, Any],
    buildings: list[Zone],
    predict_dt: float = PREDICT_DT,
) -> float | None:
    trajectory = drone.get("predict_traj", [])
    for step_idx, point in enumerate(trajectory):
        for zone in buildings:
            if str(zone.get("zone_kind", "")) != "building":
                continue
            if not _zone_height_overlap(point, zone):
                continue
            clearance = _zone_clearance(point, zone)
            if clearance <= BUILDING_RED_BUFFER:
                return (step_idx + 1) * predict_dt
    return None
