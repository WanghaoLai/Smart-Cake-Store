<template>
  <div class="chat-container">
    <!-- 左侧会话列表 -->
    <div class="conversation-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" @click="createConversation" style="width: 100%">
          <el-icon><Plus /></el-icon>
          新对话
        </el-button>
      </div>
      <div class="conversation-list">
        <div
          v-for="conv in data.conversations"
          :key="conv.id"
          :class="['conversation-item', { active: data.currentConversation === conv.id }]"
          @click="switchConversation(conv.id)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-time">{{ conv.updated_at }}</div>
          <el-button
            class="delete-btn"
            type="danger"
            :icon="Delete"
            circle
            size="small"
            @click.stop="deleteConversation(conv.id)"
          />
        </div>
      </div>
    </div>

    <!-- 右侧聊天区域 -->
    <div class="chat-main">
      <div class="messages-container" ref="messagesContainer">
        <div v-if="data.messages.length === 0" class="empty-state">
          <el-icon :size="64" color="#c0c4cc"><ChatDotRound /></el-icon>
          <p>开始与智能客服对话吧！</p>
        </div>
        <div v-for="(msg, index) in data.messages" :key="index" :class="['message', msg.role]">
          <div class="message-avatar">
            <el-avatar v-if="msg.role === 'user'" :src="data.user.avatar || 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'" />
            <el-avatar v-else style="background-color: #409eff">
              <el-icon><Monitor /></el-icon>
            </el-avatar>
          </div>
          <div class="message-content">
            <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>
        <div v-if="data.loading" class="message assistant">
          <div class="message-avatar">
            <el-avatar style="background-color: #409eff">
              <el-icon><Monitor /></el-icon>
            </el-avatar>
          </div>
          <div class="message-content">
            <div class="message-text loading">
              <span class="dot">.</span>
              <span class="dot">.</span>
              <span class="dot">.</span>
            </div>
          </div>
        </div>
      </div>

      <div class="input-container">
        <el-input
          v-model="data.inputMessage"
          type="textarea"
          :rows="2"
          placeholder="输入您的问题..."
          @keydown.enter.ctrl="sendMessage"
          @keydown.enter.exact.prevent="sendMessage"
        />
        <el-button type="primary" @click="sendMessage" :disabled="!data.inputMessage.trim() || data.loading">
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, nextTick, onMounted } from 'vue'
import { Plus, Delete, ChatDotRound, Monitor } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import { marked } from 'marked'

const messagesContainer = ref(null)

const data = reactive({
  user: JSON.parse(localStorage.getItem('system-user') || '{}'),
  conversations: [],
  currentConversation: null,
  messages: [],
  inputMessage: '',
  loading: false
})

const renderMarkdown = (text) => {
  return marked(text || '')
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
    if (res.code === '200') {
      data.conversations = res.data || []
    }
  } catch (error) {
    console.error('加载会话列表失败:', error)
  }
}

const createConversation = async () => {
  try {
    const res = await request.post('/chat/conversation', {
      title: '新对话'
    })
    if (res.code === '200') {
      await loadConversations()
      data.currentConversation = res.data.id
      data.messages = []
    }
  } catch (error) {
    ElMessage.error('创建会话失败')
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
  } catch (error) {
    ElMessage.error('加载消息失败')
  }
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
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const sendMessage = async () => {
  if (!data.inputMessage.trim() || data.loading) return

  if (!data.currentConversation) {
    await createConversation()
  }

  const userMessage = data.inputMessage.trim()
  data.inputMessage = ''

  data.messages.push({
    role: 'user',
    content: userMessage
  })
  scrollToBottom()

  data.loading = true
  data.messages.push({
    role: 'assistant',
    content: ''
  })

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

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let assistantMessage = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const text = decoder.decode(value)
      const lines = text.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonStr = line.slice(6)
            if (jsonStr.trim()) {
              const sseData = JSON.parse(jsonStr)
              if (sseData.content) {
                assistantMessage += sseData.content
                const lastMsg = data.messages[data.messages.length - 1]
                if (lastMsg && lastMsg.role === 'assistant') {
                  lastMsg.content = assistantMessage
                }
                scrollToBottom()
              }
              if (sseData.done) {
                break
              }
            }
          } catch (e) {
            console.error('解析 SSE 数据失败:', e)
          }
        }
      }
    }

    await loadConversations()
  } catch (error) {
    ElMessage.error('发送消息失败')
    console.error('发送消息失败:', error)
  } finally {
    data.loading = false
    scrollToBottom()
  }
}

onMounted(() => {
  loadConversations()
})
</script>

<style scoped>
.chat-container {
  display: flex;
  height: calc(100vh - 100px);
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.conversation-sidebar {
  width: 280px;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conversation-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 8px;
  position: relative;
  transition: background-color 0.2s;
}

.conversation-item:hover {
  background-color: #f5f7fa;
}

.conversation-item.active {
  background-color: #ecf5ff;
  border: 1px solid #b3d8ff;
}

.conv-title {
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 30px;
}

.conv-time {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.delete-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
  transition: opacity 0.2s;
}

.conversation-item:hover .delete-btn {
  opacity: 1;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #909399;
}

.empty-state p {
  margin-top: 16px;
  font-size: 16px;
}

.message {
  display: flex;
  margin-bottom: 20px;
  gap: 12px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  max-width: 70%;
}

.message-text {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
}

.message.user .message-text {
  background-color: #409eff;
  color: white;
  border-top-right-radius: 4px;
}

.message.assistant .message-text {
  background-color: #f4f4f5;
  color: #303133;
  border-top-left-radius: 4px;
}

.message-text.loading {
  display: flex;
  gap: 4px;
}

.dot {
  animation: bounce 1.4s infinite ease-in-out both;
  font-size: 24px;
  line-height: 1;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.input-container {
  padding: 16px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-container .el-input {
  flex: 1;
}

:deep(.el-textarea__inner) {
  resize: none;
}

:deep(.message-text p) {
  margin: 0;
}

:deep(.message-text pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
}

:deep(.message-text code) {
  background: #e6e8ea;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 14px;
}

:deep(.message-text pre code) {
  background: none;
  padding: 0;
}

:deep(.message-text ul),
:deep(.message-text ol) {
  padding-left: 20px;
  margin: 8px 0;
}

:deep(.message-text table) {
  border-collapse: collapse;
  margin: 8px 0;
}

:deep(.message-text th),
:deep(.message-text td) {
  border: 1px solid #dcdfe6;
  padding: 8px 12px;
  text-align: left;
}

:deep(.message-text th) {
  background: #f5f7fa;
}
</style>
