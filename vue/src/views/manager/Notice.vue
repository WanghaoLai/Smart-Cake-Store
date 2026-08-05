<template>
  <div class="admin-page">
    <div class="toolbar card">
      <el-input v-model="data.name" placeholder="请输入公告标题查询" :prefix-icon="Search" clearable class="toolbar-search" @keyup.enter="load" @clear="load" />
      <el-button type="primary" round @click="load"><el-icon style="margin-right:4px"><Search /></el-icon>查询</el-button>
      <el-button round @click="reset">重置</el-button>
      <div class="toolbar-right">
        <el-button type="primary" round @click="handleAdd"><el-icon style="margin-right:4px"><Plus /></el-icon>发布公告</el-button>
      </div>
    </div>

    <div class="card table-card">
      <el-table :data="data.tableData" stripe class="admin-table">
        <el-table-column label="公告标题" prop="name" min-width="200">
          <template #default="scope">
            <div class="title-cell">
              <el-icon class="title-icon"><Bell /></el-icon>
              <span class="title-text">{{ scope.row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="公告内容" prop="content" min-width="320">
          <template #default="scope">
            <div class="content-text line2">{{ scope.row.content }}</div>
          </template>
        </el-table-column>
        <el-table-column label="发布时间" prop="time" width="180">
          <template #default="scope">
            <span class="time-text">{{ scope.row.time }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" align="center" width="180">
          <template #default="scope">
            <el-button text type="primary" @click="handleEdit(scope.row)"><el-icon><Edit /></el-icon>编辑</el-button>
            <el-button text type="danger" @click="handleDelete(scope.row.id)"><el-icon><Delete /></el-icon>删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card pagination-card">
      <el-pagination @current-change="load" background layout="total, prev, pager, next" v-model:page-size="data.pageSize" v-model:current-page="data.pageNum" :total="data.total"/>
    </div>

    <el-dialog v-model="data.formVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <template #header>
        <div class="dialog-header-custom">
          <el-icon class="dialog-icon"><Bell /></el-icon>
          <div>
            <div class="dialog-title">{{ data.form.id ? '编辑公告' : '发布公告' }}</div>
            <div class="dialog-sub">公告将展示在用户首页</div>
          </div>
        </div>
      </template>
      <el-form ref="formRef" :model="data.form" :rules="data.rules" label-position="top">
        <el-form-item label="公告标题" prop="name">
          <el-input v-model="data.form.name" autocomplete="off" placeholder="请输入公告标题" />
        </el-form-item>
        <el-form-item label="公告内容" prop="content">
          <el-input type="textarea" :rows="4" v-model="data.form.content" autocomplete="off" placeholder="请输入公告内容" />
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
import { Search, Plus, Edit, Delete, Bell } from "@element-plus/icons-vue";

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
    name: [{ required: true, message: '请输入公告标题', trigger: 'blur' }],
    content: [{ required: true, message: '请输入公告内容', trigger: 'blur' }],
  }
})

const load = () => {
  request.get('/notice/selectPage', {
    params: { pageNum: data.pageNum, pageSize: data.pageSize, name: data.name }
  }).then(res => {
    if (res.code === '200') {
      data.tableData = res.data?.list || []
      data.total = res.data?.total || 0
    } else { ElMessage.error(res.msg) }
  })
}
load()

const handleAdd = () => { data.form = {}; data.formVisible = true }
const handleEdit = (row) => { data.form = JSON.parse(JSON.stringify(row)); data.formVisible = true }

const handleDelete = (id) => {
  ElMessageBox.confirm('删除后数据无法恢复，您确定删除吗?', '删除确认', { type: 'warning' }).then(res => {
    request.delete('/notice/delete/' + id).then(res => {
      if (res.code === '200') { load(); ElMessage.success('操作成功') } else { ElMessage.error(res.msg) }
    })
  }).catch(() => {})
}

const add = () => {
  request.post('/notice/add', data.form).then(res => {
    if (res.code === '200') { ElMessage.success('操作成功'); data.formVisible = false; load() } else { ElMessage.error(res.msg) }
  })
}

const update = () => {
  request.put('/notice/update', data.form).then(res => {
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

.title-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.title-icon { color: var(--c-primary); font-size: 14px; }
.title-text { font-weight: 600; color: var(--c-text-primary); }
.content-text { color: var(--c-text-regular); font-size: 13px; line-height: 1.5; }
.time-text { font-size: 12px; color: var(--c-text-secondary); font-family: ui-monospace, monospace; }
</style>
