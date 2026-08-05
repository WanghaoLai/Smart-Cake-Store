<template>
  <div class="password-page">
    <div class="password-card card">
      <div class="form-head">
        <div class="head-icon">
          <el-icon><Lock /></el-icon>
        </div>
        <div>
          <h2 class="form-title">修改密码</h2>
          <p class="form-sub">{{ isForceChange ? '首次登录须修改密码，为账号安全请尽快设置新密码' : '为了账号安全，请定期更新密码' }}</p>
        </div>
      </div>

      <el-form ref="formRef" :rules="data.rules" :model="data.form" label-position="top" class="password-form">
        <el-form-item label="原密码" prop="password">
          <el-input v-model="data.form.password" show-password placeholder="请输入当前密码" prefix-icon="Key" />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="data.form.newPassword" show-password placeholder="请输入新密码" prefix-icon="Lock" />
          <div class="password-strength" v-if="data.form.newPassword">
            <div class="strength-bars">
              <span v-for="i in 4" :key="i" :class="['bar', { active: passwordStrength.score >= i, weak: passwordStrength.level === 'weak', mid: passwordStrength.level === 'mid', strong: passwordStrength.level === 'strong' }]"></span>
            </div>
            <span class="strength-label" :class="passwordStrength.level">{{ passwordStrength.text }}</span>
          </div>
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPasword">
          <el-input v-model="data.form.confirmPasword" show-password placeholder="请再次输入新密码" prefix-icon="CircleCheck" />
        </el-form-item>

        <div class="tips-card">
          <div class="tips-title"><el-icon><InfoFilled /></el-icon>密码安全建议</div>
          <ul>
            <li :class="{ pass: data.form.newPassword?.length >= 8 }">至少 8 位字符</li>
            <li :class="{ pass: /[A-Z]/.test(data.form.newPassword || '') }">包含大写字母</li>
            <li :class="{ pass: /[0-9]/.test(data.form.newPassword || '') }">包含数字</li>
            <li :class="{ pass: /[^A-Za-z0-9]/.test(data.form.newPassword || '') }">包含特殊字符</li>
          </ul>
        </div>

        <el-form-item>
          <el-button type="primary" round size="large" @click="save">
            <el-icon style="margin-right: 4px"><Check /></el-icon>确认修改
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from "vue";
import request from "@/utils/request";
import { ElMessage } from "element-plus";
import router from "@/router";
import { Lock, Key, CircleCheck, Check, InfoFilled } from "@element-plus/icons-vue";

const formRef = ref()
const isForceChange = computed(() => router.currentRoute.value.query.force === '1')
const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  form: {
    id: null,
    role: '',
    password: '',
    newPassword: '',
    confirmPasword: '',
  },
  rules: {
    password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
    newPassword: [{ required: true, message: '请输入新密码', trigger: 'blur' }],
    confirmPasword: [{ required: true, message: '请确认新密码', trigger: 'blur' }],
  }
})
data.form.id = data.user.id
data.form.role = data.user.role

const passwordStrength = computed(() => {
  const pwd = data.form.newPassword || ''
  if (!pwd) return { score: 0, level: '', text: '' }
  let score = 0
  if (pwd.length >= 8) score++
  if (/[A-Z]/.test(pwd)) score++
  if (/[0-9]/.test(pwd)) score++
  if (/[^A-Za-z0-9]/.test(pwd)) score++
  const levels = [
    { level: 'weak', text: '弱' },
    { level: 'weak', text: '弱' },
    { level: 'mid', text: '中' },
    { level: 'strong', text: '强' },
    { level: 'strong', text: '非常强' },
  ]
  return { score, ...levels[score] }
})

const save = () => {
  formRef.value.validate(valid => {
    if (!valid) return
    if (data.form.password === data.form.newPassword) {
      ElMessage.error('新密码不能和原密码一致')
      return
    }
    if (data.form.newPassword !== data.form.confirmPasword) {
      ElMessage.error('确认新密码错误')
      return
    }
    request.put('/updatePassword', data.form).then(res => {
      if (res.code === '200') {
        ElMessage.success('修改密码成功，请重新登录')
        localStorage.removeItem('token')
        localStorage.removeItem('system-user')
        router.replace('/login')
      } else { ElMessage.error(res.msg) }
    })
  })
}
</script>

<style scoped>
.password-page {
  padding: 20px;
  width: 100%;
}

.password-card {
  padding: 32px;
  max-width: 600px;
  margin: 0 auto;
}

.form-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--c-border-light);
}

.head-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--grad-primary);
  color: #fff;
  font-size: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
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
  margin: 4px 0 0;
}

.password-form :deep(.el-input__wrapper) {
  border-radius: var(--r-sm);
}

.password-strength {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
  font-size: 12px;
}

.strength-bars {
  display: flex;
  gap: 3px;
}

.bar {
  width: 28px;
  height: 4px;
  border-radius: 2px;
  background: var(--c-border);
  transition: background var(--t-fast) var(--ease-out);
}

.bar.active.weak { background: var(--c-danger); }
.bar.active.mid { background: var(--c-accent); }
.bar.active.strong { background: var(--c-success); }

.strength-label.weak { color: var(--c-danger); font-weight: 600; }
.strength-label.mid { color: var(--c-accent); font-weight: 600; }
.strength-label.strong { color: var(--c-success); font-weight: 600; }

.tips-card {
  background: var(--c-bg-soft);
  border-radius: var(--r-md);
  padding: 14px 16px;
  margin-bottom: 20px;
}

.tips-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin-bottom: 8px;
}

.tips-title .el-icon { color: var(--c-primary); }

.tips-card ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.tips-card li {
  font-size: 12px;
  color: var(--c-text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.tips-card li::before {
  content: '○';
  color: var(--c-text-placeholder);
}

.tips-card li.pass {
  color: var(--c-success);
}

.tips-card li.pass::before {
  content: '✓';
  color: var(--c-success);
  font-weight: 700;
}

.password-form :deep(.el-button--primary) {
  background: var(--grad-primary);
  border: none;
  padding: 0 24px;
  box-shadow: 0 6px 16px rgba(184, 148, 31, 0.28);
}
</style>
