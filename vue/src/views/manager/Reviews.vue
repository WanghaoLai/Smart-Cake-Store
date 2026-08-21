<template>
  <div class="admin-page">
    <div class="toolbar card">
      <el-input v-model="data.goodsName" placeholder="请输入商品名称查询" :prefix-icon="Search" clearable class="toolbar-search" @keyup.enter="load" @clear="load" />
      <el-select v-model="data.rating" placeholder="全部星级" clearable class="rating-filter" @change="load">
        <el-option :value="5" label="5 星" />
        <el-option :value="4" label="4 星" />
        <el-option :value="3" label="3 星" />
        <el-option :value="2" label="2 星" />
        <el-option :value="1" label="1 星" />
      </el-select>
      <el-button type="primary" round @click="load"><el-icon style="margin-right:4px"><Search /></el-icon>查询</el-button>
      <el-button round @click="reset">重置</el-button>
    </div>

    <div class="card table-card">
      <el-table :data="data.tableData" stripe class="admin-table">
        <el-table-column label="商品" min-width="240">
          <template #default="scope">
            <div class="goods-cell">
              <img v-if="scope.row.goodsImg" :src="$fileUrl(scope.row.goodsImg)" class="cell-img" alt="" />
              <div v-else class="cell-img placeholder"><el-icon><Picture /></el-icon></div>
              <div class="goods-info-cell">
                <div class="goods-name-cell line1">{{ scope.row.goodsName }}</div>
                <div class="goods-meta-cell">订单号 {{ scope.row.orderId || '—' }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="评价用户" width="120">
          <template #default="scope">
            <span class="user-tag">{{ scope.row.userName || '匿名' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="评分" width="160">
          <template #default="scope">
            <el-rate :model-value="scope.row.rating" disabled size="small" />
          </template>
        </el-table-column>
        <el-table-column label="评价内容" min-width="280">
          <template #default="scope">
            <div class="review-content line-clamp">{{ scope.row.content || '—' }}</div>
            <div class="review-thumbs" v-if="scope.row.images && scope.row.images.length">
              <el-image
                v-for="(img, idx) in scope.row.images"
                :key="idx"
                :src="$fileUrl(img)"
                :preview-src-list="scope.row.images"
                :initial-index="idx"
                preview-teleported
                class="thumb"
                fit="cover"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="评价时间" width="160">
          <template #default="scope">{{ scope.row.time || '—' }}</template>
        </el-table-column>
        <el-table-column label="商家回复" min-width="200">
          <template #default="scope">
            <div v-if="scope.row.reply" class="reply-cell">
              <div class="reply-text line-clamp">{{ scope.row.reply }}</div>
              <div class="reply-time">{{ scope.row.replyTime }}</div>
            </div>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" align="center" width="140">
          <template #default="scope">
            <el-button text type="primary" size="small" @click="openReply(scope.row)">
              <el-icon><ChatLineSquare /></el-icon>{{ scope.row.reply ? '修改回复' : '回复' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card pagination-card">
      <el-pagination
        @current-change="load"
        background
        layout="total, prev, pager, next"
        v-model:page-size="data.pageSize"
        v-model:current-page="data.pageNum"
        :total="data.total"
      />
    </div>

    <!-- 回复弹窗 -->
    <el-dialog v-model="data.replyVisible" width="520px" :close-on-click-modal="false" destroy-on-close>
      <template #header>
        <div class="dialog-header-custom">
          <el-icon class="dialog-icon"><ChatLineSquare /></el-icon>
          <div>
            <div class="dialog-title">{{ data.replyForm.existed ? '修改商家回复' : '回复评价' }}</div>
            <div class="dialog-sub">回复将公开展示在商品详情页</div>
          </div>
        </div>
      </template>
      <div class="reply-context">
        <div class="reply-context-head">
          <el-rate :model-value="data.replyForm.rating" disabled size="small" />
          <span class="reply-context-user">{{ data.replyForm.userName }}</span>
        </div>
        <div class="reply-context-text">{{ data.replyForm.content || '（无文字评价）' }}</div>
      </div>
      <el-input
        v-model="data.replyForm.reply"
        type="textarea"
        :rows="4"
        maxlength="500"
        show-word-limit
        placeholder="请输入回复内容，友善、专业地解答用户问题..."
      />
      <template #footer>
        <el-button @click="data.replyVisible = false" round>取消</el-button>
        <el-button type="primary" @click="submitReply" round :loading="data.replySubmitting">提交回复</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive } from "vue";
import request from "@/utils/request";
import { ElMessage } from "element-plus";
import { Search, Picture, ChatLineSquare } from "@element-plus/icons-vue";

const data = reactive({
  goodsName: '',
  rating: null,
  pageNum: 1,
  pageSize: 10,
  total: 0,
  tableData: [],
  replyVisible: false,
  replySubmitting: false,
  replyForm: {
    id: null,
    rating: 0,
    userName: '',
    content: '',
    reply: '',
    existed: false,
  },
})

const load = () => {
  request.get('/reviews/selectPage', {
    params: {
      goodsName: data.goodsName,
      rating: data.rating || 0,
      pageNum: data.pageNum,
      pageSize: data.pageSize,
    }
  }).then(res => {
    if (res.code === '200') {
      data.tableData = res.data?.list || []
      data.total = res.data?.total || 0
    } else {
      ElMessage.error(res.msg)
    }
  })
}
load()

const reset = () => {
  data.goodsName = ''
  data.rating = null
  data.pageNum = 1
  load()
}

const openReply = (row) => {
  data.replyForm = {
    id: row.id,
    rating: row.rating || 0,
    userName: row.userName || '匿名用户',
    content: row.content,
    reply: row.reply || '',
    existed: !!row.reply,
  }
  data.replyVisible = true
}

const submitReply = () => {
  if (!data.replyForm.reply || !data.replyForm.reply.trim()) {
    ElMessage.warning('请输入回复内容')
    return
  }
  data.replySubmitting = true
  request.put('/reviews/reply/' + data.replyForm.id, { reply: data.replyForm.reply.trim() }).then(res => {
    if (res.code === '200') {
      ElMessage.success('回复已提交')
      data.replyVisible = false
      load()
    } else {
      ElMessage.error(res.msg)
    }
  }).finally(() => {
    data.replySubmitting = false
  })
}
</script>

<style scoped>
@import './_admin-base.css';

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
.goods-info-cell { flex: 1; min-width: 0; }
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

.rating-filter {
  width: 120px;
}

.text-muted {
  color: var(--c-text-placeholder);
  font-size: 13px;
}

.review-content {
  font-size: 13px;
  color: var(--c-text-regular);
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 两行截断 */
.line-clamp {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.review-thumbs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}
.thumb {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  background: var(--c-bg-soft);
  cursor: pointer;
}

.reply-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.reply-cell .reply-text {
  font-size: 12px;
  color: var(--c-text-regular);
  line-height: 1.5;
}
.reply-cell .reply-time {
  font-size: 11px;
  color: var(--c-text-placeholder);
}

/* 回复弹窗：引用上下文 */
.reply-context {
  background: var(--c-bg-soft);
  border-radius: var(--r-md);
  padding: 10px 14px;
  margin-bottom: 14px;
}
.reply-context-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.reply-context-user {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-text-primary);
}
.reply-context-text {
  font-size: 13px;
  color: var(--c-text-regular);
  line-height: 1.6;
  margin-top: 6px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
