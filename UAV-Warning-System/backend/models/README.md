# Model Drop-In Guide

支持直接加载你训练得到的速度模型目录（如 `runs/vel_xxx/`）：

```bash
export UAV_MODEL_DIR=/path/to/runs/vel_xxx
export UAV_VEL_STATS=/path/to/runs/vel_xxx/vel_stats.npz   # optional
```

推荐目录内容：

- `best_model.pth`
- `config.json`（包含 `model_name`、`hidden_dim`、`num_layers` 等）
- `vel_stats.npz`（建议包含 `max_velocity`）

当前已兼容：

- `model_name=TrajectoryPredictor`
- `model_name=CNNGruPredictor`
- `model_name=CNNGruTrajectoryPredictor`

缺少模型文件时，系统会自动回退到运动学预测器（demo 仍可运行）。
