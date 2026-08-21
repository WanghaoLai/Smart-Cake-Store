<template>
  <div class="admin-page">
    <div class="toolbar card">
      <el-input v-model="data.name" placeholder="请输入商品名称查询" :prefix-icon="Search" clearable class="toolbar-search" @keyup.enter="load" @clear="load" />
      <el-button type="primary" round @click="load"><el-icon style="margin-right:4px"><Search /></el-icon>查询</el-button>
      <el-button round @click="reset">重置</el-button>
      <!-- 状态筛选：用单选 chip 组而非下拉，让用户/管理员一眼看清订单生命周期 -->
      <div class="status-tabs">
        <button
          v-for="opt in statusOptions"
          :key="opt.value"
          class="status-chip"
          :class="{ active: data.status === opt.value }"
          @click="switchStatus(opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <div class="card table-card">
      <el-table :data="data.tableData" stripe class="admin-table">
        <el-table-column label="订单号" prop="order_no" width="200">
          <template #default="scope">
            <div class="order-no-cell">
              <el-icon class="order-icon"><Tickets /></el-icon>
              <span class="order-no-text">{{ scope.row.order_no }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="商品" prop="goodsName" min-width="240">
          <template #default="scope">
            <div class="goods-cell">
              <img v-if="scope.row.goodsImg" :src="$fileUrl(scope.row.goodsImg)" class="cell-img" alt="" />
              <div v-else class="cell-img placeholder"><el-icon><Picture /></el-icon></div>
              <div class="goods-info-cell">
                <div class="goods-name-cell line1">{{ scope.row.goodsName }}</div>
                <div class="goods-meta-cell">¥{{ scope.row.goodsPrice }} / {{ scope.row.goodsUnit }} × {{ scope.row.num }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="总价" prop="total" width="100">
          <template #default="scope">
            <span class="cell-price">¥{{ scope.row.total }}</span>
          </template>
        </el-table-column>
        <el-table-column label="收货信息" min-width="220">
          <template #default="scope">
            <div class="addr-cell">
              <div class="addr-name">{{ scope.row.aName }} · {{ scope.row.aPhone }}</div>
              <div class="addr-detail line1">{{ scope.row.aAddress }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="下单用户" prop="userName" width="110" v-if="data.user.role === '管理员'">
          <template #default="scope">
            <span class="user-tag">{{ scope.row.userName }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="scope">
            <span class="status-tag" :class="statusClass(scope.row.status)">{{ scope.row.status || '待发货' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" align="center" width="280">
          <template #default="scope">
            <div class="row-actions">
              <!-- 管理员：待发货 -> 标记发货 -->
              <el-button v-if="data.user.role === '管理员' && scope.row.status === '待发货'" text type="primary" size="small" @click="handleShip(scope.row.id)">
                <el-icon><Van /></el-icon>标记发货
              </el-button>
              <!-- 用户：已发货 -> 确认签收（合并到"待评价"语义） -->
              <el-button v-if="data.user.role === '用户' && scope.row.status === '已发货'" text type="success" size="small" @click="handleConfirm(scope.row.id)">
                <el-icon><CircleCheck /></el-icon>确认签收
              </el-button>
              <!-- 用户：待评价 -> 去评价（打开评价弹窗） -->
              <el-button v-if="data.user.role === '用户' && scope.row.status === '待评价'" text type="primary" size="small" @click="openReview(scope.row)">
                <el-icon><StarFilled /></el-icon>去评价
              </el-button>
              <!-- 通用：待发货/已发货 可取消；角色权限在后端状态机校验 -->
              <el-button v-if="canCancel(scope.row.status)" text type="warning" size="small" @click="handleCancel(scope.row.id)">
                <el-icon><CloseBold /></el-icon>取消
              </el-button>
              <el-button text type="danger" size="small" @click="handleDelete(scope.row.id)">
                <el-icon><Delete /></el-icon>删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card pagination-card">
      <el-pagination @current-change="load" background layout="total, prev, pager, next" v-model:page-size="data.pageSize" v-model:current-page="data.pageNum" :total="data.total"/>
    </div>

    <!-- 评价弹窗：星级 + 文本 + 多图上传 -->
    <el-dialog v-model="data.reviewVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <template #header>
        <div class="dialog-header-custom">
          <el-icon class="dialog-icon"><StarFilled /></el-icon>
          <div>
            <div class="dialog-title">评价商品</div>
            <div class="dialog-sub">您的评价将公开展示在商品详情页</div>
          </div>
        </div>
      </template>
      <el-form ref="reviewFormRef" :model="data.reviewForm" :rules="reviewRules" label-position="top">
        <el-form-item label="商品">
          <div class="review-goods">
            <img :src="$fileUrl(data.reviewForm.goodsImg)" class="review-goods-img" v-if="data.reviewForm.goodsImg" />
            <div class="review-goods-info">
              <div class="review-goods-name line1">{{ data.reviewForm.goodsName }}</div>
              <div class="review-goods-meta">订单号 {{ data.reviewForm.orderNo || '—' }}</div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="总体评分" prop="rating">
          <el-rate v-model="data.reviewForm.rating" :texts="['很差', '较差', '一般', '满意', '非常满意']" show-text />
        </el-form-item>
        <el-form-item label="评价内容" prop="content">
          <el-input
            v-model="data.reviewForm.content"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            placeholder="分享商品质量、口感、配送体验..."
          />
        </el-form-item>
        <el-form-item label="上传图片（最多 5 张）">
          <el-upload
            :action="uploadUrl"
            :headers="uploadHeaders"
            :file-list="data.reviewForm.fileList"
            list-type="picture-card"
            :limit="5"
            :on-success="handleUploadSuccess"
            :on-remove="handleUploadRemove"
            :on-exceed="() => ElMessage.warning('最多上传 5 张图片')"
            accept="image/*"
          >
            <el-icon><Plus /></el-icon>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="data.reviewVisible = false" round>取消</el-button>
        <el-button type="primary" @click="submitReview" round :loading="data.reviewSubmitting">提交评价</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from "vue";
import request from "@/utils/request";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Search, Delete, Tickets, Picture, Van, CircleCheck, CloseBold, StarFilled, Plus,
} from "@element-plus/icons-vue";

// 状态筛选选项：覆盖订单完整生命周期（已签收已合并为待评价）
const statusOptions = [
  { label: '全部', value: '' },
  { label: '待发货', value: '待发货' },
  { label: '已发货', value: '已发货' },
  { label: '待评价', value: '待评价' },
  { label: '已评价', value: '已评价' },
  { label: '已取消', value: '已取消' },
]

const STATUS_CLASS = {
  '待发货': 'st-pending',
  '已发货': 'st-shipped',
  '待评价': 'st-review',
  '已评价': 'st-reviewed',
  '已取消': 'st-cancelled',
}
const statusClass = (s) => STATUS_CLASS[s] || 'st-pending'
const canCancel = (s) => s === '待发货' || s === '已发货'

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  name: null,
  status: '',
  pageNum: 1,
  pageSize: 10,
  total: 0,
  tableData: [],
  // 评价弹窗状态
  reviewVisible: false,
  reviewSubmitting: false,
  reviewForm: {
    orderId: null,
    goodsId: null,
    goodsName: '',
    goodsImg: '',
    orderNo: '',
    rating: 5,
    content: '',
    fileList: [],   // el-upload 显示用
    images: [],     // 已上传 URL 列表
  },
})

const reviewFormRef = ref()
const reviewRules = {
  rating: [{ required: true, message: '请选择评分', trigger: 'change' }],
  content: [{ required: true, message: '请填写评价内容', trigger: 'blur' }],
}

// 上传地址 + 鉴权头：复用 axios 拦截器里同款 token
const uploadUrl = computed(() => (import.meta.env.VITE_BASE_URL || '') + '/files/upload_review')
const uploadHeaders = computed(() => ({
  Authorization: 'Bearer ' + localStorage.getItem('token'),
}))

const load = () => {
  request.get('/orders/selectPage', {
    params: {
      pageNum: data.pageNum,
      pageSize: data.pageSize,
      goodsName: data.name,
      status: data.status,
      userId: data.user.role === '用户' ? data.user.id : 0
    }
  }).then(res => {
    if (res.code === '200') {
      data.tableData = res.data?.list || []
      data.total = res.data?.total || 0
    } else { ElMessage.error(res.msg) }
  })
}
load()

const switchStatus = (v) => {
  data.status = v
  data.pageNum = 1
  load()
}

// 统一的状态变更入口：角色权限与状态合法性都在后端状态机校验
const _callStatus = (id, status, label) =>
  ElMessageBox.confirm(`确定将订单${label}吗？`, '操作确认', { type: 'warning' })
    .then(() => request.put(`/orders/update_status/${id}`, null, { params: { status } }))
    .then(res => {
      if (res.code === '200') { load(); ElMessage.success('操作成功') } else { ElMessage.error(res.msg) }
    })
    .catch(() => {})

const handleShip = (id) => _callStatus(id, '已发货', '标记为已发货')
// 用户确认签收 = 进入"待评价"（签收的本质就是等待评价）
const handleConfirm = (id) => _callStatus(id, '待评价', '确认签收')
const handleCancel = (id) => _callStatus(id, '已取消', '取消')

const handleDelete = (id) => {
  ElMessageBox.confirm('删除后数据无法恢复，您确定删除吗?', '删除确认', { type: 'warning' }).then(res => {
    request.delete('/orders/delete/' + id).then(res => {
      if (res.code === '200') { load(); ElMessage.success('操作成功') } else { ElMessage.error(res.msg) }
    })
  }).catch(() => {})
}

// ============ 评价 ============
const openReview = (row) => {
  data.reviewForm = {
    orderId: row.id,
    goodsId: row.goodsId,
    goodsName: row.goodsName,
    goodsImg: row.goodsImg,
    orderNo: row.order_no,
    rating: 5,
    content: '',
    fileList: [],
    images: [],
  }
  data.reviewVisible = true
}

const handleUploadSuccess = (res, file, fileList) => {
  if (res.code === '200') {
    data.reviewForm.images.push(res.data)
    data.reviewForm.fileList = fileList
  } else {
    ElMessage.error(res.msg || '上传失败')
  }
}

const handleUploadRemove = (file, fileList) => {
  // 用 url 匹配剔除被删的图片
  const removed = file.response?.data
  data.reviewForm.images = data.reviewForm.images.filter(u => u !== removed)
  data.reviewForm.fileList = fileList
}

const submitReview = () => {
  reviewFormRef.value.validate(valid => {
    if (!valid) return
    data.reviewSubmitting = true
    request.post('/reviews/add', {
      orderId: data.reviewForm.orderId,
      goodsId: data.reviewForm.goodsId,
      rating: data.reviewForm.rating,
      content: data.reviewForm.content,
      // 后端约定 images 为 JSON 字符串
      images: JSON.stringify(data.reviewForm.images || []),
    }).then(res => {
      if (res.code === '200') {
        ElMessage.success('评价已提交，感谢您的反馈')
        data.reviewVisible = false
        load()
      } else {
        ElMessage.error(res.msg)
      }
    }).finally(() => {
      data.reviewSubmitting = false
    })
  })
}

const reset = () => { data.name = null; data.status = ''; data.pageNum = 1; load() }
</script>

<style scoped>
@import './_admin-base.css';

.order-no-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.order-icon { color: var(--c-primary); font-size: 14px; }

.order-no-text {
  font-family: ui-monospace, "SFMono-Regular", monospace;
  font-size: 12px;
  color: var(--c-text-regular);
}

.goods-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cell-img.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--c-bg-soft);
  color: var(--c-text-placeholder);
}

.goods-info-cell {
  flex: 1;
  min-width: 0;
}

.goods-name-cell {
  font-weight: 600;
  color: var(--c-text-primary);
  font-size: 14px;
}

.goods-meta-cell {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin-top: 2px;
}

.addr-cell { display: flex; flex-direction: column; }
.addr-name { font-size: 13px; color: var(--c-text-primary); font-weight: 500; }
.addr-detail { font-size: 12px; color: var(--c-text-secondary); margin-top: 2px; }

.user-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  background: var(--c-accent-soft);
  color: var(--c-accent);
  border-radius: var(--r-pill);
  font-size: 12px;
  font-weight: 600;
}

/* —— 状态筛选 chip 组 —— */
.status-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 3px;
  background: var(--c-bg-soft);
  border-radius: var(--r-pill);
}

.status-chip {
  border: none;
  background: transparent;
  color: var(--c-text-secondary);
  padding: 5px 14px;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--r-pill);
  cursor: pointer;
  transition: all var(--t-fast) var(--ease-out);
}

.status-chip:hover { color: var(--c-text-primary); }

.status-chip.active {
  background: var(--c-bg-card);
  color: var(--c-primary);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

/* —— 状态徽标 —— */
.status-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 12px;
  border-radius: var(--r-pill);
  font-size: 12px;
  font-weight: 600;
  min-width: 64px;
  justify-content: center;
}

.status-tag.st-pending {
  background: var(--c-warning-soft);
  color: var(--c-warning);
}
.status-tag.st-shipped {
  background: var(--c-primary-soft);
  color: var(--c-primary);
}
.status-tag.st-review {
  background: var(--c-success-soft);
  color: var(--c-success);
}
.status-tag.st-reviewed {
  background: var(--c-accent-soft);
  color: var(--c-accent);
}
.status-tag.st-cancelled {
  background: var(--c-info-soft);
  color: var(--c-info);
  text-decoration: line-through;
}

/* —— 行内操作按钮组 —— */
.row-actions {
  display: inline-flex;
  flex-wrap: nowrap;
  justify-content: center;
  align-items: center;
  gap: 0;
}

/* text 按钮默认左右 padding 偏大，紧一下保证单行不换行 */
.row-actions :deep(.el-button) {
  padding: 0 6px;
  height: 28px;
}
.row-actions :deep(.el-button .el-icon) {
  margin-right: 2px;
  font-size: 13px;
}

/* —— 评价弹窗 —— */
.review-goods {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 8px 12px;
  background: var(--c-bg-soft);
  border-radius: var(--r-md);
}
.review-goods-img {
  width: 56px; height: 56px;
  border-radius: 8px;
  object-fit: cover;
}
.review-goods-info { flex: 1; min-width: 0; }
.review-goods-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
}
.review-goods-meta {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin-top: 2px;
}
</style>
