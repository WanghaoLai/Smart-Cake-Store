<template>
  <div class="qa-section">
    <!-- 欢迎横幅：商品上下文 + 建议问题 -->
    <div class="qa-banner">
      <div class="qa-banner-main">
        <div class="qa-bot-avatar"><el-icon><MagicStick /></el-icon></div>
        <div class="qa-banner-text">
          <div class="qa-banner-title">AI 商品问答</div>
          <div class="qa-banner-sub">关于「{{ goods.name }}」的任何疑问，AI 为您解答</div>
        </div>
      </div>
      <div class="qa-suggestions">
        <button class="sugg-chip" v-for="s in suggestions" :key="s" @click="ask(s)">{{ s }}</button>
      </div>
    </div>

    <!-- 消息区 -->
    <div class="qa-messages" ref="messagesEl">
      <div v-if="!qa.messages.length" class="qa-empty">
        <el-icon :size="40"><ChatDotRound /></el-icon>
        <p>向 AI 提问关于这款蛋糕的任何问题</p>
      </div>
      <div v-for="(msg, index) in qa.messages" :key="index" :class="['qa-row', msg.role]">
        <div v-if="msg.role === 'assistant'" class="qa-bot-avatar sm"><el-icon><MagicStick /></el-icon></div>
        <div class="qa-bubble">
          <div v-html="renderMarkdown(msg.content)"></div>
          <div v-if="msg.role === 'assistant' && msg.source" class="qa-source">
            {{ sourceLabel(msg.source) }}
          </div>
        </div>
        <div v-if="msg.role === 'user'" class="qa-user-avatar">
          <el-avatar :size="30" :src="$fileUrl(user.avatar) || fallbackAvatar" />
        </div>
      </div>
      <div v-if="qa.loading" class="qa-row assistant">
        <div class="qa-bot-avatar sm"><el-icon><MagicStick /></el-icon></div>
        <div class="qa-bubble loading">
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="qa-input-area">
      <div class="qa-input-wrapper">
        <el-input
          v-model="qa.input"
          type="textarea"
          :rows="1"
          :autosize="{ minRows: 1, maxRows: 3 }"
          placeholder="输入您的问题，Enter 发送，Shift+Enter 换行..."
          @keydown="onKeydown"
        />
        <button class="qa-send" @click="ask()" :disabled="!qa.input.trim() || qa.loading">
          <el-icon><Promotion /></el-icon>
        </button>
      </div>
      <div class="qa-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>AI 回答基于商品信息生成，仅供参考</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, nextTick } from 'vue'
import { MagicStick, Promotion, InfoFilled, ChatDotRound } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import request from '@/utils/request'

const props = defineProps({ goods: { type: Object, default: () => ({}) } })

const messagesEl = ref(null)
const fallbackAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'
const user = computed(() => JSON.parse(localStorage.getItem('system-user') || '{}'))

const suggestions = computed(() => [
  '这款蛋糕适合什么场合？',
  '保质期多久？如何储存？',
  '含有哪些过敏原？',
  '适合几个人食用？',
])

const qa = reactive({ messages: [], input: '', loading: false })

const renderMarkdown = (text) => DOMPurify.sanitize(marked.parse(text || ''))

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

const onKeydown = (e) => {
  // 输入法选词阶段放行，避免 Enter 确认候选词时误发送
  if (e.isComposing) return
  if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey) {
    e.preventDefault()
    ask()
  }
}

const ERROR_TEXT = '商品问答暂时不可用，请稍后重试；配料或过敏等重要信息也可以直接咨询人工客服。'
const sourceLabel = (source) => source === 'ai_grounded' ? 'AI · 基于商品资料' : '商品资料'

const ask = (preset) => {
  const question = (preset || qa.input).trim()
  if (!question || qa.loading) return
  // 只发送当前商品页最近 6 条上下文；服务端仍会逐条校验并以 MySQL 商品事实为准。
  const history = qa.messages.slice(-6).map(({ role, content }) => ({ role, content }))
  qa.input = ''
  qa.messages.push({ role: 'user', content: question })
  qa.loading = true
  scrollToBottom()

  request.post('/qa/goods', { goods_id: props.goods.id, question, history })
    .then(res => {
      const answer = res.code === '200' && res.data?.answer ? res.data.answer : ERROR_TEXT
      qa.messages.push({ role: 'assistant', content: answer, source: res.data?.source })
    })
    .catch(() => {
      qa.messages.push({ role: 'assistant', content: ERROR_TEXT })
    })
    .finally(() => {
      qa.loading = false
      scrollToBottom()
    })
}
</script>

<style scoped>
.qa-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* —— 欢迎横幅 —— */
.qa-banner {
  padding: 18px 20px;
  background: linear-gradient(135deg, #fdf6e0 0%, #f5ecc8 100%);
  border-radius: var(--r-md);
}

.qa-banner-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.qa-banner-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--c-text-primary);
}

.qa-banner-sub {
  font-size: 12px;
  color: var(--c-text-secondary);
  margin-top: 2px;
}

.qa-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.sugg-chip {
  padding: 6px 12px;
  border-radius: var(--r-pill);
  background: var(--c-bg-card);
  border: none;
  color: var(--c-text-regular);
  font-size: 12px;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: all var(--t-fast) var(--ease-out);
}

.sugg-chip:hover {
  background: var(--c-primary);
  color: #fff;
}

/* —— 消息区 —— */
.qa-messages {
  max-height: 420px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 4px 2px;
}

.qa-empty {
  padding: 20px 0;
  text-align: center;
  color: var(--c-text-placeholder);
}

.qa-empty p {
  margin: 8px 0 0;
  font-size: 13px;
}

.qa-row {
  display: flex;
  gap: 8px;
  max-width: 85%;
  animation: qaIn 0.25s var(--ease-out);
}

@keyframes qaIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.qa-row.user {
  flex-direction: row-reverse;
  align-self: flex-end;
}

.qa-bot-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--grad-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(184, 148, 31, 0.22);
}

.qa-bot-avatar.sm {
  width: 30px;
  height: 30px;
  font-size: 15px;
}

.qa-bubble {
  padding: 9px 14px;
  border-radius: 14px;
  line-height: 1.6;
  word-break: break-word;
  font-size: 13px;
}

.qa-row.user .qa-bubble {
  background: var(--grad-primary);
  color: #fff;
  border-top-right-radius: 4px;
}

.qa-row.assistant .qa-bubble {
  background: var(--c-bg-soft);
  color: var(--c-text-primary);
  border-top-left-radius: 4px;
}

.qa-source {
  width: fit-content;
  margin-top: 6px;
  padding-top: 5px;
  border-top: 1px solid var(--c-border-light);
  color: var(--c-text-placeholder);
  font-size: 10px;
}

.qa-bubble.loading {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dot {
  width: 6px;
  height: 6px;
  background: var(--c-primary);
  border-radius: 50%;
  animation: qabounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes qabounce {
  0%, 80%, 100% { transform: scale(0.5); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* —— 输入区 —— */
.qa-input-area { margin-top: 2px; }

.qa-input-wrapper {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  background: var(--c-bg-soft);
  border-radius: var(--r-md);
  padding: 5px 5px 5px 12px;
  transition: all var(--t-fast) var(--ease-out);
}

.qa-input-wrapper:focus-within {
  background: var(--c-bg-card);
  box-shadow: 0 0 0 3px var(--c-primary-soft);
}

.qa-input-wrapper :deep(.el-textarea__inner) {
  background: transparent;
  border: none;
  resize: none;
  box-shadow: none;
  padding: 6px 0;
  font-size: 13px;
  line-height: 1.5;
}

.qa-send {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--grad-primary);
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
  transition: all var(--t-fast) var(--ease-out);
}

.qa-send:hover:not(:disabled) {
  transform: scale(1.05);
}

.qa-send:disabled {
  background: var(--c-text-placeholder);
  cursor: not-allowed;
}

.qa-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  font-size: 11px;
  color: var(--c-text-secondary);
  justify-content: center;
}

/* —— Markdown 排版（与 Chat.vue 保持一致） —— */
:deep(.qa-bubble p) { margin: 0; }
:deep(.qa-bubble p + p) { margin-top: 6px; }
:deep(.qa-bubble ul), :deep(.qa-bubble ol) { padding-left: 18px; margin: 6px 0; }
:deep(.qa-bubble li) { margin: 2px 0; }
:deep(.qa-bubble code) {
  background: rgba(0, 0, 0, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}
:deep(.qa-row.user .qa-bubble code) { background: rgba(255, 255, 255, 0.2); }
</style>
