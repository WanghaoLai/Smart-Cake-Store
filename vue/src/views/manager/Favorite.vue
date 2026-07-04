<template>
  <div>
    <div class="card" style="margin-bottom: 5px;">
      <el-input v-model="data.name" style="width: 300px; margin-right: 10px" placeholder="请输入蛋糕名称查询"></el-input>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button type="info" style="margin: 0 10px" @click="reset">重置</el-button>
    </div>
    <div style="margin: 10px 0">
      <el-row :gutter="10">
        <el-col :span="6" v-for="item in filteredData">
          <div class="card">
            <img :src="item.img" alt="" style="width: 100%; height: 300px; border-radius: 5px">
            <div>
              <div style="font-weight: bold; font-size: 16px">{{ item.name }}</div>
              <el-tooltip :content="item.description" placement="top" effect="light">
                <div style="margin-top: 5px" class="line1">简介：{{ item.description }}</div>
              </el-tooltip>
              <div style="margin-top: 10px; display: flex">
                <div style="color: red; font-weight: bold; flex: 1">价格：￥{{ item.price }}</div>
                <div style="flex: 1; text-align: right">剩余{{ item.num }}{{ item.unit }}</div>
              </div>
              <div style="margin-top: 10px; display: flex; justify-content: space-between">
                <el-button type="danger" size="big" @click="removeFav(item.id)">取消收藏</el-button>
                <el-button type="success" :disabled="item.num === 0" @click="reserveInit(item.id)">预订</el-button>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
      <div v-if="filteredData.length === 0 && data.allData.length === 0" style="text-align: center; padding: 60px; color: #909399;">
        <el-icon :size="48"><Star /></el-icon>
        <p style="margin-top: 12px;">还没有收藏商品，去商品页面看看吧</p>
      </div>
    </div>
    <el-dialog title="订单信息" width="40%" v-model="data.formVisible" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="data.form" :rules="data.rules" label-width="100px" style="padding-right: 50px">
        <el-form-item label="预定数量" prop="num">
          <el-input-number v-model="data.form.num" :min="1" autocomplete="off" />
        </el-form-item>
        <el-form-item label="收货地址" prop="addressId">
          <el-select v-model="data.form.addressId" placeholder="请选择地址">
            <el-option
              v-for="addr in data.addressList"
              :key="addr.id"
              :label="addr.name + ' - ' + addr.address"
              :value="addr.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
      <span class="dialog-footer">
        <el-button @click="data.formVisible = false">取 消</el-button>
        <el-button type="primary" @click="save">预 定</el-button>
      </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from "vue";
import request from "@/utils/request";
import {ElMessage} from "element-plus";
import { Star } from "@element-plus/icons-vue";

const formRef = ref()
const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  form: {},
  formVisible: false,
  name: null,
  allData: [],
  addressList: [],
})

const filteredData = computed(() => {
  if (!data.name) return data.allData
  return data.allData.filter(item => item.name.includes(data.name))
})

const rules = reactive({
  num: [{ required: true, message: '请输入数量', trigger: 'blur' }],
  addressId: [{ required: true, message: '请选择地址', trigger: 'change' }],
})

const load = () => {
  request.get('/favorite/list').then(res => {
    if (res.code === '200') {
      data.allData = res.data || []
    }
  })
}

const reset = () => {
  data.name = null
}

const loadAddress = () => {
  request.get('/address/selectAll', {
    params: { userId: data.user.id }
  }).then(res => {
    if (res.code === '200') {
      data.addressList = res.data
    }
  })
}

const reserveInit = (goodsId) => {
  data.form = {}
  data.form.userId = data.user.id
  data.form.goodsId = goodsId
  data.formVisible = true
}

const save = () => {
  formRef.value.validate(valid => {
    if (valid) {
      request.post('/orders/add', data.form).then(res => {
        if (res.code === '200') {
          ElMessage.success('预定成功，等待管理员发货')
          data.formVisible = false
        } else {
          ElMessage.error(res.msg)
        }
      })
    }
  })
}

const removeFav = (goodsId) => {
  request.delete('/favorite/remove/' + goodsId).then(res => {
    if (res.code === '200') {
      ElMessage.success('已取消收藏')
      load()
    } else {
      ElMessage.error(res.msg)
    }
  })
}

load()
loadAddress()
</script>
