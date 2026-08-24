<template>
  <div class="detail-page" v-loading="data.loading">
    <!-- 面包屑 -->
    <div class="breadcrumb-bar card">
      <el-breadcrumb :separator-icon="ArrowRight">
        <el-breadcrumb-item @click="$router.push('/manager/cake')" class="breadcrumb-link">
          <el-icon><Goods /></el-icon>商品列表
        </el-breadcrumb-item>
        <el-breadcrumb-item v-if="data.goods.categoryName">
          {{ data.goods.categoryName }}
        </el-breadcrumb-item>
        <el-breadcrumb-item>{{ data.goods.name || '商品详情' }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 主体 -->
    <template v-if="data.goods.id">
      <div class="detail-grid">
        <!-- 左侧：图片 -->
        <section class="gallery-card card">
          <div class="main-image">
            <img :src="$fileUrl(data.goods.img)" :alt="data.goods.name" />
            <div class="gallery-badge" v-if="data.goods.categoryName">{{ data.goods.categoryName }}</div>
            <div class="gallery-stock" :class="{ out: data.goods.num === 0 }">
              <template v-if="data.goods.num === 0">已售罄</template>
              <template v-else-if="data.goods.num <= 5">仅剩 {{ data.goods.num }}{{ data.goods.unit }}</template>
              <template v-else>现货充足</template>
            </div>
          </div>
        </section>

        <!-- 右侧：购买信息 -->
        <section class="info-card card">
          <h1 class="goods-title">{{ data.goods.name }}</h1>
          <p class="goods-subtitle line2">{{ data.goods.description }}</p>

          <!-- 价格面板 -->
          <div class="price-panel">
            <div class="price-row">
              <span class="price-label">售价</span>
              <div class="price-value">
                <span class="pv-symbol">¥</span>
                <span class="pv-num">{{ data.goods.price }}</span>
                <span class="pv-unit">/ {{ data.goods.unit }}</span>
              </div>
            </div>
            <div class="price-tags">
              <span class="ptag" v-if="data.goods.serves">
                <el-icon><User /></el-icon>{{ data.goods.serves }}
              </span>
              <span class="ptag" v-if="data.goods.shelf_life">
                <el-icon><Timer /></el-icon>{{ data.goods.shelf_life }}
              </span>
            </div>
          </div>

          <!-- 规格选择 -->
          <div class="spec-row" v-if="data.specList.length">
            <div class="spec-label">规格</div>
            <div class="spec-list">
              <button
                v-for="spec in data.specList"
                :key="spec"
                class="spec-chip"
                :class="{ active: data.selectedSpec === spec }"
                @click="data.selectedSpec = spec">
                {{ spec }}
              </button>
            </div>
          </div>

          <!-- 数量 -->
          <div class="qty-row">
            <div class="qty-label">数量</div>
            <el-input-number
              v-model="data.qty"
              :min="1"
              :max="Math.max(1, data.goods.num || 99)"
              :disabled="data.goods.num === 0"
            />
            <span class="qty-hint" v-if="data.goods.num > 0">库存 {{ data.goods.num }}{{ data.goods.unit }}</span>
          </div>

          <!-- 操作按钮 -->
          <div class="action-row">
            <el-button
              round
              class="ghost-action"
              :class="{ active: data.favorited }"
              @click="toggleFav(data.goods.id)">
              <el-icon style="margin-right: 4px"><StarFilled v-if="data.favorited" /><Star v-else /></el-icon>
              {{ data.favorited ? '已收藏' : '收藏' }}
            </el-button>
            <el-button
              type="primary"
              round
              class="primary-action"
              :disabled="data.goods.num === 0"
              @click="reserveInit">
              <el-icon style="margin-right: 4px"><ShoppingCart /></el-icon>
              {{ data.goods.num === 0 ? '已售罄' : '立即预订' }}
            </el-button>
          </div>

          <!-- 服务保障 -->
          <div class="service-grid">
            <div class="service-item">
              <el-icon class="service-icon"><CircleCheck /></el-icon>
              <div>
                <div class="service-title">现做现发</div>
                <div class="service-desc">24 小时内现做</div>
              </div>
            </div>
            <div class="service-item">
              <el-icon class="service-icon"><Van /></el-icon>
              <div>
                <div class="service-title">冷链配送</div>
                <div class="service-desc">全程低温保鲜</div>
              </div>
            </div>
            <div class="service-item">
              <el-icon class="service-icon"><Medal /></el-icon>
              <div>
                <div class="service-title">品质保障</div>
                <div class="service-desc">质量问题可申请售后</div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- 底部：分区导航（商品详情 / 规格参数 / 温馨提示 / 用户评价 / AI 问答） -->
      <GoodsDetailTabs :key="String(route.params.id)" :goods="data.goods" />
    </template>

    <!-- 占位：未加载到 -->
    <div v-else-if="!data.loading" class="empty-state card">
      <el-icon :size="64"><Cherry /></el-icon>
      <p>商品不存在或已下架</p>
      <el-button type="primary" round @click="$router.push('/manager/cake')">返回列表</el-button>
    </div>

    <!-- 预订弹窗 -->
    <el-dialog v-model="data.formVisible" width="480px" :close-on-click-modal="false" destroy-on-close class="reserve-dialog">
      <template #header>
        <div class="dialog-header-custom">
          <el-icon class="dialog-icon"><ShoppingBag /></el-icon>
          <div>
            <div class="dialog-title">确认订单信息</div>
            <div class="dialog-sub">填写预订信息后提交</div>
          </div>
        </div>
      </template>
      <el-form ref="formRef" :model="data.form" :rules="rules" label-position="top">
        <el-form-item label="商品">
          <div class="dialog-goods">
            <img :src="$fileUrl(data.goods.img)" class="dialog-goods-img" />
            <div class="dialog-goods-info">
              <div class="dialog-goods-name line1">{{ data.goods.name }}</div>
              <div class="dialog-goods-spec" v-if="data.selectedSpec">{{ data.selectedSpec }}</div>
            </div>
            <div class="dialog-goods-price">¥{{ data.goods.price }}<small>/{{ data.goods.unit }}</small></div>
          </div>
        </el-form-item>
        <el-form-item label="预订数量" prop="num">
          <el-input-number v-model="data.form.num" :min="1" :max="Math.max(1, data.goods.num || 99)" />
        </el-form-item>
        <el-form-item label="收货地址" prop="addressId">
          <el-select v-model="data.form.addressId" placeholder="请选择收货地址" style="width: 100%">
            <el-option
              v-for="item in data.addressList"
              :key="item.id"
              :label="item.name + ' · ' + item.phone + ' · ' + item.address"
              :value="item.id"
            />
          </el-select>
          <div v-if="!data.addressList.length" class="hint-empty">
            还没有收货地址，<router-link to="/manager/address">去添加</router-link>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="data.formVisible = false" round>取消</el-button>
        <el-button type="primary" @click="save" round>提交订单</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, watch, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import request from "@/utils/request";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  ArrowRight, Goods, User, Timer, Star, StarFilled, ShoppingCart, ShoppingBag,
  CircleCheck, Van, Medal, Cherry,
} from "@element-plus/icons-vue";
import GoodsDetailTabs from '@/components/product/GoodsDetailTabs.vue'

const route = useRoute()
const router = useRouter()
const formRef = ref()

const data = reactive({
  loading: false,
  goods: {},
  qty: 1,
  selectedSpec: '',
  specList: [],
  favorited: false,
  formVisible: false,
  form: {},
  addressList: [],
})

const rules = {
  num: [{ required: true, message: '请输入数量', trigger: 'blur' }],
  addressId: [{ required: true, message: '请选择地址', trigger: 'change' }],
}

const user = computed(() => JSON.parse(localStorage.getItem('system-user') || '{}'))

const parseSpecs = (specsStr) => {
  if (!specsStr) return []
  return specsStr
    .split(/[/／|、；,，\s]+/)
    .map(s => s.trim())
    .filter(Boolean)
}

const loadDetail = () => {
  data.loading = true
  request.get('/goods/detail/' + route.params.id).then(res => {
    if (res.code === '200' && res.data) {
      data.goods = res.data
      data.specList = parseSpecs(res.data.specs)
      data.selectedSpec = data.specList[0] || ''
    } else {
      data.goods = {}
      ElMessage.error(res.msg || '商品不存在')
    }
  }).finally(() => {
    data.loading = false
  })
}

const loadFavoriteStatus = () => {
  request.get('/favorite/list').then(res => {
    if (res.code === '200') {
      const list = res.data || []
      data.favorited = list.some(g => g.id === Number(route.params.id))
    }
  })
}

const toggleFav = (goodsId) => {
  if (data.favorited) {
    request.delete('/favorite/remove/' + goodsId).then(res => {
      if (res.code === '200') {
        data.favorited = false
        ElMessage.success('已取消收藏')
      } else { ElMessage.error(res.msg) }
    })
  } else {
    request.post('/favorite/add', { goods_id: goodsId }).then(res => {
      if (res.code === '200') {
        data.favorited = true
        ElMessage.success('已加入收藏')
      } else { ElMessage.error(res.msg) }
    })
  }
}

const loadAddress = () => {
  request.get('/address/selectAll', { params: { userId: user.value.id } }).then(res => {
    if (res.code === '200') data.addressList = res.data
  })
}

const reserveInit = () => {
  data.form = { userId: user.value.id, goodsId: data.goods.id, num: data.qty }
  data.formVisible = true
}

const save = () => {
  formRef.value.validate(valid => {
    if (!valid) return
    request.post('/orders/add', data.form).then(res => {
      if (res.code === '200') {
        ElMessage.success('预订成功，等待商家配送')
        data.formVisible = false
        loadDetail()
      } else { ElMessage.error(res.msg) }
    }).catch(error => handleBalanceError(error))
  })
}

const handleBalanceError = (error) => {
  const msg = error.response?.data?.msg || ''
  if (!msg.includes('余额不足')) return
  ElMessageBox.confirm(`${msg}。是否前往“我的余额”充值？`, '余额不足', { confirmButtonText: '去充值', cancelButtonText: '暂不充值', type: 'warning' })
    .then(() => router.push('/manager/person')).catch(() => {})
}

onMounted(() => {
  loadDetail()
  loadFavoriteStatus()
  loadAddress()
})

watch(() => route.params.id, (newId) => {
  if (newId) {
    data.qty = 1
    data.selectedSpec = ''
    data.specList = []
    loadDetail()
    loadFavoriteStatus()
  }
})
</script>

<style scoped>
/* 页面锁定一屏不滚动（经 .app-content 的 flex:1 拉伸撑满）：
   上半购买区天然固定，滚动只发生在 Tab 分区容器内部 */
.detail-page {
  padding: 12px 16px;
  width: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

/* —— 面包屑 —— */
.breadcrumb-bar {
  padding: 8px 16px;
  flex-shrink: 0;
}

.breadcrumb-bar :deep(.el-breadcrumb__item) {
  font-size: 13px;
}

.breadcrumb-bar :deep(.el-breadcrumb__inner) {
  color: var(--c-text-secondary);
  font-weight: 500;
}

.breadcrumb-bar :deep(.el-breadcrumb__inner.is-link),
.breadcrumb-bar :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--c-text-primary);
}

.breadcrumb-link {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.breadcrumb-link:hover :deep(.el-breadcrumb__inner) {
  color: var(--c-primary) !important;
}

/* —— 主体网格 —— */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  flex-shrink: 0;
}

@media (max-width: 960px) {
  .detail-grid { grid-template-columns: 1fr; }
  /* 窄屏上部内容超一屏：恢复页面级滚动，配合 Tab 容器解除高度锁定 */
  .detail-page { height: auto; overflow: visible; }
}

/* —— 图片区 —— */
.gallery-card {
  padding: 10px;
}

.main-image {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: var(--r-md);
  overflow: hidden;
  background: var(--c-bg-soft);
}

.main-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.gallery-badge {
  position: absolute;
  top: 16px; left: 16px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  color: var(--c-primary);
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: var(--r-pill);
}

.gallery-stock {
  position: absolute;
  top: 16px; right: 16px;
  background: rgba(94, 138, 47, 0.92);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: var(--r-pill);
}

.gallery-stock.out {
  background: rgba(110, 101, 88, 0.92);
}

/* —— 信息区 —— */
.info-card {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.goods-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--c-text-primary);
  margin: 0;
  line-height: 1.3;
}

.goods-subtitle {
  font-size: 13px;
  color: var(--c-text-secondary);
  margin: 0;
  line-height: 1.6;
}

/* —— 价格面板 —— */
.price-panel {
  background: linear-gradient(135deg, #fdf6e0 0%, #f7eed1 100%);
  border-radius: var(--r-md);
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.price-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.price-label {
  font-size: 12px;
  color: var(--c-text-secondary);
  font-weight: 500;
}

.price-value {
  display: flex;
  align-items: baseline;
  color: var(--c-primary);
}

.pv-symbol { font-size: 14px; font-weight: 600; }
.pv-num {
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
  font-feature-settings: "tnum";
  letter-spacing: -0.5px;
}
.pv-unit { font-size: 13px; color: var(--c-text-secondary); margin-left: 4px; }

.price-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ptag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.7);
  color: var(--c-text-regular);
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: var(--r-pill);
}

.ptag .el-icon { color: var(--c-primary); font-size: 14px; }

/* —— 规格选择 —— */
.spec-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.spec-label, .qty-label {
  font-size: 13px;
  color: var(--c-text-secondary);
  font-weight: 600;
  min-width: 48px;
  padding-top: 8px;
}

.spec-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.spec-chip {
  padding: 4px 12px;
  border-radius: var(--r-pill);
  background: var(--c-bg-soft);
  color: var(--c-text-regular);
  border: 1.5px solid transparent;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--t-fast) var(--ease-out);
}

.spec-chip:hover {
  background: var(--c-primary-soft);
  color: var(--c-primary);
}

.spec-chip.active {
  background: var(--c-primary-soft);
  color: var(--c-primary);
  border-color: var(--c-primary);
  font-weight: 600;
}

/* —— 数量 —— */
.qty-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.qty-hint {
  font-size: 12px;
  color: var(--c-text-secondary);
}

/* —— 操作按钮 —— */
.action-row {
  display: flex;
  gap: 12px;
  margin-top: 4px;
}

.action-row .el-button {
  flex: 1;
}

.ghost-action {
  background: var(--c-bg-soft);
  border: 1.5px solid transparent;
  color: var(--c-text-regular);
  font-weight: 500;
}

.ghost-action:hover {
  background: var(--c-primary-soft);
  color: var(--c-primary);
}

.ghost-action.active {
  background: var(--c-primary-soft);
  color: var(--c-primary);
  border-color: var(--c-primary);
}

.primary-action {
  background: var(--grad-primary);
  border: none;
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(168, 138, 63, 0.28);
}

/* —— 服务保障 —— */
.service-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--c-divider);
}

@media (max-width: 560px) {
  .service-grid { grid-template-columns: 1fr; }
}

.service-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.service-icon {
  width: 24px; height: 24px;
  background: var(--c-primary-soft);
  color: var(--c-primary);
  border-radius: 7px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.service-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-primary);
}

.service-desc {
  font-size: 11px;
  color: var(--c-text-secondary);
  margin-top: 1px;
}

/* —— 空态 —— */
.empty-state {
  padding: 60px 20px;
  text-align: center;
  color: var(--c-text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

/* —— 弹窗 —— */
.dialog-header-custom { display: flex; gap: 12px; align-items: center; }
.dialog-icon {
  width: 40px; height: 40px;
  background: var(--c-primary-soft);
  color: var(--c-primary);
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}
.dialog-title { font-size: 16px; font-weight: 600; color: var(--c-text-primary); }
.dialog-sub { font-size: 12px; color: var(--c-text-secondary); margin-top: 2px; }

.dialog-goods {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 8px;
  background: var(--c-bg-soft);
  border-radius: var(--r-md);
}

.dialog-goods-img {
  width: 56px; height: 56px;
  border-radius: 8px;
  object-fit: cover;
}

.dialog-goods-info { flex: 1; min-width: 0; }
.dialog-goods-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
}
.dialog-goods-spec {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin-top: 2px;
}

.dialog-goods-price {
  font-size: 16px;
  font-weight: 700;
  color: var(--c-primary);
}

.dialog-goods-price small {
  font-size: 11px;
  color: var(--c-text-secondary);
  font-weight: 400;
}

.hint-empty {
  margin-top: 6px;
  font-size: 12px;
  color: var(--c-text-secondary);
}

</style>
