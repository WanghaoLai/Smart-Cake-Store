<template>
  <div class="cart-page" v-loading="cart.loading">
    <div class="page-head">
      <h2 class="page-title">我的购物车</h2>
      <span class="head-count" v-if="cart.items.length">共 {{ cart.count }} 件商品</span>
    </div>

    <template v-if="cart.items.length">
      <section class="cart-card card">
        <!-- 表头 -->
        <div class="cart-head">
          <div class="col-check">
            <el-checkbox :model-value="cart.allSelected" @change="v => cart.toggleSelectAll(v)">全选</el-checkbox>
          </div>
          <div class="col-goods">商品信息</div>
          <div class="col-price">单价</div>
          <div class="col-num">数量</div>
          <div class="col-subtotal">小计</div>
          <div class="col-action">操作</div>
        </div>

        <!-- 条目 -->
        <div v-for="item in cart.items" :key="item.id"
             class="cart-row" :class="{ disabled: item.stock === 0 }">
          <div class="col-check">
            <el-checkbox
              v-model="item.selected"
              :disabled="item.stock === 0"
              @change="cart.toggleSelect(item)" />
          </div>
          <div class="col-goods">
            <img :src="$fileUrl(item.goodsImg)" class="goods-img" @click="goDetail(item.goodsId)" />
            <div class="goods-info">
              <div class="goods-name line2" @click="goDetail(item.goodsId)">{{ item.goodsName }}</div>
              <el-tag v-if="item.stock === 0" type="danger" size="small" effect="light" round>已售罄</el-tag>
              <el-tag v-else-if="item.num > item.stock" type="warning" size="small" effect="light" round>
                库存仅剩 {{ item.stock }} {{ item.goodsUnit }}
              </el-tag>
            </div>
          </div>
          <div class="col-price">¥{{ Number(item.goodsPrice).toFixed(2) }}</div>
          <div class="col-num">
            <el-input-number
              v-model="item.num"
              :min="1"
              :max="Math.max(1, item.stock)"
              :disabled="item.stock === 0"
              size="small"
              @change="onNumChange(item)" />
          </div>
          <div class="col-subtotal">¥{{ (Number(item.goodsPrice) * item.num).toFixed(2) }}</div>
          <div class="col-action">
            <el-button link type="danger" size="small" @click="removeOne(item)">删除</el-button>
          </div>
        </div>
      </section>

      <!-- 结算栏 -->
      <section class="settle-bar card">
        <div class="settle-left">
          <el-checkbox :model-value="cart.allSelected" @change="v => cart.toggleSelectAll(v)">全选</el-checkbox>
          <el-button v-if="cart.selectedItems.length" link type="danger" size="small" @click="removeSelected">
            删除选中（{{ cart.selectedItems.length }}）
          </el-button>
        </div>
        <div class="settle-right">
          <span class="settle-info">已选 <b>{{ cart.selectedCount }}</b> 件</span>
          <span class="settle-total">合计：<b>¥{{ cart.selectedTotal.toFixed(2) }}</b></span>
          <el-button type="primary" round size="large" class="settle-btn"
                     :disabled="!cart.selectedItems.length" @click="openCheckout">
            去结算（{{ cart.selectedItems.length }}）
          </el-button>
        </div>
      </section>
    </template>

    <!-- 空态 -->
    <div v-else class="cart-empty card">
      <el-icon :size="64"><ShoppingCart /></el-icon>
      <p>购物车还是空的</p>
      <span>去挑一款心仪的蛋糕吧</span>
      <el-button type="primary" round @click="router.push('/manager/cake')">去逛逛</el-button>
    </div>

    <!-- 结算弹窗 -->
    <el-dialog v-model="checkoutVisible" width="460px" :close-on-click-modal="false" destroy-on-close>
      <template #header>
        <div class="dialog-head">
          <el-icon class="dialog-icon"><ShoppingBag /></el-icon>
          <div>
            <div class="dialog-title">确认结算</div>
            <div class="dialog-sub">{{ cart.selectedItems.length }} 件商品 · 合计 ¥{{ cart.selectedTotal.toFixed(2) }}</div>
          </div>
        </div>
      </template>
      <el-form label-position="top">
        <el-form-item label="收货地址" required>
          <el-select v-model="addressId" placeholder="请选择收货地址" style="width: 100%">
            <el-option v-for="a in addressList" :key="a.id"
                       :label="a.name + ' · ' + a.phone + ' · ' + a.address" :value="a.id" />
          </el-select>
          <div v-if="!addressList.length" class="hint-empty">
            还没有收货地址，<router-link to="/manager/address">去添加</router-link>
          </div>
        </el-form-item>
        <div class="checkout-summary">
          <div v-for="i in cart.selectedItems" :key="i.id" class="summary-row">
            <span class="line1">{{ i.goodsName }} × {{ i.num }}</span>
            <span>¥{{ (Number(i.goodsPrice) * i.num).toFixed(2) }}</span>
          </div>
          <div class="summary-row total">
            <span>应付总额（余额支付）</span>
            <b>¥{{ cart.selectedTotal.toFixed(2) }}</b>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button round @click="checkoutVisible = false">取消</el-button>
        <el-button type="primary" round :loading="submitting" :disabled="!addressId" @click="submitCheckout">
          确认支付 ¥{{ cart.selectedTotal.toFixed(2) }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ShoppingCart, ShoppingBag } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { useCartStore } from '@/stores/cart'

const router = useRouter()
const cart = useCartStore()

const checkoutVisible = ref(false)
const submitting = ref(false)
const addressId = ref(null)
const addressList = ref([])

const goDetail = (goodsId) => router.push('/manager/cake/' + goodsId)

const onNumChange = async (item) => {
  if (item.num < 1) return
  const res = await cart.updateNum(item)
  if (res.code !== '200') {
    ElMessage.error(res.msg || '修改数量失败')
    await cart.loadCart()
  }
}

const removeOne = async (item) => {
  const res = await cart.removeOne(item.id)
  if (res.code === '200') ElMessage.success('已移出购物车')
  else ElMessage.error(res.msg)
}

const removeSelected = () => {
  ElMessageBox.confirm(`确定删除选中的 ${cart.selectedItems.length} 件商品吗？`, '删除确认', { type: 'warning' })
    .then(async () => {
      const res = await cart.removeBatch(cart.selectedItems.map(i => i.id))
      if (res.code === '200') ElMessage.success('删除成功')
      else ElMessage.error(res.msg)
    }).catch(() => {})
}

const openCheckout = async () => {
  addressId.value = null
  const res = await request.get('/address/selectAll', {
    params: { userId: JSON.parse(localStorage.getItem('system-user') || '{}').id },
  })
  if (res.code === '200') {
    addressList.value = res.data || []
    const def = addressList.value.find(a => a.isDefault) || addressList.value[0]
    if (def) addressId.value = def.id
  }
  checkoutVisible.value = true
}

const submitCheckout = () => {
  if (!addressId.value || submitting.value) return
  submitting.value = true
  cart.checkout(cart.selectedItems.map(i => i.id), addressId.value)
    .then(res => {
      if (res.code === '200') {
        checkoutVisible.value = false
        ElMessage.success(`结算成功，已生成 ${res.data.order_nos.length} 笔订单`)
      } else {
        ElMessage.error(res.msg)
      }
    })
    .catch(() => ElMessage.error('结算失败，请稍后重试'))
    .finally(() => { submitting.value = false })
}

onMounted(() => cart.loadCart())
</script>

<style scoped>
.cart-page {
  padding: 20px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.page-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.page-head .page-title { margin: 0; }

.head-count {
  font-size: 13px;
  color: var(--c-text-secondary);
}

/* —— 列表卡片 —— */
.cart-card { padding: 8px 20px; }

.cart-head, .cart-row {
  display: grid;
  grid-template-columns: 70px 1fr 110px 150px 110px 70px;
  align-items: center;
  gap: 8px;
}

.cart-head {
  padding: 12px 0;
  font-size: 13px;
  color: var(--c-text-secondary);
  font-weight: 600;
  border-bottom: 1px dashed var(--c-divider);
}

.cart-row {
  padding: 16px 0;
  border-bottom: 1px dashed var(--c-border-light);
  transition: background var(--t-fast) var(--ease-out);
}

.cart-row:last-child { border-bottom: none; }
.cart-row:hover { background: var(--c-bg-soft); border-radius: var(--r-md); }
.cart-row.disabled .col-goods, .cart-row.disabled .col-price { opacity: 0.55; }

.col-price, .col-subtotal { font-size: 14px; color: var(--c-text-primary); }
.col-subtotal { font-weight: 700; color: var(--c-primary); }
.col-action { text-align: center; }

.goods-img {
  width: 72px;
  height: 72px;
  border-radius: var(--r-sm);
  object-fit: cover;
  background: var(--c-bg-soft);
  cursor: pointer;
  flex-shrink: 0;
}

.col-goods { display: flex; align-items: center; gap: 12px; min-width: 0; }

.goods-info { display: flex; flex-direction: column; gap: 6px; min-width: 0; }

.goods-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
  cursor: pointer;
  line-height: 1.4;
}

.goods-name:hover { color: var(--c-primary); }

/* —— 结算栏 —— */
.settle-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  position: sticky;
  bottom: 12px;
}

.settle-left { display: flex; align-items: center; gap: 16px; }

.settle-right { display: flex; align-items: center; gap: 18px; }

.settle-info { font-size: 13px; color: var(--c-text-secondary); }
.settle-info b { color: var(--c-primary); }

.settle-total { font-size: 14px; color: var(--c-text-primary); }
.settle-total b { font-size: 22px; color: var(--c-primary); font-weight: 700; }

.settle-btn {
  background: var(--grad-primary);
  border: none;
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(168, 138, 63, 0.28);
  min-width: 140px;
}

/* —— 空态 —— */
.cart-empty {
  padding: 80px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: var(--c-text-secondary);
}

.cart-empty .el-icon { color: var(--c-text-placeholder); }
.cart-empty p { margin: 0; font-size: 16px; font-weight: 600; color: var(--c-text-primary); }
.cart-empty span { font-size: 13px; margin-bottom: 8px; }

/* —— 弹窗 —— */
.dialog-head { display: flex; gap: 12px; align-items: center; }
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

.checkout-summary {
  margin-top: 4px;
  padding: 12px 14px;
  background: var(--c-bg-soft);
  border-radius: var(--r-md);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  color: var(--c-text-regular);
}

.summary-row.total {
  padding-top: 8px;
  border-top: 1px dashed var(--c-border);
  font-size: 14px;
}

.summary-row.total b { color: var(--c-primary); font-size: 16px; }

.hint-empty { margin-top: 6px; font-size: 12px; color: var(--c-text-secondary); }

@media (max-width: 860px) {
  .cart-head { display: none; }
  .cart-row {
    grid-template-columns: 40px 1fr auto;
    grid-template-areas:
      "check goods subtotal"
      "check num action";
  }
  .col-check { grid-area: check; }
  .col-goods { grid-area: goods; }
  .col-num { grid-area: num; }
  .col-subtotal { grid-area: subtotal; }
  .col-action { grid-area: action; text-align: right; }
  .col-price { display: none; }
  .settle-bar { flex-direction: column; gap: 10px; align-items: stretch; }
  .settle-right { justify-content: flex-end; }
}
</style>
