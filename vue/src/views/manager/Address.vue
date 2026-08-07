<template>
  <div class="admin-page">
    <div class="toolbar card">
      <el-input v-model="data.name" placeholder="请输入地址关键词查询" :prefix-icon="Search" clearable class="toolbar-search" @keyup.enter="load" @clear="load" />
      <el-button type="primary" round @click="load"><el-icon style="margin-right:4px"><Search /></el-icon>查询</el-button>
      <el-button round @click="reset">重置</el-button>
      <div class="toolbar-right" v-if="data.user.role === '用户'">
        <el-button type="primary" round @click="handleAdd"><el-icon style="margin-right:4px"><Plus /></el-icon>新增地址</el-button>
      </div>
    </div>

    <div class="card table-card">
      <el-table :data="data.tableData" stripe class="admin-table">
        <el-table-column label="收货人" prop="name" width="160">
          <template #default="scope">
            <div class="receiver-cell">
              <el-icon class="receiver-icon"><User /></el-icon>
              <span class="receiver-name">{{ scope.row.name }}</span>
              <el-tag v-if="scope.row.isDefault" type="success" effect="light" round size="small" class="default-tag">
                <el-icon><StarFilled /></el-icon>默认
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="联系方式" prop="phone" width="160">
          <template #default="scope">
            <span class="phone-text">{{ scope.row.phone }}</span>
          </template>
        </el-table-column>
        <el-table-column label="所在地区" min-width="200">
          <template #default="scope">
            <div class="region-cell">
              <template v-if="scope.row.provinceName || scope.row.cityName || scope.row.townName">
                <el-icon class="region-icon"><Location /></el-icon>
                <span class="region-text">
                  {{ [scope.row.provinceName, scope.row.cityName, scope.row.townName].filter(Boolean).join(' / ') }}
                </span>
              </template>
              <span v-else class="region-fallback">未结构化</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="详细地址" prop="detail" min-width="240">
          <template #default="scope">
            <div class="address-text line2">{{ scope.row.detail || scope.row.address || '—' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="所属用户" prop="userName" width="120" v-if="data.user.role === '管理员'">
          <template #default="scope">
            <span class="user-tag">{{ scope.row.userName || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" align="center" width="220" fixed="right">
          <template #default="scope">
            <div class="action-bar">
              <el-button
                text
                type="primary"
                size="small"
                @click="handleEdit(scope.row)"
                v-if="data.user.role === '用户'"
                class="action-btn">
                <el-icon><Edit /></el-icon><span>编辑</span>
              </el-button>
              <el-button
                text
                :type="scope.row.isDefault ? 'info' : 'success'"
                size="small"
                :disabled="scope.row.isDefault"
                @click="handleSetDefault(scope.row.id)"
                v-if="data.user.role === '用户'"
                class="action-btn">
                <el-icon><Star /></el-icon><span>{{ scope.row.isDefault ? '默认' : '设为默认' }}</span>
              </el-button>
              <el-button
                text
                type="danger"
                size="small"
                @click="handleDelete(scope.row.id)"
                class="action-btn">
                <el-icon><Delete /></el-icon><span>删除</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card pagination-card">
      <el-pagination @current-change="load" background layout="total, prev, pager, next" v-model:page-size="data.pageSize" v-model:current-page="data.pageNum" :total="data.total"/>
    </div>

    <el-dialog v-model="data.formVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <template #header>
        <div class="dialog-header-custom">
          <el-icon class="dialog-icon"><Location /></el-icon>
          <div>
            <div class="dialog-title">{{ data.form.id ? '编辑地址' : '新增地址' }}</div>
            <div class="dialog-sub">完善收货信息以方便配送</div>
          </div>
        </div>
      </template>
      <el-form ref="formRef" :model="data.form" :rules="rules" label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="收货人" prop="name">
              <el-input v-model="data.form.name" autocomplete="off" placeholder="收货人姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系方式" prop="phone">
              <el-input v-model="data.form.phone" autocomplete="off" placeholder="联系电话" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="所在地区" prop="provinceId" class="region-form-item">
          <div class="region-row">
            <el-select
              v-model="data.form.provinceId"
              placeholder="省/直辖市"
              filterable
              clearable
              class="region-select"
              :loading="data.regionLoading"
              @change="onProvinceChange"
            >
              <el-option v-for="p in data.provinceList" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
            <el-select
              v-model="data.form.cityId"
              placeholder="市"
              filterable
              clearable
              :disabled="!data.form.provinceId"
              class="region-select"
              :loading="data.regionLoading"
              @change="onCityChange"
            >
              <el-option v-for="c in data.cityList" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-select
              v-model="data.form.townId"
              placeholder="区/县"
              filterable
              clearable
              :disabled="!data.form.cityId"
              class="region-select"
              :loading="data.regionLoading"
            >
              <el-option v-for="t in data.townList" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
          </div>
          <div class="region-hint" v-if="!data.form.provinceId">
            请先选择省份，再依次选择市/区县
          </div>
        </el-form-item>

        <el-form-item label="详细地址" prop="detail">
          <el-input
            type="textarea"
            :rows="2"
            v-model="data.form.detail"
            autocomplete="off"
            placeholder="街道、门牌号、小区楼宇等（如：南京东路 818 号 5F）"
          />
        </el-form-item>

        <el-form-item class="default-form-item">
          <el-checkbox v-model="data.form.isDefault">
            <el-icon class="default-checkbox-icon"><StarFilled /></el-icon>
            设为默认地址
          </el-checkbox>
          <span class="default-hint">下单时默认选中此地址；每个账号仅保留一条默认地址</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="data.formVisible = false" round>取消</el-button>
        <el-button type="primary" @click="save" round>保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import request from "@/utils/request";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Plus, Edit, Delete, User, Location, Star, StarFilled } from "@element-plus/icons-vue";

const formRef = ref()

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  form: {},
  formVisible: false,
  name: null,
  pageNum: 1,
  pageSize: 10,
  total: 0,
  tableData: [],
  // 地区级联数据
  provinceList: [],
  cityList: [],
  townList: [],
  regionLoading: false,
})

const rules = {
  name: [{ required: true, message: '请输入收货人', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入联系方式', trigger: 'blur' }],
  provinceId: [{ required: true, message: '请选择省份', trigger: 'change' }],
  cityId: [{ required: true, message: '请选择城市', trigger: 'change' }],
  townId: [{ required: true, message: '请选择区/县', trigger: 'change' }],
  detail: [{ required: true, message: '请输入详细地址', trigger: 'blur' }],
}

const load = () => {
  request.get('/address/selectPage', {
    params: {
      pageNum: data.pageNum,
      pageSize: data.pageSize,
      address: data.name,
      userId: data.user.role === '用户' ? data.user.id : 0
    }
  }).then(res => {
    if (res.code === '200') {
      data.tableData = res.data?.list || []
      data.total = res.data?.total || 0
    } else { ElMessage.error(res.msg) }
  })
}
load()

const loadProvinces = () => {
  if (data.provinceList.length) return
  data.regionLoading = true
  request.get('/region/provinces').then(res => {
    if (res.code === '200') data.provinceList = res.data || []
    else ElMessage.error(res.msg)
  }).finally(() => { data.regionLoading = false })
}

const loadCities = (provinceId) => {
  if (!provinceId) { data.cityList = []; return Promise.resolve() }
  data.regionLoading = true
  return request.get('/region/cities', { params: { provinceId } }).then(res => {
    if (res.code === '200') data.cityList = res.data || []
    else { ElMessage.error(res.msg); data.cityList = [] }
  }).finally(() => { data.regionLoading = false })
}

const loadTowns = (cityId) => {
  if (!cityId) { data.townList = []; return Promise.resolve() }
  data.regionLoading = true
  return request.get('/region/towns', { params: { cityId } }).then(res => {
    if (res.code === '200') data.townList = res.data || []
    else { ElMessage.error(res.msg); data.townList = [] }
  }).finally(() => { data.regionLoading = false })
}

const onProvinceChange = (provinceId) => {
  // 省变化时清空市/区县，并加载新市的列表
  data.form.cityId = null
  data.form.townId = null
  data.cityList = []
  data.townList = []
  if (provinceId) loadCities(provinceId)
}

const onCityChange = (cityId) => {
  data.form.townId = null
  data.townList = []
  if (cityId) loadTowns(cityId)
}

const handleAdd = () => {
  data.form = {
    userId: data.user.id,
    name: '', phone: '',
    provinceId: null, cityId: null, townId: null,
    detail: '',
    isDefault: false,
  }
  data.cityList = []
  data.townList = []
  loadProvinces()
  data.formVisible = true
}

const handleEdit = async (row) => {
  data.form = JSON.parse(JSON.stringify(row))
  // 编辑回显：先把省份列表加载好；如果已有 provinceId 还要异步加载市/区
  loadProvinces()
  data.cityList = []
  data.townList = []
  if (data.form.provinceId) {
    await loadCities(data.form.provinceId)
  }
  if (data.form.cityId) {
    await loadTowns(data.form.cityId)
  }
  data.formVisible = true
}

const handleDelete = (id) => {
  ElMessageBox.confirm('删除后数据无法恢复，您确定删除吗?', '删除确认', { type: 'warning' }).then(res => {
    request.delete('/address/delete/' + id).then(res => {
      if (res.code === '200') { load(); ElMessage.success('操作成功') } else { ElMessage.error(res.msg) }
    })
  }).catch(() => {})
}

const handleSetDefault = (id) => {
  request.put('/address/set_default/' + id).then(res => {
    if (res.code === '200') {
      ElMessage.success('已设为默认地址')
      load()
    } else { ElMessage.error(res.msg) }
  })
}

const add = () => {
  request.post('/address/add', data.form).then(res => {
    if (res.code === '200') { ElMessage.success('操作成功'); data.formVisible = false; load() } else { ElMessage.error(res.msg) }
  })
}

const update = () => {
  request.put('/address/update', data.form).then(res => {
    if (res.code === '200') { ElMessage.success('操作成功'); data.formVisible = false; load() } else { ElMessage.error(res.msg) }
  })
}

const save = () => {
  formRef.value.validate(valid => {
    if (valid) data.form.id ? update() : add()
  })
}

const reset = () => { data.name = null; load() }
</script>

<style scoped>
@import './_admin-base.css';

.receiver-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.receiver-icon { color: var(--c-primary); font-size: 14px; }
.receiver-name { font-weight: 600; color: var(--c-text-primary); }

.default-tag {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: 4px;
}

.default-tag :deep(.el-icon) {
  font-size: 11px;
}
.phone-text { font-family: ui-monospace, monospace; color: var(--c-text-regular); font-size: 13px; }

/* —— 行政区单元格 —— */
.region-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.region-icon { color: var(--c-primary); font-size: 14px; flex-shrink: 0; }
.region-text { color: var(--c-text-regular); }
.region-fallback {
  color: var(--c-text-placeholder);
  font-size: 12px;
  font-style: italic;
}

.address-text { color: var(--c-text-regular); font-size: 13px; line-height: 1.5; }

.user-tag {
  display: inline-flex;
  padding: 2px 10px;
  background: var(--c-accent-soft);
  color: var(--c-accent);
  border-radius: var(--r-pill);
  font-size: 12px;
  font-weight: 600;
}

/* —— 操作列：3 按钮一行紧凑布局 —— */
.action-bar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.action-bar :deep(.el-button.action-btn) {
  margin: 0;
  height: 26px;
  padding: 0 6px;
  font-size: 12px;
}

.action-bar :deep(.el-button.action-btn .el-icon) {
  margin-right: 2px;
  font-size: 12px;
}

.action-bar :deep(.el-button.action-btn.is-disabled) {
  opacity: 0.5;
}

/* —— 表单内行政区级联 —— */
.region-form-item :deep(.el-form-item__content) {
  display: block;
}

.region-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
  width: 100%;
}

@media (max-width: 600px) {
  .region-row { grid-template-columns: 1fr; }
}

.region-select :deep(.el-input__wrapper) {
  border-radius: var(--r-md);
}

.region-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--c-text-secondary);
}

/* —— 默认地址复选框 —— */
.default-form-item {
  margin-bottom: 0;
}

.default-form-item :deep(.el-form-item__content) {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.default-checkbox-icon {
  color: var(--c-primary);
  margin-right: 2px;
  vertical-align: -2px;
}

.default-hint {
  font-size: 12px;
  color: var(--c-text-secondary);
  padding-left: 24px;
}
</style>
