<template>
  <div>

    <div class="card" style="margin-bottom: 10px">
      <div>欢迎您，<b>{{ data.user.name }}</b> 祝您今天过得开心！</div>
    </div>
<!--    <div class="card" style="line-height:30px; padding: 20px">-->
<!--      <div>B站UP：<a style="color: #1890ff" href="https://space.bilibili.com/432113931">武哥聊编程</a> 出品，感谢大家的支持~</div>-->
<!--      <div>从0开始带你做一套完整的前后端分离项目，<b style="color: red">完全免费</b>，大家多多三连支持一波噢~</div>-->
<!--      <div>获取项目资料请访问：<a style="color: #1890ff; font-weight: bold" href="https://javaxm.cn">https://javaxm.cn</a></div>-->
<!--      <div>另外，项目实战网是我们的官方网站，里面有很多精致的带敲学习项目，大家可以来这里看看：-->
<!--        <a style="color: #1890ff; font-weight: bold" href="https://javaxmsz.cn">https://javaxmsz.cn</a></div>-->
<!--    </div>-->
    <div class="card" style="margin-top: 10px">
      <div style="font-size: 18px; font-weight: bold; padding: 20px">系统公告</div>
      <el-timeline style="max-width: 600px" v-for="item in data.noticeData">
          <el-timeline-item :timestamp="item.time" placement="top">
            <h4>{{ item.name }}</h4>
            <p>{{ item.content }}</p>
          </el-timeline-item>
      </el-timeline>
    </div>
  </div>
</template>

<script setup>
import { reactive } from "vue";
import request from "@/utils/request";
import {ElMessage} from "element-plus";

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
})

const loadNotice = () => {
  request.get('/notice/selectAll').then(res => {
    if (res.code === '200') {
      data.noticeData = res.data
    } else {
      ElMessage.error(res.msg)
    }
  })
}
loadNotice()

</script>