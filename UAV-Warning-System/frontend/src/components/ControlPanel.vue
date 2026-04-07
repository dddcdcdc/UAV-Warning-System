<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { useSituationStore } from "../store/situation";

const store = useSituationStore();

const apiBase =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  `${window.location.protocol}//${window.location.hostname}:8000`;
const scenarioDescriptions = ref<Record<string, string>>({});
const switchingScenario = ref(false);
const showScenarioPanel = ref(true);

const scenarios = computed(() => Object.entries(scenarioDescriptions.value));
const canShowScenarioPanel = computed(
  () => showScenarioPanel.value && store.dataMode === "simulation"
);

function sceneAlias(name: string): string {
  const map: Record<string, string> = {
    safe_patrol: "安全巡航",
    crossing_conflict: "交汇冲突",
    building_conflict: "建筑冲突",
    restricted_zone_demo: "限飞区违规",
  };
  return map[name] ?? name;
}

function statusText(status: string): string {
  if (status === "RED") return "红色";
  if (status === "YELLOW") return "黄色";
  return "绿色";
}

function rowClassName(params: { row: { status: string } }): string {
  const status = params.row.status;
  if (status === "RED") return "row-red";
  if (status === "YELLOW") return "row-yellow";
  return "row-green";
}

async function loadScenarios(): Promise<void> {
  try {
    const res = await fetch(`${apiBase}/api/scenarios`);
    const data = (await res.json()) as { items: Record<string, string> };
    scenarioDescriptions.value = data.items;
  } catch {
    scenarioDescriptions.value = {};
  }
}

async function switchScenario(name: string): Promise<void> {
  switchingScenario.value = true;
  try {
    await fetch(`${apiBase}/api/scenario/${name}`, { method: "POST" });
  } finally {
    switchingScenario.value = false;
  }
}

async function pauseSystem(): Promise<void> {
  await fetch(`${apiBase}/api/control/pause`, { method: "POST" });
}

async function resumeSystem(): Promise<void> {
  await fetch(`${apiBase}/api/control/resume`, { method: "POST" });
}

function toggleScenarioPanel(): void {
  showScenarioPanel.value = !showScenarioPanel.value;
}

onMounted(() => {
  void loadScenarios();
});
</script>

<template>
  <section class="panel card control-panel">
    <header class="panel-header">
      <h1>飞中态势监控台</h1>
      <div class="conn-status" :class="{ online: store.connected }">
        <span class="dot"></span>
        <span>{{ store.connected ? "连接正常" : "连接断开" }}</span>
      </div>
    </header>

    <div class="quick-stats">
      <div class="stat-item">
        <label>总数</label>
        <strong>{{ store.stats.total }}</strong>
      </div>
      <div class="stat-item green">
        <label>绿色</label>
        <strong>{{ store.stats.green }}</strong>
      </div>
      <div class="stat-item yellow">
        <label>黄色</label>
        <strong>{{ store.stats.yellow }}</strong>
      </div>
      <div class="stat-item red">
        <label>红色</label>
        <strong>{{ store.stats.red }}</strong>
      </div>
    </div>

    <div class="ops-line">
      <el-button size="small" type="warning" plain @click="pauseSystem">暂停系统</el-button>
      <el-button size="small" type="success" plain @click="resumeSystem">恢复系统</el-button>
      <el-button size="small" plain @click="toggleScenarioPanel">
        {{ showScenarioPanel ? "隐藏演示按钮" : "显示演示按钮" }}
      </el-button>
    </div>

    <div class="scenario-list" v-if="canShowScenarioPanel">
      <div class="scenario-grid">
        <el-button
          v-for="[name] in scenarios"
          :key="name"
          size="small"
          :type="name === store.scenario ? 'primary' : 'default'"
          plain
          :loading="switchingScenario"
          @click="switchScenario(name)"
        >
          {{ sceneAlias(name) }}
        </el-button>
      </div>
      <p class="scenario-desc" v-if="store.scenario && scenarioDescriptions[store.scenario]">
        {{ scenarioDescriptions[store.scenario] }}
      </p>
    </div>

    <el-table
      :data="store.sortedDrones"
      size="small"
      :row-class-name="rowClassName"
      height="calc(100vh - 380px)"
      empty-text="等待无人机实时态势数据..."
    >
      <el-table-column prop="id" label="编号" min-width="102" />
      <el-table-column prop="type" label="类型" min-width="100" />
      <el-table-column label="状态" min-width="84">
        <template #default="{ row }">
          {{ statusText(row.status) }}
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>
