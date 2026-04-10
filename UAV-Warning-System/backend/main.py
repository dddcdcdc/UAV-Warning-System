from __future__ import annotations

import asyncio
from collections import deque
from contextlib import asynccontextmanager
import os
import time
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from ai_engine import VelocityPredictionEngine
from collision_detector import estimate_building_collision_time, run_collision_detection
from config import (
    AI_EVERY_N_TICKS,
    BUILDINGS,
    DEFAULT_SCENARIO,
    HISTORY_LEN,
    NO_FLY_ZONES,
    PREDICT_DT,
    PREDICT_STEPS,
    RESTRICTED_ZONES,
    TICK_DT,
    WORLD_SIZE,
)
from simulator import ScenarioSimulator


LIVE_DROP_TIMEOUT_SEC = 6.0
SIM_BUILDING_HALT_TRIGGER_SEC = 0.40


class WebSocketHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)

    async def broadcast_json(self, payload: dict[str, Any]) -> None:
        if not self._clients:
            return
        stale: list[WebSocket] = []
        for client in self._clients:
            try:
                await client.send_json(payload)
            except Exception:
                stale.append(client)
        for client in stale:
            self._clients.discard(client)

    #把实时数据广播给所有的websocket连接

    @property
    def total_clients(self) -> int:
        return len(self._clients)


class PolygonZonePayload(BaseModel):
    zone_id: str | None = None
    points: list[list[float]]
    height: float = 50.0
    base_z: float = 0.0
#定义多边形区域


class DataModePayload(BaseModel):
    clear_existing: bool = True
#定义模式切换是否清楚无人机

class ModelReloadPayload(BaseModel):
    model_dir: str
    stats_path: str | None = None
#定义ai模型重载

class TelemetryDronePayload(BaseModel):
    id: str = Field(..., min_length=1)
    type: str | None = None
    current_pos: list[float]
    current_vel: list[float] | None = None
    history_pos: list[list[float]] | None = None
    timestamp: float | None = None

    @field_validator("current_pos")
    @classmethod
    def validate_current_pos(cls, value: list[float]) -> list[float]:
        if len(value) < 3:
            raise ValueError("current_pos must contain x,y,z.")
        return value

    @field_validator("current_vel")
    @classmethod
    def validate_current_vel(cls, value: list[float] | None) -> list[float] | None:
        if value is not None and len(value) < 3:
            raise ValueError("current_vel must contain vx,vy,vz.")
        return value

#定义无人机数据结构

class TelemetryBatchPayload(BaseModel):
    drones: list[TelemetryDronePayload]
    source: str | None = "external_stream"

#定义批次无人机

def _vec3(values: list[float] | tuple[float, float, float]) -> list[float]:
    return [float(values[0]), float(values[1]), float(values[2])]

#返回速度

def _zone_from_cylinder(zone: Any, zone_kind: str) -> dict[str, Any]:
    return {
        "zone_id": zone.zone_id,
        "shape": "cylinder",
        "zone_kind": zone_kind,
        "center": list(zone.center),
        "radius": float(zone.radius),
        "height": float(zone.height),
        "base_z": float(zone.center[2]),
    }

#返回圆柱体

def _rect_points(center_x: float, center_y: float, width: float, depth: float) -> list[list[float]]:
    half_w = width / 2.0
    half_d = depth / 2.0
    return [
        [center_x - half_w, center_y - half_d],
        [center_x + half_w, center_y - half_d],
        [center_x + half_w, center_y + half_d],
        [center_x - half_w, center_y + half_d],
    ]

#类似于建筑四至

def _zone_from_building_box(zone: Any) -> dict[str, Any]:
    center_x, center_y, base_z = zone.center
    return {
        "zone_id": zone.zone_id,
        "shape": "polygon",
        "zone_kind": "building",
        "points": _rect_points(center_x, center_y, float(zone.width), float(zone.depth)),
        "height": float(zone.height),
        "base_z": float(base_z),
    }


def _default_runtime_zones() -> dict[str, list[dict[str, Any]]]:
    return {
        "buildings": [_zone_from_building_box(item) for item in BUILDINGS],
        "no_fly": [_zone_from_cylinder(item, "no_fly") for item in NO_FLY_ZONES],
        "restricted": [_zone_from_cylinder(item, "restricted") for item in RESTRICTED_ZONES],
    }


#返回相关区域

def _default_bucket_zones(bucket: str) -> list[dict[str, Any]]:
    defaults = _default_runtime_zones()
    return defaults.get(bucket, [])

#按需要获取特定类别

def _next_zone_id(prefix: str, bucket: str) -> str:
    existing = {
        item.get("zone_id")
        for item in RUNTIME_ZONES.get(bucket, [])
        if isinstance(item.get("zone_id"), str) and str(item.get("zone_id")).startswith(prefix)
    }
    suffix = 1
    while f"{prefix}-{suffix:03d}" in existing:
        suffix += 1
    return f"{prefix}-{suffix:03d}"

#为新区域生成唯一有序的id。


def _init_predictor(model_dir: str | None = None, stats_path: str | None = None) -> VelocityPredictionEngine:
    return VelocityPredictionEngine(
        model_dir=model_dir,
        stats_path=stats_path,
        history_dt=TICK_DT,
        predict_steps=PREDICT_STEPS,
        predict_dt=PREDICT_DT,
    )



SIMULATOR = ScenarioSimulator(bootstrap_dt=TICK_DT)
ACTIVE_DRONES = SIMULATOR.load_scenario(DEFAULT_SCENARIO)
STATE_LOCK = asyncio.Lock()
RUNTIME_ZONES = _default_runtime_zones()

MODEL_DIR = os.getenv("UAV_MODEL_DIR")
VEL_STATS_PATH = os.getenv("UAV_VEL_STATS") #因此需要通过env写入
PREDICTOR = _init_predictor(model_dir=MODEL_DIR, stats_path=VEL_STATS_PATH)
PREDICTOR.predict_for_all(ACTIVE_DRONES)
LAST_COUNTS = run_collision_detection(
    ACTIVE_DRONES,
    buildings=RUNTIME_ZONES["buildings"],
    no_fly_zones=RUNTIME_ZONES["no_fly"],
    restricted_zones=RUNTIME_ZONES["restricted"],
)

SYSTEM_META = {
    "running": True,
    "tick_count": 0,
    "data_mode": "simulation",  # simulation | live
    "telemetry_source": "internal_simulator",
}

WS_HUB = WebSocketHub()
SYSTEM_LOOP_TASK: asyncio.Task[None] | None = None


def _empty_history(pos: list[float]) -> deque[list[float]]:
    history: deque[list[float]] = deque(maxlen=HISTORY_LEN)
    for _ in range(HISTORY_LEN):
        history.append(pos.copy())
    return history


def _ensure_live_record(drone_id: str, drone_type: str, pos: list[float]) -> dict[str, Any]:
    record = ACTIVE_DRONES.get(drone_id)
    if record is None:
        record = {
            "id": drone_id,
            "type": drone_type,
            "history_pos": _empty_history(pos),
            "current_pos": pos.copy(),
            "current_vel": [0.0, 0.0, 0.0],
            "predict_traj": [],
            "status": "GREEN",
            "warning_msg": "",
            "warning_category": "none",
            "_live_last_ingest": time.time(),
        }
        ACTIVE_DRONES[drone_id] = record
    return record

#输入id，如果不在相应的列表中，则创建并存入

def _append_history(record: dict[str, Any], pos: list[float]) -> None:
    history = record.get("history_pos")
    if not isinstance(history, deque):
        history = deque(history or [], maxlen=HISTORY_LEN)
        record["history_pos"] = history
    if len(history) == 0:
        history.append(pos.copy())
        return
    #历史为空时，直接添加当前位置

    prev = np.array(history[-1], dtype=np.float32)
    cur = np.array(pos, dtype=np.float32)
    if float(np.linalg.norm(cur - prev)) > 1e-5:
        history.append(pos.copy())
#位置有显著变化时才记录

def _upsert_live_drone(payload: TelemetryDronePayload) -> None:
    now_ts = time.time()
    pos = _vec3(payload.current_pos)
    record = _ensure_live_record(payload.id, payload.type or "External", pos)
    record["type"] = payload.type or record.get("type", "External")

    prev_pos = _vec3(record.get("current_pos", pos))
    prev_ts = float(record.get("_live_last_ingest", now_ts))
    dt = max(now_ts - prev_ts, 1e-6)

    if payload.current_vel is not None:
        vel = _vec3(payload.current_vel)
    else:
        vel_vec = (np.array(pos, dtype=np.float32) - np.array(prev_pos, dtype=np.float32)) / dt
        vel = vel_vec.round(4).tolist()

    #直接使用payload中的历史数据，如果没有则根据当前和之前的位置计算出历史数据

    if payload.history_pos:
        rebuilt: deque[list[float]] = deque(maxlen=HISTORY_LEN)
        for item in payload.history_pos[-HISTORY_LEN:]:
            if len(item) >= 3:
                rebuilt.append(_vec3(item))
        if len(rebuilt) == 0:
            rebuilt = _empty_history(pos)
        record["history_pos"] = rebuilt
    else:
        _append_history(record, pos)

    #如果有则加入历史，没有，则重建历史
    record["current_pos"] = pos
    record["current_vel"] = vel
    record["_live_last_ingest"] = payload.timestamp if payload.timestamp else now_ts


def _advance_live_drones(dt: float) -> None:
    now_ts = time.time()
    stale_ids: list[str] = []
    for drone_id, record in ACTIVE_DRONES.items():
        last_ingest = float(record.get("_live_last_ingest", now_ts))
        staleness = now_ts - last_ingest
        if staleness > LIVE_DROP_TIMEOUT_SEC:
            stale_ids.append(drone_id)
            continue

        if staleness <= dt * 0.9:
            continue   #外部数据的断帧补偿

        pos = np.array(record.get("current_pos", [0.0, 0.0, 0.0]), dtype=np.float32)
        vel = np.array(record.get("current_vel", [0.0, 0.0, 0.0]), dtype=np.float32)
        next_pos = pos + vel * dt
        next_pos[2] = max(0.0, float(next_pos[2]))

        record["current_pos"] = next_pos.round(4).tolist()
        _append_history(record, record["current_pos"])

    for drone_id in stale_ids:
        ACTIVE_DRONES.pop(drone_id, None)

#收集离线id，统一清理，通过物理学外推（这里似乎是临时代替模拟器的作用）

def _snapshot_payload() -> dict[str, Any]:
    drones = []
    for drone_id in sorted(ACTIVE_DRONES.keys()):
        drone = ACTIVE_DRONES[drone_id]
        history_values = list(drone.get("history_pos", []))
        drones.append(
            {
                "id": drone_id,
                "type": drone.get("type", "Unknown"),
                "current_pos": drone.get("current_pos", [0.0, 0.0, 0.0]),
                "current_vel": drone.get("current_vel", [0.0, 0.0, 0.0]),
                "history_pos": history_values[-HISTORY_LEN:],
                "predict_traj": drone.get("predict_traj", []),
                "status": drone.get("status", "GREEN"),
                "warning_msg": drone.get("warning_msg", ""),
                "warning_category": drone.get("warning_category", "none"),
            }
        )

    #存入默认无人机信息

    return {
        "timestamp": time.time(),
        "scenario": SIMULATOR.current_scenario,
        "engine": PREDICTOR.info,
        "system": {
            "running": SYSTEM_META["running"],
            "tick_dt": TICK_DT, #主循环时间步长
            "predict_dt": PREDICT_DT, #预测时间步长
            "ws_clients": WS_HUB.total_clients,
            "data_mode": SYSTEM_META["data_mode"],
            "telemetry_source": SYSTEM_META["telemetry_source"], #数据源
        },
        "stats": {
            "total": len(drones),
            "green": LAST_COUNTS.get("GREEN", 0),
            "yellow": LAST_COUNTS.get("YELLOW", 0),
            "red": LAST_COUNTS.get("RED", 0),
        },
        "zones": RUNTIME_ZONES,
        "drones": drones,
    }

#系统状态快照生成

def _run_ai_and_collision() -> dict[str, int]:
    PREDICTOR.predict_for_all(ACTIVE_DRONES)
    run_collision_detection(
        ACTIVE_DRONES,
        buildings=RUNTIME_ZONES["buildings"],
        no_fly_zones=RUNTIME_ZONES["no_fly"],
        restricted_zones=RUNTIME_ZONES["restricted"],
    )
    _apply_simulation_emergency_logic()

#模拟状态下的紧急处理逻辑
    counts = {"GREEN": 0, "YELLOW": 0, "RED": 0}
    for drone in ACTIVE_DRONES.values():
        status = str(drone.get("status", "GREEN"))
        if status not in counts:
            status = "GREEN"
        counts[status] += 1
    return counts


def _apply_simulation_emergency_logic() -> None:
    if SYSTEM_META.get("data_mode") != "simulation":
        return

    for drone in ACTIVE_DRONES.values():
        sim_state = drone.get("_sim")
        if isinstance(sim_state, dict) and sim_state.get("halted") and sim_state.get("halt_reason") == "building_collision":
            drone["status"] = "RED"
            drone["warning_category"] = "building_collision"
            persisted_msg = str(drone.get("warning_msg", "")).strip()
            if not persisted_msg:
                persisted_msg = "建筑碰撞高危：已执行应急悬停"
            elif "已执行应急悬停" not in persisted_msg:
                persisted_msg = f"{persisted_msg}（已执行应急悬停）"
            drone["warning_msg"] = persisted_msg
            drone["current_vel"] = [0.0, 0.0, 0.0]
            drone["predict_traj"] = []
            continue

        if drone.get("status") != "RED":
            continue
        if drone.get("warning_category") != "building_collision":
            continue

        warning_msg = str(drone.get("warning_msg", ""))
        impact_seconds = estimate_building_collision_time(
            drone=drone,
            buildings=RUNTIME_ZONES["buildings"],
            predict_dt=PREDICT_DT,
        )
        if impact_seconds is not None and impact_seconds > SIM_BUILDING_HALT_TRIGGER_SEC:
            continue

        if isinstance(sim_state, dict):
            sim_state["halted"] = True
            sim_state["halt_reason"] = "building_collision"

        drone["current_vel"] = [0.0, 0.0, 0.0]
        drone["predict_traj"] = []
        if "已执行应急悬停" not in warning_msg:
            drone["warning_msg"] = f"{warning_msg}（已执行应急悬停）"


async def _system_loop() -> None:
    global LAST_COUNTS
    while True:
        async with STATE_LOCK:
            if SYSTEM_META["running"]:
                if SYSTEM_META["data_mode"] == "simulation":
                    SIMULATOR.update(TICK_DT) #模拟器更新无人机状态
                else:
                    _advance_live_drones(TICK_DT) 

                SYSTEM_META["tick_count"] += 1 #系统状态更新
                if SYSTEM_META["tick_count"] % AI_EVERY_N_TICKS == 0: #每隔一定tick运行一次AI和碰撞检测
                    LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
            payload = _snapshot_payload()   #快照记录

        await WS_HUB.broadcast_json(payload) #广播
        await asyncio.sleep(TICK_DT)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global SYSTEM_LOOP_TASK
    SYSTEM_LOOP_TASK = asyncio.create_task(_system_loop())
    try:
        yield
    finally:
        if SYSTEM_LOOP_TASK:
            SYSTEM_LOOP_TASK.cancel()
            try:
                await SYSTEM_LOOP_TASK
            except asyncio.CancelledError:
                pass

#应用生命周期管理，启动系统主循环，优雅关闭

app = FastAPI(
    title="UAV In-Flight Warning System",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#初始化FastAPI应用，添加CORS中间件

@app.get("/")
async def index() -> dict[str, Any]:
    return {
        "service": "UAV In-Flight Warning System Backend",
        "status": "ok",
        "docs": "/docs",
        "health": "/api/health",
        "websocket": "/ws/situation",
    }


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "running": SYSTEM_META["running"],
        "scenario": SIMULATOR.current_scenario,
        "predict_engine": PREDICTOR.info,
        "data_mode": SYSTEM_META["data_mode"],
    }

#系统状态监控接口，返回当前运行状态、场景、预测引擎信息和数据模式等基本信息

@app.get("/api/scenarios")
async def list_scenarios() -> dict[str, Any]:
    return {
        "current": SIMULATOR.current_scenario,
        "items": SIMULATOR.available_scenarios(),
    }

#可用场景列表

@app.post("/api/scenario/{scenario_name}")
async def switch_scenario(scenario_name: str) -> dict[str, Any]:
    global ACTIVE_DRONES, LAST_COUNTS, RUNTIME_ZONES
    scenarios = SIMULATOR.available_scenarios()
    if scenario_name not in scenarios:
        raise HTTPException(status_code=404, detail=f"Scenario `{scenario_name}` does not exist.")

    async with STATE_LOCK:
        ACTIVE_DRONES = SIMULATOR.load_scenario(scenario_name)
        # Built-in scenarios should run against default zones and not inherit
        # manually drawn polygons from previous interactive tests.
        RUNTIME_ZONES = _default_runtime_zones()
        SYSTEM_META["data_mode"] = "simulation"
        SYSTEM_META["telemetry_source"] = "internal_simulator"
        LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
        payload = _snapshot_payload() #生成快照

    await WS_HUB.broadcast_json(payload)
    return {"ok": True, "current": SIMULATOR.current_scenario, "description": scenarios[scenario_name]}

#场景切换接口，加载指定场景的无人机数据，重置区域信息，切换到模拟模式，并广播更新后的状态


@app.post("/api/control/{action}")
async def control_system(action: str) -> dict[str, Any]:
    normalized = action.lower()
    if normalized not in {"pause", "resume"}:
        raise HTTPException(status_code=400, detail="Action must be `pause` or `resume`.")
    async with STATE_LOCK:
        SYSTEM_META["running"] = normalized == "resume"
        payload = _snapshot_payload()
    await WS_HUB.broadcast_json(payload)
    return {"ok": True, "running": SYSTEM_META["running"]}

#场景控制:切换大小写，更新运行状态，并广播更新后的状态


@app.get("/api/state")
async def get_state() -> dict[str, Any]:
    async with STATE_LOCK:
        return _snapshot_payload()

#实时快照获取

@app.get("/api/config")
async def get_config() -> dict[str, Any]:
    return {
        "world_size": WORLD_SIZE,
        "timing": {
            "tick_dt": TICK_DT,
            "predict_dt": PREDICT_DT,
            "predict_steps": PREDICT_STEPS,
            "ai_every_n_ticks": AI_EVERY_N_TICKS,
        },
        "zones": RUNTIME_ZONES,
    }

#系统配置信息接口，返回世界尺寸、时间步长、预测步长、AI运行频率等配置信息，以及当前的区域信息

@app.get("/api/mode")
async def get_mode() -> dict[str, Any]:
    return {
        "data_mode": SYSTEM_META["data_mode"],
        "telemetry_source": SYSTEM_META["telemetry_source"],
    }

#数据模式接口，返回当前的数据模式和数据源信息

@app.post("/api/mode/live")
async def set_live_mode(payload: DataModePayload) -> dict[str, Any]:
    global ACTIVE_DRONES, LAST_COUNTS
    async with STATE_LOCK:
        SYSTEM_META["data_mode"] = "live"
        SYSTEM_META["telemetry_source"] = "external_stream"
        if payload.clear_existing:
            ACTIVE_DRONES = {}
        LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
        snapshot = _snapshot_payload()
    await WS_HUB.broadcast_json(snapshot)
    return {"ok": True, "data_mode": SYSTEM_META["data_mode"], "cleared": payload.clear_existing}

#设置实时模式

@app.post("/api/mode/simulation")
async def set_simulation_mode() -> dict[str, Any]:
    global ACTIVE_DRONES, LAST_COUNTS, RUNTIME_ZONES
    async with STATE_LOCK:
        ACTIVE_DRONES = SIMULATOR.load_scenario(DEFAULT_SCENARIO)
        RUNTIME_ZONES = _default_runtime_zones()
        SYSTEM_META["data_mode"] = "simulation"
        SYSTEM_META["telemetry_source"] = "internal_simulator"
        LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
        snapshot = _snapshot_payload()
    await WS_HUB.broadcast_json(snapshot)
    return {"ok": True, "data_mode": SYSTEM_META["data_mode"], "scenario": SIMULATOR.current_scenario}

#设置模拟模式

@app.post("/api/model/reload")
async def reload_model(payload: ModelReloadPayload) -> dict[str, Any]:
    global PREDICTOR, LAST_COUNTS
    async with STATE_LOCK:
        PREDICTOR = _init_predictor(model_dir=payload.model_dir, stats_path=payload.stats_path)
        LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
        snapshot = _snapshot_payload()
    await WS_HUB.broadcast_json(snapshot)
    return {"ok": True, "engine": PREDICTOR.info}

#AI模型重载接口，接受新的模型目录和统计数据路径，重新初始化预测引擎，并广播更新后的状态

@app.post("/api/telemetry/drone")
async def ingest_single_telemetry(payload: TelemetryDronePayload) -> dict[str, Any]:
    global LAST_COUNTS
    async with STATE_LOCK:
        SYSTEM_META["data_mode"] = "live"
        SYSTEM_META["telemetry_source"] = "external_stream"
        _upsert_live_drone(payload)
        LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
        snapshot = _snapshot_payload()
    await WS_HUB.broadcast_json(snapshot)
    return {"ok": True, "received": 1, "id": payload.id}

#接收单个实时无人机数据的接口，更新相应的无人机记录，运行AI和碰撞检测，并广播更新后的状态

@app.post("/api/telemetry/batch")
async def ingest_batch_telemetry(payload: TelemetryBatchPayload) -> dict[str, Any]:
    global LAST_COUNTS
    if len(payload.drones) == 0:
        raise HTTPException(status_code=400, detail="drones payload is empty.")

    async with STATE_LOCK:
        SYSTEM_META["data_mode"] = "live"
        SYSTEM_META["telemetry_source"] = payload.source or "external_stream"
        for item in payload.drones:
            _upsert_live_drone(item)
        LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
        snapshot = _snapshot_payload()
    await WS_HUB.broadcast_json(snapshot)
    return {"ok": True, "received": len(payload.drones)}

#接收批次实时无人机数据的接口，更新相应的无人机记录，运行AI和碰撞检测，并广播更新后的状态

@app.post("/api/telemetry/clear")
async def clear_live_telemetry() -> dict[str, Any]:
    global ACTIVE_DRONES, LAST_COUNTS
    async with STATE_LOCK:
        ACTIVE_DRONES = {}
        SYSTEM_META["data_mode"] = "live"
        SYSTEM_META["telemetry_source"] = "external_stream"
        LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
        snapshot = _snapshot_payload()
    await WS_HUB.broadcast_json(snapshot)
    return {"ok": True}

#清理无人机并切换到实时模式

@app.post("/api/zones/no-fly/polygon")
async def add_no_fly_polygon(payload: PolygonZonePayload) -> dict[str, Any]:
    global LAST_COUNTS
    if len(payload.points) < 3:
        raise HTTPException(status_code=400, detail="Polygon requires at least 3 points.")

    cleaned_points: list[list[float]] = []
    for point in payload.points:
        if len(point) < 2:
            raise HTTPException(status_code=400, detail="Each point must contain at least x and y.")
        cleaned_points.append([float(point[0]), float(point[1])])

    zone_id = payload.zone_id or _next_zone_id("NFZ-USER", "no_fly")
    zone = {
        "zone_id": zone_id,
        "shape": "polygon",
        "zone_kind": "no_fly",
        "points": cleaned_points,
        "height": float(payload.height),
        "base_z": float(payload.base_z),
    }

    async with STATE_LOCK:
        RUNTIME_ZONES["no_fly"] = [
            item for item in RUNTIME_ZONES["no_fly"] if item.get("zone_id") != zone_id
        ]
        RUNTIME_ZONES["no_fly"].append(zone)
        LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
        snapshot = _snapshot_payload()

    await WS_HUB.broadcast_json(snapshot)
    return {"ok": True, "zone": zone}


#动态添加多边形禁飞区接口，验证输入数据，更新区域列表，运行AI和碰撞检测，并广播更新后的状态

@app.post("/api/zones/restricted/polygon")
async def add_restricted_polygon(payload: PolygonZonePayload) -> dict[str, Any]:
    global LAST_COUNTS
    if len(payload.points) < 3:
        raise HTTPException(status_code=400, detail="Polygon requires at least 3 points.")

    cleaned_points: list[list[float]] = []
    for point in payload.points:
        if len(point) < 2:
            raise HTTPException(status_code=400, detail="Each point must contain at least x and y.")
        cleaned_points.append([float(point[0]), float(point[1])])

    zone_id = payload.zone_id or _next_zone_id("RZ-USER", "restricted")
    zone = {
        "zone_id": zone_id,
        "shape": "polygon",
        "zone_kind": "restricted",
        "points": cleaned_points,
        "height": float(payload.height),
        "base_z": float(payload.base_z),
    }

    async with STATE_LOCK:
        RUNTIME_ZONES["restricted"] = [
            item for item in RUNTIME_ZONES["restricted"] if item.get("zone_id") != zone_id
        ]
        RUNTIME_ZONES["restricted"].append(zone)
        LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
        snapshot = _snapshot_payload()

    await WS_HUB.broadcast_json(snapshot)
    return {"ok": True, "zone": zone}


#动态添加多边形限制区接口，验证输入数据，更新区域列表，运行AI和碰撞检测，并广播更新后的状态

@app.post("/api/zones/reset")
async def reset_zones() -> dict[str, Any]:
    global LAST_COUNTS, RUNTIME_ZONES
    async with STATE_LOCK:
        RUNTIME_ZONES = _default_runtime_zones()
        LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
        snapshot = _snapshot_payload()
    await WS_HUB.broadcast_json(snapshot)
    return {"ok": True, "zones": RUNTIME_ZONES}

#完全重置区域接口，恢复默认区域配置，运行AI和碰撞检测，并广播更新后的状态

@app.post("/api/zones/no-fly/reset")
async def reset_no_fly_zones() -> dict[str, Any]:
    global LAST_COUNTS
    async with STATE_LOCK:
        RUNTIME_ZONES["no_fly"] = _default_bucket_zones("no_fly")
        LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
        snapshot = _snapshot_payload()
    await WS_HUB.broadcast_json(snapshot)
    return {"ok": True, "no_fly": RUNTIME_ZONES["no_fly"]}


#重置禁飞区接口，恢复默认禁飞区配置，运行AI和碰撞检测，并广播更新后的状态
@app.post("/api/zones/restricted/reset")
async def reset_restricted_zones() -> dict[str, Any]:
    global LAST_COUNTS
    async with STATE_LOCK:
        RUNTIME_ZONES["restricted"] = _default_bucket_zones("restricted")
        LAST_COUNTS = await asyncio.to_thread(_run_ai_and_collision)
        snapshot = _snapshot_payload()
    await WS_HUB.broadcast_json(snapshot)
    return {"ok": True, "restricted": RUNTIME_ZONES["restricted"]}


#重置限制区接口，恢复默认限制区配置，运行AI和碰撞检测，并广播更新后的状态
@app.websocket("/ws/situation")
async def ws_situation(websocket: WebSocket) -> None:
    await WS_HUB.connect(websocket)
    try:
        async with STATE_LOCK:
            await websocket.send_json(_snapshot_payload())
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        WS_HUB.disconnect(websocket)
    except Exception:
        WS_HUB.disconnect(websocket)


#app代表了fastapi。
#websocket接口，连接后立即发送当前状态快照，并保持连接以便后续广播更新，处理断开连接和异常情况
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
