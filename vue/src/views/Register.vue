<template>
  <div class="auth-page">
    <!-- 左侧：品牌展示 -->
    <aside class="auth-hero">
      <div class="hero-inner">
        <div class="brand">
          <img src="@/assets/imgs/logo.png" alt="logo" class="brand-logo" />
          <span class="brand-name">甜心烘焙 Sweet Hearts Bakery</span>
        </div>
        <h1 class="hero-title">加入我们<br/>开启<span class="text-gradient">专属甜品</span>旅程</h1>
        <p class="hero-desc">注册成为会员，享受收藏、下单、智能推荐<br/>定制属于你的蛋糕时光</p>
        <ul class="hero-points">
          <li><el-icon><CircleCheckFilled /></el-icon>一键收藏喜爱的口味</li>
          <li><el-icon><CircleCheckFilled /></el-icon>订单实时跟踪</li>
          <li><el-icon><CircleCheckFilled /></el-icon>专属客服 7×12 在线</li>
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
          <h2 class="auth-title">创建账号</h2>
          <p class="auth-subtitle">填写信息即可完成注册</p>
        </div>

        <el-form :model="data.form" ref="formRef" :rules="data.rules" class="auth-form" label-position="top">
          <el-form-item prop="username" label="账号">
            <el-input :prefix-icon="User" size="large" v-model="data.form.username" placeholder="请输入账号" />
          </el-form-item>
          <el-form-item prop="password" label="密码">
            <el-input :prefix-icon="Lock" size="large" v-model="data.form.password" placeholder="请输入密码" show-password />
          </el-form-item>
          <el-form-item prop="confirmPassword" label="确认密码">
            <el-input :prefix-icon="Lock" size="large" v-model="data.form.confirmPassword" placeholder="请再次输入密码" show-password @keyup.enter="register" />
          </el-form-item>
          <el-form-item>
            <el-button class="auth-submit" type="primary" size="large" @click="register">
              <el-icon style="margin-right: 6px"><Right /></el-icon>注 册
            </el-button>
          </el-form-item>
        </el-form>

        <div class="auth-footer">
          已有账号？<a href="/login">立即登录 →</a>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
  import { reactive, ref } from "vue";
  import { User, Lock, Right, CircleCheckFilled } from "@element-plus/icons-vue";
  import request from "@/utils/request";
  import { ElMessage } from "element-plus";
  import router from "@/router";

  const validatePass = (rule, value, callback) => {
    if (!value) {
      callback(new Error('请确认密码'))
    } else if (value !== data.form.password) {
      callback(new Error('两次输入密码不一致'))
    } else {
      callback()
    }
  }

  const data = reactive({
    form: { role: 'USER' },
    rules: {
      username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
      password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
      confirmPassword: [{ validator: validatePass, trigger: 'blur' }],
    }
  })

  const formRef = ref()

  const register = () => {
    formRef.value.validate((valid => {
      if (valid) {
        request.post('/register', data.form).then(res => {
          if (res.code === '200') {
            ElMessage.success("注册成功")
            router.push('/login')
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

.auth-hero {
  position: relative;
  background: linear-gradient(135deg, #fdf6e3 0%, #f5ecc8 50%, #e6c558 100%);
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
  color: #524939;
}

.hero-points .el-icon {
  font-size: 18px;
  color: #b8941f;
}

.hero-deco {
  position: absolute;
  border-radius: 50%;
  filter: blur(2px);
  opacity: 0.35;
}

.hero-deco-1 { width: 280px; height: 280px; background: #ffffff; top: -80px; right: -80px; opacity: 0.55; }
.hero-deco-2 { width: 180px; height: 180px; background: #d4af37; bottom: -50px; right: 30%; opacity: 0.25; }
.hero-deco-3 { width: 120px; height: 120px; background: #ffffff; bottom: 18%; left: -40px; opacity: 0.55; }

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

.auth-submit {
  width: 100%;
  border-radius: 10px;
  background: linear-gradient(135deg, #d4af37 0%, #b8941f 100%);
  border: none;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  height: 44px;
  color: #fff;
  box-shadow: 0 8px 20px rgba(184, 148, 31, 0.32);
  transition: all var(--t-base) var(--ease-out);
}

.auth-submit:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 26px rgba(184, 148, 31, 0.42);
  background: linear-gradient(135deg, #e6c558 0%, #d4af37 100%);
  color: #fff;
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

@media (max-width: 900px) {
  .auth-page { grid-template-columns: 1fr; }
  .auth-hero { display: none; }
}
</style>
