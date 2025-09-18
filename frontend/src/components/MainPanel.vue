<template>
  <div class="main-panel">
    <!-- 用户信息卡片 -->
    <el-card class="glass-card user-card slide-in" shadow="never">
      <div class="user-info">
        <div class="user-details">
          <el-avatar :size="50" class="user-avatar">
            <el-icon><User /></el-icon>
          </el-avatar>
          <div class="user-text">
            <h3>{{ userInfo.username }}</h3>
            <p>
              会话ID:
              <el-tag type="info" size="small">{{ sessionIdShort }}</el-tag>
            </p>
          </div>
        </div>
        <div class="user-actions">
          <el-button
            type="info"
            :icon="PieChart"
            @click="getStatus"
            :loading="statusLoading"
          >
            状态检查
          </el-button>
          <el-button type="danger" :icon="SwitchButton" @click="handleLogout">
            登出
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 主要操作区域 -->
    <el-row :gutter="20" class="main-content">
      <!-- 左侧：搜索和选课操作 -->
      <el-col :lg="14" :md="24">
        <!-- 课程搜索 -->
        <CourseSearch
          ref="courseSearchRef"
          :session-id="userInfo.session_id"
          @search-success="handleSearchSuccess"
          @search-error="handleSearchError"
        />

        <!-- 选课操作 -->
        <SelectCourse
          :session-id="userInfo.session_id"
          :can-select="canSelect"
          :course-data="courseData"
        />
      </el-col>

      <!-- 右侧：日志监控 -->
      <el-col :lg="10" :md="24">
        <LogMonitor ref="logMonitorRef" :session-id="userInfo.session_id" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import { User, PieChart, SwitchButton } from "@element-plus/icons-vue";
import CourseSearch from "./CourseSearch.vue";
import SelectCourse from "./SelectCourse.vue";
import LogMonitor from "./LogMonitor.vue";
import { getStatusAPI, logoutAPI } from "@/utils/api";
import { setupWebSocket, closeWebSocket } from "@/utils/websocket";

// 组件属性
const props = defineProps({
  userInfo: {
    type: Object,
    required: true,
  },
});

// 定义事件
const emit = defineEmits(["logout"]);

// 响应式数据
const courseSearchRef = ref();
const logMonitorRef = ref();
const statusLoading = ref(false);
const canSelect = ref(false);
const courseData = ref(null);

// 计算属性
const sessionIdShort = computed(() => {
  return props.userInfo.session_id.substring(0, 8) + "...";
});

// 处理搜索成功
const handleSearchSuccess = (data) => {
  canSelect.value =
    data.has_results && data.secret_val && data.secret_val.length > 0;
  courseData.value = data;

  if (canSelect.value) {
    ElMessage.success("✅ 搜索成功，已获取选课密钥，可以开始选课");
  } else {
    ElMessage.warning("⚠️ 搜索成功，但未获取到选课密钥");
  }
};

// 处理搜索错误
const handleSearchError = (error) => {
  canSelect.value = false;
  courseData.value = null;
  ElMessage.error(`❌ 搜索失败: ${error}`);
};

// 获取系统状态
const getStatus = async () => {
  statusLoading.value = true;
  try {
    const response = await getStatusAPI(props.userInfo.session_id);
    if (response.success) {
      const status = response.data;
      const statusText = `认证=${status.authenticated ? "✅" : "❌"}, 搜索=${
        status.search_ready ? "✅" : "❌"
      }, 选课=${status.selector_ready ? "✅" : "❌"}`;
      ElMessage.info(`📊 系统状态: ${statusText}`);
    }
  } catch (error) {
    ElMessage.error(`💥 状态查询失败: ${error.message}`);
  } finally {
    statusLoading.value = false;
  }
};

// 处理登出
const handleLogout = async () => {
  try {
    await logoutAPI(props.userInfo.session_id);
    ElMessage.success("👋 已安全登出");
  } catch (error) {
    ElMessage.warning("⚠️ 登出请求失败，但将继续本地清理");
  } finally {
    emit("logout");
  }
};

// 生命周期钩子
onMounted(() => {
  // 建立WebSocket连接
  setupWebSocket(props.userInfo.session_id, logMonitorRef.value);

  ElMessage.success({
    message: "🚀 主面板已加载，WebSocket连接已建立",
    duration: 2000,
  });
});

onUnmounted(() => {
  // 关闭WebSocket连接
  closeWebSocket();
});
</script>

<style lang="scss" scoped>
.main-panel {
  .user-card {
    margin-bottom: 20px;

    .user-info {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .user-details {
        display: flex;
        align-items: center;
        gap: 15px;

        .user-avatar {
          background: var(--el-color-primary);
        }

        .user-text {
          h3 {
            margin: 0 0 5px 0;
            color: var(--el-text-color-primary);
            font-weight: 600;
          }

          p {
            margin: 0;
            color: var(--el-text-color-secondary);
            font-size: 0.9rem;
          }
        }
      }

      .user-actions {
        display: flex;
        gap: 10px;
      }
    }
  }

  .main-content {
    margin-top: 20px;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .main-panel .user-card .user-info {
    flex-direction: column;
    gap: 15px;

    .user-actions {
      align-self: stretch;

      .el-button {
        flex: 1;
      }
    }
  }
}
</style>
