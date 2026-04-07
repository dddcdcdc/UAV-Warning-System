<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

import { useSituationStore } from "../store/situation";

const store = useSituationStore();
const nowTs = ref(Date.now() / 1000);
const viewportHeight = ref(window.innerHeight);
let timer = 0;

const maxCards = computed(() => {
  if (viewportHeight.value >= 1100) return 8;
  if (viewportHeight.value >= 900) return 6;
  if (viewportHeight.value >= 760) return 5;
  return 4;
});

const buildingCriticalCards = computed(() => {
  const items = store.alerts.filter(
    (item) =>
      item.status === "RED" &&
      (item.category === "building_collision" || item.message.includes("建筑碰撞"))
  );
  return items.slice(-maxCards.value).reverse();
});

const redCards = computed(() => {
  const items = store.redAlerts.filter(
    (item) => !buildingCriticalCards.value.some((critical) => critical.at === item.at && critical.id === item.id)
  );
  return items.slice(0, maxCards.value);
});

const yellowCards = computed(() => store.yellowAlerts.slice(0, maxCards.value));
const activeCritical = computed(() => buildingCriticalCards.value[0]);
const showCriticalOverlay = computed(() => {
  if (!activeCritical.value) return false;
  return nowTs.value - activeCritical.value.at <= 7;
});

function handleResize(): void {
  viewportHeight.value = window.innerHeight;
}

onMounted(() => {
  timer = window.setInterval(() => {
    nowTs.value = Date.now() / 1000;
  }, 350);
  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  window.clearInterval(timer);
  window.removeEventListener("resize", handleResize);
});
</script>

<template>
  <section class="panel card warning-center">
    <header class="panel-header">
      <h2>战术告警中心</h2>
    </header>

    <div class="warning-layout">
      <div class="warning-block high">
        <h3>建筑碰撞高危</h3>
        <div class="warning-list" v-if="buildingCriticalCards.length > 0">
          <article class="warning-card red critical" v-for="item in buildingCriticalCards" :key="`${item.id}-${item.at}`">
            <div class="warning-title">{{ item.id }} / 建筑碰撞警报</div>
            <p>{{ item.message }}</p>
          </article>
        </div>
        <p class="empty" v-else>当前暂无建筑碰撞高危警报。</p>
      </div>

      <div class="warning-block">
        <h3>红色警报</h3>
        <div class="warning-list" v-if="redCards.length > 0">
          <article class="warning-card red" v-for="item in redCards" :key="`${item.id}-${item.at}`">
            <div class="warning-title">{{ item.id }} / 红色警报</div>
            <p>{{ item.message }}</p>
          </article>
        </div>
        <p class="empty" v-else>当前暂无红色警报。</p>
      </div>

      <div class="warning-block">
        <h3>黄色预警</h3>
        <div class="warning-list" v-if="yellowCards.length > 0">
          <article class="warning-card yellow" v-for="item in yellowCards" :key="`${item.id}-${item.at}`">
            <div class="warning-title">{{ item.id }} / 黄色预警</div>
            <p>{{ item.message }}</p>
          </article>
        </div>
        <p class="empty" v-else>当前暂无黄色预警。</p>
      </div>
    </div>

    <transition name="danger-pop">
      <div class="danger-overlay" v-if="showCriticalOverlay && activeCritical">
        <div class="danger-box">
          <div class="danger-label">建筑碰撞紧急警报</div>
          <div class="danger-id">{{ activeCritical.id }}</div>
          <p>{{ activeCritical.message }}</p>
        </div>
      </div>
    </transition>
  </section>
</template>
