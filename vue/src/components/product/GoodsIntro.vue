<template>
  <div class="intro-section">
    <div class="detail-text" v-if="goods.detail">
      <p v-for="(line, idx) in goods.detail.split('\n')" :key="idx">{{ line }}</p>
    </div>
    <div v-else class="empty-block">暂无详细介绍</div>

    <div class="ingredients" v-if="goods.ingredients">
      <div class="ing-head">
        <span class="ing-title"><el-icon><Warning /></el-icon>配料表 · 过敏原提示</span>
        <span class="ing-tag">请过敏体质仔细查阅</span>
      </div>
      <div class="ing-text">{{ goods.ingredients }}</div>
    </div>
  </div>
</template>

<script setup>
import { Warning } from '@element-plus/icons-vue'

defineProps({ goods: { type: Object, default: () => ({}) } })
</script>

<style scoped>
.detail-text {
  font-size: 14px;
  line-height: 1.85;
  color: var(--c-text-regular);
  white-space: pre-wrap;
}

.detail-text p { margin: 0 0 8px; }

.empty-block {
  font-size: 13px;
  color: var(--c-text-secondary);
  padding: 16px 0;
  text-align: center;
}

.ingredients {
  margin-top: 18px;
  padding: 16px 18px;
  background: var(--c-warning-soft);
  border-radius: var(--r-md);
}

.ing-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.ing-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
}

.ing-title .el-icon { color: var(--c-warning); }

.ing-tag {
  font-size: 11px;
  color: var(--c-warning);
  background: rgba(255, 255, 255, 0.7);
  padding: 2px 10px;
  border-radius: var(--r-pill);
  font-weight: 600;
}

.ing-text {
  font-size: 13px;
  line-height: 1.8;
  color: var(--c-text-regular);
}
</style>
