<template>
  <div class="favorite-page">
    <div class="page-head card">
      <div>
        <h2 class="page-title">我的收藏</h2>
        <p class="page-sub">收藏的蛋糕一目了然，随时下单</p>
      </div>
      <div class="head-meta">
        <span class="meta-num"><b>{{ data.allData.length }}</b> 款</span>
      </div>
    </div>

    <div class="toolbar card">
      <el-input
        v-model="data.name"
        placeholder="搜索收藏的蛋糕"
        :prefix-icon="Search"
        clearable
        class="toolbar-search"
      />
      <el-button round @click="reset">重置</el-button>
    </div>

    <div v-if="filteredData.length" class="goods-grid">
      <article v-for="item in filteredData" :key="item.id" class="goods-card" @click="$router.push('/manager/cake/' + item.id)">
        <div class="goods-img-wrap">
          <img :src="item.img" :alt="item.name" class="goods-img" />
          <div class="goods-overlay">
            <div class="overlay-detail-hint">
              <el-icon><View /></el-icon>
              <span>查看详情</span>
            </div>
          </div>
          <div class="goods-badge" v-if="item.categoryName">{{ item.categoryName }}</div>
          <div class="goods-stock" :class="{ out: item.num === 0 }">
            <template v-if="item.num === 0">已售罄</template>
            <template v-else>现货 {{ item.num }}{{ item.unit }}</template>
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
          </div>
          <div class="card-actions">
            <el-button class="ghost-btn" round size="small" @click.stop="removeFav(item.id)">
              <el-icon style="margin-right: 4px"><Delete /></el-icon>取消收藏
            </el-button>
            <el-button type="primary" class="buy-btn" round size="small" :disabled="item.num === 0" @click.stop="reserveInit(item.id)">
              <el-icon style="margin-right: 4px"><ShoppingCart /></el-icon>立即预订
            </el-button>
          </div>
        </div>
      </article>
    </div>

    <div v-else class="empty-state card">
      <el-icon :size="64"><Star /></el-icon>
      <p>还没有收藏商品，去商品页面看看吧</p>
      <el-button type="primary" round @click="$router.push('/manager/cake')">前往商城</el-button>
    </div>

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
              v-for="addr in data.addressList"
              :key="addr.id"
              :label="addr.name + ' · ' + addr.phone + ' · ' + addr.address"
              :value="addr.id"
            />
          </el-select>
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
import { reactive, ref, computed, onMounted } from "vue";
import request from "@/utils/request";
import { ElMessage } from "element-plus";
import { Search, Star, Delete, ShoppingCart, ShoppingBag, View } from "@element-plus/icons-vue";

const formRef = ref()
const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  form: {},
  formVisible: false,
  name: null,
  allData: [],
  addressList: [],
})

const rules = {
  num: [{ required: true, message: '请输入数量', trigger: 'blur' }],
  addressId: [{ required: true, message: '请选择地址', trigger: 'change' }],
}

const filteredData = computed(() => {
  if (!data.name) return data.allData
  return data.allData.filter(item => item.name.includes(data.name))
})

const load = () => {
  request.get('/favorite/list').then(res => {
    if (res.code === '200') {
      data.allData = res.data || []
    }
  })
}

const reset = () => { data.name = null }

const loadAddress = () => {
  request.get('/address/selectAll', { params: { userId: data.user.id } }).then(res => {
    if (res.code === '200') data.addressList = res.data
  })
}

const reserveInit = (goodsId) => {
  data.form = { userId: data.user.id, goodsId, num: 1 }
  data.formVisible = true
}

const save = () => {
  formRef.value.validate(valid => {
    if (!valid) return
    request.post('/orders/add', data.form).then(res => {
      if (res.code === '200') {
        ElMessage.success('预订成功，等待商家配送')
        data.formVisible = false
      } else { ElMessage.error(res.msg) }
    })
  })
}

const removeFav = (goodsId) => {
  request.delete('/favorite/remove/' + goodsId).then(res => {
    if (res.code === '200') {
      ElMessage.success('已取消收藏')
      load()
    } else { ElMessage.error(res.msg) }
  })
}

onMounted(() => {
  load()
  loadAddress()
})
</script>

<style scoped>
.favorite-page {
  padding: 20px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: linear-gradient(135deg, #fdf6e0 0%, #f5ecc8 100%);
  border: none;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--c-text-primary);
  margin: 0;
}

.page-title::before { display: none; }

.page-sub {
  font-size: 13px;
  color: var(--c-text-secondary);
  margin: 4px 0 0;
}

.head-meta {
  font-size: 13px;
  color: var(--c-text-secondary);
}

.meta-num b {
  font-size: 22px;
  color: var(--c-primary);
  margin-right: 4px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
}

.toolbar-search { max-width: 320px; }
.toolbar-search :deep(.el-input__wrapper) { border-radius: var(--r-pill); }

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

.goods-img { width: 100%; height: 100%; object-fit: cover; }

.goods-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.4), transparent 60%);
  opacity: 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
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

.goods-name { font-size: 16px; font-weight: 600; color: var(--c-text-primary); margin: 0; }
.goods-desc { font-size: 12px; color: var(--c-text-secondary); margin: 0; min-height: 36px; }

.goods-bottom {
  display: flex;
  align-items: baseline;
  justify-content: flex-start;
  margin-top: auto;
}

.goods-price { color: var(--c-primary); display: flex; align-items: baseline; }
.price-symbol { font-size: 14px; font-weight: 600; }
.price-num { font-size: 22px; font-weight: 700; line-height: 1; font-feature-settings: "tnum"; }
.price-unit { font-size: 12px; color: var(--c-text-secondary); margin-left: 2px; }

.card-actions {
  display: flex;
  gap: 8px;
  padding-top: 8px;
  margin-top: 4px;
  border-top: 1px dashed var(--c-divider);
}

.ghost-btn {
  background: var(--c-bg-soft);
  border: none;
  color: var(--c-text-regular);
}
.ghost-btn:hover { color: var(--c-danger); background: var(--c-danger-soft); }

.buy-btn { background: var(--grad-primary); border: none; }

.empty-state {
  padding: 60px 20px;
  text-align: center;
  color: var(--c-text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.dialog-header-custom { display: flex; gap: 12px; align-items: center; }
.dialog-icon {
  width: 40px; height: 40px;
  background: var(--c-primary-soft); color: var(--c-primary);
  border-radius: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 20px;
}
.dialog-title { font-size: 16px; font-weight: 600; color: var(--c-text-primary); }
.dialog-sub { font-size: 12px; color: var(--c-text-secondary); margin-top: 2px; }
</style>
