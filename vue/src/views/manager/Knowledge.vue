<template>
  <div class="knowledge-page">
    <!-- 顶部统计 + 上传 -->
    <div class="stats-row">
      <div class="stat-card stat-primary">
        <div class="stat-icon"><el-icon><Document /></el-icon></div>
        <div class="stat-meta">
          <div class="stat-label">文档总数</div>
          <div class="stat-num">{{ data.stats.document_count || 0 }}</div>
        </div>
      </div>
      <div class="stat-card stat-accent">
        <div class="stat-icon"><el-icon><Files /></el-icon></div>
        <div class="stat-meta">
          <div class="stat-label">分块总数</div>
          <div class="stat-num">{{ data.stats.chunk_count || 0 }}</div>
        </div>
      </div>
      <div class="upload-zone card" @click="triggerUpload" @dragover.prevent="data.dragActive = true" @dragleave.prevent="data.dragActive = false" @drop.prevent="handleDrop" :class="{ active: data.dragActive }">
        <input ref="fileInputRef" type="file" accept=".txt,.pdf,.docx" hidden @change="handleFileSelect" />
        <div class="upload-icon"><el-icon><Upload /></el-icon></div>
        <div class="upload-body">
          <div class="upload-title">{{ data.uploading ? '上传中...' : '点击或拖拽上传文档' }}</div>
          <div class="upload-sub">支持 .txt .pdf .docx 格式，单文件 ≤ 20MB</div>
        </div>
        <el-button v-if="data.uploading" type="primary" loading round>上传中</el-button>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="card list-card">
      <div class="card-head">
        <h3 class="card-title"><el-icon><FolderOpened /></el-icon>知识库文档</h3>
        <span class="card-sub">共 {{ data.tableData.length }} 个文档</span>
      </div>

      <div v-if="data.tableData.length" class="doc-list">
        <div v-for="doc in data.tableData" :key="doc.id" class="doc-item">
          <div class="doc-icon" :class="docExt(doc.original_name)">
            {{ docExt(doc.original_name) }}
          </div>
          <div class="doc-main">
            <div class="doc-name line1">{{ doc.original_name }}</div>
            <div class="doc-meta">
              <span class="meta-pill"><el-icon><Document /></el-icon>{{ formatSize(doc.file_size) }}</span>
              <span class="meta-pill"><el-icon><Grid /></el-icon>{{ doc.chunk_count }} 分块</span>
              <span class="meta-pill"><el-icon><Clock /></el-icon>{{ formatTime(doc.created_at) }}</span>
            </div>
          </div>
          <el-button text type="danger" @click="handleDelete(doc.id)">
            <el-icon><Delete /></el-icon>删除
          </el-button>
        </div>
      </div>
      <div v-else class="empty-state">
        <el-icon :size="56"><Document /></el-icon>
        <p>暂无文档</p>
        <span>上传文档后将自动构建知识库</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from "vue";
import request from "@/utils/request";
import { ElMessage, ElMessageBox } from "element-plus";
import { Upload, Document, Files, Grid, Clock, FolderOpened, Delete } from "@element-plus/icons-vue";

const fileInputRef = ref(null)

const data = reactive({
  tableData: [],
  uploading: false,
  dragActive: false,
  stats: {},
})

const load = () => {
  request.get('/knowledge/list').then(res => {
    if (res.code === '200') data.tableData = res.data || []
  })
  request.get('/knowledge/stats').then(res => {
    if (res.code === '200') data.stats = res.data || {}
  })
}

const triggerUpload = () => {
  if (!data.uploading) fileInputRef.value?.click()
}

const handleFileSelect = (e) => {
  const file = e.target.files?.[0]
  if (file) tryUpload(file)
  e.target.value = ''
}

const handleDrop = (e) => {
  data.dragActive = false
  const file = e.dataTransfer.files?.[0]
  if (file) tryUpload(file)
}

const tryUpload = async (file) => {
  const ext = file.name.split('.').pop().toLowerCase()
  if (!['txt', 'pdf', 'docx'].includes(ext)) {
    ElMessage.error('仅支持 .txt .pdf .docx 格式')
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 20MB')
    return
  }

  data.uploading = true
  const formData = new FormData()
  formData.append('file', file)
  try {
    const res = await request.post('/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    if (res.code === '200') {
      ElMessage.success('文档上传成功，已构建知识库')
      load()
    } else { ElMessage.error(res.msg) }
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    data.uploading = false
  }
}

const handleDelete = (id) => {
  ElMessageBox.confirm('删除后知识库中将移除该文档的所有内容，确定删除吗？', '删除确认', { type: 'warning' }).then(() => {
    request.delete('/knowledge/delete/' + id).then(res => {
      if (res.code === '200') { ElMessage.success('删除成功'); load() } else { ElMessage.error(res.msg) }
    })
  }).catch(() => {})
}

const docExt = (name) => {
  if (!name) return 'txt'
  return (name.split('.').pop() || 'txt').toLowerCase()
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const formatTime = (t) => {
  if (!t) return ''
  const d = new Date(t)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => { load() })
</script>

<style scoped>
.knowledge-page {
  padding: 20px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* —— 顶部统计行 —— */
.stats-row {
  display: grid;
  grid-template-columns: 220px 220px 1fr;
  gap: 16px;
}

.stat-card {
  background: var(--c-bg-card);
  border-radius: var(--r-lg);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  border: none;
  box-shadow: var(--shadow-card);
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0;
  width: 4px; height: 100%;
  background: var(--c-primary);
}

.stat-primary::before { background: var(--grad-primary); }
.stat-accent::before { background: var(--grad-warm); }

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.stat-primary .stat-icon { background: var(--c-primary-soft); color: var(--c-primary); }
.stat-accent .stat-icon { background: var(--c-accent-soft); color: var(--c-accent); }

.stat-label {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin-bottom: 4px;
}

.stat-num {
  font-size: 22px;
  font-weight: 700;
  color: var(--c-text-primary);
  font-feature-settings: "tnum";
}

/* —— 上传区 —— */
.upload-zone {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  cursor: pointer;
  border: 2px dashed var(--c-border);
  transition: all var(--t-base) var(--ease-out);
  background: var(--c-bg-card);
}

.upload-zone:hover,
.upload-zone.active {
  border-color: var(--c-primary);
  background: var(--c-primary-soft);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.upload-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--grad-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.upload-body { flex: 1; }

.upload-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
}

.upload-sub {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin-top: 2px;
}

/* —— 列表卡片 —— */
.list-card { padding: 20px; }

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title .el-icon { color: var(--c-primary); }

.card-sub {
  font-size: 12px;
  color: var(--c-text-secondary);
  padding: 2px 8px;
  background: var(--c-bg-soft);
  border-radius: var(--r-pill);
}

.doc-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border-radius: var(--r-md);
  background: var(--c-bg-soft);
  border: 1px solid transparent;
  transition: all var(--t-fast) var(--ease-out);
}

.doc-item:hover {
  background: var(--c-bg-card);
  box-shadow: var(--shadow-sm);
}

.doc-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
  background: var(--c-info);
  text-transform: uppercase;
}

.doc-icon.pdf { background: #c25450; }
.doc-icon.docx { background: #6b9b37; }
.doc-icon.txt { background: var(--c-accent); }

.doc-main { flex: 1; min-width: 0; }

.doc-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
}

.doc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.meta-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--c-bg-soft);
  color: var(--c-text-secondary);
  border-radius: var(--r-pill);
  font-size: 11px;
}

.doc-item:hover .meta-pill { background: var(--c-bg-soft); }

.empty-state {
  padding: 50px 20px;
  text-align: center;
  color: var(--c-text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.empty-state p {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text-primary);
  margin: 8px 0 0;
}

.empty-state span {
  font-size: 12px;
}

@media (max-width: 900px) {
  .stats-row { grid-template-columns: 1fr; }
}
</style>
