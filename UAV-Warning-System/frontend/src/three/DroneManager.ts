import * as THREE from "three";

import type { DroneSnapshot, DroneStatus } from "../types";

type DroneVisual = {
  mesh: THREE.Mesh;
  historyLine: THREE.Line;
  predictLine: THREE.Line<THREE.BufferGeometry, THREE.LineDashedMaterial>;
  labelSprite: THREE.Sprite;
  targetPos: THREE.Vector3;
  predictPoints: THREE.Vector3[];
};

const MESH_COLOR: Record<DroneStatus, number> = {
  GREEN: 0x2eb56d,
  YELLOW: 0xeaa81a,
  RED: 0xd83f3f,
};

const PREDICT_COLOR: Record<DroneStatus, number> = {
  GREEN: 0xffbd2d,
  YELLOW: 0xf57c00,
  RED: 0xd32f2f,
};

const HISTORY_WINDOW_POINTS = 5; // 0.8s at 5Hz (tick=0.2s)
const LABEL_HEIGHT_OFFSET = 0.88;

function createLabelSprite(text: string): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 320;
  canvas.height = 96;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = "700 30px 'Rajdhani', 'Noto Sans SC', 'Microsoft YaHei', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineJoin = "round";
    ctx.lineWidth = 8;
    ctx.strokeStyle = "rgba(14, 24, 34, 0.82)";
    ctx.strokeText(text, canvas.width / 2, canvas.height / 2 + 1);
    ctx.fillStyle = "rgba(218, 238, 255, 0.98)";
    ctx.fillText(text, canvas.width / 2, canvas.height / 2 + 1);
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: true,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(2.55, 0.8, 1.0);
  return sprite;
}

export class DroneManager {
  private readonly scene: THREE.Scene;
  private readonly drones = new Map<string, DroneVisual>();

  constructor(scene: THREE.Scene) {
    this.scene = scene;
  }

  sync(snapshots: DroneSnapshot[]): void {
    const active = new Set<string>();
    for (const snapshot of snapshots) {
      active.add(snapshot.id);
      if (!this.drones.has(snapshot.id)) {
        this.drones.set(snapshot.id, this.createDroneVisual(snapshot));
      }
      const visual = this.drones.get(snapshot.id);
      if (!visual) continue;
      this.updateDroneVisual(visual, snapshot);
    }

    for (const [id, visual] of this.drones.entries()) {
      if (active.has(id)) continue;
      this.disposeVisual(visual);
      this.drones.delete(id);
    }
  }

  animate(alpha = 0.24): void {
    for (const visual of this.drones.values()) {
      visual.mesh.position.lerp(visual.targetPos, alpha);
      visual.labelSprite.position.set(
        visual.mesh.position.x,
        visual.mesh.position.y,
        visual.mesh.position.z + LABEL_HEIGHT_OFFSET
      );

      if (visual.predictPoints.length > 0) {
        const stitched = [...visual.predictPoints];
        stitched[0] = visual.mesh.position.clone();
        this.replaceLineGeometry(visual.predictLine, stitched, true);
      }
    }
  }

  dispose(): void {
    for (const visual of this.drones.values()) {
      this.disposeVisual(visual);
    }
    this.drones.clear();
  }

  private createDroneVisual(snapshot: DroneSnapshot): DroneVisual {
    const pos = new THREE.Vector3(...snapshot.current_pos);
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.22, 14, 14),
      new THREE.MeshStandardMaterial({
        color: MESH_COLOR[snapshot.status],
        emissive: MESH_COLOR[snapshot.status],
        emissiveIntensity: 0.3,
        roughness: 0.45,
        metalness: 0.1,
      })
    );
    mesh.position.copy(pos);
    this.scene.add(mesh);

    const historyLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([pos]),
      new THREE.LineBasicMaterial({ color: 0x3f4a56, transparent: true, opacity: 0.9 })
    );
    this.scene.add(historyLine);

    const predictLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([pos]),
      new THREE.LineDashedMaterial({
        color: PREDICT_COLOR[snapshot.status],
        dashSize: 0.55,
        gapSize: 0.32,
        transparent: true,
        opacity: 0.98,
      })
    );
    predictLine.computeLineDistances();
    this.scene.add(predictLine);

    const labelSprite = createLabelSprite(snapshot.id);
    labelSprite.position.set(pos.x, pos.y, pos.z + LABEL_HEIGHT_OFFSET);
    this.scene.add(labelSprite);

    return {
      mesh,
      historyLine,
      predictLine,
      labelSprite,
      targetPos: pos.clone(),
      predictPoints: [pos.clone()],
    };
  }

  private updateDroneVisual(visual: DroneVisual, snapshot: DroneSnapshot): void {
    visual.targetPos = new THREE.Vector3(...snapshot.current_pos);

    const historyWindow = snapshot.history_pos.slice(-HISTORY_WINDOW_POINTS);
    let horizonSteps = 4;
    const isBuildingEmergency =
      snapshot.status === "RED" &&
      (snapshot.warning_category === "building_collision" || snapshot.warning_msg.includes("建筑碰撞"));
    if (isBuildingEmergency) {
      const match = snapshot.warning_msg.match(/预测\s*([0-9.]+)s/);
      if (match) {
        const impactSec = Number(match[1]);
        if (Number.isFinite(impactSec)) {
          horizonSteps = Math.max(1, Math.min(4, Math.ceil(impactSec / 0.1)));
        }
      } else {
        horizonSteps = 1;
      }
    }
    const predictWindow = snapshot.predict_traj.slice(0, horizonSteps); // Around 2~4m visual horizon

    visual.predictPoints = [
      new THREE.Vector3(...snapshot.current_pos),
      ...predictWindow.map((point) => new THREE.Vector3(...point)),
    ];

    this.replaceLineGeometry(
      visual.historyLine,
      historyWindow.map((point) => new THREE.Vector3(...point)),
      false
    );
    this.replaceLineGeometry(visual.predictLine, visual.predictPoints, true);

    const material = visual.mesh.material as THREE.MeshStandardMaterial;
    material.color.setHex(MESH_COLOR[snapshot.status]);
    material.emissive.setHex(MESH_COLOR[snapshot.status]);
    visual.predictLine.material.color.setHex(PREDICT_COLOR[snapshot.status]);
  }

  private replaceLineGeometry(line: THREE.Line, points: THREE.Vector3[], dashed: boolean): void {
    const nextPoints = points.length > 0 ? points : [new THREE.Vector3(0, 0, 0)];
    const nextGeometry = new THREE.BufferGeometry().setFromPoints(nextPoints);
    line.geometry.dispose();
    line.geometry = nextGeometry;
    if (dashed && "computeLineDistances" in line) {
      (line as THREE.Line<THREE.BufferGeometry, THREE.LineDashedMaterial>).computeLineDistances();
    }
  }

  private disposeVisual(visual: DroneVisual): void {
    this.scene.remove(visual.mesh, visual.historyLine, visual.predictLine, visual.labelSprite);
    visual.mesh.geometry.dispose();
    (visual.mesh.material as THREE.Material).dispose();
    visual.historyLine.geometry.dispose();
    (visual.historyLine.material as THREE.Material).dispose();
    visual.predictLine.geometry.dispose();
    (visual.predictLine.material as THREE.Material).dispose();
    const labelMaterial = visual.labelSprite.material as THREE.SpriteMaterial;
    labelMaterial.map?.dispose();
    labelMaterial.dispose();
  }
}
