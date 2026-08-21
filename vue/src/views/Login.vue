<template>
  <div class="auth-page">
    <!-- 左侧：品牌展示 -->
    <aside class="auth-hero">
      <div class="hero-inner">
        <div class="brand">
          <img src="@/assets/imgs/logo.png" alt="logo" class="brand-logo" />
          <span class="brand-name">智能商城导购与运营平台</span>
        </div>
        <h1 class="hero-title">每一口<br/>都是<span class="text-gradient">甜蜜时光</span></h1>
        <p class="hero-desc">精选天然食材，手工烘焙制作<br/>为每一个值得纪念的瞬间，定制专属蛋糕</p>
        <ul class="hero-points">
          <li><el-icon><CircleCheckFilled /></el-icon>当日现做，新鲜直达</li>
          <li><el-icon><CircleCheckFilled /></el-icon>多种风味，专属定制</li>
          <li><el-icon><CircleCheckFilled /></el-icon>智能客服，全程陪伴</li>
        </ul>
        <div class="hero-deco hero-deco-1"></div>
        <div class="hero-deco hero-deco-2"></div>
        <div class="hero-deco hero-deco-3"></div>
      </div>
    </aside>

    <!-- 右侧：表单 -->
    <main class="auth-main">
      <div class="auth-box">
        <div class="auth-head">
          <h2 class="auth-title">欢迎回来</h2>
          <p class="auth-subtitle">登录账号开启甜蜜之旅</p>
        </div>

        <el-form :model="data.form" ref="formRef" :rules="data.rules" class="auth-form" label-position="top">
          <el-form-item prop="username" label="账号">
            <el-input :prefix-icon="User" size="large" v-model="data.form.username" placeholder="请输入账号" />
          </el-form-item>
          <el-form-item prop="password" label="密码">
            <el-input :prefix-icon="Lock" size="large" v-model="data.form.password" placeholder="请输入密码" show-password @keyup.enter="login" />
          </el-form-item>
          <el-form-item prop="role" label="登录身份">
            <div class="role-tabs">
              <div
                v-for="r in roleOptions"
                :key="r.value"
                :class="['role-tab', { active: data.form.role === r.value }]"
                @click="data.form.role = r.value"
              >
                <el-icon><component :is="r.icon" /></el-icon>
                <span>{{ r.label }}</span>
              </div>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button class="auth-submit" type="primary" size="large" @click="login">
              <el-icon style="margin-right: 6px"><Right /></el-icon>登 录
            </el-button>
          </el-form-item>
        </el-form>

        <div class="auth-footer">
          还没有账号？<a href="/register">立即注册 →</a>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
  import { reactive, ref, markRaw } from "vue";
  import { User, Lock, Right, UserFilled, Histogram, CircleCheckFilled } from "@element-plus/icons-vue";
  import request from "@/utils/request";
  import { ElMessage } from "element-plus";
  import router from "@/router";

  const roleOptions = [
    { value: '管理员', label: '管理员', icon: markRaw(Histogram) },
    { value: '用户', label: '用户', icon: markRaw(UserFilled) },
  ]

  const data = reactive({
    form: { role: '用户' },
    rules: {
      username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
      password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
    }
  })

  const formRef = ref()

  const login = () => {
    formRef.value.validate((valid => {
      if (valid) {
        request.post('/login', data.form).then(res => {
          if (res.code === '200') {
            ElMessage.success("登录成功")
            localStorage.setItem('token', res.data.token)
            localStorage.setItem('system-user', JSON.stringify(res.data.user))
            // 首次登录（或密码被重置）需强制改密，先跳转改密页
            if (res.data.user?.must_change_password) {
              router.replace('/manager/password?force=1')
            } else {
              // 用 replace 而非 push：
              // 1) 清除登录页历史，返回键不会回到已登录的 /login
              // 2) 避免 push 到已存在的路由导致 vue-router 重复导航中断，
              //    偶发"登录后停在原地、刷新才进"的根因之一
              router.replace('/manager/home')
            }
          } else {
            ElMessage.error(res.msg)
          }
        })
      }
    })).catch(error => { console.error(error) })
  }
</script>

<style scoped lang="scss">
.auth-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  background: var(--c-bg-page);
}

/* —— 左侧品牌区 —— */
.auth-hero {
  position: relative;
  background: linear-gradient(135deg, #fdf6e0 0%, #f5ecc8 50%, #e6c558 100%);
  color: #524939;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: 64px;
}

.hero-inner {
  position: relative;
  z-index: 2;
  max-width: 520px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 80px;
}

.brand-logo {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.6);
  background: var(--c-bg-card);
}

.brand-name {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.hero-title {
  font-family: var(--font-display);
  font-size: 56px;
  line-height: 1.15;
  margin: 0 0 24px;
  font-weight: 700;
}

.hero-title .text-gradient {
  background: linear-gradient(135deg, #b8941f 0%, #d4af37 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-points li {
  color: #524939;
}

.hero-desc {
  font-size: 16px;
  line-height: 1.7;
  opacity: 0.95;
  margin-bottom: 36px;
  color: #524939;
}

.hero-points {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.hero-points li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  opacity: 0.95;
}

.hero-points .el-icon {
  font-size: 18px;
  color: #b8941f;
}

/* —— 装饰圆 —— */
.hero-deco {
  position: absolute;
  border-radius: 50%;
  filter: blur(2px);
  opacity: 0.35;
}

.hero-deco-1 { width: 280px; height: 280px; background: #ffffff; top: -80px; right: -80px; }
.hero-deco-2 { width: 180px; height: 180px; background: #d4af37; bottom: -50px; right: 30%; opacity: 0.25; }
.hero-deco-3 { width: 120px; height: 120px; background: #ffffff; bottom: 18%; left: -40px; opacity: 0.5; }

/* —— 右侧表单区 —— */
.auth-main {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
}

.auth-box {
  width: 100%;
  max-width: 400px;
}

.auth-head {
  margin-bottom: 32px;
}

.auth-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--c-text-primary);
  margin: 0 0 8px;
}

.auth-subtitle {
  font-size: 14px;
  color: var(--c-text-secondary);
  margin: 0;
}

.auth-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: var(--c-text-regular);
  padding-bottom: 4px;
}

.auth-form :deep(.el-input__wrapper) {
  border-radius: 10px;
  padding: 4px 12px;
  box-shadow: 0 0 0 1px var(--c-border) inset;
  transition: all var(--t-fast) var(--ease-out);
}

.auth-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--c-primary) inset;
}

.auth-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--c-primary) inset, 0 0 0 4px var(--c-primary-soft) inset;
}

.role-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  width: 100%;
}

.role-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 10px;
  border: none;
  background: var(--c-bg-soft);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--c-text-regular);
  transition: all var(--t-fast) var(--ease-out);
}

.role-tab:hover {
  border-color: var(--c-primary);
  color: var(--c-primary);
}

.role-tab.active {
  border-color: var(--c-primary);
  background: var(--c-primary-soft);
  color: var(--c-primary);
  box-shadow: 0 4px 12px rgba(184, 148, 31, 0.15);
}

.auth-submit {
  width: 100%;
  border-radius: 10px;
  background: var(--grad-primary);
  border: none;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  height: 44px;
  box-shadow: 0 8px 20px rgba(184, 148, 31, 0.3);
  transition: all var(--t-base) var(--ease-out);
}

.auth-submit:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 26px rgba(184, 148, 31, 0.38);
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: var(--c-text-secondary);
}

.auth-footer a {
  font-weight: 500;
}

/* —— 响应式：窄屏隐藏左侧品牌区 —— */
@media (max-width: 900px) {
  .auth-page {
    grid-template-columns: 1fr;
  }
  .auth-hero {
    display: none;
  }
}
</style>
