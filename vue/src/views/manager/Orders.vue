<template>
  <div>
    <div class="card" style="margin-bottom: 5px;">
      <el-input v-model="data.name" style="width: 300px; margin-right: 10px" placeholder="请输入商品名称查询"></el-input>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button type="info" style="margin: 0 10px" @click="reset">重置</el-button>
    </div>
    <div class="card" style="margin-bottom: 5px">
      <el-table :data="data.tableData" stripe>
        <el-table-column label="订单号" prop="order_no" width="180"></el-table-column>
        <el-table-column label="下单用户" prop="userName"></el-table-column>
        <el-table-column label="商品图片" prop="goodsImg">
          <template #default="scope">
            <el-image v-if="scope.row.goodsImg" preview-teleported :src="scope.row.goodsImg" :preview-src-list="[scope.row.goodsImg]" style="width: 40px; height: 40px; border-radius: 5px"></el-image>
          </template>
        </el-table-column>
        <el-table-column label="商品名称" prop="goodsName"></el-table-column>
        <el-table-column label="商品单价" prop="goodsPrice">
          <template v-slot="scope">
            <span>￥{{ scope.row.goodsPrice }} / {{ scope.row.goodsUnit }}</span>
          </template>
        </el-table-column>
        <el-table-column label="预订数量" prop="num"></el-table-column>
        <el-table-column label="订单总价" prop="total"></el-table-column>
        <el-table-column label="收货人" prop="aName"></el-table-column>
        <el-table-column label="收货地址" prop="aAddress"></el-table-column>
        <el-table-column label="联系方式" prop="aPhone"></el-table-column>
        <el-table-column label="操作" align="center" width="160">
          <template #default="scope">
            <el-button type="danger" @click="handleDelete(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="card">
      <el-pagination @current-change="load" background layout="total, prev, pager, next" v-model:page-size="data.pageSize" v-model:current-page="data.pageNum" :total="data.total"/>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import request from "@/utils/request";
import {ElMessage, ElMessageBox} from "element-plus";


const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  name: null,
  pageNum: 1,
  pageSize: 8,
  total: 0,
  tableData: [],
})

const load = () => {
  request.get('/orders/selectPage', {
    params: {
      pageNum: data.pageNum,
      pageSize: data.pageSize,
      goodsName: data.name,
      userId: data.user.role === '用户' ? data.user.id : 0
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
load()

const handleDelete = (id) => {
  ElMessageBox.confirm('删除后数据无法恢复，您确定删除吗?', '删除确认', { type: 'warning' }).then(res => {
    request.delete('/orders/delete/' + id).then(res => {
      if (res.code === '200') {
        load()
        ElMessage.success('操作成功')
      } else {
        ElMessage.error(res.msg)
      }
    })
  }).catch(err => {})
}

const reset = () => {
  data.name = null
  load()
}

</script>