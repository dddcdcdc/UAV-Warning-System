from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False
    torch = None  # type: ignore[assignment]
    nn = object  # type: ignore[assignment]
    F = object  # type: ignore[assignment]


if TORCH_AVAILABLE:
    class TrajectoryPredictor(nn.Module):
        """Baseline GRU encoder-decoder used by previous model versions."""

        def __init__(
            self,
            input_dim: int = 3,
            hidden_dim: int = 64,
            output_dim: int = 3,
            num_layers: int = 2,
            dropout: float = 0.3,
            output_length: int = 10,
        ) -> None:
            super().__init__()
            self.hidden_dim = hidden_dim
            self.output_length = output_length
            self.gru_encoder = nn.GRU(
                input_dim,
                hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
            )
            self.gru_decoder = nn.GRU(
                hidden_dim,
                hidden_dim,
                num_layers=num_layers,
                batch_first=True,
            )
            self.fc = nn.Linear(hidden_dim, output_dim)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            _, hidden = self.gru_encoder(x)
            dec_input = torch.zeros(
                x.size(0),
                self.output_length,
                self.hidden_dim,
                dtype=x.dtype,
                device=x.device,
            )
            out, _ = self.gru_decoder(dec_input, hidden)
            return self.fc(out)


    class CNNGruTrajectoryPredictor(nn.Module):
        """CNN + Residual + GRU + Additive Attention + GRU decoder."""

        def __init__(
            self,
            input_dim: int = 3,
            hidden_dim: int = 64,
            output_dim: int = 3,
            num_layers: int = 2,
            dropout: float = 0.5,
            cnn_out_channels: int = 16,
            kernel_size: int = 3,
            output_length: int = 10,
        ) -> None:
            super().__init__()
            self.hidden_dim = hidden_dim
            self.output_length = output_length

            self.conv1d = nn.Conv1d(
                in_channels=input_dim,
                out_channels=cnn_out_channels,
                kernel_size=kernel_size,
                padding=kernel_size // 2,
            )
            self.bn = nn.BatchNorm1d(cnn_out_channels)
            self.residual_conv = nn.Conv1d(input_dim, cnn_out_channels, kernel_size=1)
            self.res_scale = nn.Parameter(torch.ones(1))

            self.gru1 = nn.GRU(
                cnn_out_channels,
                hidden_dim,
                num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
            )

            self.attn_W = nn.Linear(hidden_dim, hidden_dim, bias=False)
            self.attn_v = nn.Linear(hidden_dim, 1, bias=False)

            self.gru2 = nn.GRU(hidden_dim, hidden_dim, num_layers, batch_first=True)
            self.fc = nn.Linear(hidden_dim, output_dim)
            self.act = nn.ELU()

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x_permuted = x.permute(0, 2, 1)  # (B, C, T)

            main_out = self.act(self.bn(self.conv1d(x_permuted)))
            res_out = self.residual_conv(x_permuted)
            out = main_out + self.res_scale * res_out
            out = out.permute(0, 2, 1)  # (B, T, C')

            enc_out, h_n = self.gru1(out)

            attn_hidden = torch.tanh(self.attn_W(enc_out))
            attn_scores = self.attn_v(attn_hidden)
            attn_weights = F.softmax(attn_scores, dim=1)
            context_vector = torch.sum(attn_weights * enc_out, dim=1)  # (B, H)

            dec_input = context_vector.unsqueeze(1).repeat(1, self.output_length, 1)
            dec_out, _ = self.gru2(dec_input, h_n)
            return self.fc(dec_out)
else:
    class TrajectoryPredictor:  # pragma: no cover
        pass

    class CNNGruTrajectoryPredictor:  # pragma: no cover
        pass


def _clean_state_dict_keys(state_dict: dict[str, Any]) -> dict[str, Any]:
    if not state_dict:
        return state_dict
    if all(key.startswith("module.") for key in state_dict.keys()):
        return {key.replace("module.", "", 1): value for key, value in state_dict.items()}
    return state_dict


class VelocityPredictionEngine:
    def __init__(
        self,
        model_dir: str | None = None,
        stats_path: str | None = None,
        history_dt: float = 0.2,
        predict_steps: int = 10,
        predict_dt: float = 0.1,
        default_max_velocity: float = 8.0,
    ) -> None:
        self.history_dt = history_dt
        self.predict_steps = predict_steps
        self.predict_dt = predict_dt
        self.input_len = 20
        self.max_velocity = default_max_velocity
        self.model_name = "kinematic_fallback"
        self.stats_path = stats_path

        self.model: Any = None
        self.device = "cpu"
        self.info: dict[str, str] = {
            "mode": "kinematic_fallback",
            "detail": "No model configured. Using kinematic velocity extrapolation.",
        }

        if model_dir:
            self._try_load_model(model_dir, stats_path)

    def _resolve_model_artifacts(self, model_dir: str) -> tuple[Path | None, Path | None, Path]:
        model_path = Path(model_dir)
        if model_path.is_file():
            weights_path = model_path
            model_root = model_path.parent
            config_path = model_root / "config.json"
            return (config_path if config_path.exists() else None), weights_path, model_root

        model_root = model_path
        config_path = model_root / "config.json"
        weights_path = model_root / "best_model.pth"
        if not weights_path.exists():
            candidates = sorted(model_root.glob("*.pth"))
            if candidates:
                weights_path = candidates[0]
        return (
            config_path if config_path.exists() else None,
            weights_path if weights_path.exists() else None,
            model_root,
        )

    def _create_model(self, model_name: str, config: dict[str, Any], output_steps: int) -> Any:
        hidden_dim = int(config.get("hidden_dim", 64))
        num_layers = int(config.get("num_layers", 2))
        dropout = float(config.get("dropout", 0.5))

        normalized_name = model_name.strip()
        if normalized_name in {"CNNGruPredictor", "CNNGruTrajectoryPredictor"}:
            cnn_out_channels = int(config.get("cnn_out_channels", 16))
            kernel_size = int(config.get("kernel_size", 3))
            return CNNGruTrajectoryPredictor(
                input_dim=3,
                hidden_dim=hidden_dim,
                output_dim=3,
                num_layers=num_layers,
                dropout=dropout,
                cnn_out_channels=cnn_out_channels,
                kernel_size=kernel_size,
                output_length=output_steps,
            )

        # fallback to base predictor for TrajectoryPredictor / AttentionPredictor
        return TrajectoryPredictor(
            input_dim=3,
            hidden_dim=hidden_dim,
            output_dim=3,
            num_layers=num_layers,
            dropout=dropout,
            output_length=output_steps,
        )

    def _try_load_model(self, model_dir: str, stats_path: str | None = None) -> None:
        if not TORCH_AVAILABLE:
            self.info = {
                "mode": "kinematic_fallback",
                "detail": "torch is unavailable in this runtime. Falling back to kinematics.",
            }
            return

        config_path, weights_path, model_root = self._resolve_model_artifacts(model_dir)
        if not weights_path:
            self.info = {
                "mode": "kinematic_fallback",
                "detail": f"No .pth file found under {model_root}",
            }
            return

        try:
            config: dict[str, Any] = {}
            if config_path and config_path.exists():
                with open(config_path, "r", encoding="utf-8") as file:
                    config = json.load(file)

            raw_state = torch.load(weights_path, map_location="cpu")
            if isinstance(raw_state, dict) and "state_dict" in raw_state:
                raw_state = raw_state["state_dict"]
            if not isinstance(raw_state, dict):
                raise ValueError("Invalid checkpoint format: expected state_dict.")
            state = _clean_state_dict_keys(raw_state)

            self.input_len = int(config.get("input_len", config.get("input_length", self.input_len)))
            self.predict_steps = int(config.get("output_len", config.get("predict_steps", self.predict_steps)))
            model_name = str(config.get("model_name", ""))
            if not model_name:
                # Config-less checkpoint fallback: infer by key pattern.
                if any(key.startswith("conv1d.") or key.startswith("residual_conv.") for key in state.keys()):
                    model_name = "CNNGruPredictor"
                else:
                    model_name = "TrajectoryPredictor"

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            model = self._create_model(model_name=model_name, config=config, output_steps=self.predict_steps)
            model = model.to(self.device)

            # strict=False to tolerate minor key mismatch between training wrappers.
            model.load_state_dict(state, strict=False)
            model.eval()

            self.model = model
            self.model_name = model_name
            self._load_velocity_scale(model_root=model_root, explicit_stats_path=stats_path)
            self.info = {
                "mode": "torch_velocity_model",
                "detail": (
                    f"Loaded {model_name} from {weights_path.name}; "
                    f"input_len={self.input_len}, predict_steps={self.predict_steps}, "
                    f"max_vel={self.max_velocity:.3f}"
                ),
            }
        except Exception as exc:  # pragma: no cover
            self.model = None
            self.info = {
                "mode": "kinematic_fallback",
                "detail": f"Model load failed: {exc}",
            }

    def _load_velocity_scale(self, model_root: Path, explicit_stats_path: str | None = None) -> None:
        env_stats = explicit_stats_path
        candidates: list[Path] = []
        if env_stats:
            candidates.append(Path(env_stats))
        candidates.extend(
            [
                model_root / "vel_stats.npz",
                model_root / "stats.npz",
                model_root.parent / "data" / "processed" / "vel_stats.npz",
            ]
        )
        for candidate in candidates:
            if not candidate.exists():
                continue
            try:
                stats = np.load(candidate)
                for key in ["max_velocity", "max_vel", "velocity_scale"]:
                    if key in stats:
                        self.max_velocity = float(stats[key])
                        self.stats_path = str(candidate)
                        return
            except Exception:
                continue

    def predict_for_all(self, active_drones: dict[str, dict[str, Any]]) -> None:
        for drone in active_drones.values():
            sim_state = drone.get("_sim")
            if isinstance(sim_state, dict) and sim_state.get("halted"):
                drone["predict_traj"] = []
                continue
            history = list(drone.get("history_pos", []))
            current_vel = drone.get("current_vel")
            drone["predict_traj"] = self.predict(history, current_vel)

    def predict(
        self,
        history_positions: list[list[float]],
        current_velocity: list[float] | None,
    ) -> list[list[float]]:
        if len(history_positions) == 0:
            return []

        if self.model is not None and len(history_positions) >= 2:
            predicted_vel = self._predict_velocity_by_model(history_positions)
        else:
            predicted_vel = self._predict_velocity_kinematic(history_positions, current_velocity)
        return self._integrate_to_positions(history_positions[-1], predicted_vel)

    def _predict_velocity_by_model(self, history_positions: list[list[float]]) -> np.ndarray:
        try:
            positions = np.asarray(history_positions, dtype=np.float32)
            velocity_seq = np.diff(positions, axis=0) / max(self.history_dt, 1e-6)
            if velocity_seq.shape[0] == 0:
                return np.zeros((self.predict_steps, 3), dtype=np.float32)

            if velocity_seq.shape[0] < self.input_len:
                pad = np.repeat(velocity_seq[:1], self.input_len - velocity_seq.shape[0], axis=0)
                velocity_seq = np.concatenate([pad, velocity_seq], axis=0)
            else:
                velocity_seq = velocity_seq[-self.input_len :]

            velocity_norm = velocity_seq / max(self.max_velocity, 1e-6)
            tensor = torch.tensor(velocity_norm, dtype=torch.float32, device=self.device).unsqueeze(0)
            with torch.no_grad():
                pred_norm = self.model(tensor).squeeze(0).cpu().numpy()

            pred_vel = pred_norm * self.max_velocity
            pred_vel = np.clip(pred_vel, -1.8 * self.max_velocity, 1.8 * self.max_velocity)
            if pred_vel.shape[0] < self.predict_steps:
                tail = np.repeat(pred_vel[-1:], self.predict_steps - pred_vel.shape[0], axis=0)
                pred_vel = np.concatenate([pred_vel, tail], axis=0)
            return pred_vel[: self.predict_steps]
        except Exception:
            return self._predict_velocity_kinematic(history_positions, current_velocity=None)

    def _predict_velocity_kinematic(
        self,
        history_positions: list[list[float]],
        current_velocity: list[float] | None,
    ) -> np.ndarray:
        if len(history_positions) < 2:
            base = np.array(current_velocity or [0.0, 0.0, 0.0], dtype=np.float32)
            return np.repeat(base[None, :], self.predict_steps, axis=0)

        positions = np.asarray(history_positions, dtype=np.float32)
        vel_window = np.diff(positions[-6:], axis=0) / max(self.history_dt, 1e-6)
        base_vel = np.mean(vel_window, axis=0)
        acc = np.zeros(3, dtype=np.float32)
        if vel_window.shape[0] >= 2:
            acc = (vel_window[-1] - vel_window[0]) / max((vel_window.shape[0] - 1) * self.history_dt, 1e-6)

        if current_velocity is not None:
            base_vel = 0.7 * base_vel + 0.3 * np.asarray(current_velocity, dtype=np.float32)

        predicted = []
        vel = base_vel.astype(np.float32)
        for _ in range(self.predict_steps):
            vel = vel + 0.25 * acc * self.predict_dt
            vel = vel * 0.995
            predicted.append(vel.copy())
        return np.asarray(predicted, dtype=np.float32)

    def _integrate_to_positions(
        self,
        last_position: list[float],
        predicted_velocity: np.ndarray,
    ) -> list[list[float]]:
        points: list[list[float]] = []
        current = np.asarray(last_position, dtype=np.float32)
        for velocity in predicted_velocity[: self.predict_steps]:
            current = current + velocity * self.predict_dt
            points.append(current.round(4).tolist())
        return points
