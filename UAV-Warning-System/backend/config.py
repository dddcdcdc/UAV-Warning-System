from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class CylinderZone:
    zone_id: str
    center: tuple[float, float, float]
    radius: float
    height: float


@dataclass(frozen=True)
class BuildingBox:
    zone_id: str
    center: tuple[float, float, float]
    width: float
    depth: float
    height: float


# Core timing
TICK_DT: Final[float] = 0.2          # 5Hz physical update(位置刷新频率)
AI_EVERY_N_TICKS: Final[int] = 2     # 2.5Hz prediction + collision
PREDICT_STEPS: Final[int] = 10       # Predict next 1.0s
PREDICT_DT: Final[float] = 0.1
HISTORY_LEN: Final[int] = 20

# Status
STATUS_GREEN: Final[str] = "GREEN"
STATUS_YELLOW: Final[str] = "YELLOW"
STATUS_RED: Final[str] = "RED"
STATUS_PRIORITY: Final[dict[str, int]] = {
    STATUS_GREEN: 0,
    STATUS_YELLOW: 1,
    STATUS_RED: 2,
}

# Collision thresholds
STATIC_RED_BUFFER: Final[float] = 1.0
STATIC_YELLOW_BUFFER: Final[float] = 2.0
# Building-specific thresholds (tighter than generic static zones)
BUILDING_RED_BUFFER: Final[float] = 0.55
BUILDING_YELLOW_BUFFER: Final[float] = 1.25
DYNAMIC_RED_DISTANCE: Final[float] = 1.0
DYNAMIC_YELLOW_DISTANCE: Final[float] = 2.0
RESTRICTED_WARN_BUFFER: Final[float] = 2.0

# Scene bounds (for display)
WORLD_SIZE: Final[tuple[float, float, float]] = (100.0, 100.0, 50.0)

# Obstacles / zones
# Keep aligned with frontend/src/three/Buildings.ts (BoxGeometry specs).
BUILDING_CENTER_SCALE: Final[float] = 0.92


def _scaled_center(center: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        round(center[0] * BUILDING_CENTER_SCALE, 4),
        round(center[1] * BUILDING_CENTER_SCALE, 4),
        center[2],
    )


_BUILDINGS_RAW: Final[list[BuildingBox]] = [
    BuildingBox("B1-P", (-34.0, 32.0, 0.0), 22.0, 13.5, 6.4),
    BuildingBox("B1", (-34.0, 32.0, 0.0), 8.8, 8.4, 36.0),
    BuildingBox("B1-A", (-45.0, 38.0, 0.0), 7.0, 7.2, 19.0),
    BuildingBox("B2-P", (34.0, 32.0, 0.0), 23.0, 13.5, 6.6),
    BuildingBox("B2-A", (29.5, 32.0, 0.0), 6.8, 6.8, 31.0),
    BuildingBox("B2-B", (38.5, 32.0, 0.0), 6.4, 6.4, 28.0),
    BuildingBox("B2-L", (46.0, 38.0, 0.0), 7.4, 6.6, 14.0),
    BuildingBox("B3-P", (-34.0, -32.0, 0.0), 22.0, 13.5, 6.5),
    BuildingBox("B3-H", (-37.0, -34.0, 0.0), 9.0, 8.4, 34.0),
    BuildingBox("B3-S1", (-27.0, -28.0, 0.0), 7.4, 7.2, 20.0),
    BuildingBox("B3-S2", (-22.0, -23.0, 0.0), 6.6, 6.2, 13.0),
    BuildingBox("B4-P", (34.0, -32.0, 0.0), 23.0, 13.5, 6.4),
    BuildingBox("B4", (34.0, -32.0, 0.0), 8.6, 8.2, 33.0),
    BuildingBox("B4-A", (45.0, -38.0, 0.0), 7.2, 7.0, 15.0),
    BuildingBox("B5", (-78.0, 60.0, 0.0), 15.0, 11.0, 32.0),
    BuildingBox("B6", (-60.0, 76.0, 0.0), 11.0, 13.0, 27.0),
    BuildingBox("B7", (-86.0, -58.0, 0.0), 14.0, 10.0, 25.0),
    BuildingBox("B8", (-66.0, -76.0, 0.0), 11.0, 13.0, 29.0),
    BuildingBox("B9", (80.0, 60.0, 0.0), 15.0, 11.0, 31.0),
    BuildingBox("B10", (62.0, 76.0, 0.0), 11.0, 12.0, 26.0),
    BuildingBox("B11", (88.0, -58.0, 0.0), 14.0, 10.0, 26.0),
    BuildingBox("B12", (68.0, -76.0, 0.0), 11.0, 13.0, 28.0),
    BuildingBox("B13", (-96.0, 24.0, 0.0), 17.0, 14.0, 24.0),
    BuildingBox("B14", (96.0, -24.0, 0.0), 17.0, 14.0, 25.0),
    BuildingBox("B15", (-92.0, 72.0, 0.0), 12.0, 10.0, 21.0),
    BuildingBox("B16", (-74.0, 88.0, 0.0), 10.0, 12.0, 18.0),
    BuildingBox("B17", (92.0, 74.0, 0.0), 12.0, 10.0, 22.0),
    BuildingBox("B18", (74.0, 88.0, 0.0), 10.0, 12.0, 19.0),
    BuildingBox("B19", (-94.0, -72.0, 0.0), 12.0, 10.0, 20.0),
    BuildingBox("B20", (-72.0, -88.0, 0.0), 10.0, 12.0, 18.0),
    BuildingBox("B21", (94.0, -72.0, 0.0), 12.0, 10.0, 21.0),
    BuildingBox("B22", (72.0, -88.0, 0.0), 10.0, 12.0, 19.0),
    BuildingBox("L1", (-54.0, 24.0, 0.0), 10.0, 8.0, 6.2),
    BuildingBox("L2", (-44.0, 18.0, 0.0), 9.0, 7.0, 5.6),
    BuildingBox("L3", (54.0, 24.0, 0.0), 10.0, 8.0, 6.4),
    BuildingBox("L4", (62.0, 18.0, 0.0), 8.0, 7.0, 5.4),
    BuildingBox("L5", (-56.0, -24.0, 0.0), 10.0, 8.0, 6.5),
    BuildingBox("L6", (-46.0, -30.0, 0.0), 8.0, 7.0, 5.6),
    BuildingBox("L7", (54.0, -20.0, 0.0), 10.0, 8.0, 6.1),
    BuildingBox("L8", (62.0, -18.0, 0.0), 8.0, 7.0, 5.2),
    BuildingBox("L9", (22.0, 52.0, 0.0), 10.0, 8.0, 7.2),
    BuildingBox("L10", (-22.0, -52.0, 0.0), 10.0, 8.0, 7.0),
    BuildingBox("L11", (-28.0, 84.0, 0.0), 14.0, 9.0, 8.0),
    BuildingBox("L12", (28.0, -84.0, 0.0), 14.0, 9.0, 8.0),
]

BUILDINGS: Final[list[BuildingBox]] = [
    BuildingBox(item.zone_id, _scaled_center(item.center), item.width, item.depth, item.height)
    for item in _BUILDINGS_RAW
]

NO_FLY_ZONES: Final[list[CylinderZone]] = [
    CylinderZone("NFZ-CENTER", (0.0, 0.0, 0.0), 8.0, 50.0),
]

RESTRICTED_ZONES: Final[list[CylinderZone]] = [
    CylinderZone("RZ-EAST", (30.0, 0.0, 0.0), 7.0, 50.0),
]

DEFAULT_SCENARIO: Final[str] = "safe_patrol"
