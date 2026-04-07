from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class CylinderZone:
    zone_id: str
    center: tuple[float, float, float]
    radius: float
    height: float


# Core timing
TICK_DT: Final[float] = 0.2          # 5Hz physical update
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
BUILDINGS: Final[list[CylinderZone]] = [
    CylinderZone("B1", (20.0, 20.0, 0.0), 6.0, 32.0),
    CylinderZone("B2", (-22.0, 24.0, 0.0), 5.5, 28.0),
    CylinderZone("B3", (-20.0, -18.0, 0.0), 6.5, 30.0),
    CylinderZone("B4", (24.0, -22.0, 0.0), 5.8, 26.0),
    # Peripheral city blocks (kept in sync with frontend visual buildings).
    CylinderZone("B5", (-64.0, 48.0, 0.0), 6.8, 28.0),
    CylinderZone("B6", (-48.0, 62.0, 0.0), 6.3, 24.0),
    CylinderZone("B7", (-70.0, -44.0, 0.0), 7.1, 22.0),
    CylinderZone("B8", (-54.0, -60.0, 0.0), 6.2, 26.0),
    CylinderZone("B9", (66.0, 50.0, 0.0), 6.8, 25.0),
    CylinderZone("B10", (52.0, 64.0, 0.0), 6.0, 22.0),
    CylinderZone("B11", (72.0, -46.0, 0.0), 7.2, 22.0),
    CylinderZone("B12", (56.0, -62.0, 0.0), 6.3, 24.0),
    CylinderZone("B13", (-82.0, 8.0, 0.0), 8.7, 21.0),
    CylinderZone("B14", (84.0, -10.0, 0.0), 8.7, 22.0),
]

NO_FLY_ZONES: Final[list[CylinderZone]] = [
    CylinderZone("NFZ-CENTER", (0.0, 0.0, 0.0), 8.0, 50.0),
]

RESTRICTED_ZONES: Final[list[CylinderZone]] = [
    CylinderZone("RZ-EAST", (30.0, 0.0, 0.0), 7.0, 50.0),
]

DEFAULT_SCENARIO: Final[str] = "safe_patrol"
