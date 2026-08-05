<template>
  <div class="admin-page">
    <!-- 工具栏 -->
    <div class="toolbar card">
      <el-input v-model="data.name" placeholder="请输入名称查询" :prefix-icon="Search" clearable class="toolbar-search" @keyup.enter="load" @clear="load" />
      <el-button type="primary" round @click="load"><el-icon style="margin-right:4px"><Search /></el-icon>查询</el-button>
      <el-button round @click="reset">重置</el-button>
      <div class="toolbar-right">
        <el-button type="primary" round @click="handleAdd"><el-icon style="margin-right:4px"><Plus /></el-icon>新增商品</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="card table-card">
      <el-table :data="data.tableData" stripe class="admin-table">
        <el-table-column label="商品" prop="name" min-width="280">
          <template #default="scope">
            <div class="goods-cell">
              <el-image v-if="scope.row.img" preview-teleported :src="scope.row.img" :preview-src-list="[scope.row.img]" class="cell-img" fit="cover" />
              <div v-else class="cell-img placeholder"><el-icon><Picture /></el-icon></div>
              <div class="goods-info-cell">
                <div class="goods-name-cell line1">{{ scope.row.name }}</div>
                <div class="goods-desc-cell line1">{{ scope.row.description }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="价格" prop="price" width="120">
          <template #default="scope">
            <span class="cell-price">¥{{ scope.row.price }}</span>
          </template>
        </el-table-column>
        <el-table-column label="库存" prop="num" width="120">
          <template #default="scope">
            <span class="cell-stock" :class="{ warn: scope.row.num <= 5 && scope.row.num > 0, empty: scope.row.num === 0 }">
              {{ scope.row.num }} {{ scope.row.unit }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="分类" prop="categoryName" width="120">
          <template #default="scope">
            <el-tag v-if="scope.row.categoryName" type="info" effect="light" round>{{ scope.row.categoryName }}</el-tag>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" align="center" width="180">
          <template #default="scope">
            <el-button text type="primary" @click="handleEdit(scope.row)"><el-icon><Edit /></el-icon>编辑</el-button>
            <el-button text type="danger" @click="handleDelete(scope.row.id)"><el-icon><Delete /></el-icon>删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card pagination-card">
      <el-pagination @current-change="load" background layout="total, prev, pager, next" v-model:page-size="data.pageSize" v-model:current-page="data.pageNum" :total="data.total"/>
    </div>

    <el-dialog v-model="data.formVisible" width="600px" :close-on-click-modal="false" destroy-on-close>
      <template #header>
        <div class="dialog-header-custom">
          <el-icon class="dialog-icon"><Refrigerator /></el-icon>
          <div>
            <div class="dialog-title">{{ data.form.id ? '编辑商品' : '新增商品' }}</div>
            <div class="dialog-sub">完善商品信息与图片</div>
          </div>
        </div>
      </template>
      <el-form ref="formRef" :model="data.form" :rules="data.rules" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="商品名称" prop="name">
              <el-input v-model="data.form.name" autocomplete="off" placeholder="请输入商品名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类" prop="categoryId">
              <el-select v-model="data.form.categoryId" placeholder="请选择分类" style="width: 100%">
                <el-option v-for="c in data.categoryList" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="商品描述" prop="description">
          <el-input type="textarea" :rows="2" v-model="data.form.description" autocomplete="off" placeholder="请输入商品描述" />
        </el-form-item>
        <el-form-item label="商品图片" prop="img">
          <el-upload :action="uploadUrl" list-type="picture-card" :on-success="handleImgSuccess" :file-list="data.fileList" :limit="1" :headers="uploadHeaders" class="goods-uploader">
            <el-icon><Plus /></el-icon>
          </el-upload>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="价格 (¥)" prop="price">
              <el-input v-model="data.form.price" autocomplete="off" placeholder="0.00" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单位" prop="unit">
              <el-input v-model="data.form.unit" autocomplete="off" placeholder="如：个 / 份" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="库存" prop="num">
              <el-input-number v-model="data.form.num" :min="0" :max="9999" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="data.formVisible = false" round>取消</el-button>
        <el-button type="primary" @click="save" round>保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from "vue";
import request from "@/utils/request";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Plus, Edit, Delete, Refrigerator, Picture } from "@element-plus/icons-vue";

const formRef = ref()
const uploadUrl = import.meta.env.VITE_BASE_URL + '/files/upload?category=goods'
const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  form: {},
  formVisible: false,
  fileList: [],
  name: null,
  pageNum: 1,
  pageSize: 10,
  total: 0,
  tableData: [],
  categoryList: [],
  rules: {
    name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
    description: [{ required: true, message: '请输入描述', trigger: 'blur' }],
    price: [{ required: true, message: '请输入价格', trigger: 'blur' }],
    unit: [{ required: true, message: '请输入单位', trigger: 'blur' }],
    num: [{ required: true, message: '请输入库存', trigger: 'blur' }],
    categoryId: [{ required: true, message: '请选择分类', trigger: 'change' }],
    img: [{ required: true, message: '请上传图片', trigger: 'change' }],
  }
})

const loadCategory = () => {
  request.get('/category/selectAll').then(res => {
    if (res.code === '200') data.categoryList = res.data
    else ElMessage.error(res.msg)
  })
}
loadCategory()

const load = () => {
  request.get('/goods/selectPage', {
    params: { pageNum: data.pageNum, pageSize: data.pageSize, name: data.name }
  }).then(res => {
    if (res.code === '200') {
      data.tableData = res.data?.list || []
      data.total = res.data?.total || 0
    } else { ElMessage.error(res.msg) }
  })
}
load()

const handleAdd = () => {
  data.form = {}
  data.fileList = []
  data.formVisible = true
}

const handleEdit = (row) => {
  data.form = JSON.parse(JSON.stringify(row))
  data.fileList = row.img ? [{ name: 'img', url: row.img }] : []
  data.formVisible = true
}

const handleDelete = (id) => {
  ElMessageBox.confirm('删除后数据无法恢复，您确定删除吗?', '删除确认', { type: 'warning' }).then(res => {
    request.delete('/goods/delete/' + id).then(res => {
      if (res.code === '200') { load(); ElMessage.success('操作成功') } else { ElMessage.error(res.msg) }
    })
  }).catch(() => {})
}

const add = () => {
  request.post('/goods/add', data.form).then(res => {
    if (res.code === '200') { ElMessage.success('操作成功'); data.formVisible = false; load() } else { ElMessage.error(res.msg) }
  })
}

const update = () => {
  request.put('/goods/update', data.form).then(res => {
    if (res.code === '200') { ElMessage.success('操作成功'); data.formVisible = false; load() } else { ElMessage.error(res.msg) }
  })
}

const save = () => {
  formRef.value.validate(valid => {
    if (valid) data.form.id ? update() : add()
  })
}

const reset = () => { data.name = null; load() }

const handleImgSuccess = (res) => {
  data.form.img = res.data
}

watch(() => data.formVisible, (v) => {
  if (!v) data.fileList = []
})
</script>

<style scoped>
@import './_admin-base.css';

.goods-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.goods-info-cell {
  flex: 1;
  min-width: 0;
}

.goods-name-cell {
  font-weight: 600;
  color: var(--c-text-primary);
  font-size: 14px;
}

.goods-desc-cell {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin-top: 2px;
}

.cell-img {
  width: 56px;
  height: 56px;
  border-radius: var(--r-sm);
  flex-shrink: 0;
}

.cell-img.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--c-bg-soft);
  color: var(--c-text-placeholder);
}

.text-muted {
  color: var(--c-text-secondary);
}

.goods-uploader :deep(.el-upload--picture-card) {
  width: 100px;
  height: 100px;
  border-radius: var(--r-md);
}

.goods-uploader :deep(.el-upload-list--picture-card .el-upload-list__item) {
  width: 100px;
  height: 100px;
  border-radius: var(--r-md);
}
</style>
