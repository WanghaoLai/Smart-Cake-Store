<template>
  <div class="admin-page">
    <div class="toolbar card">
      <el-input v-model="data.name" placeholder="请输入商品名称查询" :prefix-icon="Search" clearable class="toolbar-search" @keyup.enter="load" @clear="load" />
      <el-button type="primary" round @click="load"><el-icon style="margin-right:4px"><Search /></el-icon>查询</el-button>
      <el-button round @click="reset">重置</el-button>
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
              <img v-if="scope.row.goodsImg" :src="scope.row.goodsImg" class="cell-img" alt="" />
              <div v-else class="cell-img placeholder"><el-icon><Picture /></el-icon></div>
              <div class="goods-info-cell">
                <div class="goods-name-cell line1">{{ scope.row.goodsName }}</div>
                <div class="goods-meta-cell">¥{{ scope.row.goodsPrice }} / {{ scope.row.goodsUnit }} × {{ scope.row.num }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="总价" prop="total" width="120">
          <template #default="scope">
            <span class="cell-price">¥{{ scope.row.total }}</span>
          </template>
        </el-table-column>
        <el-table-column label="收货信息" min-width="240">
          <template #default="scope">
            <div class="addr-cell">
              <div class="addr-name">{{ scope.row.aName }} · {{ scope.row.aPhone }}</div>
              <div class="addr-detail line1">{{ scope.row.aAddress }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="下单用户" prop="userName" width="120">
          <template #default="scope">
            <span class="user-tag">{{ scope.row.userName }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" align="center" width="120">
          <template #default="scope">
            <el-button text type="danger" @click="handleDelete(scope.row.id)"><el-icon><Delete /></el-icon>删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card pagination-card">
      <el-pagination @current-change="load" background layout="total, prev, pager, next" v-model:page-size="data.pageSize" v-model:current-page="data.pageNum" :total="data.total"/>
    </div>
  </div>
</template>

<script setup>
import { reactive } from "vue";
import request from "@/utils/request";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Delete, Tickets, Picture } from "@element-plus/icons-vue";

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  name: null,
  pageNum: 1,
  pageSize: 10,
  total: 0,
  tableData: [],
})

const load = () => {
  request.get('/orders/selectPage', {
    params: {
      pageNum: data.pageNum,
      pageSize: data.pageSize,
      goodsName: data.name,
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

const handleDelete = (id) => {
  ElMessageBox.confirm('删除后数据无法恢复，您确定删除吗?', '删除确认', { type: 'warning' }).then(res => {
    request.delete('/orders/delete/' + id).then(res => {
      if (res.code === '200') { load(); ElMessage.success('操作成功') } else { ElMessage.error(res.msg) }
    })
  }).catch(() => {})
}

const reset = () => { data.name = null; load() }
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
</style>
