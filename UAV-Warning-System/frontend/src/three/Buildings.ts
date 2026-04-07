import * as THREE from "three";

import type { RuntimeZones, RuntimeZone } from "../types";

type BuildingSpec = {
  x: number;
  y: number;
  width: number;
  depth: number;
  height: number;
  color?: number;
};

function addBoxBuilding(scene: THREE.Scene, spec: BuildingSpec): void {
  const geometry = new THREE.BoxGeometry(spec.width, spec.depth, spec.height);
  const material = new THREE.MeshStandardMaterial({
    color: spec.color ?? 0xbcc3cc,
    roughness: 0.88,
    metalness: 0.08,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(spec.x, spec.y, spec.height / 2);
  scene.add(mesh);

  const edges = new THREE.EdgesGeometry(geometry);
  const frame = new THREE.LineSegments(
    edges,
    new THREE.LineBasicMaterial({
      color: 0x5e6874,
      transparent: true,
      opacity: 0.52,
    })
  );
  frame.position.copy(mesh.position);
  scene.add(frame);
}

function drawRectPlane(
  scene: THREE.Scene,
  width: number,
  height: number,
  color: number,
  z: number
): THREE.Mesh {
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(width, height),
    new THREE.MeshStandardMaterial({ color, roughness: 1.0, metalness: 0.0 })
  );
  mesh.position.set(0, 0, z);
  scene.add(mesh);
  return mesh;
}

function createLaneLine(scene: THREE.Scene, x: number, y: number, length: number, horizontal: boolean): void {
  const line = new THREE.Mesh(
    new THREE.PlaneGeometry(horizontal ? length : 0.38, horizontal ? 0.38 : length),
    new THREE.MeshBasicMaterial({ color: 0xf1f4f7 })
  );
  line.position.set(x, y, 0.04);
  scene.add(line);
}

function createRoadMarkings(scene: THREE.Scene): void {
  for (let i = -84; i <= 84; i += 9) {
    if (Math.abs(i) < 11) continue;
    createLaneLine(scene, i, -2.4, 5, true);
    createLaneLine(scene, i, 2.4, 5, true);
    createLaneLine(scene, -2.4, i, 5, false);
    createLaneLine(scene, 2.4, i, 5, false);
  }

  const centerBox = new THREE.Mesh(
    new THREE.PlaneGeometry(16, 16),
    new THREE.MeshBasicMaterial({
      color: 0xdedede,
      transparent: true,
      opacity: 0.4,
    })
  );
  centerBox.position.set(0, 0, 0.03);
  scene.add(centerBox);
}

function addCoreBuildings(scene: THREE.Scene): void {
  const core: BuildingSpec[] = [
    { x: 20, y: 20, width: 8.5, depth: 8.5, height: 23, color: 0xadb6c0 },
    { x: -22, y: 24, width: 7.8, depth: 7.8, height: 21, color: 0xb6bec8 },
    { x: -20, y: -18, width: 9.2, depth: 9.2, height: 25, color: 0xa5aeb8 },
    { x: 24, y: -22, width: 8.2, depth: 8.2, height: 22, color: 0xb2bcc7 },
  ];
  for (const item of core) {
    addBoxBuilding(scene, item);
  }
}

function addStreetBuildings(scene: THREE.Scene): void {
  const extras: BuildingSpec[] = [
    { x: -64, y: 48, width: 12, depth: 10, height: 28, color: 0xc3cad3 },
    { x: -48, y: 62, width: 9, depth: 12, height: 24, color: 0xbec7cf },
    { x: -70, y: -44, width: 13, depth: 9, height: 22, color: 0xc4ccd4 },
    { x: -54, y: -60, width: 9, depth: 10, height: 26, color: 0xbfc7d0 },
    { x: 66, y: 50, width: 12, depth: 10, height: 25, color: 0xc2cbd4 },
    { x: 52, y: 64, width: 9, depth: 10, height: 22, color: 0xb8c1cb },
    { x: 72, y: -46, width: 13, depth: 10, height: 22, color: 0xc2cad2 },
    { x: 56, y: -62, width: 9, depth: 12, height: 24, color: 0xb9c2cc },
    { x: -82, y: 8, width: 15, depth: 13, height: 21, color: 0xc7ced6 },
    { x: 84, y: -10, width: 15, depth: 13, height: 22, color: 0xc8ced5 },
  ];
  for (const item of extras) {
    addBoxBuilding(scene, item);
  }
}

function addUrbanGround(scene: THREE.Scene): void {
  drawRectPlane(scene, 200, 200, 0xc1c7cd, 0);

  const roadMaterial = new THREE.MeshStandardMaterial({
    color: 0x5f666c,
    roughness: 1.0,
    metalness: 0.0,
  });
  const roadX = new THREE.Mesh(new THREE.PlaneGeometry(200, 19), roadMaterial);
  roadX.position.set(0, 0, 0.01);
  scene.add(roadX);

  const roadY = new THREE.Mesh(new THREE.PlaneGeometry(19, 200), roadMaterial);
  roadY.position.set(0, 0, 0.01);
  scene.add(roadY);

  const laneSplitX = new THREE.Mesh(
    new THREE.PlaneGeometry(200, 0.26),
    new THREE.MeshBasicMaterial({ color: 0xffde7a })
  );
  laneSplitX.position.set(0, 0, 0.03);
  scene.add(laneSplitX);

  const laneSplitY = new THREE.Mesh(
    new THREE.PlaneGeometry(0.26, 200),
    new THREE.MeshBasicMaterial({ color: 0xffde7a })
  );
  laneSplitY.position.set(0, 0, 0.03);
  scene.add(laneSplitY);

  createRoadMarkings(scene);
}

function zoneLabel(zone: RuntimeZone): string {
  return zone.zone_id || (zone.shape === "polygon" ? "NFZ-POLY" : "ZONE");
}

function disposeObject(object: THREE.Object3D): void {
  const mesh = object as THREE.Mesh;
  const geometry = (mesh.geometry ?? null) as THREE.BufferGeometry | null;
  const material = mesh.material as THREE.Material | THREE.Material[] | undefined;
  geometry?.dispose();
  if (Array.isArray(material)) {
    material.forEach((item) => item.dispose());
  } else {
    material?.dispose();
  }
  for (const child of object.children) {
    disposeObject(child);
  }
}

function clearGroup(group: THREE.Group): void {
  const children = [...group.children];
  for (const child of children) {
    group.remove(child);
    disposeObject(child);
  }
}

function createCylinderZone(zone: RuntimeZone, color: number, alpha: number): THREE.Object3D {
  const center = zone.center ?? [0, 0, 0];
  const radius = zone.radius ?? 1;
  const height = zone.height ?? 50;
  const baseZ = zone.base_z ?? center[2] ?? 0;

  const group = new THREE.Group();
  const mesh = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius, height, 48, 1, true),
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: alpha,
      side: THREE.DoubleSide,
      depthWrite: false,
    })
  );
  mesh.rotation.x = Math.PI / 2;
  mesh.position.set(center[0], center[1], baseZ + height / 2);
  group.add(mesh);

  const cap = new THREE.Mesh(
    new THREE.CircleGeometry(radius, 48),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: alpha * 0.7 })
  );
  cap.position.set(center[0], center[1], baseZ + 0.03);
  group.add(cap);

  return group;
}

function createPolygonZone(zone: RuntimeZone, color: number, alpha: number): THREE.Object3D | null {
  const points = zone.points ?? [];
  if (points.length < 3) return null;
  const shape = new THREE.Shape();
  shape.moveTo(points[0][0], points[0][1]);
  for (let i = 1; i < points.length; i += 1) {
    shape.lineTo(points[i][0], points[i][1]);
  }
  shape.lineTo(points[0][0], points[0][1]);

  const height = zone.height ?? 50;
  const baseZ = zone.base_z ?? 0;
  const extrude = new THREE.ExtrudeGeometry(shape, {
    depth: height,
    bevelEnabled: false,
    curveSegments: 1,
  });
  const mesh = new THREE.Mesh(
    extrude,
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: alpha,
      side: THREE.DoubleSide,
      depthWrite: false,
    })
  );
  mesh.position.set(0, 0, baseZ);
  return mesh;
}

export class CitySceneLayers {
  private readonly zoneGroup = new THREE.Group();
  private readonly draftGroup = new THREE.Group();

  constructor(private readonly scene: THREE.Scene) {
    addUrbanGround(scene);
    addCoreBuildings(scene);
    addStreetBuildings(scene);
    scene.add(this.zoneGroup);
    scene.add(this.draftGroup);
  }

  updateZones(zones: RuntimeZones): void {
    clearGroup(this.zoneGroup);

    for (const zone of zones.no_fly) {
      const object =
        zone.shape === "polygon"
          ? createPolygonZone(zone, 0xe84f4f, 0.22)
          : createCylinderZone(zone, 0xe84f4f, 0.2);
      if (!object) continue;
      object.userData = { label: zoneLabel(zone) };
      this.zoneGroup.add(object);
    }

    for (const zone of zones.restricted) {
      const object =
        zone.shape === "polygon"
          ? createPolygonZone(zone, 0xffc24a, 0.14)
          : createCylinderZone(zone, 0xffc24a, 0.14);
      if (!object) continue;
      object.userData = { label: zoneLabel(zone) };
      this.zoneGroup.add(object);
    }
  }

  setDraftPolygon(points: [number, number][]): void {
    clearGroup(this.draftGroup);
    if (points.length === 0) return;

    points.forEach((point) => {
      const dot = new THREE.Mesh(
        new THREE.SphereGeometry(0.45, 10, 10),
        new THREE.MeshBasicMaterial({ color: 0x1e88ff })
      );
      dot.position.set(point[0], point[1], 0.35);
      this.draftGroup.add(dot);
    });

    if (points.length >= 2) {
      const linePoints = points.map((point) => new THREE.Vector3(point[0], point[1], 0.2));
      const polyline = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(linePoints),
        new THREE.LineDashedMaterial({
          color: 0x1e88ff,
          dashSize: 1.4,
          gapSize: 0.7,
        })
      );
      polyline.computeLineDistances();
      this.draftGroup.add(polyline);
    }
  }

  dispose(): void {
    clearGroup(this.zoneGroup);
    clearGroup(this.draftGroup);
    this.scene.remove(this.zoneGroup, this.draftGroup);
  }
}
