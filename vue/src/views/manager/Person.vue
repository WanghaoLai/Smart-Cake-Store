<template>
  <div class="person-page">
    <div class="profile-grid">
      <!-- 左侧：头像卡片 -->
      <aside class="profile-side card">
        <div class="avatar-wrap">
          <el-upload :show-file-list="false" class="avatar-uploader" :action="uploadUrl" :on-success="handleFileUpload" :headers="uploadHeaders">
            <img v-if="data.user.avatar" :src="$fileUrl(data.user.avatar)" class="avatar" />
            <div v-else class="avatar placeholder">
              <el-icon><Plus /></el-icon>
            </div>
            <div class="avatar-overlay">
              <el-icon><Camera /></el-icon>
              <span>更换头像</span>
            </div>
          </el-upload>
          <div class="role-badge" :class="data.user.role === '管理员' ? 'admin' : 'user'">
            {{ data.user.role || '用户' }}
          </div>
        </div>
        <h3 class="user-name">{{ data.user.name || '未设置' }}</h3>
        <p class="user-id">@{{ data.user.username }}</p>

        <ul class="side-stats">
          <li>
            <div class="side-stat-label">账号角色</div>
            <div class="side-stat-value">{{ data.user.role }}</div>
          </li>
          <li>
            <div class="side-stat-label">账号 ID</div>
            <div class="side-stat-value">#{{ data.user.id }}</div>
          </li>
        </ul>

        <div class="side-tip">
          <el-icon><InfoFilled /></el-icon>
          <span>良好的个人资料有助于客服更好地服务您</span>
        </div>
      </aside>

      <!-- 右侧：表单 -->
      <section class="profile-main card">
        <div class="form-head">
          <h2 class="form-title">个人资料</h2>
          <p class="form-sub">更新你的个人信息，所有修改将实时保存</p>
        </div>

        <el-form ref="formRef" :model="data.user" :rules="data.rules" label-position="top" class="profile-form">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="账号" prop="username">
                <el-input disabled v-model="data.user.username" autocomplete="off" prefix-icon="User" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="姓名" prop="name">
                <el-input v-model="data.user.name" autocomplete="off" placeholder="请输入姓名" prefix-icon="EditPen" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item>
            <el-button type="primary" round @click="save" size="large">
              <el-icon style="margin-right: 4px"><Check /></el-icon>保存修改
            </el-button>
          </el-form-item>
        </el-form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import request from "@/utils/request";
import { ElMessage } from "element-plus";
import { Plus, Camera, Check, User, EditPen, InfoFilled } from "@element-plus/icons-vue";

const uploadUrl = import.meta.env.VITE_BASE_URL + '/files/upload?category=avatar'
const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }

const formRef = ref()
const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  rules: {
    username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
    name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  }
})

const handleFileUpload = (file) => {
  data.user.avatar = file.data
}

const emit = defineEmits(["updateUser"])

const save = () => {
  formRef.value.validate(valid => {
    if (!valid) return
    const url = data.user.role === '管理员' ? '/admin/update' : '/user/update'
    request.put(url, data.user).then(res => {
      if (res.code === '200') {
        ElMessage.success('更新成功')
        localStorage.setItem('system-user', JSON.stringify(data.user))
        emit('updateUser')
      } else { ElMessage.error(res.msg) }
    })
  })
}
</script>

<style scoped>
.person-page {
  padding: 20px;
  width: 100%;
}

.profile-grid {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
  align-items: start;
}

@media (max-width: 768px) {
  .profile-grid { grid-template-columns: 1fr; }
}

/* —— 左侧 —— */
.profile-side {
  padding: 32px 24px;
  text-align: center;
}

.avatar-wrap {
  position: relative;
  display: inline-block;
}

.avatar-uploader {
  display: inline-block;
  cursor: pointer;
}

.avatar-uploader :deep(.el-upload) {
  border-radius: 50%;
  overflow: hidden;
  position: relative;
  width: 110px;
  height: 110px;
  border: 3px solid #fff;
  box-shadow: 0 4px 16px rgba(184, 148, 31, 0.22);
}

.avatar {
  width: 110px;
  height: 110px;
  object-fit: cover;
  display: block;
}

.avatar.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--grad-primary);
  color: #fff;
  font-size: 32px;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-size: 12px;
  opacity: 0;
  transition: opacity var(--t-fast) var(--ease-out);
}

.avatar-uploader:hover .avatar-overlay { opacity: 1; }

.role-badge {
  position: absolute;
  bottom: -4px;
  right: -4px;
  padding: 3px 10px;
  border-radius: var(--r-pill);
  font-size: 11px;
  font-weight: 600;
  border: 2px solid #fff;
}

.role-badge.admin {
  background: var(--c-primary);
  color: #fff;
}

.role-badge.user {
  background: var(--c-accent);
  color: #fff;
}

.user-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--c-text-primary);
  margin: 16px 0 4px;
}

.user-id {
  font-size: 13px;
  color: var(--c-text-secondary);
  margin: 0 0 20px;
}

.side-stats {
  list-style: none;
  padding: 0;
  margin: 0 0 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  text-align: left;
}

.side-stats li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: var(--c-bg-soft);
  border-radius: var(--r-md);
}

.side-stat-label {
  font-size: 12px;
  color: var(--c-text-secondary);
}

.side-stat-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-primary);
}

.side-tip {
  display: flex;
  gap: 8px;
  padding: 12px;
  background: var(--c-accent-soft);
  border-radius: var(--r-md);
  color: var(--c-accent);
  font-size: 12px;
  line-height: 1.5;
  text-align: left;
}

.side-tip .el-icon {
  flex-shrink: 0;
  margin-top: 1px;
}

/* —— 右侧表单 —— */
.profile-main {
  padding: 28px 32px;
}

.form-head {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--c-border-light);
}

.form-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--c-text-primary);
  margin: 0;
}

.form-title::before { display: none; }

.form-sub {
  font-size: 13px;
  color: var(--c-text-secondary);
  margin: 6px 0 0;
}

.profile-form :deep(.el-input__wrapper) {
  border-radius: var(--r-sm);
}

.profile-form :deep(.el-button--primary) {
  background: var(--grad-primary);
  border: none;
  padding: 0 24px;
  box-shadow: 0 6px 16px rgba(184, 148, 31, 0.28);
}
</style>
