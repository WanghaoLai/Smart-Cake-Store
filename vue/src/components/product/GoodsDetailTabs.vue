<template>
  <section class="detail-tabs card">
    <!-- 分区导航：页面锁定一屏、上半区固定，仅此容器内的内容随切换变化 -->
    <div class="tabs-nav">
      <button
        v-for="t in tabs" :key="t.key"
        class="tab-btn" :class="{ active: active === t.key }"
        @click="active = t.key">
        <el-icon><component :is="t.icon" /></el-icon>
        <span>{{ t.label }}</span>
        <span v-if="t.key === 'reviews' && reviewTotal" class="tab-badge">{{ reviewTotal }}</span>
      </button>
    </div>

    <div class="tab-body">
      <!-- 不用 out-in：过渡被打断（快速连续切换）时新旧分区会短暂共存导致内容重叠。
           改为离开瞬时移除 + 新内容短淡入，任意时刻 DOM 中只有一个分区 -->
      <Transition name="fade">
        <div :key="active" class="tab-pane">
          <GoodsIntro v-if="active === 'intro'" :goods="goods" />
          <GoodsSpecs v-else-if="active === 'specs'" :goods="goods" />
          <GoodsTips v-else-if="active === 'tips'" :goods="goods" />
          <ProductReviews
            v-else-if="active === 'reviews'"
            :goods-id="goods.id"
            @loaded="total => reviewTotal = total"
          />
          <GoodsAIQa v-else-if="active === 'qa'" :goods="goods" />
        </div>
      </Transition>
    </div>
  </section>
</template>

<script setup>
import { markRaw, ref } from 'vue'
import { Document, InfoFilled, Warning, ChatLineSquare, MagicStick } from '@element-plus/icons-vue'
import GoodsIntro from './GoodsIntro.vue'
import GoodsSpecs from './GoodsSpecs.vue'
import GoodsTips from './GoodsTips.vue'
import ProductReviews from './ProductReviews.vue'
import GoodsAIQa from './GoodsAIQa.vue'

defineProps({ goods: { type: Object, default: () => ({}) } })

const tabs = [
  { key: 'intro', label: '商品详情', icon: markRaw(Document) },
  { key: 'specs', label: '规格参数', icon: markRaw(InfoFilled) },
  { key: 'tips', label: '温馨提示', icon: markRaw(Warning) },
  { key: 'reviews', label: '用户评价', icon: markRaw(ChatLineSquare) },
  { key: 'qa', label: 'AI 问答', icon: markRaw(MagicStick) },
]

const active = ref('intro')
const reviewTotal = ref(0)
</script>

<style scoped>
/* 撑满页面剩余高度：页面自身不滚动，分区内容在本容器内滚 */
.detail-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 14px 18px;
}

.tabs-nav {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--c-divider);
  flex-shrink: 0;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--r-pill);
  background: var(--c-bg-soft);
  color: var(--c-text-regular);
  border: 1.5px solid transparent;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all var(--t-fast) var(--ease-out);
}

.tab-btn .el-icon { font-size: 16px; }

.tab-btn:hover {
  background: var(--c-primary-soft);
  color: var(--c-primary);
}

.tab-btn.active {
  background: var(--c-primary-soft);
  color: var(--c-primary);
  border-color: var(--c-primary);
  font-weight: 600;
}

.tab-badge {
  font-size: 11px;
  font-weight: 600;
  background: var(--c-primary-bg);
  color: var(--c-primary);
  padding: 0 8px;
  border-radius: var(--r-pill);
  line-height: 18px;
}

/* 覆盖全局 fade：离开的分区瞬时移除（不留过渡），杜绝新旧内容共存 */
.fade-leave-active { transition: none; }
.fade-enter-active { transition: opacity 0.18s var(--ease-out); }
.fade-enter-from { opacity: 0; }
.fade-leave-to { opacity: 0; }

/* 分区内容的独立滚动容器：页面高度锁定，长内容在此内部滚动 */
.tab-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-top: 12px;
}

/* 窄屏单列布局：上部内容可能超一屏，放弃锁定模型，恢复页面级滚动 */
@media (max-width: 960px) {
  .detail-tabs { flex: none; }
  .tab-body { overflow: visible; }
  .tab-pane { min-height: 50vh; }
  .tab-btn { padding: 6px 12px; font-size: 12px; }
}
</style>
