#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from typing import Callable
from urllib import request

import numpy as np


Vec3 = tuple[float, float, float]


@dataclass
class DroneTrack:
    drone_id: str
    drone_type: str
    sampler: Callable[[float], tuple[np.ndarray, np.ndarray]]


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=5) as resp:
        body = resp.read().decode("utf-8")
        if not body:
            return {}
        return json.loads(body)


def build_loop_sampler(waypoints: list[Vec3], speed: float) -> Callable[[float], tuple[np.ndarray, np.ndarray]]:
    pts = [np.array(item, dtype=np.float32) for item in waypoints]
    if len(pts) < 2:
        raise ValueError("waypoints length must be >= 2")

    segments = []
    durations = []
    total = 0.0
    for idx in range(len(pts)):
        p0 = pts[idx]
        p1 = pts[(idx + 1) % len(pts)]
        diff = p1 - p0
        dist = float(np.linalg.norm(diff))
        if dist < 1e-6:
            continue
        dur = dist / max(speed, 1e-6)
        segments.append((p0, p1, diff / dist))
        durations.append(dur)
        total += dur

    cumulative = np.cumsum([0.0, *durations]).tolist()
    if total <= 1e-6:
        raise ValueError("invalid waypoint path")

    def sample(t: float) -> tuple[np.ndarray, np.ndarray]:
        t_mod = t % total
        seg_idx = 0
        for i in range(len(durations)):
            if cumulative[i] <= t_mod < cumulative[i + 1]:
                seg_idx = i
                break
        p0, p1, direction = segments[seg_idx]
        seg_t = t_mod - cumulative[seg_idx]
        ratio = seg_t / max(durations[seg_idx], 1e-6)
        pos = p0 + (p1 - p0) * ratio
        vel = direction * speed
        return pos, vel

    return sample


def build_tracks(scenario: str) -> list[DroneTrack]:
    if scenario == "crossing_alert":
        return [
            DroneTrack(
                "UAV-LIVE-001",
                "物流机",
                build_loop_sampler([(-18, 0, 12), (18, 0, 12)], speed=3.2),
            ),
            DroneTrack(
                "UAV-LIVE-002",
                "巡检机",
                build_loop_sampler([(0, -18, 12), (0, 18, 12)], speed=3.1),
            ),
            DroneTrack(
                "UAV-LIVE-003",
                "测绘机",
                build_loop_sampler([(-34, -26, 15), (-34, 26, 15), (34, 26, 15), (34, -26, 15)], speed=2.9),
            ),
        ]

    if scenario == "dense_safe":
        return [
            DroneTrack("UAV-LIVE-011", "物流机", build_loop_sampler([(-42, -42, 14), (-42, 42, 14), (42, 42, 14), (42, -42, 14)], speed=3.0)),
            DroneTrack("UAV-LIVE-012", "巡检机", build_loop_sampler([(-35, 35, 12), (35, 35, 12), (35, -35, 12), (-35, -35, 12)], speed=2.8)),
            DroneTrack("UAV-LIVE-013", "警戒机", build_loop_sampler([(-18, 46, 16), (18, 46, 16), (18, -46, 16), (-18, -46, 16)], speed=3.2)),
            DroneTrack("UAV-LIVE-014", "测绘机", build_loop_sampler([(46, -12, 18), (-46, -12, 18), (-46, 12, 18), (46, 12, 18)], speed=3.1)),
        ]

    # mixed_demo: one conflict pair + one restricted violation style flyby
    return [
        DroneTrack("UAV-LIVE-021", "物流机", build_loop_sampler([(-20, 0, 12), (20, 0, 12)], speed=3.0)),
        DroneTrack("UAV-LIVE-022", "巡检机", build_loop_sampler([(0, -20, 12), (0, 20, 12)], speed=3.0)),
        DroneTrack("UAV-LIVE-023", "训练机", build_loop_sampler([(8, -26, 12), (34, 0, 12), (8, 26, 12), (-24, 0, 12)], speed=2.7)),
    ]


def run_feeder(api_base: str, scenario: str, hz: float, duration: float, clear_first: bool) -> None:
    tracks = build_tracks(scenario)
    dt = 1.0 / max(hz, 1e-6)

    if clear_first:
        post_json(f"{api_base}/api/mode/live", {"clear_existing": True})
    else:
        post_json(f"{api_base}/api/mode/live", {"clear_existing": False})

    print(f"开始推流: scenario={scenario}, drones={len(tracks)}, hz={hz}, duration={duration}s")
    t0 = time.time()
    step = 0
    while True:
        elapsed = time.time() - t0
        if elapsed > duration:
            break

        drones_payload = []
        for track in tracks:
            pos, vel = track.sampler(elapsed)
            # Add tiny oscillation to altitude for more realistic stream
            pos = pos.copy()
            pos[2] = pos[2] + 0.15 * math.sin(elapsed * 1.6 + step * 0.05)
            drones_payload.append(
                {
                    "id": track.drone_id,
                    "type": track.drone_type,
                    "current_pos": [round(float(pos[0]), 4), round(float(pos[1]), 4), round(float(pos[2]), 4)],
                    "current_vel": [round(float(vel[0]), 4), round(float(vel[1]), 4), round(float(vel[2]), 4)],
                }
            )

        post_json(
            f"{api_base}/api/telemetry/batch",
            {
                "source": f"demo_{scenario}",
                "drones": drones_payload,
            },
        )
        step += 1
        time.sleep(dt)

    print("推流结束。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Feed live telemetry demo data into UAV warning backend.")
    parser.add_argument("--api", type=str, default="http://127.0.0.1:8000", help="Backend API base URL")
    parser.add_argument(
        "--scenario",
        type=str,
        default="crossing_alert",
        choices=["crossing_alert", "dense_safe", "mixed_demo"],
        help="Demo stream scenario",
    )
    parser.add_argument("--hz", type=float, default=5.0, help="Telemetry push frequency")
    parser.add_argument("--duration", type=float, default=60.0, help="Push duration in seconds")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear existing live drones before feeding")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_feeder(
        api_base=args.api.rstrip("/"),
        scenario=args.scenario,
        hz=args.hz,
        duration=args.duration,
        clear_first=not args.no_clear,
    )
