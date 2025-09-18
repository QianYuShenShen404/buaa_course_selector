import { ElMessage } from 'element-plus'

// WebSocket连接实例
let websocket = null
let logMonitorRef = null
let reconnectTimer = null
let reconnectAttempts = 0
const maxReconnectAttempts = 5

/**
 * 建立WebSocket连接
 * @param {string} sessionId - 会话ID
 * @param {Object} logMonitor - 日志监控组件引用
 */
export const setupWebSocket = (sessionId, logMonitor) => {
  if (!sessionId) {
    console.error('WebSocket: 缺少会话ID')
    return
  }
  
  logMonitorRef = logMonitor
  connectWebSocket(sessionId)
}

/**
 * 连接WebSocket
 * @param {string} sessionId - 会话ID
 */
const connectWebSocket = (sessionId) => {
  try {
    // 关闭现有连接
    if (websocket) {
      websocket.close()
    }
    
    // 构建WebSocket URL
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/${sessionId}`
    
    console.log('WebSocket: 尝试连接', wsUrl)
    
    // 创建新连接
    websocket = new WebSocket(wsUrl)
    
    // 连接成功
    websocket.onopen = (event) => {
      console.log('WebSocket: 连接建立', event)
      reconnectAttempts = 0
      
      if (logMonitorRef) {
        logMonitorRef.handleWebSocketOpen()
      }
      
      // 发送心跳包
      startHeartbeat()
    }
    
    // 接收消息
    websocket.onmessage = (event) => {
      console.log('WebSocket: 收到消息', event.data)
      
      try {
        const message = JSON.parse(event.data)
        
        // 处理心跳响应
        if (event.data === 'pong') {
          console.log('WebSocket: 心跳响应')
          return
        }
        
        // 传递消息给日志监控组件
        if (logMonitorRef) {
          logMonitorRef.handleWebSocketMessage(event)
        }
        
        // 可以在这里添加其他消息处理逻辑
        handleSpecialMessages(message)
        
      } catch (error) {
        console.error('WebSocket: 消息解析失败', error, event.data)
        if (logMonitorRef) {
          logMonitorRef.addLog(`💥 消息解析失败: ${error.message}`, 'error')
        }
      }
    }
    
    // 连接关闭
    websocket.onclose = (event) => {
      console.log('WebSocket: 连接关闭', event)
      
      if (logMonitorRef) {
        logMonitorRef.handleWebSocketClose()
      }
      
      stopHeartbeat()
      
      // 如果不是主动关闭，尝试重连
      if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
        attemptReconnect(sessionId)
      }
    }
    
    // 连接错误
    websocket.onerror = (error) => {
      console.error('WebSocket: 连接错误', error)
      
      if (logMonitorRef) {
        logMonitorRef.handleWebSocketError(error)
      }
    }
    
  } catch (error) {
    console.error('WebSocket: 创建连接失败', error)
    ElMessage.error(`WebSocket连接失败: ${error.message}`)
  }
}

/**
 * 尝试重连WebSocket
 * @param {string} sessionId - 会话ID
 */
const attemptReconnect = (sessionId) => {
  if (reconnectAttempts >= maxReconnectAttempts) {
    console.log('WebSocket: 超过最大重连次数，停止重连')
    ElMessage.error('WebSocket连接失败，已停止重连')
    return
  }
  
  reconnectAttempts++
  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000) // 指数退避，最大30秒
  
  console.log(`WebSocket: ${delay}ms后尝试第${reconnectAttempts}次重连`)
  
  if (logMonitorRef) {
    logMonitorRef.addLog(`🔄 ${delay/1000}秒后尝试第${reconnectAttempts}次重连...`, 'warning')
  }
  
  reconnectTimer = setTimeout(() => {
    connectWebSocket(sessionId)
  }, delay)
}

/**
 * 心跳检测
 */
let heartbeatTimer = null

const startHeartbeat = () => {
  stopHeartbeat()
  
  heartbeatTimer = setInterval(() => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.send(JSON.stringify({ type: 'ping' }))
    }
  }, 30000) // 每30秒发送一次心跳
}

const stopHeartbeat = () => {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

/**
 * 处理特殊消息
 * @param {Object} message - 消息对象
 */
const handleSpecialMessages = (message) => {
  if (message.type === 'status_update' && message.data) {
    switch (message.data.type) {
      case 'auto_select_stopped':
        ElMessage.success('✅ 自动选课已停止')
        break
      case 'task_completed':
        ElMessage.info('✅ 任务已完成')
        break
      case 'stop_auto_select_requested':
        ElMessage.warning('🛑 停止信号已发送，正在等待任务完成...')
        break
    }
  }
}

/**
 * 发送WebSocket消息
 * @param {Object} message - 要发送的消息
 */
export const sendWebSocketMessage = (message) => {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.send(JSON.stringify(message))
    return true
  } else {
    console.warn('WebSocket: 连接未建立，无法发送消息')
    return false
  }
}

/**
 * 获取WebSocket连接状态
 * @returns {boolean} 是否已连接
 */
export const isWebSocketConnected = () => {
  return websocket && websocket.readyState === WebSocket.OPEN
}

/**
 * 关闭WebSocket连接
 */
export const closeWebSocket = () => {
  console.log('WebSocket: 主动关闭连接')
  
  // 清除重连定时器
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  
  // 停止心跳
  stopHeartbeat()
  
  // 关闭连接
  if (websocket) {
    websocket.close(1000, '用户主动关闭')
    websocket = null
  }
  
  // 清除引用
  logMonitorRef = null
  reconnectAttempts = 0
}