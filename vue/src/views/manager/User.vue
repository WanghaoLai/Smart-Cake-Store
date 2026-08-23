<template>
  <div class="admin-page">
    <div class="toolbar card">
      <el-input v-model="data.name" placeholder="请输入用户名/姓名查询" :prefix-icon="Search" clearable class="toolbar-search" @keyup.enter="load" @clear="load" />
      <el-button type="primary" round @click="load"><el-icon style="margin-right:4px"><Search /></el-icon>查询</el-button>
      <el-button round @click="reset">重置</el-button>
      <div class="toolbar-right">
        <el-button type="primary" round @click="handleAdd"><el-icon style="margin-right:4px"><Plus /></el-icon>新增用户</el-button>
      </div>
    </div>

    <div class="card table-card">
      <el-table :data="data.tableData" stripe class="admin-table">
        <el-table-column label="用户" prop="username" min-width="240">
          <template #default="scope">
            <div class="user-cell">
              <img v-if="scope.row.avatar" :src="$fileUrl(scope.row.avatar)" class="cell-avatar" alt="avatar" />
              <div v-else class="cell-avatar placeholder">{{ (scope.row.name || 'U').charAt(0) }}</div>
              <div class="user-info-cell">
                <div class="user-name-cell">{{ scope.row.name }}</div>
                <div class="user-id-cell">@{{ scope.row.username }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" prop="role" width="120">
          <template #default="scope">
            <span class="cell-role" :class="scope.row.role === '管理员' ? 'admin' : 'user'">
              {{ scope.row.role || '用户' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" align="center" width="240">
          <template #default="scope">
            <div class="row-actions">
              <el-button text type="primary" @click="handleEdit(scope.row)"><el-icon><Edit /></el-icon>编辑</el-button>
              <el-divider direction="vertical" />
              <el-button text type="warning" @click="handleResetPwd(scope.row)"><el-icon><Key /></el-icon>重置密码</el-button>
              <el-divider direction="vertical" />
              <el-button text type="danger" @click="handleDelete(scope.row.id)"><el-icon><Delete /></el-icon>删除</el-button>
            </div>
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
          <el-icon class="dialog-icon"><User /></el-icon>
          <div>
            <div class="dialog-title">{{ data.form.id ? '编辑用户' : '新增用户' }}</div>
            <div class="dialog-sub">填写账号基本信息</div>
          </div>
        </div>
      </template>
      <el-form ref="formRef" :model="data.form" :rules="data.rules" label-position="top">
        <el-form-item label="账号" prop="username">
          <el-input :disabled="data.form.id > 0" v-model="data.form.username" autocomplete="off" placeholder="登录账号" />
        </el-form-item>
        <el-form-item v-if="!data.form.id" label="初始密码" prop="password">
          <el-input v-model="data.form.password" type="password" show-password autocomplete="new-password" placeholder="留空则默认为 123" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="data.form.name" autocomplete="off" placeholder="用户姓名" />
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

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="data.pwdVisible" width="460px" :close-on-click-modal="false" destroy-on-close class="pwd-dialog">
      <template #header>
        <div class="dialog-header-custom">
          <div class="pwd-head-icon"><el-icon><Key /></el-icon></div>
          <div>
            <div class="dialog-title">重置用户密码</div>
            <div class="dialog-sub">为 <b>@{{ data.pwdTarget?.username }}</b> 设置新的登录密码</div>
          </div>
        </div>
      </template>
      <el-form label-position="top" class="pwd-form">
        <el-form-item label="新密码" required>
          <el-input v-model="data.pwdForm.newPassword" type="password" show-password autocomplete="new-password" placeholder="请输入新密码（至少 6 位）" size="large" />
        </el-form-item>
        <div class="pwd-tip">
          <el-icon><InfoFilled /></el-icon>
          <span>重置后该用户下次登录将需要修改密码</span>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="data.pwdVisible = false" round>取消</el-button>
        <el-button type="primary" round @click="doResetPwd" :loading="data.resetting"><el-icon style="margin-right:4px"><Check /></el-icon>确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import request from "@/utils/request";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Plus, Edit, Delete, User, Key, Check, InfoFilled } from "@element-plus/icons-vue";

const formRef = ref()
const uploadUrl = import.meta.env.VITE_BASE_URL + '/files/upload?category=avatar'
const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  form: {},
  formVisible: false,
  pwdVisible: false,
  pwdTarget: null,
  pwdForm: { newPassword: '' },
  resetting: false,
  name: null,
  pageNum: 1,
  pageSize: 10,
  total: 0,
  tableData: [],
  rules: {
    username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
    name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
    avatar: [{ required: true, message: '请上传头像', trigger: 'change' }],
  }
})

const load = () => {
  request.get('/user/selectPage', {
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
    request.delete('/user/delete/' + id).then(res => {
      if (res.code === '200') { load(); ElMessage.success('操作成功') } else { ElMessage.error(res.msg) }
    })
  }).catch(() => {})
}

const handleResetPwd = (row) => {
  data.pwdTarget = row
  data.pwdForm.newPassword = ''
  data.pwdVisible = true
}

const doResetPwd = () => {
  if (!data.pwdForm.newPassword) {
    ElMessage.error('请输入新密码')
    return
  }
  if (data.pwdForm.newPassword.length < 8) {
    ElMessage.error('新密码至少 8 位')
    return
  }
  data.resetting = true
  request.put('/user/reset-password/' + data.pwdTarget.id, { password: data.pwdForm.newPassword }).then(res => {
    data.resetting = false
    if (res.code === '200') {
      ElMessage.success('密码已重置，该用户下次登录需修改密码')
      data.pwdVisible = false
    } else { ElMessage.error(res.msg) }
  })
}

const add = () => {
  request.post('/user/add', data.form).then(res => {
    if (res.code === '200') {
      const generated = res.data?.initial_password
      if (generated) {
        ElMessageBox.alert(`初始密码：${generated}\n请通过安全渠道一次性下发，关闭后不再显示。`, '账号创建成功', {
          confirmButtonText: '我已安全保存',
        })
      } else {
        ElMessage.success('操作成功')
      }
      data.formVisible = false; load()
    } else { ElMessage.error(res.msg) }
  })
}

const update = () => {
  request.put('/user/update', data.form).then(res => {
    if (res.code === '200') { ElMessage.success('操作成功'); data.formVisible = false; load() } else { ElMessage.error(res.msg) }
  })
}

const save = () => {
  formRef.value.validate(valid => {
    if (valid) data.form.id ? update() : add()
  })
}

const reset = () => { data.name = null; load() }

const handleImgSuccess = (res) => { data.form.avatar = res.data }
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

/* 操作列同一行三按钮 */
.row-actions {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}
.row-actions :deep(.el-divider--vertical) {
  margin: 0 4px;
}
.row-actions :deep(.el-button) {
  padding: 0 4px;
  margin: 0;
  font-size: 13px;
}
.row-actions :deep(.el-button .el-icon) {
  margin-right: 3px;
}

/* 重置密码弹窗美化 */
.pwd-dialog :deep(.el-dialog__body) {
  padding: 8px 24px 8px;
}

.pwd-head-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: var(--c-warning-soft, #fdf3e3);
  color: var(--c-warning, #d4af37);
}

.pwd-dialog .dialog-sub b {
  color: var(--c-primary);
}

.pwd-form ::v-deep(.el-input__wrapper) {
  border-radius: var(--r-sm, 8px);
}

.pwd-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--c-text-secondary);
  background: var(--c-bg-soft);
  border-radius: var(--r-md);
  padding: 10px 12px;
  margin-top: 4px;
}

.pwd-tip .el-icon {
  color: var(--c-warning, #d4af37);
}
</style>
