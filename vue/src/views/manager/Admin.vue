<template>
  <div class="admin-page">
    <div class="toolbar card">
      <el-input v-model="data.name" placeholder="请输入管理员姓名查询" :prefix-icon="Search" clearable class="toolbar-search" @keyup.enter="load" @clear="load" />
      <el-button type="primary" round @click="load"><el-icon style="margin-right:4px"><Search /></el-icon>查询</el-button>
      <el-button round @click="reset">重置</el-button>
      <div class="toolbar-right">
        <el-button type="primary" round @click="handleAdd"><el-icon style="margin-right:4px"><Plus /></el-icon>新增管理员</el-button>
      </div>
    </div>

    <div class="card table-card">
      <el-table :data="data.tableData" stripe class="admin-table">
        <el-table-column label="管理员" prop="username" min-width="240">
          <template #default="scope">
            <div class="user-cell">
              <img v-if="scope.row.avatar" :src="$fileUrl(scope.row.avatar)" class="cell-avatar" alt="avatar" />
              <div v-else class="cell-avatar placeholder">{{ (scope.row.name || 'A').charAt(0) }}</div>
              <div class="user-info-cell">
                <div class="user-name-cell">{{ scope.row.name }}</div>
                <div class="user-id-cell">@{{ scope.row.username }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" prop="role" width="120">
          <template #default="scope">
            <span class="cell-role admin">{{ scope.row.role || '管理员' }}</span>
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

    <el-dialog v-model="data.formVisible" width="520px" :close-on-click-modal="false" destroy-on-close>
      <template #header>
        <div class="dialog-header-custom">
          <el-icon class="dialog-icon"><Avatar /></el-icon>
          <div>
            <div class="dialog-title">{{ data.form.id ? '编辑管理员' : '新增管理员' }}</div>
            <div class="dialog-sub">填写管理员账号信息</div>
          </div>
        </div>
      </template>
      <el-form ref="formRef" :model="data.form" :rules="data.rules" label-position="top">
        <el-form-item label="账号" prop="username">
          <el-input :disabled="data.form.id > 0" v-model="data.form.username" autocomplete="off" placeholder="登录账号" />
        </el-form-item>
        <el-form-item v-if="!data.form.id" label="初始密码" prop="password">
          <el-input v-model="data.form.password" type="password" show-password autocomplete="new-password" placeholder="留空则默认为 admin" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="data.form.name" autocomplete="off" placeholder="管理员姓名" />
        </el-form-item>
        <el-form-item label="头像" prop="avatar">
          <el-upload :action="uploadUrl" :show-file-list="false" :on-success="handleImgSuccess" :headers="uploadHeaders" class="avatar-uploader">
            <img v-if="data.form.avatar" :src="$fileUrl(data.form.avatar)" class="avatar" />
            <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
          </el-upload>
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
import request from "@/utils/request";
import { reactive, ref } from "vue";
import { ElMessageBox, ElMessage } from "element-plus";
import { Search, Plus, Edit, Delete, Avatar } from "@element-plus/icons-vue";

const uploadUrl = import.meta.env.VITE_BASE_URL + '/files/upload?category=avatar'
const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }
const formRef = ref()

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  pageNum: 1,
  pageSize: 10,
  total: 0,
  formVisible: false,
  form: {},
  tableData: [],
  name: null,
  rules: {
    username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
    name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
    avatar: [{ required: true, message: '请上传头像', trigger: 'change' }],
  }
})

const load = () => {
  request.get('/admin/selectPage', {
    params: { pageNum: data.pageNum, pageSize: data.pageSize, name: data.name }
  }).then(res => {
    data.tableData = res.data?.list || []
    data.total = res.data?.total || 0
  })
}

const handleAdd = () => { data.form = {}; data.formVisible = true }
const handleEdit = (row) => { data.form = JSON.parse(JSON.stringify(row)); data.formVisible = true }

const add = () => {
  request.post('/admin/add', data.form).then(res => {
    if (res.code === '200') {
      load(); data.formVisible = false
      const generated = res.data?.initial_password
      if (generated) {
        ElMessageBox.alert(`初始密码：${generated}\n请通过安全渠道一次性下发，关闭后不再显示。`, '管理员创建成功', {
          confirmButtonText: '我已安全保存',
        })
      } else {
        ElMessage.success('操作成功')
      }
    } else { ElMessage.error(res.msg) }
  })
}

const update = () => {
  request.put('/admin/update', data.form).then(res => {
    if (res.code === '200') { load(); ElMessage.success('操作成功'); data.formVisible = false } else { ElMessage.error(res.msg) }
  })
}

const save = () => {
  formRef.value.validate(valid => {
    if (valid) data.form.id ? update() : add()
  })
}

const handleDelete = (id) => {
  ElMessageBox.confirm('删除后数据无法恢复，您确定删除吗?', '删除确认', { type: 'warning' }).then(res => {
    request.delete('/admin/delete/' + id).then(res => {
      if (res.code === '200') { load(); ElMessage.success('操作成功') } else { ElMessage.error(res.msg) }
    })
  }).catch(() => {})
}

const reset = () => { data.name = null; load() }

const handleImgSuccess = (res) => { data.form.avatar = res.data }

load()
</script>

<style scoped>
@import './_admin-base.css';

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cell-avatar.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--grad-primary);
  color: #fff;
  font-weight: 600;
  font-size: 16px;
}

.user-info-cell {
  display: flex;
  flex-direction: column;
}

.user-name-cell {
  font-weight: 600;
  color: var(--c-text-primary);
  font-size: 14px;
}

.user-id-cell {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin-top: 2px;
}
</style>
