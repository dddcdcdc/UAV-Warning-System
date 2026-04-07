import { defineStore } from "pinia";
import { ElNotification } from "element-plus";

import type { DroneSnapshot, DroneStatus, RuntimeZones, SituationPayload } from "../types";

export type AlertItem = {
  id: string;
  status: DroneStatus;
  message: string;
  category: string;
  at: number;
};

function buildWsUrl(): string {
  const fromEnv = import.meta.env.VITE_WS_URL as string | undefined;
  if (fromEnv) {
    return fromEnv;
  }
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.hostname}:8000/ws/situation`;
}

function beep(status: DroneStatus): void {
  const Ctx =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  if (!Ctx) return;
  const ctx = new Ctx();
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();

  oscillator.type = status === "RED" ? "square" : "triangle";
  oscillator.frequency.value = status === "RED" ? 990 : 760;
  gain.gain.value = status === "RED" ? 0.11 : 0.07;

  oscillator.connect(gain);
  gain.connect(ctx.destination);
  oscillator.start();
  oscillator.stop(ctx.currentTime + (status === "RED" ? 0.24 : 0.12));
  oscillator.onended = () => void ctx.close();
}

function statusText(status: DroneStatus): string {
  if (status === "RED") return "红色";
  if (status === "YELLOW") return "黄色";
  return "绿色";
}

const EMPTY_ZONES: RuntimeZones = {
  buildings: [],
  no_fly: [],
  restricted: [],
};

export const useSituationStore = defineStore("situation", {
  state: () => ({
    ws: null as WebSocket | null,
    shouldReconnect: true,
    connected: false,
    drones: [] as DroneSnapshot[],
    alerts: [] as AlertItem[],
    scenario: "",
    engineMode: "",
    engineDetail: "",
    running: true,
    dataMode: "simulation",
    telemetrySource: "",
    stats: {
      total: 0,
      green: 0,
      yellow: 0,
      red: 0,
    },
    zones: { ...EMPTY_ZONES } as RuntimeZones,
    statusMap: {} as Record<string, DroneStatus>,
    lastSeq: 0,
    redPopupToken: 0,
    latestRedMessage: "",
  }),
  getters: {
    sortedDrones(state): DroneSnapshot[] {
      const rank: Record<DroneStatus, number> = {
        RED: 0,
        YELLOW: 1,
        GREEN: 2,
      };
      return [...state.drones].sort((a, b) => {
        const statusDiff = rank[a.status] - rank[b.status];
        if (statusDiff !== 0) return statusDiff;
        return a.id.localeCompare(b.id);
      });
    },
    redAlerts(state): AlertItem[] {
      return state.alerts.filter((item) => item.status === "RED").slice(-8).reverse();
    },
    yellowAlerts(state): AlertItem[] {
      return state.alerts.filter((item) => item.status === "YELLOW").slice(-8).reverse();
    },
  },
  actions: {
    connect(): void {
      if (this.ws) return;

      this.shouldReconnect = true;
      const ws = new WebSocket(buildWsUrl());
      this.ws = ws;

      ws.onopen = () => {
        this.connected = true;
      };

      ws.onmessage = (event: MessageEvent<string>) => {
        try {
          const payload = JSON.parse(event.data) as SituationPayload;
          this.applyPayload(payload);
        } catch {
          // Ignore malformed packets.
        }
      };

      ws.onclose = () => {
        this.connected = false;
        this.ws = null;
        if (this.shouldReconnect) {
          window.setTimeout(() => this.connect(), 1200);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    },

    disconnect(): void {
      this.shouldReconnect = false;
      if (this.ws) {
        this.ws.close();
      }
      this.ws = null;
      this.connected = false;
    },

    applyPayload(payload: SituationPayload): void {
      this.drones = payload.drones;
      this.scenario = payload.scenario;
      this.engineMode = payload.engine.mode;
      this.engineDetail = payload.engine.detail;
      this.running = payload.system.running;
      this.dataMode = payload.system.data_mode ?? "simulation";
      this.telemetrySource = payload.system.telemetry_source ?? "";
      this.stats = payload.stats;
      this.zones = payload.zones ?? { ...EMPTY_ZONES };
      this.lastSeq += 1;

      const nextStatusMap: Record<string, DroneStatus> = {};
      for (const drone of payload.drones) {
        const prevStatus = this.statusMap[drone.id];
        nextStatusMap[drone.id] = drone.status;

        const shouldNotifyRed = drone.status === "RED" && prevStatus !== "RED";
        const shouldNotifyYellow = drone.status === "YELLOW" && (!prevStatus || prevStatus === "GREEN");
        if (!shouldNotifyRed && !shouldNotifyYellow) {
          continue;
        }

        const status = drone.status;
        const message = drone.warning_msg || `${drone.id} 状态变化：${statusText(status)}`;
        this.alerts.push({
          id: drone.id,
          status,
          message,
          category: drone.warning_category || "general",
          at: payload.timestamp,
        });
        if (this.alerts.length > 60) {
          this.alerts.shift();
        }

        if (status === "RED") {
          this.redPopupToken += 1;
          this.latestRedMessage = message;
          ElNotification.error({
            title: "红色警报",
            message,
            duration: 4500,
            offset: 44,
          });
          beep("RED");
        } else {
          ElNotification.warning({
            title: "黄色预警",
            message,
            duration: 3200,
            offset: 44,
          });
          beep("YELLOW");
        }
      }
      this.statusMap = nextStatusMap;
    },
  },
});
