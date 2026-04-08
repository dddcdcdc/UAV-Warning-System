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
BUILDINGS: Final[list[BuildingBox]] = [
    BuildingBox("B1", (20.0, 20.0, 0.0), 8.5, 8.5, 23.0),
    BuildingBox("B2", (-22.0, 24.0, 0.0), 7.8, 7.8, 21.0),
    BuildingBox("B3", (-20.0, -18.0, 0.0), 9.2, 9.2, 25.0),
    BuildingBox("B4", (24.0, -22.0, 0.0), 8.2, 8.2, 22.0),
    BuildingBox("B5", (-64.0, 48.0, 0.0), 12.0, 10.0, 28.0),
    BuildingBox("B6", (-48.0, 62.0, 0.0), 9.0, 12.0, 24.0),
    BuildingBox("B7", (-70.0, -44.0, 0.0), 13.0, 9.0, 22.0),
    BuildingBox("B8", (-54.0, -60.0, 0.0), 9.0, 10.0, 26.0),
    BuildingBox("B9", (66.0, 50.0, 0.0), 12.0, 10.0, 25.0),
    BuildingBox("B10", (52.0, 64.0, 0.0), 9.0, 10.0, 22.0),
    BuildingBox("B11", (72.0, -46.0, 0.0), 13.0, 10.0, 22.0),
    BuildingBox("B12", (56.0, -62.0, 0.0), 9.0, 12.0, 24.0),
    BuildingBox("B13", (-82.0, 8.0, 0.0), 15.0, 13.0, 21.0),
    BuildingBox("B14", (84.0, -10.0, 0.0), 15.0, 13.0, 22.0),
]

NO_FLY_ZONES: Final[list[CylinderZone]] = [
    CylinderZone("NFZ-CENTER", (0.0, 0.0, 0.0), 8.0, 50.0),
]

RESTRICTED_ZONES: Final[list[CylinderZone]] = [
    CylinderZone("RZ-EAST", (30.0, 0.0, 0.0), 7.0, 50.0),
]

DEFAULT_SCENARIO: Final[str] = "safe_patrol"
