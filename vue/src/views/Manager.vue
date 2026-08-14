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
              <div class="brand-name">甜心烘焙</div>
              <div class="brand-tag">Sweet Hearts Bakery</div>
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

          <el-dropdown trigger="click" @command="handleCommand">
            <div class="user-chip">
              <el-avatar :size="36" :src="data.user.avatar || 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'" />
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

          <!-- 用户：蛋糕商城 -->
          <el-sub-menu index="cake-shop" v-if="data.user.role === '用户'">
            <template #title>
              <el-icon>
                <Cherry/>
              </el-icon>
              <span>蛋糕商城</span>
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
          <span>© {{ new Date().getFullYear() }} 甜心烘焙 Sweet Hearts Bakery · 智能蛋糕商城</span>
        </footer>
      </main>
    </div>
  </div>
</template>

<script setup>
import { reactive, markRaw, onMounted, onUnmounted } from "vue";
import router from "@/router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Fold, Expand, Search, HomeFilled, ChatDotRound, CaretBottom, User, Lock,
  SwitchButton, Cherry, Grid, Coin, Refrigerator, Avatar, Position, SoldOut,
  Location, Monitor, Document, Star, ChatLineSquare,
  Sunset, Present, GobletSquare, MagicStick, Watch, Medal, Trophy,
} from "@element-plus/icons-vue";
import request from "@/utils/request";

// 预加载所有侧栏页面 chunk：
// 侧栏路由均为懒加载，首次点击菜单时浏览器才拉取对应 JS 并触发 Vite 按需编译，
// 造成"卡顿、停留在首页"。进入系统后即并行预取所有页面 chunk，首次点击即瞬时响应。
const pageChunks = import.meta.glob('@/views/manager/*.vue')

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  collapsed: false,
  search: '',
  openedMenus: ['cake-shop', 'my-stuff', 'goods-mgmt', 'user-mgmt'],
  categoryList: [],
})

// 进入系统后预取所有页面，消除首次点击菜单的编译/下载等待
onMounted(() => {
  Object.values(pageChunks).forEach(load => load().catch(() => {}))
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
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--c-bg-page);
}

/* ========== 顶部导航 ========== */
.app-header {
  position: sticky;
  top: 0;
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
  min-height: 0;
}

.app-sidebar {
  width: var(--sidebar-w);
  background: var(--c-bg-card);
  border-right: none;
  transition: width var(--t-base) var(--ease-out);
  overflow: hidden;
  flex-shrink: 0;
}

.app-sidebar.collapsed {
  width: var(--sidebar-w-collapsed);
}

.sidebar-menu {
  border-right: none !important;
  padding: 12px 10px;
  height: calc(100vh - var(--header-h));
  overflow-y: auto;
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
  min-width: 0;
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
  .app-sidebar { position: fixed; z-index: 99; height: calc(100vh - var(--header-h)); }
}
</style>
