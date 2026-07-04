<template>
  <div style="width: 40%">
    <div class="card" style="padding: 30px">
      <el-form ref="formRef" :rules="data.rules" :model="data.form" label-width="100px" style="padding-right: 50px">
        <el-form-item label="原密码" prop="password">
          <el-input v-model="data.form.password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="data.form.newPassword" show-password />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPasword">
          <el-input v-model="data.form.confirmPasword" show-password />
        </el-form-item>
        <div style="text-align: center">
          <el-button type="primary" @click="save">保存</el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import {reactive, ref} from "vue"
import request from "@/utils/request";
import {ElMessage} from "element-plus";
import router from "@/router";

const formRef = ref()
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
    password: [
      {required: true, message: '请输入原密码', trigger: 'blur'}
    ],
    newPassword: [
      {required: true, message: '请输入新密码', trigger: 'blur'}
    ],
    confirmPasword: [
      {required: true, message: '请确认新密码', trigger: 'blur'}
    ],
  }
})
data.form.id = data.user.id
data.form.role = data.user.role

// 把当前修改的用户信息存储到后台数据库
const save = () => {
  formRef.value.validate(valid => {
    if (valid) {
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
          router.push('/login')
        } else {
          ElMessage.error(res.msg)
        }
      })
    }
  })
}
</script>