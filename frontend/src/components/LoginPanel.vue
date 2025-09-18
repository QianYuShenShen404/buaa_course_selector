<template>
  <div class="login-panel">
    <el-card class="glass-card login-card fade-in">
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon"><Lock /></el-icon>
          <span>用户登录</span>
        </div>
        <p class="header-subtitle">使用您的学号和密码登录北航CAS系统</p>
      </template>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        label-width="80px"
        size="large"
      >
        <el-form-item label="学号" prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入学号"
            :prefix-icon="User"
            clearable
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
            clearable
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="isLogging"
            @click="handleLogin"
            class="login-btn"
            size="large"
          >
            <template v-if="!isLogging">
              <el-icon><User /></el-icon>
              登录系统
            </template>
            <template v-else> 正在登录... </template>
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-tips">
        <el-alert title="温馨提示" type="info" :closable="false" show-icon>
          <p>🔒 使用CAS统一认证，自动获取BatchID和Token</p>
          <p>🛡️ 您的密码将通过HTTPS安全传输</p>
        </el-alert>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import { ElMessage } from "element-plus";
import { User, Lock } from "@element-plus/icons-vue";
import { loginAPI } from "@/utils/api";

// 定义事件
const emit = defineEmits(["login-success"]);

// 响应式数据
const loginFormRef = ref();
const isLogging = ref(false);

const loginForm = reactive({
  username: "",
  password: "",
});

const loginRules = {
  username: [
    { required: true, message: "请输入学号", trigger: "blur" },
    { min: 8, max: 12, message: "学号长度应为8-12位", trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 6, message: "密码长度不能少于6位", trigger: "blur" },
  ],
};

// 处理登录
const handleLogin = async () => {
  if (!loginFormRef.value) return;

  try {
    const valid = await loginFormRef.value.validate();
    if (!valid) return;

    isLogging.value = true;

    ElMessage.info({
      message: `🔐 开始登录，用户: ${loginForm.username}`,
      duration: 2000,
    });

    const response = await loginAPI({
      username: loginForm.username,
      password: loginForm.password,
    });

    if (response.success) {
      ElMessage.success({
        message: "🎉 登录成功！系统已就绪",
        duration: 3000,
      });

      // 发送登录成功事件
      emit("login-success", response.data);

      // 清空表单
      loginForm.username = "";
      loginForm.password = "";
    } else {
      ElMessage.error({
        message: `❌ 登录失败: ${response.message}`,
        duration: 4000,
      });
    }
  } catch (error) {
    console.error("登录异常:", error);
    ElMessage.error({
      message: `💥 登录异常: ${error.message}`,
      duration: 4000,
    });
  } finally {
    isLogging.value = false;
  }
};
</script>

<style lang="scss" scoped>
.login-panel {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.login-card {
  width: 100%;
  max-width: 500px;
  margin: 0 auto;

  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--el-color-primary);

    .header-icon {
      font-size: 1.4rem;
    }
  }

  .header-subtitle {
    margin-top: 8px;
    font-size: 0.9rem;
    color: var(--el-text-color-secondary);
  }
}

.login-btn {
  width: 100%;
  height: 50px;
  font-size: 1.1rem;
  font-weight: 600;
  border-radius: 25px;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
  }
}

.login-tips {
  margin-top: 20px;

  :deep(.el-alert__content) {
    line-height: 1.8;

    p {
      margin: 4px 0;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .login-card {
    margin: 0 10px;
  }
}
</style>
