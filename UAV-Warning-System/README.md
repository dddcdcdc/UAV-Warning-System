# UAV In-Flight Warning System

面向毕设演示的“飞中实时态势与冲突预警系统”，支持：

- 基于 ID 的多机实时状态管理
- 速度预测模型（含 `CNNGruPredictor`）推理
- 基于预测轨迹的红黄绿预警
- `simulation`（内置剧本）与 `live`（外部轨迹流）双模式
- WebSocket 实时推送到前端三维沙盘

---

## 1. 快速启动

### 后端
```bash
cd UAV-Warning-System/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端
```bash
cd UAV-Warning-System/frontend
rm -rf node_modules package-lock.json
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

---

## 2. 导入你已有的模型（pth + stats）

你当前训练代码输出目录通常为 `runs/<exp_name>/`，里面至少有：

- `best_model.pth`
- `config.json`（建议保留，里面有 `model_name`、`hidden_dim` 等）
- `vel_stats.npz`（建议包含 `max_velocity`）

### 方式 A：环境变量启动（推荐）
```bash
export UAV_MODEL_DIR=/path/to/runs/vel_xxx
export UAV_VEL_STATS=/path/to/runs/vel_xxx/vel_stats.npz   # 可选
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 方式 B：运行中热加载
```bash
curl -X POST http://127.0.0.1:8000/api/model/reload \
  -H "Content-Type: application/json" \
  -d '{
    "model_dir": "/path/to/runs/vel_xxx",
    "stats_path": "/path/to/runs/vel_xxx/vel_stats.npz"
  }'
```

系统会自动读取 `config.json` 的 `model_name` 并实例化模型：

- `TrajectoryPredictor`
- `CNNGruPredictor` / `CNNGruTrajectoryPredictor`

并使用 `vel_stats.npz` 的 `max_velocity` 做速度反归一化。

---

## 3. 当前系统是否硬编码轨迹？

### 当前能力
已支持两种数据来源：

1. `simulation`：内置剧本（用于快速演示）
2. `live`：外部接口持续输入轨迹（你真实系统应使用此模式）

也就是说，不再只能依赖硬编码轨迹。你可以持续推送新轨迹点，系统会在 5Hz 主循环中不断预测与告警。

---

## 4. 实时轨迹输入结构（live 模式）

### 单机输入
`POST /api/telemetry/drone`
```json
{
  "id": "UAV-001",
  "type": "物流机",
  "current_pos": [12.3, -4.6, 11.2],
  "current_vel": [2.1, 0.4, 0.0]
}
```

### 批量输入（推荐）
`POST /api/telemetry/batch`
```json
{
  "source": "my_realtime_stream",
  "drones": [
    {
      "id": "UAV-001",
      "type": "物流机",
      "current_pos": [12.3, -4.6, 11.2],
      "current_vel": [2.1, 0.4, 0.0]
    },
    {
      "id": "UAV-002",
      "type": "巡检机",
      "current_pos": [9.8, -6.1, 11.0],
      "current_vel": [1.8, 0.7, 0.0]
    }
  ]
}
```

系统会自动切换到 `live` 模式，并对所有 ID 进行预测与两两冲突检测（同时间步距离阈值判定）。

---

## 5. Demo 轨迹喂入脚本（已提供）

脚本：`backend/demo_feeder.py`

用途：在你系统已支持实时输入的基础上，自动推送可演示场景（包含冲突与正常飞行），并控制速度上限在合理范围（不超过约 8m/s）。

```bash
cd UAV-Warning-System/backend
python demo_feeder.py --api http://127.0.0.1:8000 --scenario crossing_alert --hz 5 --duration 60
```

可选场景：

- `crossing_alert`：两机交汇触发冲突
- `mixed_demo`：冲突 + 违规混合
- `dense_safe`：多机正常巡航

### 文件回放（接入你自己的轨迹）
脚本：`backend/replay_from_file.py`

```bash
cd UAV-Warning-System/backend
python replay_from_file.py --api http://127.0.0.1:8000 --file ./my_frames.json
```

`my_frames.json` 示例：
```json
{
  "fps": 5,
  "frames": [
    {
      "drones": [
        {
          "id": "UAV-001",
          "type": "物流机",
          "current_pos": [0.0, 0.0, 12.0],
          "current_vel": [2.0, 0.0, 0.0]
        },
        {
          "id": "UAV-002",
          "type": "巡检机",
          "current_pos": [0.0, -10.0, 12.0],
          "current_vel": [0.0, 2.0, 0.0]
        }
      ]
    }
  ]
}
```

---

## 6. 主要 API

- `GET /api/health`
- `GET /api/state`
- `GET /api/config`
- `GET /api/scenarios`
- `POST /api/scenario/{name}`
- `POST /api/control/pause`
- `POST /api/control/resume`
- `GET /api/mode`
- `POST /api/mode/live`
- `POST /api/mode/simulation`
- `POST /api/model/reload`
- `POST /api/telemetry/drone`
- `POST /api/telemetry/batch`
- `POST /api/telemetry/clear`
- `POST /api/zones/no-fly/polygon`
- `POST /api/zones/restricted/polygon`
- `POST /api/zones/reset`
- `WS /ws/situation`

---

## 7. 说明与建议

1. 你说得对：合格飞中系统应以实时接口为主，内置剧本仅用于答辩演示。  
2. 你的速度模型（最大约 8m/s、均值约 3m/s）与当前 1 秒 / 10 步预测窗口匹配良好。  
3. 前端“演示剧本按钮”已支持手动隐藏，并在 `live` 模式下自动收起，避免影响真实演示流。  
