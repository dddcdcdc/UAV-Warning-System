<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, onUnmounted, ref, watch } from "vue";

import ControlPanel from "./components/ControlPanel.vue";
import WarningAlert from "./components/WarningAlert.vue";
import { useSituationStore } from "./store/situation";
import { CitySceneLayers } from "./three/Buildings";
import { DroneManager } from "./three/DroneManager";
import { SceneInit } from "./three/SceneInit";

type DrawMode = "none" | "no_fly" | "restricted";

const apiBase =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  `${window.location.protocol}//${window.location.hostname}:8000`;

const sceneHost = ref<HTMLDivElement | null>(null);
const store = useSituationStore();

const drawMode = ref<DrawMode>("none");
const noFlyDraft = ref<[number, number][]>([]);
const restrictedDraft = ref<[number, number][]>([]);
const submittingNoFly = ref(false);
const submittingRestricted = ref(false);
const resettingNoFly = ref(false);
const resettingRestricted = ref(false);

let scene: SceneInit | null = null;
let cityLayers: CitySceneLayers | null = null;
let drones: DroneManager | null = null;
let animationId = 0;
let zoneFingerprint = "";

function frameLoop(): void {
  drones?.animate(0.24);
  scene?.render();
  animationId = window.requestAnimationFrame(frameLoop);
}

function handleGroundClick(point: { x: number; y: number }): void {
  if (drawMode.value === "no_fly") {
    noFlyDraft.value = [...noFlyDraft.value, [point.x, point.y]];
    return;
  }
  if (drawMode.value === "restricted") {
    restrictedDraft.value = [...restrictedDraft.value, [point.x, point.y]];
  }
}

function toggleNoFlyDrawing(): void {
  drawMode.value = drawMode.value === "no_fly" ? "none" : "no_fly";
}

function toggleRestrictedDrawing(): void {
  drawMode.value = drawMode.value === "restricted" ? "none" : "restricted";
}

function undoNoFlyPoint(): void {
  noFlyDraft.value = noFlyDraft.value.slice(0, -1);
}

function undoRestrictedPoint(): void {
  restrictedDraft.value = restrictedDraft.value.slice(0, -1);
}

function clearNoFlyDraft(): void {
  noFlyDraft.value = [];
}

function clearRestrictedDraft(): void {
  restrictedDraft.value = [];
}

async function submitNoFlyPolygon(): Promise<void> {
  if (noFlyDraft.value.length < 3) {
    ElMessage.warning("禁飞区至少需要 3 个点。");
    return;
  }
  submittingNoFly.value = true;
  try {
    const res = await fetch(`${apiBase}/api/zones/no-fly/polygon`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        points: noFlyDraft.value,
        height: 50,
        base_z: 0,
      }),
    });
    if (!res.ok) {
      throw new Error(await res.text());
    }
    ElMessage.success("禁飞区已提交并生效。");
    drawMode.value = "none";
    noFlyDraft.value = [];
  } catch {
    ElMessage.error("禁飞区提交失败，请稍后重试。");
  } finally {
    submittingNoFly.value = false;
  }
}

async function submitRestrictedPolygon(): Promise<void> {
  if (restrictedDraft.value.length < 3) {
    ElMessage.warning("限飞区至少需要 3 个点。");
    return;
  }
  submittingRestricted.value = true;
  try {
    const res = await fetch(`${apiBase}/api/zones/restricted/polygon`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        points: restrictedDraft.value,
        height: 50,
        base_z: 0,
      }),
    });
    if (!res.ok) {
      throw new Error(await res.text());
    }
    ElMessage.success("限飞区已提交并生效。");
    drawMode.value = "none";
    restrictedDraft.value = [];
  } catch {
    ElMessage.error("限飞区提交失败，请稍后重试。");
  } finally {
    submittingRestricted.value = false;
  }
}

async function resetNoFlyZones(): Promise<void> {
  resettingNoFly.value = true;
  try {
    const res = await fetch(`${apiBase}/api/zones/no-fly/reset`, { method: "POST" });
    if (!res.ok) {
      throw new Error(await res.text());
    }
    ElMessage.success("禁飞区已恢复默认设置。");
    if (drawMode.value === "no_fly") {
      drawMode.value = "none";
    }
    noFlyDraft.value = [];
  } catch {
    ElMessage.error("禁飞区恢复失败，请检查后端连接。");
  } finally {
    resettingNoFly.value = false;
  }
}

async function resetRestrictedZones(): Promise<void> {
  resettingRestricted.value = true;
  try {
    const res = await fetch(`${apiBase}/api/zones/restricted/reset`, { method: "POST" });
    if (!res.ok) {
      throw new Error(await res.text());
    }
    ElMessage.success("限飞区已恢复默认设置。");
    if (drawMode.value === "restricted") {
      drawMode.value = "none";
    }
    restrictedDraft.value = [];
  } catch {
    ElMessage.error("限飞区恢复失败，请检查后端连接。");
  } finally {
    resettingRestricted.value = false;
  }
}

watch(
  () => [noFlyDraft.value, restrictedDraft.value, drawMode.value],
  () => {
    const activeDraft =
      drawMode.value === "no_fly"
        ? noFlyDraft.value
        : drawMode.value === "restricted"
          ? restrictedDraft.value
          : [];
    cityLayers?.setDraftPolygon(activeDraft);
  },
  { deep: true }
);

watch(
  () => drawMode.value,
  (mode) => {
    scene?.setNavigationEnabled(mode === "none");
  }
);

watch(
  () => store.lastSeq,
  () => {
    drones?.sync(store.drones);
    const nextZoneFingerprint = JSON.stringify(store.zones);
    if (nextZoneFingerprint !== zoneFingerprint) {
      cityLayers?.updateZones(store.zones);
      zoneFingerprint = nextZoneFingerprint;
    }
  }
);

onMounted(() => {
  store.connect();
  if (!sceneHost.value) return;

  scene = new SceneInit(sceneHost.value);
  scene.setGroundClickHandler(handleGroundClick);
  cityLayers = new CitySceneLayers(scene.scene);
  drones = new DroneManager(scene.scene);
  frameLoop();
});

onUnmounted(() => {
  window.cancelAnimationFrame(animationId);
  store.disconnect();
  drones?.dispose();
  cityLayers?.dispose();
  scene?.dispose();
});
</script>

<template>
  <div class="app-shell">
    <aside class="left-panel">
      <ControlPanel />
    </aside>
    <main class="radar-panel">
      <div ref="sceneHost" class="scene-host"></div>

      <div class="zone-editor-row">
        <div class="zone-editor-box">
          <h3>禁飞区划定模块</h3>
          <p>点击地面逐点采样，至少 3 点形成禁飞区多边形。</p>
          <div class="zone-buttons">
            <el-button
              size="small"
              :type="drawMode === 'no_fly' ? 'warning' : 'danger'"
              @click="toggleNoFlyDrawing"
            >
              {{ drawMode === "no_fly" ? "结束绘制" : "开始绘制" }}
            </el-button>
            <el-button size="small" @click="undoNoFlyPoint" :disabled="noFlyDraft.length === 0">
              撤销一点
            </el-button>
            <el-button size="small" @click="clearNoFlyDraft" :disabled="noFlyDraft.length === 0">
              清空草稿
            </el-button>
            <el-button
              size="small"
              type="danger"
              :loading="submittingNoFly"
              :disabled="noFlyDraft.length < 3"
              @click="submitNoFlyPolygon"
            >
              确认禁飞区
            </el-button>
            <el-button
              size="small"
              type="info"
              plain
              :loading="resettingNoFly"
              @click="resetNoFlyZones"
            >
              恢复默认区域
            </el-button>
          </div>
          <div class="point-hint">
            当前草稿点数：<strong>{{ noFlyDraft.length }}</strong>
          </div>
        </div>

        <div class="zone-editor-box">
          <h3>限飞区划定模块</h3>
          <p>点击地面逐点采样，至少 3 点形成限飞区多边形。</p>
          <div class="zone-buttons">
            <el-button
              size="small"
              :type="drawMode === 'restricted' ? 'warning' : 'primary'"
              @click="toggleRestrictedDrawing"
            >
              {{ drawMode === "restricted" ? "结束绘制" : "开始绘制" }}
            </el-button>
            <el-button
              size="small"
              @click="undoRestrictedPoint"
              :disabled="restrictedDraft.length === 0"
            >
              撤销一点
            </el-button>
            <el-button
              size="small"
              @click="clearRestrictedDraft"
              :disabled="restrictedDraft.length === 0"
            >
              清空草稿
            </el-button>
            <el-button
              size="small"
              type="primary"
              :loading="submittingRestricted"
              :disabled="restrictedDraft.length < 3"
              @click="submitRestrictedPolygon"
            >
              确认限飞区
            </el-button>
            <el-button
              size="small"
              type="info"
              plain
              :loading="resettingRestricted"
              @click="resetRestrictedZones"
            >
              恢复默认区域
            </el-button>
          </div>
          <div class="point-hint">
            当前草稿点数：<strong>{{ restrictedDraft.length }}</strong>
          </div>
        </div>
      </div>

    </main>
    <section class="right-panel">
      <WarningAlert />
    </section>
  </div>
</template>
