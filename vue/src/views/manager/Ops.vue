<template>
  <div class="ops-page">
    <h2 class="page-title"><el-icon><DataAnalysis /></el-icon> 商品分析</h2>
    <p class="page-sub">评价 · 销量 · 库存 · 综合表现四维分析；AI 结论基于工具返回的实时数据，不编造数字。</p>

    <!-- 控制栏：选商品 → 选窗口 → AI 分析 -->
    <div class="card ctrl-bar">
      <el-select v-model="selectedId" filterable placeholder="选择商品（可搜索）" class="goods-select"
                 :loading="productsLoading" @change="loadFacts">
        <el-option v-for="p in products" :key="p.id"
                   :label="`${p.name}（${p.category} · 库存 ${p.stock}）`" :value="p.id" />
      </el-select>
      <el-radio-group v-model="days" @change="loadFacts">
        <el-radio-button :value="7">近 7 天</el-radio-button>
        <el-radio-button :value="30">近 30 天</el-radio-button>
        <el-radio-button :value="90">近 90 天</el-radio-button>
      </el-radio-group>
      <div class="ctrl-actions">
        <el-button type="primary" :icon="MagicStick" :loading="aiLoading"
                   :disabled="!selectedId" @click="runAiAnalysis">AI 分析</el-button>
        <el-button :icon="Download" :disabled="!reportId" @click="downloadReport">下载报告</el-button>
      </div>
    </div>

    <p v-if="error" class="error-hint">{{ error }}</p>

    <!-- AI 结论 -->
    <div v-if="aiAnswer || aiLoading" class="card ai-panel">
      <div class="card-head">
        <h3><el-icon><MagicStick /></el-icon> AI 分析结论</h3>
        <el-tag v-if="degraded && !aiLoading" type="warning" size="small">模型暂不可用，已降级为数据报告</el-tag>
      </div>
      <div v-if="aiLoading" class="ai-loading">
        <el-icon class="is-loading"><Loading /></el-icon> Agent 正在调用分析工具…
      </div>
      <div v-else class="markdown-body" v-html="renderedAnswer"></div>
    </div>

    <!-- 四维概览卡片 -->
    <div class="cards-row">
      <div class="metric-card card" v-if="perf">
        <div class="card-head"><h3>综合表现</h3></div>
        <div class="card-body">
          <div class="grade-row">
            <span class="grade" :class="gradeClass">{{ perf.score.grade }}</span>
            <span class="grade-score">{{ perf.score.total }}<small>/100</small></span>
          </div>
          <div v-for="(dim, key) in perf.score.dimensions" :key="key" class="dim-row">
            <span class="metric-label">{{ dimNames[key] }}（{{ dim.weight * 100 }}%）</span>
            <el-progress :percentage="dim.score" :stroke-width="8" class="dim-progress" />
          </div>
        </div>
      </div>

      <div class="metric-card card" v-if="reviews">
        <div class="card-head"><h3>评价分析</h3></div>
        <div class="card-body">
          <div class="metric"><span class="metric-label">平均星级</span>
            <span class="metric-value">{{ reviews.avg_rating || '—' }}<el-rate :model-value="reviews.avg_rating" disabled size="small" class="mini-rate" /></span></div>
          <div class="metric"><span class="metric-label">好评率</span>
            <span class="metric-value success">{{ reviews.positive_rate }}%</span></div>
          <div class="sentiment-bar">
            <span class="seg pos" :style="{ width: segWidth(reviews.sentiment['好评'], reviews.total) }" />
            <span class="seg mid" :style="{ width: segWidth(reviews.sentiment['中评'], reviews.total) }" />
            <span class="seg neg" :style="{ width: segWidth(reviews.sentiment['差评'], reviews.total) }" />
          </div>
          <div class="metric"><span class="metric-label">好评 {{ reviews.sentiment['好评'] }} · 中评 {{ reviews.sentiment['中评'] }} · 差评 {{ reviews.sentiment['差评'] }}</span></div>
        </div>
      </div>

      <div class="metric-card card" v-if="sales">
        <div class="card-head"><h3>销量分析<em class="range-note">{{ salesRange }}</em></h3></div>
        <div class="card-body">
          <div class="metric"><span class="metric-label">窗口销量</span><span class="metric-value">{{ sales.total_qty }} 件</span></div>
          <div class="metric"><span class="metric-label">订单 / 营收</span>
            <span class="metric-value">{{ sales.order_count }} 单 · ¥{{ sales.total_revenue }}</span></div>
          <div class="metric"><span class="metric-label">环比上一窗口</span>
            <span class="metric-value" :class="{ success: (sales.qty_change_pct ?? 0) >= 0, warning: (sales.qty_change_pct ?? 0) < 0 }">
              {{ sales.qty_change_pct == null ? '无基线' : (sales.qty_change_pct >= 0 ? '+' : '') + sales.qty_change_pct + '%' }}
            </span></div>
        </div>
      </div>

      <div class="metric-card card" v-if="inventory">
        <div class="card-head"><h3>库存分析（全店）</h3></div>
        <div class="card-body">
          <div class="metric"><span class="metric-label">预警商品</span>
            <span class="metric-value warning">{{ inventory.warning_count }} 个</span></div>
          <div class="metric"><span class="metric-label">资金占用</span>
            <span class="metric-value">¥{{ inventory.total_inventory_value }}</span></div>
          <div class="metric"><span class="metric-label">水位分布</span>
            <span class="metric-label">健康 {{ inventory.levels['健康'] }} · 偏低 {{ inventory.levels['偏低'] }} · 紧张 {{ inventory.levels['紧张'] }} · 售罄 {{ inventory.levels['售罄'] }}</span></div>
        </div>
      </div>
    </div>

    <!-- 销量趋势（选中商品时）：真实日期坐标轴 -->
    <div v-if="sales && selectedId" class="card section-card">
      <div class="card-head"><h3>按天销量趋势（{{ trendRange }}）</h3></div>
      <div v-if="sales.total_qty === 0" class="empty-hint">窗口内暂无销量</div>
      <div v-else>
        <div class="trend-chart">
          <div v-for="d in sales.daily_trend" :key="d.date" class="trend-col"
               :data-tip="`${d.date} · 销量 ${d.qty} 件`">
            <div class="trend-bar" :style="{ height: barHeight(d.qty) }" :class="{ zero: d.qty === 0 }"></div>
          </div>
        </div>
        <div class="trend-axis">
          <span v-for="(d, i) in sales.daily_trend" :key="`ax-${d.date}`" class="axis-label"
                :class="{ on: isAxisTick(i) }">{{ axisDate(d.date) }}</span>
        </div>
      </div>
    </div>

    <!-- 全店排行 -->
    <div v-if="ranking" class="cards-row two-col">
      <div class="card section-card">
        <div class="card-head"><h3>热销 Top 10（近 {{ days }} 天）</h3></div>
        <el-table :data="ranking.hot_ranking" size="small" :show-header="true" empty-text="窗口内暂无销量">
          <el-table-column type="index" label="#" width="40" />
          <el-table-column prop="name" label="商品" show-overflow-tooltip />
          <el-table-column prop="qty" label="销量" width="70" />
          <el-table-column label="库存" width="80">
            <template #default="{ row }">{{ row.stock }}</template>
          </el-table-column>
        </el-table>
      </div>
      <div class="card section-card">
        <div class="card-head"><h3>滞销关注 Top 10（有库存）</h3></div>
        <el-table :data="ranking.slow_ranking" size="small" empty-text="无有库存商品">
          <el-table-column type="index" label="#" width="40" />
          <el-table-column prop="name" label="商品" show-overflow-tooltip />
          <el-table-column prop="qty" label="销量" width="70" />
          <el-table-column prop="stock" label="库存" width="80" />
        </el-table>
      </div>
    </div>

    <!-- 关键词 + 差评聚焦 -->
    <div v-if="reviews" class="cards-row two-col">
      <div class="card section-card">
        <div class="card-head"><h3>评价关键词</h3></div>
        <div class="tag-wall">
          <el-tag v-for="k in reviews.keywords" :key="k.keyword" class="kw-tag" effect="plain">
            {{ k.keyword }} <small>{{ k.count }}</small>
          </el-tag>
          <span v-if="!reviews.keywords.length" class="empty-hint">暂无评价内容</span>
        </div>
        <div class="card-head" style="margin-top:16px"><h3>差评聚焦</h3></div>
        <div class="tag-wall">
          <el-tag v-for="f in reviews.negative_focus" :key="f.term" type="danger" effect="plain" class="kw-tag">
            {{ f.term }} ×{{ f.count }}
          </el-tag>
          <span v-if="!reviews.negative_focus.length" class="empty-hint">无差评关键词</span>
        </div>
      </div>
      <div class="card section-card">
        <div class="card-head"><h3>差评原文（{{ reviews.sentiment['差评'] }} 条）</h3></div>
        <el-table :data="reviews.negative_reviews" size="small" empty-text="无差评，继续保持">
          <el-table-column prop="rating" label="星级" width="55">
            <template #default="{ row }"><el-tag type="danger" size="small">{{ row.rating }}★</el-tag></template>
          </el-table-column>
          <el-table-column prop="content" label="内容" show-overflow-tooltip />
          <el-table-column prop="time" label="时间" width="100">
            <template #default="{ row }">{{ (row.time || '').slice(0, 10) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 库存预警清单 -->
    <div v-if="inventory && inventory.warning_count" class="card section-card">
      <div class="card-head"><h3><el-icon color="var(--el-color-warning)"><Warning /></el-icon> 库存预警清单</h3></div>
      <el-table :data="inventory.warning_list" size="small">
        <el-table-column type="index" label="#" width="40" />
        <el-table-column prop="name" label="商品" show-overflow-tooltip />
        <el-table-column label="库存" width="90">
          <template #default="{ row }">
            <el-tag :type="row.stock === 0 ? 'danger' : 'warning'" size="small">
              {{ row.stock }}{{ row.unit }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sold_qty" label="窗口销量" width="90" />
        <el-table-column label="可售天数" width="90">
          <template #default="{ row }">{{ row.days_of_stock ?? '—' }}</template>
        </el-table-column>
      </el-table>
    </div>

    <p v-if="!selectedId && !error" class="empty-hint">从上方选择一个商品开始分析；排行与库存为全店视角，已默认加载。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { DataAnalysis, Download, Loading, MagicStick, Warning } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import request from '@/utils/request'

const products = ref([])
const productsLoading = ref(false)
const selectedId = ref(null)
const days = ref(30)

const reviews = ref(null)
const sales = ref(null)
const inventory = ref(null)
const perf = ref(null)
const ranking = ref(null)

const aiLoading = ref(false)
const aiAnswer = ref('')
const degraded = ref(false)
const reportId = ref(null)
const error = ref('')

const dimNames = { sales: '销量', review: '评价', inventory: '库存' }
const gradeClass = computed(() => ({
  A: 'grade-a', B: 'grade-b', C: 'grade-c', D: 'grade-d',
}[perf.value?.score.grade] || ''))

const renderedAnswer = computed(() =>
  DOMPurify.sanitize(marked.parse(aiAnswer.value || '')))

const segWidth = (count, total) => (total ? `${(count / total) * 100}%` : '0%')
const barHeight = (qty) => {
  const max = Math.max(1, ...(sales.value?.daily_trend || []).map(d => d.qty))
  return `${Math.max(2, (qty / max) * 100)}%`
}

// ---- 真实日期展示：时间窗换算为具体日期区间 + 趋势图坐标轴刻度 ----
const trendRange = computed(() => {
  const t = sales.value?.daily_trend
  if (!t?.length) return ''
  return `${t[0].date} ~ ${t[t.length - 1].date}`
})
const salesRange = computed(() => {
  const t = sales.value?.daily_trend
  if (!t?.length) return ''
  return `（${t[0].date.slice(5)} ~ ${t[t.length - 1].date.slice(5)}）`
})
// 坐标轴最多 ~7 个刻度，首尾日期必显示
const isAxisTick = (i) => {
  const n = sales.value?.daily_trend?.length || 0
  const step = Math.max(1, Math.ceil(n / 6))
  if (i % step === 0) return true
  return i === n - 1 && (n - 1) % step > step / 2
}
const axisDate = (iso) => iso.slice(5) // MM-DD

const fetchProducts = async () => {
  productsLoading.value = true
  try {
    const res = await request.get('/ops/products')
    if (res.code === '200') products.value = res.data || []
    else ElMessage.error(res.msg || '商品列表加载失败')
  } finally { productsLoading.value = false }
}

const loadFacts = async () => {
  error.value = ''
  perf.value = reviews.value = sales.value = null
  // 全店视角：排行 + 库存不依赖选中商品
  const window = { days: days.value }
  request.get('/ops/analysis/sales', { params: window }).then(res => {
    if (res.code === '200') ranking.value = res.data
  })
  request.get('/ops/analysis/inventory', { params: window }).then(res => {
    if (res.code === '200') inventory.value = res.data
  })
  if (!selectedId.value) return
  const params = { goods_id: selectedId.value, days: days.value }
  try {
    const [revRes, salesRes, perfRes] = await Promise.all([
      request.get('/ops/analysis/reviews', { params }),
      request.get('/ops/analysis/sales', { params }),
      request.get('/ops/analysis/performance', { params }),
    ])
    if (revRes.code === '200') reviews.value = revRes.data
    if (salesRes.code === '200') sales.value = salesRes.data
    if (perfRes.code === '200') perf.value = perfRes.data
    if (revRes.code !== '200' && salesRes.code !== '200') {
      error.value = revRes.msg || '分析数据加载失败'
    }
  } catch (e) {
    error.value = '分析数据加载失败，请重试'
  }
}

const runAiAnalysis = async () => {
  aiLoading.value = true
  aiAnswer.value = ''
  degraded.value = false
  try {
    const res = await request.post('/ops/analysis/ai', { goods_id: selectedId.value, days: days.value })
    if (res.code === '200') {
      aiAnswer.value = res.data.answer || ''
      degraded.value = res.data.degraded
      reportId.value = res.data.report_id
      if (!aiAnswer.value && !degraded.value) ElMessage.warning('AI 未返回结论，请查看数据卡片')
      // AI 返回的 facts 与页面一致，直接补齐（免重复请求）
      perf.value = res.data.facts.performance
      reviews.value = res.data.facts.reviews
      sales.value = res.data.facts.sales
      inventory.value = res.data.facts.inventory
    } else {
      ElMessage.error(res.msg || 'AI 分析失败')
    }
  } catch (e) {
    ElMessage.error('AI 分析请求失败，请稍后重试')
  } finally { aiLoading.value = false }
}

const downloadReport = async () => {
  if (!reportId.value) return
  try {
    const res = await request.get(`/ops/analysis/report/${reportId.value}`, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res], { type: 'text/markdown;charset=utf-8' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `商品分析报告_${Date.now()}.md`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('报告下载失败')
  }
}

onMounted(async () => {
  await fetchProducts()
  await loadFacts()
})
</script>

<style scoped>
.ops-page { padding: 20px; }
.page-title { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.page-sub { color: var(--c-text-secondary); font-size: 13px; margin-bottom: 20px; }

.card {
  padding: 20px;
  border-radius: var(--el-card-border-radius, 8px);
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  margin-bottom: 16px;
}
.card-head h3 {
  font-size: 14px; color: var(--c-text-secondary); margin-bottom: 12px;
  display: flex; align-items: center; gap: 6px;
}

/* 控制栏 */
.ctrl-bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.goods-select { width: 340px; }
.ctrl-actions { margin-left: auto; display: flex; gap: 8px; }

/* AI 结论 */
.ai-panel .markdown-body { line-height: 1.7; font-size: 14px; }
.ai-panel .markdown-body :deep(h1),
.ai-panel .markdown-body :deep(h2) { font-size: 15px; margin: 12px 0 6px; }
.ai-panel .markdown-body :deep(ul),
.ai-panel .markdown-body :deep(ol) { padding-left: 20px; margin: 6px 0; }
.ai-loading { color: var(--c-text-secondary); display: flex; align-items: center; gap: 8px; padding: 12px 0; }

.cards-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}
.cards-row.two-col { grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); }
.metric-card { padding: 20px; margin-bottom: 0; }
.card-body { display: flex; flex-direction: column; gap: 12px; }

.metric { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.metric-label { font-size: 13px; color: var(--c-text-secondary); }
.metric-value { font-size: 20px; font-weight: 600; color: var(--c-text); display: flex; align-items: center; gap: 6px; }
.metric-value.success { color: var(--c-success); }
.metric-value.warning { color: var(--c-warning); }
.metric-value { font-size: 18px; }
.mini-rate { transform: scale(0.8); transform-origin: left; }

/* 综合表现 */
.grade-row { display: flex; align-items: center; gap: 12px; }
.grade { font-size: 40px; font-weight: 700; line-height: 1; }
.grade-a { color: var(--c-success); } .grade-b { color: var(--c-primary); }
.grade-c { color: var(--c-warning); } .grade-d { color: var(--c-danger); }
.grade-score { font-size: 26px; font-weight: 600; }
.grade-score small { font-size: 13px; color: var(--c-text-secondary); }
.dim-row { display: flex; align-items: center; gap: 10px; }
.dim-row .metric-label { width: 76px; flex-shrink: 0; }
.dim-progress { flex: 1; }

/* 情感三段条 */
.sentiment-bar { display: flex; height: 10px; border-radius: 5px; overflow: hidden; background: var(--el-fill-color-light); }
.seg.pos { background: var(--c-success); } .seg.mid { background: var(--el-color-info); } .seg.neg { background: var(--c-danger); }

/* 趋势图（纯 CSS 柱状，无图表依赖） */
.trend-chart { display: flex; align-items: flex-end; gap: 2px; height: 140px; padding: 8px 0 0; }
.trend-col { flex: 1; height: 100%; display: flex; align-items: flex-end; position: relative; cursor: pointer; }
.trend-bar { width: 100%; background: var(--c-primary); border-radius: 2px 2px 0 0; opacity: .85; }
.trend-bar.zero { background: var(--el-fill-color); opacity: 1; }

/* 悬停气泡 + 当日柱高亮：CSS 即时响应，无原生 title 的 1s 延迟 */
.trend-col:hover .trend-bar { opacity: 1; }
.trend-col:hover::after {
  content: attr(data-tip);
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  padding: 4px 10px;
  border-radius: 6px;
  background: var(--el-color-info-dark-2, #303133);
  color: #fff;
  font-size: 12px;
  line-height: 1.4;
  white-space: nowrap;
  pointer-events: none;
  z-index: 5;
}
/* 首尾柱的气泡向内偏移，避免超出卡片 */
.trend-col:first-child:hover::after { left: 0; transform: none; }
.trend-col:last-child:hover::after { left: auto; right: 0; transform: none; }

/* 日期坐标轴：与柱列同宽对齐（flex:1），非刻度位用 visibility 占位保持网格 */
.trend-axis { display: flex; gap: 2px; margin-top: 4px; }
.axis-label {
  flex: 1; text-align: center;
  font-size: 11px; color: var(--c-text-secondary);
  white-space: nowrap; overflow: visible;
  visibility: hidden;
}
.axis-label.on { visibility: visible; }
.range-note { font-style: normal; font-weight: 400; font-size: 12px; margin-left: 6px; color: var(--c-text-secondary); }

/* 关键词墙 */
.tag-wall { display: flex; flex-wrap: wrap; gap: 8px; }
.kw-tag small { opacity: .6; margin-left: 2px; }

.section-card { margin-bottom: 0; }
.empty-hint { color: var(--c-text-secondary); font-size: 13px; padding: 12px 0; }
.error-hint { color: var(--c-danger); font-size: 13px; padding: 12px 0; }

@media (max-width: 768px) {
  .cards-row, .cards-row.two-col { grid-template-columns: 1fr; }
  .goods-select { width: 100%; }
  .ctrl-actions { margin-left: 0; }
}
</style>
