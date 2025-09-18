<template>
  <div class="log-monitor">
    <el-card class="glass-card log-card fade-in" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon"><Monitor /></el-icon>
          <span>第三步：实时状态监控</span>
          <div class="header-actions">
            <el-button
              type="info"
              size="small"
              :icon="Delete"
              @click="clearLogs"
            >
              清空日志
            </el-button>
          </div>
        </div>
      </template>

      <div class="log-container">
        <div
          ref="logAreaRef"
          class="log-area"
          :class="{ 'has-logs': logs.length > 0 }"
        >
          <transition-group name="log" tag="div">
            <div
              v-for="log in logs"
              :key="log.id"
              :class="['log-entry', `log-${log.level}`]"
            >
              <span class="log-time">{{ log.time }}</span>
              <span class="log-icon">{{ log.icon }}</span>
              <span class="log-message" v-html="log.message"></span>
            </div>
          </transition-group>

          <div v-if="logs.length === 0" class="empty-logs">
            <el-empty description="暂无日志信息">
              <el-icon class="empty-icon"><DocumentCopy /></el-icon>
              <p>系统运行日志将在这里实时显示</p>
            </el-empty>
          </div>
        </div>

        <div class="log-status">
          <el-space>
            <el-tag v-if="isConnected" type="success" size="small">
              <el-icon><Link /></el-icon>
              WebSocket已连接
            </el-tag>
            <el-tag v-else type="danger" size="small">
              <el-icon><Unlock /></el-icon>
              WebSocket未连接
            </el-tag>
            <el-text type="info" size="small">
              共 {{ logs.length }} 条日志
            </el-text>
          </el-space>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import {
  Monitor,
  Delete,
  DocumentCopy,
  Link,
  Unlock,
} from "@element-plus/icons-vue";

// 组件属性
const props = defineProps({
  sessionId: {
    type: String,
    required: true,
  },
});

// 响应式数据
const logAreaRef = ref();
const logs = reactive([]);
const isConnected = ref(false);
let logIdCounter = 0;

// 日志级别图标映射
const logIcons = {
  info: "ℹ️",
  success: "✅",
  error: "❌",
  warning: "⚠️",
};

// 添加日志
const addLog = (message, level = "info") => {
  const now = new Date();
  const time = now.toLocaleTimeString();

  const logEntry = {
    id: ++logIdCounter,
    time,
    message,
    level,
    icon: logIcons[level] || "ℹ️",
  };

  logs.push(logEntry);

  // 滚动到底部
  nextTick(() => {
    if (logAreaRef.value) {
      logAreaRef.value.scrollTop = logAreaRef.value.scrollHeight;
    }
  });

  // 限制日志数量
  if (logs.length > 500) {
    logs.splice(0, logs.length - 500);
  }
};

// 清空日志
const clearLogs = () => {
  logs.splice(0, logs.length);
  addLog("🗑️ 日志已清空", "info");
};

// 处理WebSocket消息
const handleWebSocketMessage = (event) => {
  try {
    const message = JSON.parse(event.data);

    if (message.type === "status_update") {
      addLog(message.message, message.level || "info");
    }
  } catch (error) {
    console.error("WebSocket消息解析失败:", error);
    addLog(`💥 消息解析失败: ${error.message}`, "error");
  }
};

// WebSocket连接状态处理
const handleWebSocketOpen = () => {
  isConnected.value = true;
  addLog("📡 WebSocket连接建立，实时监控已启动", "success");
};

const handleWebSocketClose = () => {
  isConnected.value = false;
  addLog("📡 WebSocket连接断开", "warning");
};

const handleWebSocketError = (error) => {
  isConnected.value = false;
  addLog("📡 WebSocket连接错误", "error");
  console.error("WebSocket错误:", error);
};

// 初始化
onMounted(() => {
  addLog("🚀 系统初始化完成，等待WebSocket连接...", "info");
});

// 暴露方法给父组件
defineExpose({
  addLog,
  clearLogs,
  handleWebSocketMessage,
  handleWebSocketOpen,
  handleWebSocketClose,
  handleWebSocketError,
});
</script>

<style lang="scss" scoped>
.log-monitor {
  .log-card {
    height: 100%;

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;

      > div:first-child {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--el-color-primary);

        .header-icon {
          font-size: 1.3rem;
        }
      }
    }
  }

  .log-container {
    .log-area {
      height: 400px;
      overflow-y: auto;
      background: #f8f9fa;
      border: 1px solid var(--el-border-color-light);
      border-radius: 8px;
      padding: 12px;
      font-family: "Consolas", "Monaco", "Courier New", monospace;
      font-size: 13px;

      &.has-logs {
        background: linear-gradient(to bottom, #f8f9fa, #fff);
      }

      .log-entry {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 6px 8px;
        margin: 2px 0;
        border-radius: 4px;
        transition: all 0.3s ease;
        word-wrap: break-word;
        line-height: 1.4;

        .log-time {
          color: var(--el-text-color-secondary);
          font-size: 11px;
          flex-shrink: 0;
          width: 80px;
        }

        .log-icon {
          flex-shrink: 0;
          width: 20px;
        }

        .log-message {
          flex: 1;

          :deep(code) {
            background: rgba(0, 0, 0, 0.1);
            padding: 2px 4px;
            border-radius: 3px;
            font-size: 12px;
          }
        }

        &.log-info {
          background: rgba(144, 202, 249, 0.1);
          border-left: 3px solid #90caf9;
        }

        &.log-success {
          background: rgba(129, 199, 132, 0.1);
          border-left: 3px solid #81c784;
        }

        &.log-error {
          background: rgba(239, 83, 80, 0.1);
          border-left: 3px solid #ef5350;
        }

        &.log-warning {
          background: rgba(255, 183, 77, 0.1);
          border-left: 3px solid #ffb74d;
        }
      }

      .empty-logs {
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: var(--el-text-color-secondary);

        .empty-icon {
          font-size: 3rem;
          margin-bottom: 16px;
          opacity: 0.3;
        }

        p {
          margin: 8px 0 0 0;
          font-size: 0.9rem;
        }
      }
    }

    .log-status {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid var(--el-border-color-lighter);
    }
  }
}

// 日志条目动画
.log-enter-active {
  transition: all 0.3s ease;
}

.log-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}

.log-enter-to {
  opacity: 1;
  transform: translateX(0);
}

// 响应式设计
@media (max-width: 768px) {
  .log-monitor .log-container .log-area {
    height: 300px;
    font-size: 12px;

    .log-entry {
      flex-direction: column;
      gap: 4px;

      .log-time {
        width: auto;
        order: -1;
      }
    }
  }
}
</style>
