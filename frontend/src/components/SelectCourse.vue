<template>
  <div class="select-course">
    <el-card class="glass-card select-card fade-in" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon"><Trophy /></el-icon>
          <span>第二步：选课操作</span>
        </div>
      </template>

      <div class="select-actions">
        <el-space direction="vertical" :size="16" style="width: 100%">
          <!-- 单次选课 -->
          <el-card class="action-card" shadow="hover">
            <div class="action-content">
              <div class="action-info">
                <h4 class="action-title">
                  <el-icon><Aim /></el-icon>
                  单次选课
                </h4>
                <p class="action-desc">执行一次选课尝试，适合测试或确认选课</p>
              </div>
              <el-button
                type="success"
                size="large"
                :disabled="!canSelect"
                :loading="isSingleSelecting"
                @click="handleSingleSelect"
                class="action-btn"
              >
                <el-icon><Aim /></el-icon>
                {{ isSingleSelecting ? "选课中..." : "开始单次选课" }}
              </el-button>
            </div>
          </el-card>

          <!-- 自动重试选课 -->
          <el-card class="action-card" shadow="hover">
            <div class="action-content">
              <div class="action-info">
                <h4 class="action-title">
                  <el-icon><Refresh /></el-icon>
                  自动重试选课
                </h4>
                <p class="action-desc">
                  持续自动尝试选课直到成功，适合抢课场景
                </p>
              </div>
              <el-button
                v-if="!isAutoMode"
                type="warning"
                size="large"
                :disabled="!canSelect"
                @click="confirmAutoSelect"
                class="action-btn"
              >
                <el-icon><Refresh /></el-icon>
                启动自动选课
              </el-button>
              <el-button
                v-else
                type="danger"
                size="large"
                @click="confirmStopAutoSelect"
                class="action-btn stop-btn"
              >
                <el-icon><CircleClose /></el-icon>
                停止自动选课
              </el-button>
            </div>
          </el-card>
        </el-space>
      </div>

      <div class="select-tips">
        <el-alert
          v-if="!canSelect"
          title="操作提示"
          type="warning"
          :closable="false"
          show-icon
        >
          💡 请先搜索课程，获取选课参数后即可开始选课
        </el-alert>
        <el-alert
          v-else
          title="选课须知"
          type="success"
          :closable="false"
          show-icon
        >
          <ul style="margin: 0; padding-left: 20px">
            <li>✅ 选课参数已获取，可以开始选课</li>
            <li>🔄 自动选课将持续运行直到成功或手动停止</li>
            <li>📊 选课进度可通过右侧日志实时监控</li>
          </ul>
        </el-alert>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Trophy, Aim, Refresh, CircleClose } from "@element-plus/icons-vue";
import { selectCourseAPI, stopAutoSelectAPI } from "@/utils/api";

// 组件属性
const props = defineProps({
  sessionId: {
    type: String,
    required: true,
  },
  canSelect: {
    type: Boolean,
    default: false,
  },
  courseData: {
    type: Object,
    default: null,
  },
});

// 响应式数据
const isSingleSelecting = ref(false);
const isAutoMode = ref(false);

// 单次选课
const handleSingleSelect = async () => {
  if (!props.canSelect) {
    ElMessage.warning("请先搜索课程");
    return;
  }

  isSingleSelecting.value = true;

  try {
    ElMessage.info("🎯 启动单次选课模式...");

    const response = await selectCourseAPI({
      session_id: props.sessionId,
      auto_retry: false,
    });

    if (response.success) {
      ElMessage.success("🎉 单次选课成功！");
    } else {
      ElMessage.error(`❌ 单次选课失败: ${response.message}`);
    }
  } catch (error) {
    console.error("单次选课异常:", error);
    ElMessage.error(`💥 选课异常: ${error.message}`);
  } finally {
    isSingleSelecting.value = false;
  }
};

// 确认启动自动选课
const confirmAutoSelect = async () => {
  try {
    await ElMessageBox.confirm(
      "🚨 确认启动自动重试选课？\n\n" +
        "🔄 系统将持续尝试选课直到成功\n" +
        '🛑 启动后按钮将变为红色"停止"按钮\n' +
        "⚠️ 点击停止按钮可优雅停止自动选课\n" +
        "👀 可通过实时日志监控选课进度\n\n" +
        "确定要继续吗？",
      "确认启动自动选课",
      {
        confirmButtonText: "确定启动",
        cancelButtonText: "取消",
        type: "warning",
        dangerouslyUseHTMLString: true,
      }
    );

    await handleAutoSelect();
  } catch {
    // 用户取消
  }
};

// 自动选课
const handleAutoSelect = async () => {
  if (!props.canSelect) {
    ElMessage.warning("请先搜索课程");
    return;
  }

  try {
    ElMessage.info("🚀 启动自动重试选课模式...");

    // 切换按钮状态
    isAutoMode.value = true;

    const response = await selectCourseAPI({
      session_id: props.sessionId,
      auto_retry: true,
    });

    if (response.success) {
      ElMessage.success("🚀 异步自动选课已启动，请通过日志监控进度");
    } else {
      ElMessage.error(`❌ 异步自动选课启动失败: ${response.message}`);
      isAutoMode.value = false;
    }
  } catch (error) {
    console.error("自动选课异常:", error);
    ElMessage.error(`💥 选课异常: ${error.message}`);
    isAutoMode.value = false;
  }
};

// 确认停止自动选课
const confirmStopAutoSelect = async () => {
  try {
    await ElMessageBox.confirm(
      "🚨 确认停止自动选课？\n\n" +
        "🛑 系统将执行：\n" +
        "1. 优雅停止当前自动选课任务\n" +
        "2. 等待当前操作完成后停止\n" +
        "3. 恢复按钮状态为可操作\n\n" +
        "✅ 注意：Web程序将继续运行，不会关闭\n\n" +
        "确定要停止自动选课吗？",
      "确认停止自动选课",
      {
        confirmButtonText: "确定停止",
        cancelButtonText: "取消",
        type: "error",
        dangerouslyUseHTMLString: true,
      }
    );

    await handleStopAutoSelect();
  } catch {
    // 用户取消
  }
};

// 停止自动选课
const handleStopAutoSelect = async () => {
  try {
    ElMessage.warning("🛑 正在发送停止信号...");

    const response = await stopAutoSelectAPI(props.sessionId);

    if (response.success) {
      ElMessage.info("✅ 停止信号已发送，等待任务完成");

      // 延迟恢复按钮状态
      setTimeout(() => {
        isAutoMode.value = false;
        ElMessage.success("✅ 自动选课已停止，可以重新开始");
      }, 2000);
    } else {
      ElMessage.error(`❌ 停止失败: ${response.message}`);
    }
  } catch (error) {
    console.error("停止自动选课异常:", error);
    ElMessage.error(`❌ 停止请求失败: ${error.message}`);
    // 失败后也要恢复按钮状态
    isAutoMode.value = false;
  }
};

// 监听WebSocket消息来恢复按钮状态
const handleWebSocketMessage = (message) => {
  if (message.data) {
    switch (message.data.type) {
      case "auto_select_stopped":
      case "task_completed":
        isAutoMode.value = false;
        break;
    }
  }
};

// 暴露方法给父组件
defineExpose({
  handleWebSocketMessage,
  resetAutoMode: () => {
    isAutoMode.value = false;
  },
});
</script>

<style lang="scss" scoped>
.select-course {
  margin-bottom: 20px;

  .select-card {
    .card-header {
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

  .select-actions {
    margin-bottom: 20px;

    .action-card {
      border: 1px solid var(--el-border-color-lighter);
      transition: all 0.3s ease;

      &:hover {
        border-color: var(--el-color-primary);
        transform: translateY(-2px);
      }

      .action-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 20px;

        .action-info {
          flex: 1;

          .action-title {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 0 0 8px 0;
            color: var(--el-text-color-primary);
            font-size: 1.1rem;
            font-weight: 600;
          }

          .action-desc {
            margin: 0;
            color: var(--el-text-color-secondary);
            font-size: 0.9rem;
            line-height: 1.5;
          }
        }

        .action-btn {
          min-width: 160px;
          height: 45px;
          font-size: 1rem;
          font-weight: 600;
          border-radius: 22px;
          transition: all 0.3s ease;

          &:hover:not(:disabled) {
            transform: translateY(-2px);
          }

          &.stop-btn {
            animation: pulse-danger 2s infinite;
          }
        }
      }
    }
  }

  .select-tips {
    :deep(.el-alert__content) {
      line-height: 1.8;

      ul {
        li {
          margin: 4px 0;
        }
      }
    }
  }
}

// 危险按钮脉冲动画
@keyframes pulse-danger {
  0% {
    box-shadow: 0 2px 4px rgba(245, 108, 108, 0.3);
    transform: scale(1);
  }
  50% {
    box-shadow: 0 4px 12px rgba(245, 108, 108, 0.6);
    transform: scale(1.02);
  }
  100% {
    box-shadow: 0 2px 4px rgba(245, 108, 108, 0.3);
    transform: scale(1);
  }
}

// 响应式设计
@media (max-width: 768px) {
  .select-course .select-actions .action-card .action-content {
    flex-direction: column;
    text-align: center;
    gap: 15px;

    .action-btn {
      width: 100%;
    }
  }
}
</style>
