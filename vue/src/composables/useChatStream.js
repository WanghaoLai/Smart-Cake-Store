/** Parse the chat SSE protocol independently from view state and rendering. */
export async function streamChat({ conversationId, message, onStatus, onContent }) {
  const response = await fetch(`${import.meta.env.VITE_BASE_URL}/chat/send`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token')}`,
    },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  })

  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    const error = await response.json()
    throw new Error(error.msg || `HTTP ${response.status}`)
  }
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  if (!response.body) throw new Error('浏览器不支持流式响应')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let fullContent = ''
  let agentFailed = false

  const handleEvent = (eventText) => {
    const payload = eventText
      .split('\n')
      .filter(line => line.startsWith('data:'))
      .map(line => line.slice(5).trimStart())
      .join('\n')
    if (!payload) return
    const event = JSON.parse(payload)
    if (event.type === 'status') onStatus?.(event.message || '正在处理…')
    if (event.content) {
      fullContent += event.content
      onContent?.(fullContent)
    }
    if (event.type === 'error' || (event.done && event.ok === false)) agentFailed = true
  }

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''
    for (const eventText of events) {
      try { handleEvent(eventText) }
      catch (error) { throw new Error(`SSE 数据格式错误: ${error.message}`) }
    }
    if (done) break
  }
  if (buffer.trim()) handleEvent(buffer)
  return { content: fullContent, agentFailed }
}
