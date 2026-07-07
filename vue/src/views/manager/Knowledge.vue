<template>
  <div>
    <div class="card" style="margin-bottom: 5px;">
      <div style="display: flex; align-items: center; gap: 16px;">
        <el-upload
          :show-file-list="false"
          :http-request="handleUpload"
          :before-upload="beforeUpload"
          accept=".txt,.pdf,.docx"
        >
          <el-button type="primary" :loading="data.uploading">
            <el-icon><Upload /></el-icon>
            上传文档
          </el-button>
        </el-upload>
        <span style="color: #909399; font-size: 13px;">支持 .txt .pdf .docx 格式</span>
        <div style="flex: 1"></div>
        <span style="color: #606266;">
          共 {{ data.stats.document_count || 0 }} 个文档，{{ data.stats.chunk_count || 0 }} 个分块
        </span>
      </div>
    </div>
    <div class="card" style="margin-bottom: 5px">
      <el-table :data="data.tableData" stripe>
        <el-table-column label="文件名" prop="original_name"></el-table-column>
        <el-table-column label="大小">
          <template #default="scope">
            {{ formatSize(scope.row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="分块数" prop="chunk_count" width="100"></el-table-column>
        <el-table-column label="上传时间" prop="created_at" width="180"></el-table-column>
        <el-table-column label="操作" align="center" width="120">
          <template #default="scope">
            <el-button type="danger" size="small" @click="handleDelete(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="data.tableData.length === 0" style="text-align: center; padding: 40px; color: #909399;">
        暂无文档，请上传文档构建知识库
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from "vue";
import request from "@/utils/request";
import {ElMessage, ElMessageBox} from "element-plus";
import { Upload } from "@element-plus/icons-vue";

const data = reactive({
  tableData: [],
  uploading: false,
  stats: {},
})

const load = () => {
  request.get('/knowledge/list').then(res => {
    if (res.code === '200') {
      data.tableData = res.data || []
    }
  })
  request.get('/knowledge/stats').then(res => {
    if (res.code === '200') {
      data.stats = res.data || {}
    }
  })
}

const beforeUpload = (file) => {
  const ext = file.name.split('.').pop().toLowerCase()
  if (!['txt', 'pdf', 'docx'].includes(ext)) {
    ElMessage.error('仅支持 .txt .pdf .docx 格式')
    return false
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 20MB')
    return false
  }
  return true
}

const handleUpload = async (options) => {
  data.uploading = true
  const formData = new FormData()
  formData.append('file', options.file)
  try {
    const res = await request.post('/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    if (res.code === '200') {
      ElMessage.success('文档上传成功，已构建知识库')
      load()
    } else {
      ElMessage.error(res.msg)
    }
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    data.uploading = false
  }
}

const handleDelete = (id) => {
  ElMessageBox.confirm('删除后知识库中将移除该文档的所有内容，确定删除吗？', '删除确认', { type: 'warning' }).then(() => {
    request.delete('/knowledge/delete/' + id).then(res => {
      if (res.code === '200') {
        ElMessage.success('删除成功')
        load()
      } else {
        ElMessage.error(res.msg)
      }
    })
  }).catch(() => {})
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

load()
</script>
