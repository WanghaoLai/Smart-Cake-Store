<template>
  <div>
    <div style="height: 60px; border-bottom: 1px solid #ddd; display: flex; align-items: center;">
      <div style="flex: 1">
        <div style="padding-left: 20px; display: flex; align-items: center">
          <img src="@/assets/imgs/logo.png" alt="" style="width: 40px; border-radius: 50%; border: 2px solid orange">
          <div style="font-weight: bold; font-size: 24px; margin-left: 5px">Little-bear Cake Store</div>
        </div>
      </div>
      <div style="width: fit-content; padding-right: 10px; display: flex; align-items: center;">
        <img style="width: 40px; height: 40px; border-radius: 50%" :src="data.user.avatar || 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'" alt="">
        <span style="margin-left: 5px">{{ data.user.name }}</span>
      </div>
    </div>

    <div style="display: flex">
      <div style="width: 200px; border-right: 1px solid #ddd; min-height: calc(100vh - 60px)">
        <el-menu
            router
            style="border: none"
            :default-active="router.currentRoute.value.fullPath"
            :default-openeds="['user']"
        >
          <el-menu-item index="/manager/home">
            <el-icon><HomeFilled /></el-icon>
            <span>系统首页</span>
          </el-menu-item>
          <el-sub-menu index="user" v-if="data.user.role === '用户'">
            <template #title>
              <el-icon><Avatar /></el-icon>
              <span>蛋糕详情</span>
            </template>
            <el-menu-item index="/manager/cake">
              <el-icon><Cherry /></el-icon>
              <span>全部商品</span>
            </el-menu-item>
            <el-menu-item index="/manager/cake?categoryName=情侣空间">
              <el-icon><Cherry /></el-icon>
              <span>情侣空间</span>
            </el-menu-item>
            <el-menu-item index="/manager/cake?categoryName=卡通乐趣">
              <el-icon><Apple /></el-icon>
              <span>卡通乐趣</span>
            </el-menu-item>
            <el-menu-item index="/manager/cake?categoryName=朋友同事">
              <el-icon><Watermelon /></el-icon>
              <span>朋友同事</span>
            </el-menu-item>
            <el-menu-item index="/manager/cake?categoryName=女神专属">
              <el-icon><Orange /></el-icon>
              <span>女神专属</span>
            </el-menu-item>
            <el-menu-item index="/manager/cake?categoryName=男生定制">
              <el-icon><Pear /></el-icon>
              <span>男生定制</span>
            </el-menu-item>
            <el-menu-item index="/manager/cake?categoryName=父母长辈">
              <el-icon><Grape /></el-icon>
              <span>父母长辈</span>
            </el-menu-item>
            <el-menu-item index="/manager/cake?categoryName=二层三层">
              <el-icon><Ice-tea /></el-icon>
              <span>二层三层</span>
            </el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="info" v-if="data.user.role === '管理员'">
            <template #title>
              <el-icon><Menu /></el-icon>
              <span>商品管理</span>
            </template>
            <el-menu-item index="/manager/category">
              <el-icon><Coin /></el-icon>
              <span>蛋糕分类</span>
            </el-menu-item>
            <el-menu-item index="/manager/goods">
              <el-icon><Refrigerator /></el-icon>
              <span>蛋糕信息</span>
            </el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="user" v-if="data.user.role === '管理员'">
            <template #title>
              <el-icon><Avatar /></el-icon>
              <span>用户管理</span>
            </template>
            <el-menu-item index="/manager/admin">
              <el-icon><Position /></el-icon>
              <span>管理员信息</span>
            </el-menu-item>
            <el-menu-item index="/manager/user">
              <el-icon><User /></el-icon>
              <span>用户信息</span>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item index="/manager/orders">
            <el-icon><Sold-out /></el-icon>
            <span>订单管理</span>
          </el-menu-item>
          <el-menu-item index="/manager/address">
            <el-icon><Location /></el-icon>
            <span>地址管理</span>
          </el-menu-item>
          <el-menu-item index="/manager/notice" v-if="data.user.role === '管理员'">
            <el-icon><Monitor /></el-icon>
            <span>公告管理</span>
          </el-menu-item>
          <el-menu-item index="/manager/chat">
            <el-icon><ChatDotRound /></el-icon>
            <span>智能客服</span>
          </el-menu-item>
          <el-menu-item index="/manager/person">
            <el-icon><User /></el-icon>
            <span>个人资料</span>
          </el-menu-item>
          <el-menu-item index="/manager/password">
            <el-icon><Lock /></el-icon>
            <span>修改密码</span>
          </el-menu-item>
          <el-menu-item index="/login" @click="logout">
            <el-icon><SwitchButton /></el-icon>
            <span>退出系统</span>
          </el-menu-item>
        </el-menu>
      </div>

      <div style="flex: 1; width: 0; background-color: #f8f8ff; padding: 10px">
        <router-view @updateUser="updateUser" />
      </div>
    </div>

  </div>
</template>

<script setup>
import { reactive } from "vue";
import router from "@/router";
import {ElMessage} from "element-plus";

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}')
})

if (!data.user?.id) {
  ElMessage.error('请登录！')
  router.push('/login')
}

const updateUser = () => {
  data.user = JSON.parse(localStorage.getItem('system-user') || '{}')
}

const logout = () => {
  ElMessage.success('退出成功')
  localStorage.removeItem('token')
  localStorage.removeItem('system-user')
  router.push('/login')
}
</script>

<style scoped>

:deep(th)  {
  color: #333;
}
</style>