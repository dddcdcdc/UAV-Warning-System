#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib import request


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=8) as resp:
        text = resp.read().decode("utf-8")
        return json.loads(text) if text else {}


def replay(api_base: str, file_path: Path, clear_first: bool) -> None:
    content = json.loads(file_path.read_text(encoding="utf-8"))
    frames = content.get("frames", [])
    if not frames:
        raise ValueError("轨迹文件不包含 frames。")

    fps = float(content.get("fps", 5.0))
    dt = 1.0 / max(fps, 1e-6)

    post_json(f"{api_base}/api/mode/live", {"clear_existing": bool(clear_first)})
    print(f"开始回放: file={file_path}, frames={len(frames)}, fps={fps}")

    for idx, frame in enumerate(frames):
        drones = frame.get("drones", [])
        if not isinstance(drones, list):
            continue
        post_json(
            f"{api_base}/api/telemetry/batch",
            {
                "source": f"file_replay_{file_path.stem}",
                "drones": drones,
            },
        )
        time.sleep(dt)
        if (idx + 1) % 50 == 0:
            print(f"已回放 {idx + 1}/{len(frames)} 帧")

    print("回放结束。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay telemetry frames from JSON file.")
    parser.add_argument("--api", type=str, default="http://127.0.0.1:8000", help="Backend API base URL")
    parser.add_argument("--file", type=str, required=True, help="Path to telemetry frames JSON")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear existing live drones")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    replay(
        api_base=args.api.rstrip("/"),
        file_path=Path(args.file),
        clear_first=not args.no_clear,
    )
