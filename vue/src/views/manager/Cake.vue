<template>
  <div class="cake-page">
    <!-- 分类胶囊条 -->
    <div class="category-bar card">
      <div class="cat-scroll">
        <div class="cat-chip"
          :class="{ active: data.categoryId === 0 }"
          @click="setCategory(0)">
          <el-icon><Grid /></el-icon>
          <span>全部</span>
        </div>
        <div v-for="c in data.categoryList" :key="c.id"
          class="cat-chip"
          :class="{ active: data.categoryId === c.id }"
          @click="setCategory(c.id)">
          <el-icon><component :is="categoryIcon(c.name)" /></el-icon>
          <span>{{ c.name }}</span>
        </div>
      </div>
    </div>

    <!-- 搜索 + 排序 -->
    <div class="toolbar card">
      <el-input
        v-model="data.name"
        placeholder="搜索蛋糕名称、口味"
        :prefix-icon="Search"
        clearable
        class="toolbar-search"
        @keyup.enter="load"
        @clear="load"
      />
      <el-button type="primary" round @click="load">
        <el-icon style="margin-right: 4px"><Search /></el-icon>搜索
      </el-button>
      <el-button round @click="reset">重置</el-button>
      <div class="toolbar-right">
        <span class="result-count">共 <b>{{ data.total }}</b> 款</span>
      </div>
    </div>

    <!-- 商品网格 -->
    <div v-if="data.tableData.length" class="goods-grid">
      <article v-for="item in data.tableData" :key="item.id" class="goods-card" @click="goDetail(item.id)">
        <div class="goods-img-wrap">
          <img :src="item.img" :alt="item.name" class="goods-img" />
          <div class="goods-overlay">
            <button class="overlay-btn" @click.stop="toggleFav(item.id)" :class="{ active: data.favoritedIds[item.id] }">
              <el-icon><Star v-if="!data.favoritedIds[item.id]" /><StarFilled v-else /></el-icon>
            </button>
            <div class="overlay-detail-hint">
              <el-icon><View /></el-icon>
              <span>查看详情</span>
            </div>
          </div>
          <div class="goods-badge" v-if="item.categoryName">{{ item.categoryName }}</div>
          <div class="goods-stock" :class="{ 'out': item.num === 0 }">
            <template v-if="item.num === 0">已售罄</template>
            <template v-else-if="item.num <= 5">仅剩 {{ item.num }}{{ item.unit }}</template>
            <template v-else>现货充足</template>
          </div>
        </div>
        <div class="goods-info">
          <h3 class="goods-name line1">{{ item.name }}</h3>
          <p class="goods-desc line2">{{ item.description || '手工制作，甜蜜呈现' }}</p>
          <div class="goods-bottom">
            <div class="goods-price">
              <span class="price-symbol">¥</span>
              <span class="price-num">{{ item.price }}</span>
              <span class="price-unit">/{{ item.unit }}</span>
            </div>
            <el-button
              type="primary"
              class="buy-btn"
              :disabled="item.num === 0"
              @click.stop="reserveInit(item.id)"
              round>
              <el-icon style="margin-right: 4px"><ShoppingCart /></el-icon>立即预订
            </el-button>
          </div>
        </div>
      </article>
    </div>

    <div v-else class="empty-state card">
      <el-icon :size="64"><Cherry /></el-icon>
      <p>暂无符合条件的蛋糕，试试其他关键词</p>
    </div>

    <!-- 分页 -->
    <div class="pagination card" v-if="data.total > 0">
      <el-pagination
        @current-change="load"
        background
        layout="total, prev, pager, next"
        v-model:page-size="data.pageSize"
        v-model:current-page="data.pageNum"
        :total="data.total"/>
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
        <el-form-item label="预订数量" prop="num">
          <el-input-number v-model="data.form.num" :min="1" :max="99" />
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
import { reactive, ref, watch, markRaw, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import request from "@/utils/request";
import { ElMessage } from "element-plus";
import {
  Search, Grid, Cherry, Sunset, Present, GobletSquare, MagicStick, Watch, Medal, Trophy,
  Star, StarFilled, ShoppingCart, ShoppingBag, View,
} from "@element-plus/icons-vue";

const route = useRoute()
const router = useRouter()
const formRef = ref()

// 分类图标：概念化设计（与 Manager.vue 一致），不走水果路线以契合简约时尚风格
const iconMap = {
  '情侣': markRaw(Sunset),
  '童趣': markRaw(Present),
  '聚会': markRaw(GobletSquare),
  '女神': markRaw(MagicStick),
  '潮男': markRaw(Watch),
  '长辈': markRaw(Medal),
  '宴席': markRaw(Trophy),
}
const categoryIcon = (name) => iconMap[name] || Grid

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  form: {},
  formVisible: false,
  name: route.query.name || null,
  categoryId: 0,
  categoryList: [],
  pageNum: 1,
  pageSize: 12,
  total: 0,
  tableData: [],
  addressList: [],
  favoritedIds: {},
})

const rules = {
  num: [{ required: true, message: '请输入数量', trigger: 'blur' }],
  addressId: [{ required: true, message: '请选择地址', trigger: 'change' }],
}

const loadFavorites = () => {
  request.get('/favorite/list').then(res => {
    if (res.code === '200') {
      const map = {}
      ;(res.data || []).forEach(g => { map[g.id] = true })
      data.favoritedIds = map
    }
  })
}

const toggleFav = (goodsId) => {
  if (data.favoritedIds[goodsId]) {
    request.delete('/favorite/remove/' + goodsId).then(res => {
      if (res.code === '200') {
        data.favoritedIds[goodsId] = false
        ElMessage.success('已取消收藏')
      } else { ElMessage.error(res.msg) }
    })
  } else {
    request.post('/favorite/add', { goods_id: goodsId }).then(res => {
      if (res.code === '200') {
        data.favoritedIds[goodsId] = true
        ElMessage.success('已加入收藏')
      } else { ElMessage.error(res.msg) }
    })
  }
}

const loadAddress = () => {
  request.get('/address/selectAll', { params: { userId: data.user.id } }).then(res => {
    if (res.code === '200') data.addressList = res.data
    else ElMessage.error(res.msg)
  })
}

const loadCategory = () => {
  request.get('/category/selectAll').then(res => {
    if (res.code === '200') {
      data.categoryList = res.data
      const categoryName = route.query.categoryName
      if (categoryName) {
        const matched = res.data.find(c => c.name === categoryName)
        data.categoryId = matched ? matched.id : 0
      }
      load()
    } else { ElMessage.error(res.msg) }
  })
}

const setCategory = (id) => {
  data.categoryId = id
  data.pageNum = 1
  load()
}

const goDetail = (id) => {
  router.push('/manager/cake/' + id)
}

const reserveInit = (goodsId) => {
  // 默认选中 is_default 的地址；找不到时为 null，由表单 required 校验拦下
  const defaultAddr = data.addressList.find(a => a.isDefault) || null
  data.form = {
    userId: data.user.id,
    goodsId,
    num: 1,
    addressId: defaultAddr ? defaultAddr.id : null,
  }
  data.formVisible = true
}

const load = () => {
  request.get('/goods/selectPage', {
    params: {
      pageNum: data.pageNum,
      pageSize: data.pageSize,
      name: data.name,
      categoryId: data.categoryId,
    }
  }).then(res => {
    if (res.code === '200') {
      data.tableData = res.data?.list || []
      data.total = res.data?.total || 0
    } else { ElMessage.error(res.msg) }
  })
}

const save = () => {
  formRef.value.validate(valid => {
    if (!valid) return
    request.post('/orders/add', data.form).then(res => {
      if (res.code === '200') {
        ElMessage.success('预订成功，等待商家配送')
        data.formVisible = false
        load()
      } else { ElMessage.error(res.msg) }
    })
  })
}

const reset = () => {
  data.name = null
  data.categoryId = 0
  data.pageNum = 1
  load()
}

onMounted(() => {
  loadAddress()
  loadCategory()
  loadFavorites()
})

watch(() => route.query.categoryName, (newName) => {
  if (newName) {
    const matched = data.categoryList.find(c => c.name === newName)
    data.categoryId = matched ? matched.id : 0
  } else {
    data.categoryId = 0
  }
  data.pageNum = 1
  load()
})

watch(() => route.query.name, (n) => {
  if (n !== undefined) {
    data.name = n
    data.pageNum = 1
    load()
  }
})
</script>

<style scoped>
.cake-page {
  padding: 20px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* —— 分类胶囊 —— */
.category-bar {
  padding: 12px 16px;
}

.cat-scroll {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.cat-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--r-pill);
  background: var(--c-bg-soft);
  color: var(--c-text-regular);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  border: 1px solid transparent;
  transition: all var(--t-fast) var(--ease-out);
}

.cat-chip:hover {
  background: var(--c-primary-soft);
  color: var(--c-primary);
}

.cat-chip.active {
  background: var(--grad-primary);
  color: #fff;
  box-shadow: 0 4px 12px rgba(184, 148, 31, 0.28);
}

/* —— 工具条 —— */
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
}

.toolbar-search {
  max-width: 320px;
}

.toolbar-search :deep(.el-input__wrapper) {
  border-radius: var(--r-pill);
}

.toolbar-right {
  margin-left: auto;
}

.result-count {
  font-size: 13px;
  color: var(--c-text-secondary);
}

.result-count b {
  color: var(--c-primary);
  font-size: 15px;
}

/* —— 商品卡片网格 —— */
.goods-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

@media (max-width: 1200px) { .goods-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 900px) { .goods-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .goods-grid { grid-template-columns: 1fr; } }

.goods-card {
  background: var(--c-bg-card);
  border-radius: var(--r-lg);
  overflow: hidden;
  border: none;
  box-shadow: var(--shadow-card);
  transition: all var(--t-base) var(--ease-out);
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

.goods-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
}

.goods-img-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: var(--c-bg-soft);
}

.goods-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--t-slow) var(--ease-out);
}

.goods-card:hover .goods-img { transform: scale(1.06); }

.goods-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.4), transparent 60%);
  opacity: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 10px;
  transition: opacity var(--t-base) var(--ease-out);
}

.goods-card:hover .goods-overlay { opacity: 1; }

.overlay-detail-hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(6px);
  color: var(--c-primary);
  font-size: 12px;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: var(--r-pill);
}

.overlay-detail-hint .el-icon { font-size: 14px; }

.overlay-btn {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(6px);
  border: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: var(--c-text-regular);
  transition: all var(--t-fast) var(--ease-out);
}

.overlay-btn:hover { transform: scale(1.1); background: var(--c-bg-card); color: var(--c-primary); }

.overlay-btn.active {
  background: var(--c-primary);
  color: #fff;
}

.goods-badge {
  position: absolute;
  top: 10px; left: 10px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--c-primary);
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--r-pill);
}

.goods-stock {
  position: absolute;
  bottom: 10px; left: 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--c-success);
  background: rgba(255, 255, 255, 0.92);
  padding: 3px 10px;
  border-radius: var(--r-pill);
}

.goods-stock.out { color: var(--c-text-secondary); }

.goods-info {
  padding: 14px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.goods-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin: 0;
}

.goods-desc {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin: 0;
  min-height: 36px;
}

.goods-bottom {
  margin-top: auto;
  padding-top: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.goods-price {
  color: var(--c-primary);
  display: flex;
  align-items: baseline;
}

.price-symbol { font-size: 14px; font-weight: 600; }
.price-num {
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
  font-feature-settings: "tnum";
}
.price-unit {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin-left: 2px;
}

.buy-btn {
  background: var(--grad-primary);
  border: none;
  font-weight: 500;
}

/* —— 分页 —— */
.pagination {
  display: flex;
  justify-content: center;
  padding: 16px;
}

/* —— 弹窗 —— */
.dialog-header-custom {
  display: flex;
  gap: 12px;
  align-items: center;
}

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

.dialog-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--c-text-primary);
}

.dialog-sub {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin-top: 2px;
}

.hint-empty {
  margin-top: 6px;
  font-size: 12px;
  color: var(--c-text-secondary);
}
</style>
