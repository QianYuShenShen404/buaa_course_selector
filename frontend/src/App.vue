<template>
  <div id="app">
    <el-container class="app-container">
      <!-- 头部标题 -->
      <el-header class="app-header">
        <div class="header-content">
          <h1 class="main-title">
            <el-icon class="title-icon"><School /></el-icon>
            北航自动选课系统
          </h1>
          <p class="subtitle">
            智能化Web界面 
            <el-tag type="success" size="small">Vue 3重构版</el-tag>
          </p>
        </div>
      </el-header>

      <!-- 主内容区域 -->
      <el-main class="app-main">
        <div class="main-container">
          <!-- 登录面板 -->
          <LoginPanel 
            v-if="!isLoggedIn" 
            @login-success="handleLoginSuccess"
          />
          
          <!-- 主操作面板 -->
          <MainPanel 
            v-if="isLoggedIn"
            :user-info="userInfo"
            @logout="handleLogout"
          />
        </div>
      </el-main>

      <!-- 底部信息 -->
      <el-footer class="app-footer">
        <div class="footer-content">
          <el-text type="info" size="small">
            🔧 Vue 3 + Element Plus | 📡 WebSocket实时通信 | 🚀 Vite构建工具
          </el-text>
        </div>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { School } from '@element-plus/icons-vue'
import LoginPanel from './components/LoginPanel.vue'
import MainPanel from './components/MainPanel.vue'

// 响应式数据
const isLoggedIn = ref(false)
const userInfo = ref(null)

// 登录成功处理
const handleLoginSuccess = (userData) => {
  isLoggedIn.value = true
  userInfo.value = userData
}

// 登出处理
const handleLogout = () => {
  isLoggedIn.value = false
  userInfo.value = null
}
</script>

<style lang="scss">
// 全局样式重置
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
}

#app {
  min-height: 100vh;
}

.app-container {
  min-height: 100vh;
  background: transparent;
}

.app-header {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  height: auto !important;
  padding: 20px 0;

  .header-content {
    text-align: center;
    color: white;

    .main-title {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      font-size: 2.5rem;
      font-weight: 700;
      margin-bottom: 8px;
      text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);

      .title-icon {
        font-size: 2.8rem;
      }
    }

    .subtitle {
      font-size: 1.1rem;
      opacity: 0.9;
      margin: 0;
    }
  }
}

.app-main {
  flex: 1;
  padding: 40px 20px;

  .main-container {
    max-width: 1200px;
    margin: 0 auto;
  }
}

.app-footer {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  height: auto !important;
  padding: 15px 0;

  .footer-content {
    text-align: center;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .app-header .header-content .main-title {
    font-size: 2rem;
    flex-direction: column;
    gap: 8px;

    .title-icon {
      font-size: 2.2rem;
    }
  }

  .app-main {
    padding: 20px 10px;
  }
}
</style>