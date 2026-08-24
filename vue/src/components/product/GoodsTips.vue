<template>
  <div class="tips-grid">
    <div class="tip-item">
      <el-icon class="tip-icon"><Clock /></el-icon>
      <div class="tip-main">
        <div class="tip-title">提前预订</div>
        <div class="tip-desc">蛋糕现做现发,建议至少提前 24 小时下单,以确保新鲜制作。</div>
      </div>
    </div>
    <div class="tip-item">
      <el-icon class="tip-icon"><Timer /></el-icon>
      <div class="tip-main">
        <div class="tip-title">储存与保质期</div>
        <div class="tip-desc">
          {{ goods.shelf_life ? `本品保质期 ${goods.shelf_life}。` : '' }}收货后请冷藏 0-4℃ 保存,风味最佳。
        </div>
      </div>
    </div>
    <div class="tip-item warning">
      <el-icon class="tip-icon"><Warning /></el-icon>
      <div class="tip-main">
        <div class="tip-title">过敏原提醒</div>
        <div class="tip-desc">
          {{ goods.ingredients || '本品可能含有蛋、乳制品、麸质及坚果成分' }},过敏体质请谨慎选购。
        </div>
      </div>
    </div>
    <div class="tip-item">
      <el-icon class="tip-icon"><Service /></el-icon>
      <div class="tip-main">
        <div class="tip-title">配送与售后</div>
        <div class="tip-desc">全程冷链配送,签收后请及时冷藏;如遇质量问题,请第一时间联系客服处理。</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Clock, Timer, Warning, Service } from '@element-plus/icons-vue'

defineProps({ goods: { type: Object, default: () => ({}) } })
</script>

<style scoped>
.tips-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

@media (max-width: 720px) {
  .tips-grid { grid-template-columns: 1fr; }
}

.tip-item {
  display: flex;
  gap: 12px;
  padding: 16px 18px;
  background: var(--c-bg-soft);
  border-radius: var(--r-md);
  align-items: flex-start;
}

.tip-icon {
  width: 36px;
  height: 36px;
  background: var(--c-primary-soft);
  color: var(--c-primary);
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.tip-item.warning .tip-icon {
  background: var(--c-warning-soft);
  color: var(--c-warning);
}

.tip-main { flex: 1; min-width: 0; }

.tip-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
}

.tip-desc {
  font-size: 13px;
  line-height: 1.7;
  color: var(--c-text-secondary);
  margin-top: 4px;
}
</style>
