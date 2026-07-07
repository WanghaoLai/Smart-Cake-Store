<template>
  <div>
    <div class="card" style="margin-bottom: 5px;">
      <el-input v-model="data.name" style="width: 300px; margin-right: 10px" placeholder="请输入蛋糕名称查询"></el-input>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button type="info" style="margin: 0 10px" @click="reset">重置</el-button>
    </div>
    <div style="margin: 10px 0">
      <el-row :gutter="10">
        <el-col :span="6" v-for="item in data.tableData">
          <div class="card">
            <img :src="item.img" alt="" style="width: 100%; height: 300px; border-radius: 5px">
            <div>
              <div style="font-weight: bold; font-size: 16px">{{ item.name }}</div>
              <div style="margin-top: 5px" class="line1" :title="item.description">简介：{{ item.description }}</div>
              <div style="margin-top: 10px; display: flex">
                <div style="color: red; font-weight: bold; flex: 1">价格：￥{{ item.price }}</div>
                <div style="flex: 1; text-align: right">剩余{{ item.num }}{{ item.unit }}</div>
              </div>
              <div style="margin-top: 10px; display: flex; justify-content: space-between">
                <el-button :type="data.favoritedIds[item.id] ? 'warning' : 'default'" size="big" @click="toggleFav(item.id)">
                  {{ data.favoritedIds[item.id] ? '已收藏' : '收藏' }}
                </el-button>
                <el-button type="success" :disabled="item.num === 0" @click="reserveInit(item.id)">预订</el-button>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
    <div class="card">
      <el-pagination @current-change="load" background layout="total, prev, pager, next" v-model:page-size="data.pageSize" v-model:current-page="data.pageNum" :total="data.total"/>
    </div>
    <el-dialog title="订单信息" width="40%" v-model="data.formVisible" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="data.form" :rules="data.rules" label-width="100px" style="padding-right: 50px">
        <el-form-item label="预定数量" prop="num">
          <el-input-number v-model="data.form.num" :min="1" autocomplete="off" />
        </el-form-item>
        <el-form-item label="收货地址" prop="addressId">
          <el-select v-model="data.form.addressId" placeholder="请选择地址">
            <el-option
              v-for="item in data.addressList"
              :key="item.id"
              :label="item.name + ' - ' + item.address"
              :value="item.id"
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
import { reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import request from "@/utils/request";
import {ElMessage, ElMessageBox} from "element-plus";

const route = useRoute()
const formRef = ref()
const uploadUrl = import.meta.env.VITE_BASE_URL + '/files/upload'


const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  form: {},
  formVisible: false,
  name: null,
  categoryId: 0,
  categoryList: [],
  pageNum: 1,
  pageSize: 8,
  total: 0,
  tableData: [],
  addressList: [],
  favoritedIds: {},
})


const loadFavorites = () => {
  request.get('/favorite/list').then(res => {
    if (res.code === '200') {
      const map = {}
      ;(res.data || []).forEach(g => { map[g.id] = true })
      data.favoritedIds = map
    }
  })
}

const toggleFav = (goodsId) => {
  if (data.favoritedIds[goodsId]) {
    request.delete('/favorite/remove/' + goodsId).then(res => {
      if (res.code === '200') {
        data.favoritedIds[goodsId] = false
        ElMessage.success('已取消收藏')
      } else {
        ElMessage.error(res.msg)
      }
    })
  } else {
    request.post('/favorite/add', { goods_id: goodsId }).then(res => {
      if (res.code === '200') {
        data.favoritedIds[goodsId] = true
        ElMessage.success('收藏成功')
      } else {
        ElMessage.error(res.msg)
      }
    })
  }
}


const loadAddress = () => {
  request.get('/address/selectAll', {
    params: {
      userId: data.user.id
    }
  }).then(res => {
    if (res.code === '200') {
      data.addressList = res.data
    } else {
      ElMessage.error(res.msg)
    }
  })
}
const loadCategory = () => {
  request.get('/category/selectAll').then(res => {
    if (res.code === '200') {
      data.categoryList = res.data
      const categoryName = route.query.categoryName
      if (categoryName) {
        const matched = res.data.find(c => c.name === categoryName)
        data.categoryId = matched ? matched.id : 0
      }
      load()
    } else {
      ElMessage.error(res.msg)
    }
  })
}
loadAddress()
loadCategory()
loadFavorites()

watch(() => route.query.categoryName, (newName) => {
  if (newName) {
    const matched = data.categoryList.find(c => c.name === newName)
    data.categoryId = matched ? matched.id : 0
  } else {
    data.categoryId = 0
  }
  data.pageNum = 1
  load()
})

const reserveInit = (goodsId) => {
  data.form = {}
  data.form.userId = data.user.id
  data.form.goodsId = goodsId
  data.formVisible = true
}


const load = () => {
  request.get('/goods/selectPage', {
    params: {
      pageNum: data.pageNum,
      pageSize: data.pageSize,
      name: data.name,
      categoryId: data.categoryId,
    }
  }).then(res => {
    if (res.code === '200') {
      data.tableData = res.data?.list
      data.total = res.data?.total
    } else {
      ElMessage.error(res.msg)
    }
  })
}

const save = () => {
  request.post('/orders/add', data.form).then(res => {
    if (res.code === '200') {
      ElMessage.success('预定成功，等待管理员发货')
      data.formVisible = false
    } else {
      ElMessage.error(res.msg)
    }
  })
}

const reset = () => {
  data.name = null
  load()
}

const handleImgSuccess = (res) => {
  data.form.img = res.data
}

</script>