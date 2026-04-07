export type DroneStatus = "GREEN" | "YELLOW" | "RED";

export interface DroneSnapshot {
  id: string;
  type: string;
  current_pos: [number, number, number];
  current_vel: [number, number, number];
  history_pos: [number, number, number][];
  predict_traj: [number, number, number][];
  status: DroneStatus;
  warning_msg: string;
  warning_category: string;
}

export interface RuntimeZone {
  zone_id: string;
  shape: "cylinder" | "polygon";
  zone_kind?: "building" | "no_fly" | "restricted" | string;
  center?: [number, number, number];
  radius?: number;
  points?: [number, number][];
  height: number;
  base_z?: number;
}

export interface RuntimeZones {
  buildings: RuntimeZone[];
  no_fly: RuntimeZone[];
  restricted: RuntimeZone[];
}

export interface SituationPayload {
  timestamp: number;
  scenario: string;
  engine: {
    mode: string;
    detail: string;
  };
  system: {
    running: boolean;
    tick_dt: number;
    predict_dt: number;
    ws_clients: number;
    data_mode?: string;
    telemetry_source?: string;
  };
  stats: {
    total: number;
    green: number;
    yellow: number;
    red: number;
  };
  zones: RuntimeZones;
  drones: DroneSnapshot[];
}
