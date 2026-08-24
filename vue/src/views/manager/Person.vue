<template>
  <div class="person-page">
    <div class="profile-grid">
      <aside class="profile-side card">
        <div class="avatar-wrap">
          <el-upload :show-file-list="false" class="avatar-uploader" :action="uploadUrl" :on-success="handleFileUpload" :headers="uploadHeaders">
            <img v-if="data.user.avatar" :src="$fileUrl(data.user.avatar)" class="avatar" />
            <div v-else class="avatar placeholder"><el-icon><Plus /></el-icon></div>
            <div class="avatar-overlay"><el-icon><Camera /></el-icon><span>更换头像</span></div>
          </el-upload>
          <div class="role-badge" :class="data.user.role === '管理员' ? 'admin' : 'user'">{{ data.user.role || '用户' }}</div>
        </div>
        <h3 class="user-name">{{ data.user.name || '未设置' }}</h3>
        <p class="user-id">@{{ data.user.username }}</p>
        <ul class="side-stats">
          <li><span>账号角色</span><b>{{ data.user.role }}</b></li>
          <li><span>账号 ID</span><b>#{{ data.user.id }}</b></li>
        </ul>
        <div class="side-tip"><el-icon><InfoFilled /></el-icon><span>良好的个人资料有助于客服更好地服务您</span></div>
      </aside>

      <section class="profile-main card">
        <div class="section-head"><div><h2>个人资料</h2><p>更新你的个人信息，所有修改将实时保存</p></div></div>
        <el-form ref="formRef" :model="data.user" :rules="data.rules" label-position="top" class="profile-form">
          <el-row :gutter="20">
            <el-col :xs="24" :sm="12"><el-form-item label="账号" prop="username"><el-input disabled v-model="data.user.username" prefix-icon="User" /></el-form-item></el-col>
            <el-col :xs="24" :sm="12"><el-form-item label="姓名" prop="name"><el-input v-model="data.user.name" placeholder="请输入姓名" prefix-icon="EditPen" /></el-form-item></el-col>
          </el-row>
          <el-form-item><el-button type="primary" round @click="save" size="large"><el-icon><Check /></el-icon>保存修改</el-button></el-form-item>
        </el-form>
      </section>

      <section v-if="data.user.role === '用户'" class="wallet-card card">
        <div class="balance-panel">
          <div class="balance-label"><el-icon><Wallet /></el-icon>我的余额</div>
          <div class="balance-amount"><small>¥</small>{{ money(data.wallet.balance) }}</div>
          <div class="balance-note">余额由平台安全托管，下单时自动扣款</div>
          <el-button type="primary" size="large" round :disabled="data.wallet.recharge_mode !== 'simulation'" @click="openRecharge"><el-icon><Plus /></el-icon>{{ data.wallet.recharge_mode === 'simulation' ? '立即充值' : '充值暂未开放' }}</el-button>
        </div>
        <div class="wallet-assurance">
          <div><el-icon><Lock /></el-icon><span><b>资金安全</b><small>金额使用精确小数存储</small></span></div>
          <div><el-icon><Refresh /></el-icon><span><b>取消即退</b><small>订单取消自动退回余额</small></span></div>
          <div><el-icon><Tickets /></el-icon><span><b>全程可查</b><small>每笔变动都有交易流水</small></span></div>
        </div>
      </section>
    </div>

    <template v-if="data.user.role === '用户'">
      <section class="transactions card">
        <div class="section-head transaction-head">
          <div><h2>交易记录</h2><p>充值、订单支付和退款明细</p></div>
          <el-select v-model="data.txType" clearable placeholder="全部类型" style="width:140px" @change="filterTransactions">
            <el-option label="充值" value="recharge" /><el-option label="订单支付" value="payment" /><el-option label="订单退款" value="refund" />
          </el-select>
        </div>
        <el-table :data="data.transactions" v-loading="data.loading" empty-text="暂无交易记录">
          <el-table-column label="交易类型" min-width="130"><template #default="scope"><span class="tx-type" :class="scope.row.type">{{ scope.row.type_label }}</span></template></el-table-column>
          <el-table-column label="交易说明" prop="remark" min-width="220" />
          <el-table-column label="时间" prop="created_at" min-width="180" />
          <el-table-column label="金额" align="right" width="130"><template #default="scope"><b class="tx-amount" :class="{ income: scope.row.amount > 0 }">{{ scope.row.amount > 0 ? '+' : '-' }}¥{{ money(Math.abs(scope.row.amount)) }}</b></template></el-table-column>
          <el-table-column label="余额" align="right" width="130"><template #default="scope">¥{{ money(scope.row.balance_after) }}</template></el-table-column>
        </el-table>
        <el-pagination v-if="data.txTotal" class="tx-pagination" background layout="total, prev, pager, next" v-model:current-page="data.pageNum" :page-size="data.pageSize" :total="data.txTotal" @current-change="loadTransactions" />
      </section>
    </template>

    <el-dialog v-model="data.rechargeVisible" width="480px" :close-on-click-modal="false" title="余额充值">
      <div class="simulation-tip"><el-icon><InfoFilled /></el-icon><span>当前为演示支付环境，确认后将模拟支付成功并即时入账，不会发起真实扣款。</span></div>
      <el-form ref="rechargeFormRef" :model="data.recharge" :rules="rechargeRules" label-position="top">
        <el-form-item label="充值金额" prop="amount"><el-input-number v-model="data.recharge.amount" :min="1" :max="10000" :precision="2" :step="100" style="width:100%" /></el-form-item>
        <div class="quick-amounts"><button v-for="amount in [100, 200, 500, 1000]" :key="amount" @click.prevent="data.recharge.amount = amount">¥{{ amount }}</button></div>
        <el-form-item label="支付方式" prop="payment_method">
          <el-radio-group v-model="data.recharge.payment_method" class="payment-methods">
            <el-radio-button v-for="method in data.wallet.payment_methods" :key="method.value" :value="method.value">{{ method.label }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer><el-button round @click="data.rechargeVisible = false">取消</el-button><el-button type="primary" round :loading="data.recharging" @click="submitRecharge">确认模拟支付 ¥{{ money(data.recharge.amount) }}</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import request from '@/utils/request'
import { ElMessage } from 'element-plus'
import { Plus, Camera, Check, InfoFilled, Wallet, Lock, Refresh, Tickets } from '@element-plus/icons-vue'

const formRef = ref()
const rechargeFormRef = ref()
const uploadUrl = import.meta.env.VITE_BASE_URL + '/files/upload?category=avatar'
const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }
const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  rules: { username: [{ required: true, message: '请输入账号', trigger: 'blur' }], name: [{ required: true, message: '请输入名称', trigger: 'blur' }] },
  wallet: { balance: 0, payment_methods: [] },
  transactions: [], txType: '', txTotal: 0, pageNum: 1, pageSize: 10, loading: false,
  rechargeVisible: false, recharging: false, recharge: { amount: 100, payment_method: 'alipay' },
})
const rechargeRules = { amount: [{ required: true, message: '请输入充值金额', trigger: 'change' }], payment_method: [{ required: true, message: '请选择支付方式', trigger: 'change' }] }
const money = value => Number(value || 0).toFixed(2)
const handleFileUpload = file => { data.user.avatar = file.data }
const emit = defineEmits(['updateUser'])

const save = () => formRef.value.validate(valid => {
  if (!valid) return
  request.put('/account/profile', { name: data.user.name, avatar: data.user.avatar }).then(res => {
    if (res.code === '200') { ElMessage.success('更新成功'); localStorage.setItem('system-user', JSON.stringify(data.user)); emit('updateUser') }
    else ElMessage.error(res.msg)
  })
})
const loadWallet = () => request.get('/wallet/summary').then(res => { if (res.code === '200') data.wallet = res.data })
const loadTransactions = () => {
  data.loading = true
  request.get('/wallet/transactions', { params: { type: data.txType, pageNum: data.pageNum, pageSize: data.pageSize } })
    .then(res => { if (res.code === '200') { data.transactions = res.data?.list || []; data.txTotal = res.data?.total || 0 } })
    .finally(() => { data.loading = false })
}
const filterTransactions = () => { data.pageNum = 1; loadTransactions() }
const openRecharge = () => { data.recharge = { amount: 100, payment_method: data.wallet.payment_methods?.[0]?.value || 'alipay' }; data.rechargeVisible = true }
const requestId = () => (globalThis.crypto?.randomUUID?.().replaceAll('-', '') || `${Date.now()}${Math.random().toString(36).slice(2)}wallet`)
const submitRecharge = () => rechargeFormRef.value.validate(valid => {
  if (!valid || data.recharging) return
  data.recharging = true
  request.post('/wallet/recharge', { ...data.recharge, request_id: requestId() }).then(res => {
    if (res.code === '200') { data.wallet = res.data; data.rechargeVisible = false; ElMessage.success('充值成功，余额已更新'); data.pageNum = 1; loadTransactions() }
    else ElMessage.error(res.msg)
  }).finally(() => { data.recharging = false })
})
onMounted(() => { if (data.user.role === '用户') { loadWallet(); loadTransactions() } })
</script>

<style scoped>
.person-page{padding:20px;width:100%;display:flex;flex-direction:column;gap:20px}.profile-grid{display:grid;grid-template-columns:280px 1fr;grid-template-rows:auto auto;gap:20px}.profile-side{padding:32px 24px;text-align:center;grid-column:1;grid-row:1/3;display:flex;flex-direction:column}.avatar-wrap{position:relative;display:inline-block}.avatar-uploader{display:inline-block}.avatar-uploader :deep(.el-upload){border-radius:50%;overflow:hidden;position:relative;width:110px;height:110px;border:3px solid #fff;box-shadow:0 4px 16px rgba(184,148,31,.22)}.avatar{width:110px;height:110px;object-fit:cover;display:block}.avatar.placeholder{display:flex;align-items:center;justify-content:center;background:var(--grad-primary);color:#fff;font-size:32px}.avatar-overlay{position:absolute;inset:0;background:rgba(0,0,0,.5);color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:12px;opacity:0;transition:.2s}.avatar-uploader:hover .avatar-overlay{opacity:1}.role-badge{position:absolute;bottom:-4px;right:-4px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;border:2px solid #fff;color:#fff}.role-badge.admin{background:var(--c-primary)}.role-badge.user{background:var(--c-accent)}.user-name{font-size:18px;margin:16px 0 4px}.user-id{font-size:13px;color:var(--c-text-secondary);margin:0 0 20px}.side-stats{list-style:none;padding:0;display:flex;flex-direction:column;gap:12px}.side-stats li{display:flex;justify-content:space-between;padding:10px 14px;background:var(--c-bg-soft);border-radius:var(--r-md);font-size:13px}.side-tip,.simulation-tip{display:flex;gap:8px;padding:12px;background:var(--c-accent-soft);border-radius:var(--r-md);color:var(--c-accent);font-size:12px;line-height:1.5;text-align:left}.profile-side .side-tip{margin-top:auto}.profile-main{padding:28px 32px;grid-column:2;grid-row:1}.section-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px;padding-bottom:16px;border-bottom:1px solid var(--c-border-light)}.section-head h2{font-size:22px;margin:0}.section-head h2:before{display:none}.section-head p{font-size:13px;color:var(--c-text-secondary);margin:6px 0 0}.profile-form .el-button .el-icon,.balance-panel .el-button .el-icon{margin-right:5px}.wallet-card{grid-column:2;grid-row:2;overflow:hidden}.balance-panel{padding:14px 16px;color:#fff;background:linear-gradient(135deg,#9b7617,#d9b84e)}.balance-label{display:flex;align-items:center;gap:6px;font-size:12px}.balance-amount{font-size:22px;font-weight:700;letter-spacing:-0.5px;margin:4px 0}.balance-amount small{font-size:14px;margin-right:3px}.balance-note{font-size:11px;opacity:.82;margin-bottom:10px}.wallet-assurance{padding:24px;display:grid;grid-template-columns:repeat(3,1fr);gap:16px;align-items:center}.wallet-assurance>div{display:flex;gap:10px;align-items:center}.wallet-assurance .el-icon{font-size:22px;color:var(--c-primary)}.wallet-assurance span{display:flex;flex-direction:column;gap:3px}.wallet-assurance small{color:var(--c-text-secondary);line-height:1.4}.transactions{padding:26px}.transaction-head{margin-bottom:8px}.tx-type{padding:4px 10px;border-radius:14px;background:#f2f2f2}.tx-type.recharge,.tx-type.refund{color:#16865b;background:#e9f8f1}.tx-type.payment{color:#a06d10;background:#fff5db}.tx-amount{color:#d34b4b}.tx-amount.income{color:#16865b}.tx-pagination{justify-content:flex-end;margin-top:18px}.quick-amounts{display:flex;gap:10px;margin:-8px 0 20px}.quick-amounts button{border:1px solid var(--c-border-light);background:#fff;padding:7px 15px;border-radius:16px;cursor:pointer}.quick-amounts button:hover{border-color:var(--c-primary);color:var(--c-primary)}.payment-methods{width:100%;display:flex}.payment-methods :deep(.el-radio-button){flex:1}.payment-methods :deep(.el-radio-button__inner){width:100%}.simulation-tip{margin-bottom:20px}@media(max-width:900px){.wallet-assurance{padding:18px}}@media(max-width:768px){.profile-grid{grid-template-columns:1fr;grid-template-rows:auto}.profile-side{grid-column:auto;grid-row:auto}.profile-main{grid-column:auto;grid-row:auto}.wallet-card{grid-column:auto;grid-row:auto}.wallet-assurance{grid-template-columns:1fr}.person-page{padding:12px}.transactions{padding:18px}}
</style>
