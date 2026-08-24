<template>
  <div class="app-shell">
    <!-- 顶部导航 -->
    <header class="app-header">
      <div class="header-inner">
        <div class="header-left">
          <button class="icon-btn" @click="data.collapsed = !data.collapsed" :title="data.collapsed ? '展开侧栏' : '收起侧栏'">
            <el-icon><Fold v-if="!data.collapsed" /><Expand v-else /></el-icon>
          </button>
          <div class="brand" @click="router.push('/manager/home')">
            <img src="@/assets/imgs/logo.png" alt="logo" class="brand-logo" />
            <div class="brand-text">
              <div class="brand-name">智能商城导购与运营平台</div>
              <div class="brand-tag">Smart Mall Guide &amp; Operations Platform</div>
            </div>
          </div>
        </div>

        <div class="header-center">
          <el-input
            v-model="data.search"
            placeholder="搜索蛋糕、口味或分类"
            :prefix-icon="Search"
            class="header-search"
            clearable
            @keyup.enter="handleSearch"
          />
        </div>

        <div class="header-right">
          <el-tooltip content="返回首页" placement="bottom">
            <button class="icon-btn" @click="router.push('/manager/home')">
              <el-icon><HomeFilled /></el-icon>
            </button>
          </el-tooltip>
          <el-tooltip content="智能客服" placement="bottom">
            <button class="icon-btn" @click="router.push('/manager/chat')">
              <el-icon><ChatDotRound /></el-icon>
            </button>
          </el-tooltip>

          <!-- 购物车：点击弹出商品概览，角标为商品总件数（Pinia 全局同步） -->
          <el-popover v-if="data.user.role === '用户'" placement="bottom" :width="340" trigger="click" @show="loadCartBrief">
            <template #reference>
              <button class="icon-btn">
                <el-badge :value="cartStore.count" :hidden="!cartStore.count" :max="99">
                  <el-icon :size="20"><ShoppingCart /></el-icon>
                </el-badge>
              </button>
            </template>
            <div class="cart-pop">
              <div class="cart-pop-head">
                <span>购物车</span>
                <el-button link type="primary" size="small" @click="router.push('/manager/cart')">查看全部</el-button>
              </div>
              <div v-if="!cartStore.items.length" class="cart-pop-empty">
                购物车是空的，
                <el-link type="primary" :underline="false" @click="router.push('/manager/cake')">去逛逛</el-link>
              </div>
              <template v-else>
                <div v-for="i in cartStore.items.slice(0, 5)" :key="i.id"
                     class="cart-pop-item" @click="router.push('/manager/cart')">
                  <img :src="$fileUrl(i.goodsImg)" class="cart-pop-img" />
                  <div class="cart-pop-info">
                    <div class="cart-pop-name line1">{{ i.goodsName }}</div>
                    <div class="cart-pop-meta">¥{{ Number(i.goodsPrice).toFixed(2) }} × {{ i.num }}{{ i.goodsUnit }}</div>
                  </div>
                  <div class="cart-pop-sub">¥{{ (Number(i.goodsPrice) * i.num).toFixed(2) }}</div>
                </div>
                <div v-if="cartStore.items.length > 5" class="cart-pop-more">
                  等 {{ cartStore.items.length }} 种商品…
                </div>
                <div class="cart-pop-foot">
                  <span>合计 <b>¥{{ cartBriefTotal.toFixed(2) }}</b></span>
                  <el-button type="primary" size="small" round @click="router.push('/manager/cart')">去结算</el-button>
                </div>
              </template>
            </div>
          </el-popover>

          <!-- 订单站内通知：未读角标 + 最近通知，60s 轮询（分钟级实时性足够） -->
          <el-popover placement="bottom" :width="340" trigger="click" @show="loadNotifications">
            <template #reference>
              <span class="bell-wrap">
                <el-badge :value="notif.unread" :hidden="!notif.unread" :max="99">
                  <el-icon :size="20"><Bell /></el-icon>
                </el-badge>
              </span>
            </template>
            <div class="notif-panel">
              <div class="notif-head">
                <span>订单通知</span>
                <div v-if="notif.list.length" class="notif-actions">
                  <el-button v-if="notif.unread" link type="primary" size="small" @click="markAllRead">
                    全部已读
                  </el-button>
                  <el-button link type="danger" size="small" @click="clearAll">清空</el-button>
                </div>
              </div>
              <div v-if="!notif.list.length" class="notif-empty">暂无通知</div>
              <div
                v-for="n in notif.list" :key="n.id"
                class="notif-item" :class="{ unread: !n.isRead }"
                @click="markRead(n)"
              >
                <div class="notif-title line1">{{ n.title }}</div>
                <div class="notif-content line1">{{ n.content }}</div>
                <div class="notif-time">{{ n.createdAt }}</div>
              </div>
            </div>
          </el-popover>

          <el-dropdown trigger="click" @command="handleCommand">
            <div class="user-chip">
              <el-avatar :size="36" :src="$fileUrl(data.user.avatar) || 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'" />
              <div class="user-meta">
                <div class="user-name">{{ data.user.name || '未登录' }}</div>
                <div class="user-role">{{ data.user.role || '游客' }}</div>
              </div>
              <el-icon class="caret"><CaretBottom /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="person">
                  <el-icon><User /></el-icon>个人资料
                </el-dropdown-item>
                <el-dropdown-item command="password">
                  <el-icon><Lock /></el-icon>修改密码
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </header>

    <!-- 主体区 -->
    <div class="app-body">
      <!-- 侧边栏 -->
      <aside class="app-sidebar" :class="{ collapsed: data.collapsed }">
        <el-menu
          :default-active="router.currentRoute.value.fullPath"
          :default-openeds="data.openedMenus"
          :collapse="data.collapsed"
          :collapse-transition="false"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/manager/home">
            <el-icon><HomeFilled /></el-icon>
            <template #title>系统首页</template>
          </el-menu-item>

          <!-- 用户：导购商城 -->
          <el-sub-menu index="cake-shop" v-if="data.user.role === '用户'">
            <template #title>
              <el-icon>
                <Cherry/>
              </el-icon>
              <span>导购商城</span>
            </template>
            <el-menu-item index="/manager/cake">
              <el-icon>
                <Grid/>
              </el-icon>
              <template #title>全部商品</template>
            </el-menu-item>
            <el-menu-item v-for="c in data.categoryList" :key="c.id"
                          :index="`/manager/cake?categoryName=${encodeURIComponent(c.name)}`">
              <el-icon>
                <component :is="categoryIcon(c.name)"/>
              </el-icon>
              <template #title>{{ c.name }}</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 用户：我的 -->
          <el-sub-menu index="my-stuff" v-if="data.user.role === '用户'">
            <template #title>
              <el-icon><User /></el-icon>
              <span>个人信息</span>
            </template>
            <el-menu-item index="/manager/cart">
              <el-icon><ShoppingCart /></el-icon>
              <template #title>我的购物车</template>
            </el-menu-item>
            <el-menu-item index="/manager/orders">
              <el-icon><SoldOut /></el-icon>
              <template #title>我的订单</template>
            </el-menu-item>
            <el-menu-item index="/manager/favorite">
              <el-icon><Star /></el-icon>
              <template #title>我的收藏</template>
            </el-menu-item>
            <el-menu-item index="/manager/address">
              <el-icon><Location /></el-icon>
              <template #title>收货地址</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 管理员：商品管理 -->
          <el-sub-menu index="goods-mgmt" v-if="data.user.role === '管理员'">
            <template #title>
              <el-icon><Goods /></el-icon>
              <span>商品管理</span>
            </template>
            <el-menu-item index="/manager/category">
              <el-icon><Coin /></el-icon>
              <template #title>蛋糕分类</template>
            </el-menu-item>
            <el-menu-item index="/manager/goods">
              <el-icon><Refrigerator /></el-icon>
              <template #title>蛋糕信息</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 管理员：用户管理 -->
          <el-sub-menu index="user-mgmt" v-if="data.user.role === '管理员'">
            <template #title>
              <el-icon><Avatar /></el-icon>
              <span>用户管理</span>
            </template>
            <el-menu-item index="/manager/admin">
              <el-icon><Position /></el-icon>
              <template #title>管理员信息</template>
            </el-menu-item>
            <el-menu-item index="/manager/user">
              <el-icon><User /></el-icon>
              <template #title>用户信息</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 管理员：订单与公告 -->
          <el-menu-item index="/manager/orders" v-if="data.user.role === '管理员'">
            <el-icon><SoldOut /></el-icon>
            <template #title>订单管理</template>
          </el-menu-item>
          <el-menu-item index="/manager/reviews" v-if="data.user.role === '管理员'">
            <el-icon><ChatLineSquare /></el-icon>
            <template #title>评价管理</template>
          </el-menu-item>
          <el-menu-item index="/manager/notice" v-if="data.user.role === '管理员'">
            <el-icon><Monitor /></el-icon>
            <template #title>公告管理</template>
          </el-menu-item>
          <el-menu-item index="/manager/knowledge" v-if="data.user.role === '管理员'">
            <el-icon><Document /></el-icon>
            <template #title>知识库管理</template>
          </el-menu-item>

          <!-- 管理员：数据分析 -->
          <el-sub-menu index="ai-ops" v-if="data.user.role === '管理员'">
            <template #title>
              <el-icon><DataAnalysis /></el-icon>
              <span>数据分析</span>
            </template>
            <el-menu-item index="/manager/ops">
              <el-icon><TrendCharts /></el-icon>
              <template #title>商品分析</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 通用 -->
          <el-menu-item index="/manager/address" v-if="data.user.role === '管理员'">
            <el-icon><Location /></el-icon>
            <template #title>地址管理</template>
          </el-menu-item>
          <el-menu-item index="/manager/chat">
            <el-icon><ChatDotRound /></el-icon>
            <template #title>智能客服</template>
          </el-menu-item>
          <el-menu-item index="/manager/person">
            <el-icon><User /></el-icon>
            <template #title>个人资料</template>
          </el-menu-item>
          <el-menu-item index="/manager/password">
            <el-icon><Lock /></el-icon>
            <template #title>修改密码</template>
          </el-menu-item>
        </el-menu>
      </aside>

      <!-- 内容区 -->
      <main class="app-content">
        <router-view @updateUser="updateUser" />
        <footer class="app-footer">
          <span>© {{ new Date().getFullYear() }} 智能商城导购与运营平台</span>
        </footer>
      </main>
    </div>
  </div>
</template>

<script setup>
import { reactive, markRaw, computed, onMounted, onUnmounted } from "vue";
import router from "@/router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Fold, Expand, Search, HomeFilled, ChatDotRound, CaretBottom, User, Lock,
  SwitchButton, Cherry, Grid, Coin, Refrigerator, Avatar, Position, SoldOut,
  Location, Monitor, Document, Star, ChatLineSquare, ShoppingCart,
  Sunset, Present, GobletSquare, MagicStick, Watch, Medal, Trophy,
  DataAnalysis, TrendCharts, Bell,
} from "@element-plus/icons-vue";
import request from "@/utils/request";
import { useCartStore } from "@/stores/cart";

// 仅预取角色对应的高频路径。低频管理页继续保持真正的按路由懒加载。
const commonPrefetch = [() => import('@/views/manager/Home.vue')]
const rolePrefetch = {
  '管理员': [
    () => import('@/views/manager/Goods.vue'),
    () => import('@/views/manager/Orders.vue'),
  ],
  '用户': [
    () => import('@/views/manager/Cake.vue'),
    () => import('@/views/manager/Orders.vue'),
    () => import('@/views/manager/Favorite.vue'),
  ],
}

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  collapsed: false,
  search: '',
  openedMenus: ['cake-shop', 'my-stuff', 'goods-mgmt', 'user-mgmt'],
  categoryList: [],
})

// 浏览器空闲时预取少量高频页，避免阻塞首屏和登录后的网络带宽。
onMounted(() => {
  const loaders = [...commonPrefetch, ...(rolePrefetch[data.user.role] || [])]
  const prefetch = () => loaders.forEach(load => load().catch(() => {}))
  if ('requestIdleCallback' in window) window.requestIdleCallback(prefetch, { timeout: 1500 })
  else window.setTimeout(prefetch, 300)
})

// 分类图标映射
// 分类图标映射：从分类语义出发，统一走"概念化"风格而非水果
// 与系统简约时尚风一致：线条极简、象征性强
const iconMap = {
  '情侣': markRaw(Sunset),        // 日落黄昏的浪漫
  '童趣': markRaw(Present),       // 生日礼物
  '聚会': markRaw(GobletSquare),  // 举杯庆祝
  '女神': markRaw(MagicStick),    // 仙气梦幻
  '潮男': markRaw(Watch),         // 极简配饰
  '长辈': markRaw(Medal),         // 荣誉寿礼
  '宴席': markRaw(Trophy),        // 典礼大场面
}
const categoryIcon = (name) => iconMap[name] || Grid

const loadCategories = () => {
  request.get('/category/selectAll').then(res => {
    if (res.code === '200') {
      data.categoryList = res.data || []
    }
  }).catch(() => {})
}
loadCategories()

// 管理员在另一会话调整分类后，用户切回本标签页时侧栏菜单自动同步；
// 静默执行不打扰用户，失败也忽略（已有列表保持不变）
let focusHandler = null
let visibilityHandler = null
const refreshCategoriesSilently = () => {
  if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return
  loadCategories()
}
onMounted(() => {
  focusHandler = () => refreshCategoriesSilently()
  visibilityHandler = () => {
    if (document.visibilityState === 'visible') refreshCategoriesSilently()
  }
  window.addEventListener('focus', focusHandler)
  document.addEventListener('visibilitychange', visibilityHandler)
})
onUnmounted(() => {
  if (focusHandler) window.removeEventListener('focus', focusHandler)
  if (visibilityHandler) document.removeEventListener('visibilitychange', visibilityHandler)
})

// ==================== 订单站内通知 ====================
// 轮询起步（60s）：分钟级实时性足够——蛋糕制作配送本身以小时计，
// 不为省几次空查询引入 WebSocket/SSE
const notif = reactive({ unread: 0, list: [] })

const loadUnreadCount = () => {
  request.get('/notification/unread-count').then(res => {
    if (res.code === '200') notif.unread = res.data?.count || 0
  }).catch(() => {})
}

const loadNotifications = () => {
  request.get('/notification/list', { params: { pageNum: 1, pageSize: 8 } }).then(res => {
    if (res.code === '200') {
      notif.list = res.data?.list || []
      loadUnreadCount()
    }
  }).catch(() => {})
}

const markAllRead = () => {
  request.put('/notification/read-all').then(res => {
    if (res.code === '200') {
      notif.unread = 0
      notif.list.forEach(n => { n.isRead = true })
    }
  }).catch(() => {})
}

// 点击单条即已读：本地即时扣减角标，60s 轮询兜底纠偏；已读条目幂等跳过
const markRead = (n) => {
  if (!n.isRead) {
    request.put(`/notification/${n.id}/read`).then(res => {
      if (res.code === '200') {
        n.isRead = true
        notif.unread = Math.max(0, notif.unread - 1)
      }
    }).catch(() => {})
  }
  router.push('/manager/orders')
}

const clearAll = () => {
  ElMessageBox.confirm('确定清空所有通知吗？', '清空通知', {
    type: 'warning',
    confirmButtonText: '清空',
    cancelButtonText: '取消',
  }).then(() => {
    request.delete('/notification/clear').then(res => {
      if (res.code === '200') {
        notif.list = []
        notif.unread = 0
      }
    }).catch(() => {})
  }).catch(() => {})
}

let notifTimer = null
const cartStore = useCartStore()
// 弹层打开即刷新概览（列表与角标共用 store，弹层/购物车页天然同步）
const loadCartBrief = () => cartStore.loadCart()
const cartBriefTotal = computed(() => cartStore.items.reduce((sum, i) => sum + Number(i.goodsPrice) * i.num, 0))
onMounted(() => {
  loadUnreadCount()
  notifTimer = window.setInterval(loadUnreadCount, 60 * 1000)
  if (data.user.role === '用户') cartStore.loadCount()
})
onUnmounted(() => {
  if (notifTimer) window.clearInterval(notifTimer)
})

if (!data.user?.id) {
  ElMessage.error('请登录！')
  router.push('/login')
}

const updateUser = () => {
  data.user = JSON.parse(localStorage.getItem('system-user') || '{}')
}

const handleCommand = (cmd) => {
  if (cmd === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '退出确认', {
      type: 'warning',
      confirmButtonText: '确定退出',
      cancelButtonText: '取消',
    }).then(() => {
      ElMessage.success('退出成功')
      localStorage.removeItem('token')
      localStorage.removeItem('system-user')
      router.push('/login')
    }).catch(() => {})
  } else if (cmd === 'person') {
    router.push('/manager/person')
  } else if (cmd === 'password') {
    router.push('/manager/password')
  }
}

const handleSearch = () => {
  if (data.search) {
    router.push({ path: '/manager/cake', query: { name: data.search } })
  }
}
</script>

<style scoped>
.app-shell {
  /* 固定视口高度并锁定滚动：header/侧栏天然固定，滚动只发生在内容区 */
  height: 100vh;
  height: 100dvh; /* 移动端地址栏收起/展开时的动态视口 */
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--c-bg-page);
}

/* ========== 顶部导航 ========== */
.app-header {
  flex-shrink: 0;
  z-index: 100;
  height: var(--header-h);
  background: var(--c-bg-card);
  border-bottom: none;
  box-shadow: var(--shadow-sm);
}

.header-inner {
  height: 100%;
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: var(--c-bg-soft);
  color: var(--c-text-regular);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--t-fast) var(--ease-out);
  font-size: 16px;
}

.icon-btn:hover {
  border-color: var(--c-primary);
  color: var(--c-primary);
  background: var(--c-primary-soft);
}

/* ==================== 订单通知铃铛 ==================== */
.bell-wrap {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--c-bg-soft);
  color: var(--c-text-regular);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--t-fast) var(--ease-out);
}
.bell-wrap:hover {
  color: var(--c-primary);
  background: var(--c-primary-soft);
}
.notif-panel {
  margin: -4px -8px;
}
.notif-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 12px 8px;
  border-bottom: 1px solid var(--c-border);
  font-weight: 600;
  font-size: 14px;
}
.notif-actions .el-button + .el-button {
  margin-left: 8px;
}
.notif-empty {
  padding: 28px 0;
  text-align: center;
  color: var(--c-text-secondary);
  font-size: 13px;
}
.notif-item {
  padding: 10px 12px;
  border-bottom: 1px solid var(--c-border);
  cursor: pointer;
  transition: background var(--t-fast) var(--ease-out);
}
.notif-item:last-child { border-bottom: none; }
.notif-item:hover { background: var(--c-bg-soft); }
.notif-item.unread .notif-title { font-weight: 600; }
.notif-item.unread .notif-title::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c-danger);
  margin-right: 6px;
  vertical-align: middle;
}
.notif-title { font-size: 13px; color: var(--c-text); }
.notif-content { font-size: 12px; color: var(--c-text-secondary); margin-top: 2px; }
.notif-time { font-size: 11px; color: var(--c-text-placeholder); margin-top: 2px; }

/* ==================== 购物车概览弹层 ==================== */
.cart-pop { margin: -4px -8px; }
.cart-pop-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 12px 8px;
  border-bottom: 1px solid var(--c-border);
  font-weight: 600;
  font-size: 14px;
}
.cart-pop-empty {
  padding: 28px 0;
  text-align: center;
  color: var(--c-text-secondary);
  font-size: 13px;
}
.cart-pop-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--c-border);
  cursor: pointer;
  transition: background var(--t-fast) var(--ease-out);
}
.cart-pop-item:hover { background: var(--c-bg-soft); }
.cart-pop-img {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  object-fit: cover;
  background: var(--c-bg-soft);
  flex-shrink: 0;
}
.cart-pop-info { flex: 1; min-width: 0; }
.cart-pop-name { font-size: 13px; color: var(--c-text); font-weight: 500; }
.cart-pop-meta { font-size: 11px; color: var(--c-text-secondary); margin-top: 3px; }
.cart-pop-sub { font-size: 13px; font-weight: 600; color: var(--c-primary); }
.cart-pop-more {
  padding: 6px 12px;
  font-size: 11px;
  color: var(--c-text-placeholder);
  border-bottom: 1px solid var(--c-border);
}
.cart-pop-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px 4px;
  font-size: 13px;
  color: var(--c-text-regular);
}
.cart-pop-foot b { color: var(--c-primary); font-size: 15px; }

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 10px;
  transition: background var(--t-fast) var(--ease-out);
}

.brand:hover {
  background: var(--c-bg-soft);
}

.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid var(--c-primary-bg);
  object-fit: cover;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.brand-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--c-text-primary);
  letter-spacing: 0.3px;
}

.brand-tag {
  font-size: 11px;
  color: var(--c-text-secondary);
  margin-top: 1px;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.header-search {
  max-width: 480px;
  width: 100%;
}

.header-search :deep(.el-input__wrapper) {
  border-radius: var(--r-pill);
  background: var(--c-bg-soft);
  box-shadow: 0 0 0 1px var(--c-border-light) inset;
}

.header-search :deep(.el-input__wrapper.is-focus) {
  background: var(--c-bg-card);
  box-shadow: 0 0 0 1px var(--c-primary) inset, 0 0 0 3px var(--c-primary-soft);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px 4px 4px;
  border-radius: var(--r-pill);
  border: none;
  background: var(--c-bg-soft);
  cursor: pointer;
  transition: all var(--t-fast) var(--ease-out);
}

.user-chip:hover {
  border-color: var(--c-primary);
  background: var(--c-primary-soft);
}

.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-primary);
}

.user-role {
  font-size: 11px;
  color: var(--c-text-secondary);
  margin-top: 2px;
}

.caret {
  color: var(--c-text-secondary);
  font-size: 12px;
}

/* ========== 主体布局 ========== */
.app-body {
  flex: 1;
  display: flex;
  min-height: 0; /* flex 子项允许收缩，内容区滚动的前提 */
  overflow: hidden;
}

.app-sidebar {
  width: var(--sidebar-w);
  background: var(--c-bg-card);
  border-right: none;
  transition: width var(--t-base) var(--ease-out);
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.app-sidebar.collapsed {
  width: var(--sidebar-w-collapsed);
}

.sidebar-menu {
  border-right: none !important;
  padding: 12px 10px;
  flex: 1;
  min-height: 0;
  overflow-y: auto; /* 菜单过长时侧栏内部滚动，不影响内容区 */
  overflow-x: hidden;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: var(--sidebar-w);
}

.sidebar-menu :deep(.el-menu-item),
.sidebar-menu :deep(.el-sub-menu__title) {
  height: 44px;
  line-height: 44px;
  border-radius: 10px;
  margin: 2px 0;
  color: var(--c-text-regular);
  font-weight: 500;
}

.sidebar-menu :deep(.el-menu-item:hover),
.sidebar-menu :deep(.el-sub-menu__title:hover) {
  background: var(--c-bg-soft);
  color: var(--c-text-primary);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--c-primary-soft);
  color: var(--c-primary);
  font-weight: 600;
}

.sidebar-menu :deep(.el-menu-item.is-active)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 16px;
  background: var(--grad-primary);
  border-radius: 0 2px 2px 0;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  position: relative;
}

/* ========== 内容区 ========== */
.app-content {
  flex: 1;
  min-width: 0;          /* 允许窄于内容宽度，防止表格撑破 */
  min-height: 0;
  overflow-y: auto;      /* 全站唯一主滚动容器：子页面在此内部滚动 */
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
}

.app-content > :first-child {
  flex: 1;
}

.app-footer {
  padding: 16px 20px;
  text-align: center;
  font-size: 12px;
  color: var(--c-text-secondary);
  border-top: none;
  background: var(--c-bg-card);
}

/* 响应式：窄屏隐藏搜索框 */
@media (max-width: 768px) {
  .header-center { display: none; }
  .user-meta { display: none; }
  .app-sidebar {
    position: fixed;
    z-index: 99;
    top: var(--header-h);
    height: calc(100dvh - var(--header-h));
  }
}
</style>
