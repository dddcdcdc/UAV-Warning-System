import * as THREE from "three";

import type { RuntimeZone, RuntimeZones } from "../types";

type FacadeTone =
  | "glass_blue"
  | "glass_green"
  | "concrete_warm"
  | "concrete_cool"
  | "brick"
  | "stone";

type BuildingSpec = {
  zoneId: string;
  x: number;
  y: number;
  width: number;
  depth: number;
  height: number;
  tone: FacadeTone;
};

const ROAD_LENGTH = 220;
const ROAD_HALF = 9.6;
const LANE_CENTER_OFFSET = ROAD_HALF * 0.5;
const STOP_LINE_OFFSET = 16.0;

const CITY_BUILDINGS: BuildingSpec[] = [
  // 西北：主塔 + 裙楼 + 附楼
  { zoneId: "B1-P", x: -34.0, y: 32.0, width: 22.0, depth: 13.5, height: 6.4, tone: "concrete_warm" },
  { zoneId: "B1", x: -34.0, y: 32.0, width: 8.8, depth: 8.4, height: 36.0, tone: "glass_blue" },
  { zoneId: "B1-A", x: -45.0, y: 38.0, width: 7.0, depth: 7.2, height: 19.0, tone: "concrete_cool" },

  // 东北：双塔 + 裙楼
  { zoneId: "B2-P", x: 34.0, y: 32.0, width: 23.0, depth: 13.5, height: 6.6, tone: "concrete_cool" },
  { zoneId: "B2-A", x: 29.5, y: 32.0, width: 6.8, depth: 6.8, height: 31.0, tone: "glass_green" },
  { zoneId: "B2-B", x: 38.5, y: 32.0, width: 6.4, depth: 6.4, height: 28.0, tone: "glass_blue" },
  { zoneId: "B2-L", x: 46.0, y: 38.0, width: 7.4, depth: 6.6, height: 14.0, tone: "stone" },

  // 西南：阶梯组团
  { zoneId: "B3-P", x: -34.0, y: -32.0, width: 22.0, depth: 13.5, height: 6.5, tone: "concrete_warm" },
  { zoneId: "B3-H", x: -37.0, y: -34.0, width: 9.0, depth: 8.4, height: 34.0, tone: "glass_blue" },
  { zoneId: "B3-S1", x: -27.0, y: -28.0, width: 7.4, depth: 7.2, height: 20.0, tone: "brick" },
  { zoneId: "B3-S2", x: -22.0, y: -23.0, width: 6.6, depth: 6.2, height: 13.0, tone: "concrete_cool" },

  // 东南：主塔 + 裙楼 + 附楼
  { zoneId: "B4-P", x: 34.0, y: -32.0, width: 23.0, depth: 13.5, height: 6.4, tone: "concrete_cool" },
  { zoneId: "B4", x: 34.0, y: -32.0, width: 8.6, depth: 8.2, height: 33.0, tone: "glass_green" },
  { zoneId: "B4-A", x: 45.0, y: -38.0, width: 7.2, depth: 7.0, height: 15.0, tone: "stone" },

  // 外围高楼
  { zoneId: "B5", x: -78.0, y: 60.0, width: 15.0, depth: 11.0, height: 32.0, tone: "glass_blue" },
  { zoneId: "B6", x: -60.0, y: 76.0, width: 11.0, depth: 13.0, height: 27.0, tone: "concrete_cool" },
  { zoneId: "B7", x: -86.0, y: -58.0, width: 14.0, depth: 10.0, height: 25.0, tone: "concrete_warm" },
  { zoneId: "B8", x: -66.0, y: -76.0, width: 11.0, depth: 13.0, height: 29.0, tone: "glass_green" },
  { zoneId: "B9", x: 80.0, y: 60.0, width: 15.0, depth: 11.0, height: 31.0, tone: "glass_green" },
  { zoneId: "B10", x: 62.0, y: 76.0, width: 11.0, depth: 12.0, height: 26.0, tone: "concrete_cool" },
  { zoneId: "B11", x: 88.0, y: -58.0, width: 14.0, depth: 10.0, height: 26.0, tone: "concrete_warm" },
  { zoneId: "B12", x: 68.0, y: -76.0, width: 11.0, depth: 13.0, height: 28.0, tone: "glass_blue" },
  { zoneId: "B13", x: -96.0, y: 24.0, width: 17.0, depth: 14.0, height: 24.0, tone: "stone" },
  { zoneId: "B14", x: 96.0, y: -24.0, width: 17.0, depth: 14.0, height: 25.0, tone: "brick" },

  // 低矮建筑
  { zoneId: "L1", x: -54.0, y: 24.0, width: 10.0, depth: 8.0, height: 6.2, tone: "brick" },
  { zoneId: "L2", x: -44.0, y: 18.0, width: 9.0, depth: 7.0, height: 5.6, tone: "stone" },
  { zoneId: "L3", x: 54.0, y: 24.0, width: 10.0, depth: 8.0, height: 6.4, tone: "brick" },
  { zoneId: "L4", x: 62.0, y: 18.0, width: 8.0, depth: 7.0, height: 5.4, tone: "stone" },
  { zoneId: "L5", x: -56.0, y: -24.0, width: 10.0, depth: 8.0, height: 6.5, tone: "stone" },
  { zoneId: "L6", x: -46.0, y: -30.0, width: 8.0, depth: 7.0, height: 5.6, tone: "brick" },
  { zoneId: "L7", x: 54.0, y: -20.0, width: 10.0, depth: 8.0, height: 6.1, tone: "stone" },
  { zoneId: "L8", x: 62.0, y: -18.0, width: 8.0, depth: 7.0, height: 5.2, tone: "brick" },
  { zoneId: "L9", x: 22.0, y: 52.0, width: 10.0, depth: 8.0, height: 7.2, tone: "concrete_warm" },
  { zoneId: "L10", x: -22.0, y: -52.0, width: 10.0, depth: 8.0, height: 7.0, tone: "concrete_warm" },
];

const BUILDING_TONE_MAP: Record<string, FacadeTone> = Object.fromEntries(
  CITY_BUILDINGS.map((item) => [item.zoneId, item.tone])
);

const FACADE_CACHE = new Map<FacadeTone, THREE.CanvasTexture>();

function facadePalette(tone: FacadeTone): {
  base: string;
  frame: string;
  glass: string;
  glow: string;
} {
  switch (tone) {
    case "glass_blue":
      return {
        base: "#3e4f63",
        frame: "#2f3e4f",
        glass: "#1f3348",
        glow: "rgba(166, 210, 245, 0.35)",
      };
    case "glass_green":
      return {
        base: "#41544d",
        frame: "#32423c",
        glass: "#203a34",
        glow: "rgba(166, 226, 198, 0.33)",
      };
    case "concrete_warm":
      return {
        base: "#7a7268",
        frame: "#5f584f",
        glass: "#4a4743",
        glow: "rgba(233, 215, 186, 0.22)",
      };
    case "concrete_cool":
      return {
        base: "#6f7882",
        frame: "#56606a",
        glass: "#424b55",
        glow: "rgba(203, 215, 229, 0.24)",
      };
    case "brick":
      return {
        base: "#7f4d42",
        frame: "#653c33",
        glass: "#4f302a",
        glow: "rgba(242, 186, 163, 0.2)",
      };
    case "stone":
    default:
      return {
        base: "#7d817f",
        frame: "#636866",
        glass: "#4b4f4d",
        glow: "rgba(210, 217, 214, 0.2)",
      };
  }
}

function getFacadeTexture(tone: FacadeTone): THREE.CanvasTexture {
  const cached = FACADE_CACHE.get(tone);
  if (cached) return cached;

  const palette = facadePalette(tone);
  const canvas = document.createElement("canvas");
  canvas.width = 144;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    const texture = new THREE.CanvasTexture(canvas);
    FACADE_CACHE.set(tone, texture);
    return texture;
  }

  ctx.fillStyle = palette.base;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const cols = 6;
  const rows = 10;
  const cellW = canvas.width / cols;
  const cellH = canvas.height / rows;

  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const x = col * cellW;
      const y = row * cellH;
      ctx.fillStyle = palette.frame;
      ctx.fillRect(x + 1.2, y + 1.2, cellW - 2.4, cellH - 2.4);

      const lit = (row * 5 + col * 3) % 11 === 0 || (row + col) % 7 === 0;
      ctx.fillStyle = lit ? palette.glow : palette.glass;
      ctx.fillRect(x + 4.0, y + 4.0, cellW - 8.0, cellH - 8.0);
    }
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  FACADE_CACHE.set(tone, texture);
  return texture;
}

function addBuilding(parent: THREE.Object3D, spec: BuildingSpec): void {
  const geometry = new THREE.BoxGeometry(spec.width, spec.depth, spec.height);
  const baseTexture = getFacadeTexture(spec.tone);

  const facadeX = baseTexture.clone();
  facadeX.wrapS = THREE.RepeatWrapping;
  facadeX.wrapT = THREE.RepeatWrapping;
  facadeX.repeat.set(Math.max(1.0, spec.width / 3.2), Math.max(1.0, spec.height / 3.8));
  facadeX.needsUpdate = true;

  const facadeY = baseTexture.clone();
  facadeY.wrapS = THREE.RepeatWrapping;
  facadeY.wrapT = THREE.RepeatWrapping;
  facadeY.repeat.set(Math.max(1.0, spec.depth / 3.2), Math.max(1.0, spec.height / 3.8));
  facadeY.needsUpdate = true;

  const sideX = new THREE.MeshStandardMaterial({ map: facadeX, roughness: 0.84, metalness: 0.14 });
  const sideY = new THREE.MeshStandardMaterial({ map: facadeY, roughness: 0.84, metalness: 0.14 });
  const roof = new THREE.MeshStandardMaterial({ color: 0x7f858c, roughness: 0.92, metalness: 0.05 });
  const bottom = new THREE.MeshStandardMaterial({ color: 0x6d737b, roughness: 0.98, metalness: 0.0 });

  const scaledX = spec.x;
  const scaledY = spec.y;
  const mesh = new THREE.Mesh(geometry, [sideX, sideX, sideY, sideY, roof, bottom]);
  mesh.position.set(scaledX, scaledY, spec.height / 2);
  mesh.userData = { zoneId: spec.zoneId };
  parent.add(mesh);

  const edges = new THREE.EdgesGeometry(geometry);
  const edgeMesh = new THREE.LineSegments(
    edges,
    new THREE.LineBasicMaterial({ color: 0x394351, transparent: true, opacity: 0.34 })
  );
  edgeMesh.position.set(scaledX, scaledY, spec.height / 2);
  parent.add(edgeMesh);
}

function addRectPlane(
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

function addRoadMark(
  scene: THREE.Scene,
  x: number,
  y: number,
  length: number,
  width: number,
  horizontal: boolean,
  color: number
): void {
  const mark = new THREE.Mesh(
    new THREE.PlaneGeometry(horizontal ? length : width, horizontal ? width : length),
    new THREE.MeshBasicMaterial({ color })
  );
  mark.position.set(x, y, 0.05);
  scene.add(mark);
}

function addDashedRun(
  scene: THREE.Scene,
  horizontal: boolean,
  fixedValue: number,
  start: number,
  end: number,
  color = 0xf2f5f8
): void {
  const dashLen = 4.8;
  const gapLen = 4.2;
  const dir = end >= start ? 1 : -1;
  let cursor = start;

  while ((dir > 0 && cursor < end - 1e-6) || (dir < 0 && cursor > end + 1e-6)) {
    const rawNext = cursor + dir * dashLen;
    const next = dir > 0 ? Math.min(rawNext, end) : Math.max(rawNext, end);
    const len = Math.abs(next - cursor);
    if (len > 0.18) {
      const center = (cursor + next) * 0.5;
      const x = horizontal ? center : fixedValue;
      const y = horizontal ? fixedValue : center;
      addRoadMark(scene, x, y, len, 0.28, horizontal, color);
    }
    cursor = next + dir * gapLen;
  }
}

function addZebraCrosswalk(
  scene: THREE.Scene,
  centerX: number,
  centerY: number,
  horizontal: boolean
): void {
  const stripeCount = 14;
  const crossSpan = ROAD_HALF * 2 - 0.6; // nearly full road width
  const stripeBreadth = 0.54;
  const stripeLength = 4.8; // between stop line and intersection center
  const gap = (crossSpan - stripeCount * stripeBreadth) / (stripeCount - 1);

  for (let i = 0; i < stripeCount; i += 1) {
    const offset = -crossSpan / 2 + i * (stripeBreadth + gap) + stripeBreadth / 2;
    const stripe = new THREE.Mesh(
      new THREE.PlaneGeometry(
        horizontal ? stripeLength : stripeBreadth,
        horizontal ? stripeBreadth : stripeLength
      ),
      new THREE.MeshBasicMaterial({ color: 0xf2f4f6, transparent: true, opacity: 0.94 })
    );
    if (horizontal) {
      stripe.position.set(centerX, centerY + offset, 0.052);
    } else {
      stripe.position.set(centerX + offset, centerY, 0.052);
    }
    scene.add(stripe);
  }
}

function addDirectionArrow(
  scene: THREE.Scene,
  x: number,
  y: number,
  rotationZ: number,
  color = 0xe9edf2
): void {
  const shape = new THREE.Shape();
  // Lengthened straight-arrow geometry for clearer lane guidance.
  shape.moveTo(0.0, 1.9);
  shape.lineTo(1.05, 0.15);
  shape.lineTo(0.42, 0.15);
  shape.lineTo(0.42, -2.05);
  shape.lineTo(-0.42, -2.05);
  shape.lineTo(-0.42, 0.15);
  shape.lineTo(-1.05, 0.15);
  shape.lineTo(0.0, 1.9);

  const mesh = new THREE.Mesh(
    new THREE.ShapeGeometry(shape),
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.92,
      side: THREE.DoubleSide,
    })
  );
  mesh.position.set(x, y, 0.056);
  mesh.rotation.z = rotationZ;
  scene.add(mesh);
}

function addRoadNetwork(scene: THREE.Scene): void {
  addRectPlane(scene, ROAD_LENGTH, ROAD_LENGTH, 0xa8b0b9, -0.01);

  const asphaltMat = new THREE.MeshStandardMaterial({
    color: 0x4b5158,
    roughness: 0.98,
    metalness: 0.02,
  });
  const roadX = new THREE.Mesh(new THREE.PlaneGeometry(ROAD_LENGTH, ROAD_HALF * 2), asphaltMat);
  roadX.position.set(0, 0, 0.01);
  scene.add(roadX);

  const roadY = new THREE.Mesh(new THREE.PlaneGeometry(ROAD_HALF * 2, ROAD_LENGTH), asphaltMat);
  roadY.position.set(0, 0, 0.01);
  scene.add(roadY);

  // 路缘带（靠近路口区域留空，与停止线区域对齐）
  const curbColor = 0x808995;
  const curbWidth = 2.8;
  const curbOffset = ROAD_HALF + curbWidth / 2;
  const curbSegLen = ROAD_LENGTH / 2 - STOP_LINE_OFFSET;
  const curbSegCenter = ROAD_LENGTH / 4 + STOP_LINE_OFFSET / 2;

  addRectPlane(scene, curbSegLen, curbWidth, curbColor, 0.02).position.set(-curbSegCenter, curbOffset, 0.02);
  addRectPlane(scene, curbSegLen, curbWidth, curbColor, 0.02).position.set(curbSegCenter, curbOffset, 0.02);
  addRectPlane(scene, curbSegLen, curbWidth, curbColor, 0.02).position.set(-curbSegCenter, -curbOffset, 0.02);
  addRectPlane(scene, curbSegLen, curbWidth, curbColor, 0.02).position.set(curbSegCenter, -curbOffset, 0.02);

  addRectPlane(scene, curbWidth, curbSegLen, curbColor, 0.02).position.set(curbOffset, -curbSegCenter, 0.02);
  addRectPlane(scene, curbWidth, curbSegLen, curbColor, 0.02).position.set(curbOffset, curbSegCenter, 0.02);
  addRectPlane(scene, curbWidth, curbSegLen, curbColor, 0.02).position.set(-curbOffset, -curbSegCenter, 0.02);
  addRectPlane(scene, curbWidth, curbSegLen, curbColor, 0.02).position.set(-curbOffset, curbSegCenter, 0.02);

  // 路口四角 L 形连接，避免“凸起正方块”
  const cornerGap = STOP_LINE_OFFSET - ROAD_HALF;
  const cornerCenter = (STOP_LINE_OFFSET + ROAD_HALF) / 2;
  const lHX = cornerCenter;
  const lHY = curbOffset;
  const lVX = curbOffset;
  const lVY = cornerCenter;
  addRectPlane(scene, cornerGap, curbWidth, curbColor, 0.02).position.set(lHX, lHY, 0.02);
  addRectPlane(scene, cornerGap, curbWidth, curbColor, 0.02).position.set(-lHX, lHY, 0.02);
  addRectPlane(scene, cornerGap, curbWidth, curbColor, 0.02).position.set(lHX, -lHY, 0.02);
  addRectPlane(scene, cornerGap, curbWidth, curbColor, 0.02).position.set(-lHX, -lHY, 0.02);
  addRectPlane(scene, curbWidth, cornerGap, curbColor, 0.02).position.set(lVX, lVY, 0.02);
  addRectPlane(scene, curbWidth, cornerGap, curbColor, 0.02).position.set(-lVX, lVY, 0.02);
  addRectPlane(scene, curbWidth, cornerGap, curbColor, 0.02).position.set(lVX, -lVY, 0.02);
  addRectPlane(scene, curbWidth, cornerGap, curbColor, 0.02).position.set(-lVX, -lVY, 0.02);

  // 道路边缘白实线（简单增强）
  const edgeWhite = 0xebeff4;
  const edgeOffset = ROAD_HALF - 0.65;
  addRoadMark(scene, -curbSegCenter, edgeOffset, curbSegLen, 0.18, true, edgeWhite);
  addRoadMark(scene, curbSegCenter, edgeOffset, curbSegLen, 0.18, true, edgeWhite);
  addRoadMark(scene, -curbSegCenter, -edgeOffset, curbSegLen, 0.18, true, edgeWhite);
  addRoadMark(scene, curbSegCenter, -edgeOffset, curbSegLen, 0.18, true, edgeWhite);
  addRoadMark(scene, edgeOffset, -curbSegCenter, curbSegLen, 0.18, false, edgeWhite);
  addRoadMark(scene, edgeOffset, curbSegCenter, curbSegLen, 0.18, false, edgeWhite);
  addRoadMark(scene, -edgeOffset, -curbSegCenter, curbSegLen, 0.18, false, edgeWhite);
  addRoadMark(scene, -edgeOffset, curbSegCenter, curbSegLen, 0.18, false, edgeWhite);

  // 白色车道虚线：一路连接到停止线
  const roadFar = ROAD_LENGTH * 0.5 - 2.0;
  addDashedRun(scene, true, -LANE_CENTER_OFFSET, -roadFar, -STOP_LINE_OFFSET);
  addDashedRun(scene, true, -LANE_CENTER_OFFSET, STOP_LINE_OFFSET, roadFar);
  addDashedRun(scene, true, LANE_CENTER_OFFSET, -roadFar, -STOP_LINE_OFFSET);
  addDashedRun(scene, true, LANE_CENTER_OFFSET, STOP_LINE_OFFSET, roadFar);
  addDashedRun(scene, false, -LANE_CENTER_OFFSET, -roadFar, -STOP_LINE_OFFSET);
  addDashedRun(scene, false, -LANE_CENTER_OFFSET, STOP_LINE_OFFSET, roadFar);
  addDashedRun(scene, false, LANE_CENTER_OFFSET, -roadFar, -STOP_LINE_OFFSET);
  addDashedRun(scene, false, LANE_CENTER_OFFSET, STOP_LINE_OFFSET, roadFar);

  // 中央黄线：路口断开，仅在进出口路段保留
  const yellow = 0xf0c44a;
  const segLen = ROAD_LENGTH / 2 - STOP_LINE_OFFSET;
  const segCenter = ROAD_LENGTH / 4 + STOP_LINE_OFFSET / 2;
  addRoadMark(scene, -segCenter, 0, segLen, 0.3, true, yellow);
  addRoadMark(scene, segCenter, 0, segLen, 0.3, true, yellow);
  addRoadMark(scene, 0, -segCenter, segLen, 0.3, false, yellow);
  addRoadMark(scene, 0, segCenter, segLen, 0.3, false, yellow);

  // 停止线：与黄线尽头对齐，并与路口中心拉开距离
  const stopColor = 0xf6f7f9;
  const stopEdgeMargin = 0.55; // keep clear of curb-like sidewalk band
  const stopLineLen = ROAD_HALF - stopEdgeMargin; // inner end exactly reaches yellow centerline
  const stopCenter = stopLineLen * 0.5;
  // 北向来车（向南），右侧在西侧（x<0）
  addRoadMark(scene, -stopCenter, STOP_LINE_OFFSET, stopLineLen, 0.46, true, stopColor);
  // 南向来车（向北），右侧在东侧（x>0）
  addRoadMark(scene, stopCenter, -STOP_LINE_OFFSET, stopLineLen, 0.46, true, stopColor);
  // 东向来车（向西），右侧在北侧（y>0）
  addRoadMark(scene, STOP_LINE_OFFSET, stopCenter, stopLineLen, 0.46, false, stopColor);
  // 西向来车（向东），右侧在南侧（y<0）
  addRoadMark(scene, -STOP_LINE_OFFSET, -stopCenter, stopLineLen, 0.46, false, stopColor);

  // 斑马线：在停止线前方
  const zebraGapFromStop = 0.75;
  const zebraDepthHalf = 2.4; // matches stripeLength / 2 in addZebraCrosswalk
  const zebraOffset = STOP_LINE_OFFSET - zebraGapFromStop - zebraDepthHalf;
  addZebraCrosswalk(scene, 0, zebraOffset, false);
  addZebraCrosswalk(scene, 0, -zebraOffset, false);
  addZebraCrosswalk(scene, zebraOffset, 0, true);
  addZebraCrosswalk(scene, -zebraOffset, 0, true);

  // 简单道路细节增强：直行箭头
  const arrowDistance = STOP_LINE_OFFSET + 3.4;
  const arrowLaneOffset = ROAD_HALF * 0.25; // center of lane, avoid dashed divider at ROAD_HALF*0.5
  addDirectionArrow(scene, -arrowLaneOffset, arrowDistance, Math.PI);
  addDirectionArrow(scene, arrowLaneOffset, -arrowDistance, 0.0);
  addDirectionArrow(scene, arrowDistance, arrowLaneOffset, -Math.PI / 2);
  addDirectionArrow(scene, -arrowDistance, -arrowLaneOffset, Math.PI / 2);
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
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth: height,
    bevelEnabled: false,
    curveSegments: 1,
  });
  const mesh = new THREE.Mesh(
    geometry,
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

function createBuildingSpecFromZone(zone: RuntimeZone): BuildingSpec | null {
  const points = zone.points ?? [];
  if (zone.zone_kind !== "building" || zone.shape !== "polygon" || points.length < 3) {
    return null;
  }
  let minX = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  for (const [x, y] of points) {
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  }
  if (!Number.isFinite(minX) || !Number.isFinite(maxX) || !Number.isFinite(minY) || !Number.isFinite(maxY)) {
    return null;
  }
  const width = maxX - minX;
  const depth = maxY - minY;
  if (width < 0.1 || depth < 0.1) {
    return null;
  }
  const zoneId = zone.zone_id ?? "B-UNKNOWN";
  const tone = BUILDING_TONE_MAP[zoneId] ?? "concrete_cool";
  return {
    zoneId,
    x: (minX + maxX) / 2,
    y: (minY + maxY) / 2,
    width,
    depth,
    height: zone.height,
    tone,
  };
}

export class CitySceneLayers {
  private readonly buildingGroup = new THREE.Group();
  private readonly zoneGroup = new THREE.Group();
  private readonly draftGroup = new THREE.Group();
  private buildingFingerprint = "";

  constructor(private readonly scene: THREE.Scene) {
    addRoadNetwork(scene);
    scene.add(this.buildingGroup);
    scene.add(this.zoneGroup);
    scene.add(this.draftGroup);
  }

  updateZones(zones: RuntimeZones): void {
    const nextBuildingFingerprint = JSON.stringify(
      zones.buildings.map((item) => [item.zone_id, item.shape, item.points, item.height, item.base_z])
    );
    if (nextBuildingFingerprint !== this.buildingFingerprint) {
      clearGroup(this.buildingGroup);
      for (const zone of zones.buildings) {
        const spec = createBuildingSpecFromZone(zone);
        if (!spec) continue;
        addBuilding(this.buildingGroup, spec);
      }
      this.buildingFingerprint = nextBuildingFingerprint;
    }

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
    clearGroup(this.buildingGroup);
    clearGroup(this.zoneGroup);
    clearGroup(this.draftGroup);
    this.scene.remove(this.buildingGroup, this.zoneGroup, this.draftGroup);
  }
}
