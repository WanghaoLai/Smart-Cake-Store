<template>
  <div class="home-page">
    <!-- 欢迎横幅 -->
    <section class="hero-banner">
      <div class="hero-bg-deco deco-1"></div>
      <div class="hero-bg-deco deco-2"></div>
      <div class="hero-bg-deco deco-3"></div>
      <div class="hero-content">
        <div class="hero-greeting">
          <span class="hello-badge">
            <el-icon><Sunny /></el-icon>
            {{ greeting }}
          </span>
          <h2 class="hello-title">
            {{ data.user.name || '朋友' }}，<br/>欢迎回到 <span class="text-gradient">甜心烘焙</span>
          </h2>
          <p class="hello-desc">{{ data.user.role === '管理员' ? '今日运营数据一览，一切尽在掌握' : '挑选一款蛋糕，开启今天的甜蜜时刻' }}</p>
          <div class="hero-cta" v-if="data.user.role === '用户'">
            <el-button type="primary" size="large" round @click="$router.push('/manager/cake')">
              <el-icon style="margin-right: 4px"><Goods /></el-icon>立即选购
            </el-button>
            <el-button size="large" round @click="$router.push('/manager/favorite')">
              <el-icon style="margin-right: 4px"><Star /></el-icon>我的收藏
            </el-button>
          </div>
        </div>
      </div>
    </section>

    <!-- 数据卡片 -->
    <section class="stat-grid">
      <div v-for="c in data.stats.cards" :key="c.key" class="stat-card" :class="`stat-${c.color}`">
        <div class="stat-icon">
          <el-icon><component :is="iconComp(c.icon)" /></el-icon>
        </div>
        <div class="stat-meta">
          <div class="stat-label">{{ c.label }}</div>
          <div class="stat-value">
            <span v-if="c.prefix" class="stat-prefix">{{ c.prefix }}</span>
            <span class="stat-num">{{ c.value }}</span>
            <span v-if="c.suffix" class="stat-suffix">{{ c.suffix }}</span>
          </div>
        </div>
      </div>
    </section>

    <div class="grid-2col">
      <!-- 公告区 -->
      <section class="card notice-card">
        <div class="card-head">
          <h3 class="card-title">
            <el-icon><Bell /></el-icon>系统公告
          </h3>
          <span class="card-sub">最新动态</span>
        </div>
        <div class="notice-list" v-if="data.stats.notices?.length">
          <div v-for="(n, i) in data.stats.notices" :key="n.id" class="notice-item">
            <div class="notice-dot" :class="{ first: i === 0 }"></div>
            <div class="notice-body">
              <div class="notice-title">{{ n.name }}</div>
              <div class="notice-content line2">{{ n.content }}</div>
              <div class="notice-time">{{ n.time }}</div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">暂无公告</div>
      </section>

      <!-- 推荐位 / 最近订单 -->
      <section class="card side-card">
        <!-- 用户：精选推荐 -->
        <template v-if="data.user.role === '用户'">
          <div class="card-head">
            <h3 class="card-title">
              <el-icon><MagicStick /></el-icon>为您推荐
            </h3>
            <a class="card-link" @click="$router.push('/manager/cake')">查看更多 →</a>
          </div>
          <div class="recommend-grid">
            <div v-for="r in data.stats.recommends" :key="r.id" class="recommend-item" @click="goCake(r)">
              <div class="recommend-img">
                <img :src="r.img" :alt="r.name" />
                <div class="recommend-tag" v-if="r.categoryName">{{ r.categoryName }}</div>
              </div>
              <div class="recommend-name line1">{{ r.name }}</div>
              <div class="recommend-price">￥{{ r.price }}<span class="recommend-unit">/{{ r.unit }}</span></div>
            </div>
          </div>
        </template>

        <!-- 管理员：最近订单 -->
        <template v-else>
          <div class="card-head">
            <h3 class="card-title">
              <el-icon><List /></el-icon>最近订单
            </h3>
            <a class="card-link" @click="$router.push('/manager/orders')">查看全部 →</a>
          </div>
          <div class="recent-order-list">
            <div v-for="o in data.stats.recentOrders" :key="o.id" class="recent-order">
              <img v-if="o.goodsImg" :src="o.goodsImg" class="recent-img" />
              <div v-else class="recent-img placeholder"><el-icon><Picture /></el-icon></div>
              <div class="recent-main">
                <div class="recent-name line1">{{ o.goodsName }}</div>
                <div class="recent-meta">
                  <span>{{ o.user }}</span> · <span>{{ o.num }} 件</span> · <span class="recent-no">{{ o.order_no }}</span>
                </div>
              </div>
              <div class="recent-time">{{ o.time }}</div>
            </div>
            <div v-if="!data.stats.recentOrders?.length" class="empty-state">暂无订单</div>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted, markRaw } from "vue";
import { useRouter } from "vue-router";
import request from "@/utils/request";
import { ElMessage } from "element-plus";
import {
  Sunny, Goods, Star, Bell, MagicStick, List, Picture,
  Money, SoldOut, WarningFilled, Timer,
} from "@element-plus/icons-vue";

const router = useRouter()

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  stats: { cards: [], notices: [], recommends: [], recentOrders: [] },
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 11) return '早上好'
  if (h < 13) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const iconMap = {
  Goods: markRaw(Goods),
  SoldOut: markRaw(SoldOut),
  Money: markRaw(Money),
  WarningFilled: markRaw(WarningFilled),
  Star: markRaw(Star),
  Timer: markRaw(Timer),
}
const iconComp = (key) => iconMap[key] || Goods

const loadStats = () => {
  request.get('/stats/home').then(res => {
    if (res.code === '200') {
      data.stats = res.data || {}
    }
  }).catch(() => {
    // 接口未就绪时静默处理
  })
}

const goCake = (r) => {
  if (r.categoryName) {
    router.push({ path: '/manager/cake', query: { categoryName: r.categoryName } })
  } else {
    router.push('/manager/cake')
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.home-page {
  padding: 20px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* —— 欢迎横幅 —— */
.hero-banner {
  position: relative;
  overflow: hidden;
  border-radius: var(--r-xl);
  padding: 36px 40px;
  background: linear-gradient(135deg, #fdf6e0 0%, #f5ecc8 50%, #e6c558 100%);
  box-shadow: 0 8px 28px rgba(184, 148, 31, 0.15);
}

.hero-bg-deco {
  position: absolute;
  border-radius: 50%;
  filter: blur(2px);
  opacity: 0.4;
}

.deco-1 { width: 220px; height: 220px; background: #ffffff; top: -60px; right: 5%; opacity: 0.55; }
.deco-2 { width: 140px; height: 140px; background: #d4af37; bottom: -40px; right: 22%; opacity: 0.25; }
.deco-3 { width: 100px; height: 100px; background: #ffffff; bottom: 12%; right: -20px; opacity: 0.6; }

.hero-content { position: relative; z-index: 2; }

.hello-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(8px);
  border-radius: var(--r-pill);
  color: var(--c-primary);
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 14px;
}

.hello-title {
  font-size: 30px;
  font-weight: 700;
  line-height: 1.25;
  margin: 0 0 10px;
  color: var(--c-text-primary);
}

.hello-desc {
  font-size: 15px;
  color: var(--c-text-secondary);
  margin: 0 0 20px;
}

.hero-cta {
  display: flex;
  gap: 12px;
}

.hero-cta .el-button--primary {
  background: linear-gradient(135deg, #b8941f 0%, #d4af37 100%);
  border: none;
  box-shadow: 0 6px 18px rgba(184, 148, 31, 0.32);
}

.hero-cta .el-button:not(.el-button--primary) {
  background: var(--c-bg-card);
  border: none;
  color: var(--c-text-primary);
  box-shadow: var(--shadow-sm);
}

/* —— 数据卡片 —— */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: var(--c-bg-card);
  border-radius: var(--r-lg);
  padding: 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: none;
  box-shadow: var(--shadow-card);
  transition: all var(--t-base) var(--ease-out);
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0;
  width: 4px; height: 100%;
  background: var(--c-primary);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stat-primary::before { background: var(--grad-primary); }
.stat-accent::before { background: var(--grad-warm); }
.stat-success::before { background: linear-gradient(135deg, #95b86a, #6b9b37); }
.stat-warning::before { background: linear-gradient(135deg, #e6c558, #d4af37); }

.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.stat-primary .stat-icon { background: var(--c-primary-soft); color: var(--c-primary); }
.stat-accent .stat-icon { background: var(--c-accent-soft); color: var(--c-accent); }
.stat-success .stat-icon { background: var(--c-success-soft); color: var(--c-success); }
.stat-warning .stat-icon { background: var(--c-warning-soft); color: var(--c-warning); }

.stat-meta { flex: 1; min-width: 0; }

.stat-label {
  font-size: 13px;
  color: var(--c-text-secondary);
  margin-bottom: 6px;
}

.stat-value {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.stat-num {
  font-size: 24px;
  font-weight: 700;
  color: var(--c-text-primary);
  line-height: 1;
  font-feature-settings: "tnum";
}

.stat-prefix, .stat-suffix {
  font-size: 14px;
  color: var(--c-text-secondary);
  font-weight: 500;
}

/* —— 两列区 —— */
.grid-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.card {
  padding: 20px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title .el-icon { color: var(--c-primary); }

.card-sub {
  font-size: 12px;
  color: var(--c-text-secondary);
  padding: 2px 8px;
  background: var(--c-bg-soft);
  border-radius: var(--r-pill);
}

.card-link {
  font-size: 13px;
  color: var(--c-primary);
  cursor: pointer;
  font-weight: 500;
}

/* —— 公告 —— */
.notice-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.notice-item {
  display: flex;
  gap: 12px;
  padding: 10px;
  border-radius: var(--r-md);
  transition: background var(--t-fast) var(--ease-out);
}

.notice-item:hover { background: var(--c-bg-soft); }

.notice-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--c-border);
  margin-top: 6px;
  flex-shrink: 0;
}

.notice-dot.first { background: var(--c-primary); box-shadow: 0 0 0 4px var(--c-primary-soft); }

.notice-body { flex: 1; min-width: 0; }

.notice-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin-bottom: 4px;
}

.notice-content {
  font-size: 13px;
  color: var(--c-text-regular);
  line-height: 1.5;
  margin-bottom: 4px;
}

.notice-time {
  font-size: 12px;
  color: var(--c-text-secondary);
}

/* —— 推荐 —— */
.recommend-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.recommend-item {
  cursor: pointer;
  border-radius: var(--r-md);
  overflow: hidden;
  border: none;
  background: var(--c-bg-card);
  box-shadow: var(--shadow-sm);
  transition: all var(--t-fast) var(--ease-out);
}

.recommend-item:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-hover);
}

.recommend-img {
  position: relative;
  width: 100%;
  height: 110px;
  overflow: hidden;
}

.recommend-img img {
  width: 100%; height: 100%;
  object-fit: cover;
  transition: transform var(--t-base) var(--ease-out);
}

.recommend-item:hover .recommend-img img { transform: scale(1.05); }

.recommend-tag {
  position: absolute;
  top: 8px; left: 8px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--c-primary);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--r-pill);
}

.recommend-name {
  padding: 8px 10px 2px;
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-primary);
}

.recommend-price {
  padding: 0 10px 10px;
  font-size: 14px;
  color: var(--c-primary);
  font-weight: 700;
}

.recommend-unit {
  font-size: 11px;
  color: var(--c-text-secondary);
  font-weight: 400;
  margin-left: 2px;
}

/* —— 最近订单 —— */
.recent-order-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recent-order {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  border-radius: var(--r-md);
  transition: background var(--t-fast) var(--ease-out);
}

.recent-order:hover { background: var(--c-bg-soft); }

.recent-img {
  width: 44px; height: 44px;
  border-radius: 8px;
  object-fit: cover;
}

.recent-img.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--c-bg-soft);
  color: var(--c-text-placeholder);
}

.recent-main { flex: 1; min-width: 0; }

.recent-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-primary);
}

.recent-meta {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin-top: 2px;
}

.recent-no {
  font-family: ui-monospace, "SFMono-Regular", monospace;
  font-size: 11px;
}

.recent-time {
  font-size: 12px;
  color: var(--c-text-secondary);
  flex-shrink: 0;
}

/* —— 响应式 —— */
@media (max-width: 1100px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .grid-2col { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .stat-grid { grid-template-columns: 1fr; }
  .hero-banner { padding: 24px; }
  .hello-title { font-size: 22px; }
}
</style>
