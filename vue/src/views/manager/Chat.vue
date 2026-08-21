<template>
  <div class="chat-page">
    <aside class="chat-sidebar">
      <div class="sidebar-head">
        <div class="sidebar-title">
          <el-icon><ChatDotRound /></el-icon>
          <span>会话列表</span>
        </div>
        <el-button type="primary" class="new-btn" @click="createConversation()">
          <el-icon><Plus /></el-icon>新对话
        </el-button>
      </div>
      <div class="conv-list">
        <div
          v-for="conv in data.conversations"
          :key="conv.id"
          :class="['conv-item', { active: data.currentConversation === conv.id }]"
          @click="switchConversation(conv.id)"
        >
          <div class="conv-icon">
            <el-icon><ChatLineRound /></el-icon>
          </div>
          <div class="conv-main">
            <div class="conv-title line1">{{ conv.title }}</div>
            <div class="conv-time">{{ formatTime(conv.updated_at) }}</div>
          </div>
          <button class="conv-del" @click.stop="deleteConversation(conv.id)">
            <el-icon><Delete /></el-icon>
          </button>
        </div>
        <div v-if="!data.conversations.length" class="conv-empty">
          <el-icon :size="40"><ChatDotRound /></el-icon>
          <p>暂无会话</p>
          <span>点击上方按钮开始对话</span>
        </div>
      </div>
    </aside>

    <main class="chat-main">
      <!-- 顶部 banner -->
      <div class="chat-banner" v-if="!data.currentConversation">
        <div class="banner-bg deco-1"></div>
        <div class="banner-bg deco-2"></div>
        <div class="banner-content">
          <div class="banner-icon">
            <el-icon><MagicStick /></el-icon>
          </div>
          <h2 class="banner-title">智能导购客服</h2>
          <p class="banner-sub">基于知识库 + 商品数据，为您提供 7×12 智能咨询</p>
          <div class="banner-suggestions">
            <button class="sugg-chip" v-for="s in suggestions" :key="s" @click="useSuggestion(s)">
              {{ s }}
            </button>
          </div>
        </div>
      </div>

      <!-- 消息区 -->
      <div class="messages-container" ref="messagesContainer">
        <div v-if="data.currentConversation && data.messages.length === 0 && !data.loading" class="empty-state">
          <el-icon :size="56" color="#c0c4cc"><ChatDotRound /></el-icon>
          <p>开始与智能客服对话吧！</p>
        </div>

        <div v-for="(msg, index) in data.messages" :key="index" :class="['message-row', msg.role]">
          <div class="message-avatar">
            <el-avatar v-if="msg.role === 'user'" :size="36" :src="data.user.avatar || 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'" />
            <div v-else class="bot-avatar">
              <el-icon><MagicStick /></el-icon>
            </div>
          </div>
          <div class="message-content">
            <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>

        <div v-if="data.loading" class="message-row assistant">
          <div class="message-avatar">
            <div class="bot-avatar"><el-icon><MagicStick /></el-icon></div>
          </div>
          <div class="message-content">
            <div class="message-text loading">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="loading-status">{{ data.status }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="input-area">
        <div class="input-wrapper">
          <el-input
            v-model="data.inputMessage"
            type="textarea"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="输入您的问题，Enter 发送，Shift+Enter 换行..."
            @keydown="onInputKeydown"
            class="chat-input"
          />
          <button class="send-btn" @click="sendMessage" :disabled="!data.inputMessage.trim() || data.loading">
            <el-icon><Promotion /></el-icon>
          </button>
        </div>
        <div class="input-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>AI 基于知识库生成回答，仅供参考</span>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { reactive, ref, nextTick, onMounted } from 'vue'
import { Plus, Delete, ChatDotRound, ChatLineRound, MagicStick, Promotion, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const messagesContainer = ref(null)

const suggestions = [
  '推荐一款生日蛋糕',
  '你们有什么口味的蛋糕',
  '巧克力蛋糕的价格',
  '蛋糕可以定制吗',
]

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  conversations: [],
  currentConversation: null,
  messages: [],
  inputMessage: '',
  loading: false,
  status: '正在连接智能客服…'
})

let conversationCreation = null

const renderMarkdown = (text) => DOMPurify.sanitize(marked.parse(text || ''))

const formatTime = (t) => {
  if (!t) return ''
  const d = new Date(t)
  if (isNaN(d.getTime())) return ''
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const loadConversations = async () => {
  try {
    const res = await request.get('/chat/conversations')
    if (res.code === '200') data.conversations = res.data || []
  } catch (e) { console.error('加载会话列表失败:', e) }
}

const createConversation = async (silent = false) => {
  // 页面初始化和用户首次发送可能同时触发创建，共享同一个请求以避免重复会话。
  if (!conversationCreation) {
    conversationCreation = (async () => {
      // 创建空会话是无参数操作，不发送 body，避免前后端 Payload 契约漂移导致 422。
      const res = await request.post('/chat/conversation')
      if (res.code !== '200' || !Number.isInteger(res.data?.id)) {
        throw new Error(res.msg || '创建会话失败')
      }
      data.currentConversation = res.data.id
      data.messages = []
      await loadConversations()
      return true
    })().finally(() => {
      conversationCreation = null
    })
  }

  try {
    return await conversationCreation
  } catch (e) {
    if (!silent) {
      ElMessage.error('创建会话失败，请稍后重试')
    }
    console.error('创建会话失败:', e)
    return false
  }
}

const switchConversation = async (conversationId) => {
  data.currentConversation = conversationId
  try {
    const res = await request.get(`/chat/messages/${conversationId}`)
    if (res.code === '200') {
      data.messages = res.data || []
      scrollToBottom()
    }
  } catch (e) { ElMessage.error('加载消息失败') }
}

const deleteConversation = async (conversationId) => {
  try {
    await ElMessageBox.confirm('确定删除这个对话吗？', '确认删除', { type: 'warning' })
    const res = await request.delete(`/chat/conversation/${conversationId}`)
    if (res.code === '200') {
      ElMessage.success('删除成功')
      if (data.currentConversation === conversationId) {
        data.currentConversation = null
        data.messages = []
      }
      await loadConversations()
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const useSuggestion = (text) => {
  data.inputMessage = text
  sendMessage()
}

const onInputKeydown = (e) => {
  // 中文输入法选词阶段（isComposing=true）一律放行，避免 Enter 确认候选词时误发送
  if (e.isComposing) return
  // 仅当「裸 Enter」（无 Shift/Ctrl/Alt/Meta）时拦截并发送；Shift+Enter 走默认换行
  if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey) {
    e.preventDefault()
    sendMessage()
  }
}

const sendMessage = async () => {
  if (!data.inputMessage.trim() || data.loading) return

  // 当前无会话时尝试创建；用户主动发送场景下失败要明确告知，并保留输入内容以便重试
  if (!data.currentConversation) {
    const ok = await createConversation()
    if (!ok) return
  }

  const userMessage = data.inputMessage.trim()
  data.inputMessage = ''

  data.messages.push({ role: 'user', content: userMessage })
  scrollToBottom()

  data.loading = true
  data.status = '正在连接智能客服…'
  data.messages.push({ role: 'assistant', content: '' })

  try {
    const response = await fetch(`${import.meta.env.VITE_BASE_URL}/chat/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        conversation_id: data.currentConversation,
        message: userMessage
      })
    })

    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    if (!response.body) throw new Error('浏览器不支持流式响应')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let assistantMessage = ''
    let buffer = ''
    let agentFailed = false

    const handleEvent = (eventText) => {
      const payload = eventText
        .split('\n')
        .filter(line => line.startsWith('data:'))
        .map(line => line.slice(5).trimStart())
        .join('\n')
      if (!payload) return
      const sseData = JSON.parse(payload)
      if (sseData.type === 'status') {
        data.status = sseData.message || '正在处理…'
        return
      }
      if (sseData.content) {
        assistantMessage += sseData.content
        const lastMsg = data.messages[data.messages.length - 1]
        if (lastMsg?.role === 'assistant') lastMsg.content = assistantMessage
        scrollToBottom()
      }
      if (sseData.type === 'error' || (sseData.done && sseData.ok === false)) {
        agentFailed = true
      }
    }

    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
      const events = buffer.split('\n\n')
      buffer = events.pop() || ''
      for (const eventText of events) {
        try { handleEvent(eventText) }
        catch (e) { throw new Error(`SSE 数据格式错误: ${e.message}`) }
      }
      if (done) break
    }
    if (buffer.trim()) handleEvent(buffer)
    if (agentFailed) ElMessage.warning('智能客服暂时不可用，请稍后重试')
    await loadConversations()
  } catch (e) {
    const lastMsg = data.messages[data.messages.length - 1]
    if (lastMsg?.role === 'assistant' && !lastMsg.content) data.messages.pop()
    ElMessage.error('发送消息失败')
    console.error(e)
  } finally {
    data.loading = false
    scrollToBottom()
  }
}

onMounted(async () => {
  await loadConversations()
  if (data.conversations.length > 0) {
    // 后端按 updated_at 倒序返回，第一条即最新会话
    await switchConversation(data.conversations[0].id)
  } else {
    // 无历史对话则尝试预创建新会话；silent=true 失败也不打扰用户：
    // currentConversation 保持 null，banner + 输入框仍可用，用户首次发送时 sendMessage 会再尝试创建
    await createConversation(true)
  }
})
</script>

<style scoped>
.chat-page {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  height: calc(100vh - var(--header-h) - 40px);
  padding: 20px;
  width: 100%;
}

/* —— 侧边栏 —— */
.chat-sidebar {
  background: var(--c-bg-card);
  border-radius: var(--r-lg);
  border: none;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-head {
  padding: 16px;
  border-bottom: 1px solid var(--c-border-light);
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-secondary);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.sidebar-title .el-icon { color: var(--c-primary); }

.new-btn {
  width: 100%;
  background: var(--grad-primary);
  border: none;
  border-radius: var(--r-md);
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(184, 148, 31, 0.22);
}

.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--r-md);
  cursor: pointer;
  margin-bottom: 4px;
  position: relative;
  transition: all var(--t-fast) var(--ease-out);
  border: 1px solid transparent;
}

.conv-item:hover {
  background: var(--c-bg-soft);
}

.conv-item.active {
  background: var(--c-primary-soft);
  border-color: var(--c-primary-bg);
}

.conv-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--c-bg-soft);
  color: var(--c-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.conv-item.active .conv-icon {
  background: var(--grad-primary);
  color: #fff;
}

.conv-main {
  flex: 1;
  min-width: 0;
}

.conv-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--c-text-primary);
}

.conv-item.active .conv-title {
  color: var(--c-primary);
  font-weight: 600;
}

.conv-time {
  font-size: 11px;
  color: var(--c-text-secondary);
  margin-top: 2px;
}

.conv-del {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--c-text-secondary);
  cursor: pointer;
  opacity: 0;
  transition: all var(--t-fast) var(--ease-out);
  display: flex;
  align-items: center;
  justify-content: center;
}

.conv-item:hover .conv-del { opacity: 1; }

.conv-del:hover {
  background: var(--c-danger-soft);
  color: var(--c-danger);
}

.conv-empty {
  padding: 40px 16px;
  text-align: center;
  color: var(--c-text-secondary);
}

.conv-empty p {
  margin: 10px 0 4px;
  font-size: 14px;
  font-weight: 500;
  color: var(--c-text-primary);
}

.conv-empty span {
  font-size: 12px;
}

/* —— 主区 —— */
.chat-main {
  background: var(--c-bg-card);
  border-radius: var(--r-lg);
  border: none;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.chat-banner {
  position: relative;
  padding: 40px 32px;
  background: linear-gradient(135deg, #fdf6e0 0%, #f5ecc8 100%);
  border-bottom: 1px solid var(--c-border-light);
  overflow: hidden;
}

.banner-bg {
  position: absolute;
  border-radius: 50%;
  filter: blur(2px);
  opacity: 0.45;
}

.deco-1 { width: 200px; height: 200px; background: #ffffff; top: -60px; right: -40px; }
.deco-2 { width: 120px; height: 120px; background: #d4af37; bottom: -30px; left: 20%; opacity: 0.22; }

.banner-content {
  position: relative;
  z-index: 2;
  text-align: center;
}

.banner-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 14px;
  border-radius: 16px;
  background: var(--grad-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  box-shadow: 0 8px 20px rgba(184, 148, 31, 0.32);
}

.banner-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--c-text-primary);
  margin: 0 0 6px;
}

.banner-sub {
  font-size: 13px;
  color: var(--c-text-secondary);
  margin: 0 0 20px;
}

.banner-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.sugg-chip {
  padding: 8px 14px;
  border-radius: var(--r-pill);
  background: var(--c-bg-card);
  border: none;
  color: var(--c-text-regular);
  font-size: 13px;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: all var(--t-fast) var(--ease-out);
}

.sugg-chip:hover {
  background: var(--c-primary);
  color: #fff;
  border-color: var(--c-primary);
  transform: translateY(-1px);
}

/* —— 消息列表 —— */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  margin: auto;
  text-align: center;
  color: var(--c-text-secondary);
}

.empty-state p {
  margin-top: 12px;
  font-size: 14px;
}

.message-row {
  display: flex;
  gap: 10px;
  max-width: 75%;
  animation: msgIn 0.25s var(--ease-out);
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-row.user {
  flex-direction: row-reverse;
  align-self: flex-end;
}

.message-avatar {
  flex-shrink: 0;
}

.bot-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--grad-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.message-content {
  min-width: 0;
}

.message-text {
  padding: 10px 14px;
  border-radius: 14px;
  line-height: 1.55;
  word-break: break-word;
  font-size: 14px;
}

.message-row.user .message-text {
  background: var(--grad-primary);
  color: #fff;
  border-top-right-radius: 4px;
  box-shadow: 0 4px 12px rgba(184, 148, 31, 0.22);
}

.message-row.assistant .message-text {
  background: var(--c-bg-soft);
  color: var(--c-text-primary);
  border-top-left-radius: 4px;
}

.message-text.loading {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 14px 16px;
}

.loading-status {
  margin-left: 8px;
  color: var(--c-text-secondary);
  font-size: 12px;
}

.dot {
  width: 6px;
  height: 6px;
  background: var(--c-primary);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.5); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* —— 输入区 —— */
.input-area {
  padding: 14px 20px 18px;
  border-top: none;
  background: var(--c-bg-card);
}

.input-wrapper {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  background: var(--c-bg-soft);
  border-radius: var(--r-lg);
  padding: 6px 6px 6px 14px;
  transition: all var(--t-fast) var(--ease-out);
  border: none;
}

.input-wrapper:focus-within {
  background: var(--c-bg-card);
  box-shadow: 0 0 0 3px var(--c-primary-soft);
}

.chat-input {
  flex: 1;
}

.chat-input :deep(.el-textarea__inner) {
  background: transparent;
  border: none;
  resize: none;
  box-shadow: none;
  padding: 6px 0;
  font-size: 14px;
  line-height: 1.5;
}

.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--grad-primary);
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
  transition: all var(--t-fast) var(--ease-out);
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(184, 148, 31, 0.32);
}

.send-btn:disabled {
  background: var(--c-text-placeholder);
  cursor: not-allowed;
}

.input-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 11px;
  color: var(--c-text-secondary);
  justify-content: center;
}

/* —— Markdown 排版 —— */
:deep(.message-text p) { margin: 0; }
:deep(.message-text p + p) { margin-top: 8px; }
:deep(.message-text pre) {
  background: #1f1d2e;
  color: #e4e4e7;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
  margin: 8px 0;
}
:deep(.message-text code) {
  background: rgba(0,0,0,0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}
:deep(.message-row.user .message-text code) {
  background: rgba(255,255,255,0.2);
}
:deep(.message-text pre code) {
  background: none;
  padding: 0;
}
:deep(.message-text ul),
:deep(.message-text ol) {
  padding-left: 20px;
  margin: 6px 0;
}
:deep(.message-text li) { margin: 2px 0; }
:deep(.message-text table) {
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 13px;
}
:deep(.message-text th),
:deep(.message-text td) {
  border: 1px solid var(--c-border);
  padding: 6px 10px;
}
:deep(.message-text th) { background: rgba(0,0,0,0.04); font-weight: 600; }
:deep(.message-text blockquote) {
  border-left: 3px solid var(--c-primary);
  padding-left: 12px;
  color: var(--c-text-secondary);
  margin: 8px 0;
}
:deep(.message-text a) { color: inherit; text-decoration: underline; }
:deep(.message-row.user .message-text a) { color: #fff; }

@media (max-width: 900px) {
  .chat-page { grid-template-columns: 1fr; }
  .chat-sidebar { display: none; }
}
</style>
