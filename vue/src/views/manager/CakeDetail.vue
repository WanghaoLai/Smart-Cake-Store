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
          <p class="goods-subtitle">{{ data.goods.description }}</p>

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
              size="large"
              class="ghost-action"
              :class="{ active: data.favorited }"
              @click="toggleFav(data.goods.id)">
              <el-icon style="margin-right: 4px"><StarFilled v-if="data.favorited" /><Star v-else /></el-icon>
              {{ data.favorited ? '已收藏' : '收藏' }}
            </el-button>
            <el-button
              type="primary"
              round
              size="large"
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

      <!-- 详情介绍 + 信息 -->
      <div class="detail-grid two">
        <section class="info-block card">
          <div class="block-head">
            <h3 class="block-title">
              <el-icon><Document /></el-icon>商品详情
            </h3>
          </div>
          <div class="detail-text" v-if="data.goods.detail">
            <p v-for="(line, idx) in data.goods.detail.split('\n')" :key="idx">{{ line }}</p>
          </div>
          <div v-else class="empty-block">暂无详细介绍</div>
        </section>

        <section class="info-block card">
          <div class="block-head">
            <h3 class="block-title">
              <el-icon><InfoFilled /></el-icon>规格参数
            </h3>
          </div>
          <dl class="spec-table">
            <div class="spec-row-item">
              <dt>规格</dt>
              <dd>{{ data.goods.specs || '—' }}</dd>
            </div>
            <div class="spec-row-item">
              <dt>净含量</dt>
              <dd>{{ data.goods.weight || '—' }}</dd>
            </div>
            <div class="spec-row-item">
              <dt>适用人数</dt>
              <dd>{{ data.goods.serves || '—' }}</dd>
            </div>
            <div class="spec-row-item">
              <dt>保质期</dt>
              <dd>{{ data.goods.shelf_life || '—' }}</dd>
            </div>
            <div class="spec-row-item">
              <dt>产地</dt>
              <dd>{{ data.goods.origin || '—' }}</dd>
            </div>
            <div class="spec-row-item">
              <dt>分类</dt>
              <dd>{{ data.goods.categoryName || '—' }}</dd>
            </div>
          </dl>
        </section>
      </div>

      <!-- 配料 -->
      <section class="info-block card ingredients-block" v-if="data.goods.ingredients">
        <div class="block-head">
          <h3 class="block-title">
            <el-icon><Warning /></el-icon>配料表 · 过敏原提示
          </h3>
          <span class="block-tag">请过敏体质仔细查阅</span>
        </div>
        <div class="ingredients-text">{{ data.goods.ingredients }}</div>
      </section>

      <ProductReviews :reviews="data.reviews" />
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
import { ElMessage } from "element-plus";
import {
  ArrowRight, Goods, User, Timer, Star, StarFilled, ShoppingCart, ShoppingBag,
  CircleCheck, Van, Medal, Document, InfoFilled, Warning, Cherry,
} from "@element-plus/icons-vue";
import ProductReviews from '@/components/product/ProductReviews.vue'

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
  reviews: [],  // 公开商品评价
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

const loadReviews = () => {
  request.get('/reviews/goods/' + route.params.id).then(res => {
    if (res.code === '200') {
      data.reviews = res.data?.list || []
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
    })
  })
}

onMounted(() => {
  loadDetail()
  loadFavoriteStatus()
  loadAddress()
  loadReviews()
})

watch(() => route.params.id, (newId) => {
  if (newId) {
    data.qty = 1
    data.selectedSpec = ''
    data.specList = []
    loadDetail()
    loadFavoriteStatus()
    loadReviews()
  }
})
</script>

<style scoped>
.detail-page {
  padding: 20px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* —— 面包屑 —— */
.breadcrumb-bar {
  padding: 14px 20px;
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
  gap: 20px;
}

.detail-grid.two {
  grid-template-columns: 1.4fr 1fr;
}

@media (max-width: 960px) {
  .detail-grid, .detail-grid.two { grid-template-columns: 1fr; }
}

/* —— 图片区 —— */
.gallery-card {
  padding: 16px;
}

.main-image {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
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
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.goods-title {
  font-size: 24px;
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
  padding: 18px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
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

.pv-symbol { font-size: 18px; font-weight: 600; }
.pv-num {
  font-size: 32px;
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
  padding: 6px 16px;
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
  padding-top: 16px;
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
  width: 32px; height: 32px;
  background: var(--c-primary-soft);
  color: var(--c-primary);
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
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

/* —— 详情块 —— */
.info-block {
  padding: 20px 24px;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--c-divider);
}

.block-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.block-title .el-icon { color: var(--c-primary); }

.block-tag {
  font-size: 11px;
  color: var(--c-warning);
  background: var(--c-warning-soft);
  padding: 2px 10px;
  border-radius: var(--r-pill);
  font-weight: 600;
}

.detail-text {
  font-size: 14px;
  line-height: 1.85;
  color: var(--c-text-regular);
  white-space: pre-wrap;
}

.detail-text p {
  margin: 0 0 8px;
}

.empty-block {
  font-size: 13px;
  color: var(--c-text-secondary);
  padding: 16px 0;
  text-align: center;
}

/* —— 规格参数表 —— */
.spec-table {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.spec-row-item {
  display: flex;
  padding: 12px 0;
  border-bottom: 1px dashed var(--c-border-light);
  font-size: 13px;
}

.spec-row-item:last-child { border-bottom: none; }

.spec-row-item dt {
  width: 90px;
  color: var(--c-text-secondary);
  font-weight: 500;
  margin: 0;
}

.spec-row-item dd {
  flex: 1;
  color: var(--c-text-primary);
  margin: 0;
  line-height: 1.6;
}

/* —— 配料块 —— */
.ingredients-block .ingredients-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--c-text-regular);
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
