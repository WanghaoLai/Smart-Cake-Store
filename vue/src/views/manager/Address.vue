<template>
  <div class="admin-page">
    <div class="toolbar card">
      <el-input v-model="data.name" placeholder="请输入地址关键词查询" :prefix-icon="Search" clearable class="toolbar-search" @keyup.enter="load" @clear="load" />
      <el-button type="primary" round @click="load"><el-icon style="margin-right:4px"><Search /></el-icon>查询</el-button>
      <el-button round @click="reset">重置</el-button>
      <div class="toolbar-right" v-if="data.user.role === '用户'">
        <el-button type="primary" round @click="handleAdd"><el-icon style="margin-right:4px"><Plus /></el-icon>新增地址</el-button>
      </div>
    </div>

    <div class="card table-card">
      <el-table :data="data.tableData" stripe class="admin-table">
        <el-table-column label="收货人" prop="name" width="160">
          <template #default="scope">
            <div class="receiver-cell">
              <el-icon class="receiver-icon"><User /></el-icon>
              <span class="receiver-name">{{ scope.row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="联系方式" prop="phone" width="180">
          <template #default="scope">
            <span class="phone-text">{{ scope.row.phone }}</span>
          </template>
        </el-table-column>
        <el-table-column label="收货地址" prop="address" min-width="280">
          <template #default="scope">
            <div class="address-text line2">{{ scope.row.address }}</div>
          </template>
        </el-table-column>
        <el-table-column label="所属用户" prop="userName" width="140" v-if="data.user.role === '管理员'">
          <template #default="scope">
            <span class="user-tag">{{ scope.row.userName || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" align="center" width="180">
          <template #default="scope">
            <el-button text type="primary" @click="handleEdit(scope.row)" v-if="data.user.role === '用户'"><el-icon><Edit /></el-icon>编辑</el-button>
            <el-button text type="danger" @click="handleDelete(scope.row.id)"><el-icon><Delete /></el-icon>删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card pagination-card">
      <el-pagination @current-change="load" background layout="total, prev, pager, next" v-model:page-size="data.pageSize" v-model:current-page="data.pageNum" :total="data.total"/>
    </div>

    <el-dialog v-model="data.formVisible" width="520px" :close-on-click-modal="false" destroy-on-close>
      <template #header>
        <div class="dialog-header-custom">
          <el-icon class="dialog-icon"><Location /></el-icon>
          <div>
            <div class="dialog-title">{{ data.form.id ? '编辑地址' : '新增地址' }}</div>
            <div class="dialog-sub">完善收货信息以方便配送</div>
          </div>
        </div>
      </template>
      <el-form ref="formRef" :model="data.form" :rules="data.rules" label-position="top">
        <el-form-item label="收货人" prop="name">
          <el-input v-model="data.form.name" autocomplete="off" placeholder="收货人姓名" />
        </el-form-item>
        <el-form-item label="联系方式" prop="phone">
          <el-input v-model="data.form.phone" autocomplete="off" placeholder="联系电话" />
        </el-form-item>
        <el-form-item label="收货地址" prop="address">
          <el-input type="textarea" :rows="2" v-model="data.form.address" autocomplete="off" placeholder="详细收货地址" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="data.formVisible = false" round>取消</el-button>
        <el-button type="primary" @click="save" round>保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import request from "@/utils/request";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Plus, Edit, Delete, User, Location } from "@element-plus/icons-vue";

const formRef = ref()

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  form: {},
  formVisible: false,
  name: null,
  pageNum: 1,
  pageSize: 10,
  total: 0,
  tableData: [],
  rules: {
    name: [{ required: true, message: '请输入收货人', trigger: 'blur' }],
    address: [{ required: true, message: '请输入收货地址', trigger: 'blur' }],
    phone: [{ required: true, message: '请输入联系方式', trigger: 'blur' }],
  }
})

const load = () => {
  request.get('/address/selectPage', {
    params: {
      pageNum: data.pageNum,
      pageSize: data.pageSize,
      address: data.name,
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

const handleAdd = () => {
  data.form = { userId: data.user.id }
  data.formVisible = true
}

const handleEdit = (row) => { data.form = JSON.parse(JSON.stringify(row)); data.formVisible = true }

const handleDelete = (id) => {
  ElMessageBox.confirm('删除后数据无法恢复，您确定删除吗?', '删除确认', { type: 'warning' }).then(res => {
    request.delete('/address/delete/' + id).then(res => {
      if (res.code === '200') { load(); ElMessage.success('操作成功') } else { ElMessage.error(res.msg) }
    })
  }).catch(() => {})
}

const add = () => {
  request.post('/address/add', data.form).then(res => {
    if (res.code === '200') { ElMessage.success('操作成功'); data.formVisible = false; load() } else { ElMessage.error(res.msg) }
  })
}

const update = () => {
  request.put('/address/update', data.form).then(res => {
    if (res.code === '200') { ElMessage.success('操作成功'); data.formVisible = false; load() } else { ElMessage.error(res.msg) }
  })
}

const save = () => {
  formRef.value.validate(valid => {
    if (valid) data.form.id ? update() : add()
  })
}

const reset = () => { data.name = null; load() }
</script>

<style scoped>
@import './_admin-base.css';

.receiver-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.receiver-icon { color: var(--c-primary); font-size: 14px; }
.receiver-name { font-weight: 600; color: var(--c-text-primary); }
.phone-text { font-family: ui-monospace, monospace; color: var(--c-text-regular); font-size: 13px; }
.address-text { color: var(--c-text-regular); font-size: 13px; line-height: 1.5; }
.user-tag {
  display: inline-flex;
  padding: 2px 10px;
  background: var(--c-accent-soft);
  color: var(--c-accent);
  border-radius: var(--r-pill);
  font-size: 12px;
  font-weight: 600;
}
</style>
