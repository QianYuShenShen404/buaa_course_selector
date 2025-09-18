<template>
  <div class="course-search">
    <el-card class="glass-card search-card fade-in" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon"><Search /></el-icon>
          <span>第一步：搜索课程</span>
        </div>
      </template>

      <el-form :model="searchForm" class="search-form">
        <el-form-item>
          <el-input
            v-model="searchForm.keyword"
            placeholder="输入课程关键词，如：计算机图形学"
            :prefix-icon="Search"
            size="large"
            clearable
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button
                type="primary"
                :loading="isSearching"
                @click="handleSearch"
                :icon="Search"
              >
                搜索
              </el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>

      <div class="search-tips">
        <el-alert title="搜索提示" type="info" :closable="false" show-icon>
          💡 搜索会自动获取选课所需的secretVal参数，搜索成功后即可开始选课
        </el-alert>
      </div>

      <!-- 搜索结果展示 -->
      <div v-if="searchResult" class="search-results">
        <el-divider content-position="left">
          <el-icon><Document /></el-icon>
          搜索结果
        </el-divider>

        <div v-if="searchResult.has_results && searchResult.courses.length > 0">
          <el-card
            v-for="(course, index) in searchResult.courses.slice(0, 3)"
            :key="index"
            class="course-item slide-in"
            shadow="hover"
          >
            <div class="course-content">
              <div class="course-main">
                <h4 class="course-name">
                  <el-icon><Reading /></el-icon>
                  {{ course.KCM || "未知课程" }}
                </h4>
                <div class="course-details">
                  <el-descriptions :column="2" size="small">
                    <el-descriptions-item label="授课教师">
                      <el-tag type="primary" size="small">
                        {{ course.JSXM || course.SKJS || "未知教师" }}
                      </el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="课程ID">
                      <el-text type="info" size="small">
                        {{ course.JXBID || course.classId || "未知" }}
                      </el-text>
                    </el-descriptions-item>
                    <el-descriptions-item label="选课情况">
                      <el-space>
                        <el-tag type="success" size="small">
                          {{
                            course.numberOfSelected || course.YXRS || 0
                          }}
                          人已选
                        </el-tag>
                        <el-tag type="info" size="small">
                          {{ course.classCapacity || course.KRL || 0 }} 人容量
                        </el-tag>
                      </el-space>
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
              </div>

              <div class="course-status">
                <el-alert
                  v-if="hasSecretVal"
                  title="选课密钥已获取"
                  type="success"
                  :closable="false"
                  show-icon
                >
                  <template #default>
                    <p>✅ 可以开始选课</p>
                  </template>
                </el-alert>
                <el-alert
                  v-else
                  title="未获取选课密钥"
                  type="warning"
                  :closable="false"
                  show-icon
                >
                  <template #default>
                    <p>⚠️ 无法选课</p>
                  </template>
                </el-alert>
              </div>
            </div>
          </el-card>

          <div v-if="searchResult.courses.length > 3" class="more-results">
            <el-text type="info">
              还有 {{ searchResult.courses.length - 3 }} 门课程未显示...
            </el-text>
          </div>
        </div>

        <el-empty v-else description="未找到匹配的课程">
          <el-text type="info"> 请尝试使用更精确的课程名称关键词 </el-text>
        </el-empty>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from "vue";
import { ElMessage } from "element-plus";
import { Search, Document, Reading } from "@element-plus/icons-vue";
import { searchCourseAPI } from "@/utils/api";

// 组件属性
const props = defineProps({
  sessionId: {
    type: String,
    required: true,
  },
});

// 定义事件
const emit = defineEmits(["search-success", "search-error"]);

// 响应式数据
const isSearching = ref(false);
const searchResult = ref(null);

const searchForm = reactive({
  keyword: "",
});

// 计算属性
const hasSecretVal = computed(() => {
  return (
    searchResult.value &&
    searchResult.value.secret_val &&
    searchResult.value.secret_val.length > 0
  );
});

// 处理搜索
const handleSearch = async () => {
  if (!searchForm.keyword.trim()) {
    ElMessage.warning("请输入搜索关键词");
    return;
  }

  isSearching.value = true;

  try {
    ElMessage.info({
      message: `🔍 开始搜索课程: "${searchForm.keyword}"`,
      duration: 2000,
    });

    const response = await searchCourseAPI({
      session_id: props.sessionId,
      keyword: searchForm.keyword,
    });

    if (response.success) {
      searchResult.value = response.data;

      ElMessage.success({
        message: `✅ 搜索完成，找到 ${response.data.courses.length} 门课程`,
        duration: 3000,
      });

      emit("search-success", response.data);
    } else {
      searchResult.value = null;
      emit("search-error", response.message);
    }
  } catch (error) {
    console.error("搜索异常:", error);
    searchResult.value = null;
    emit("search-error", error.message);
  } finally {
    isSearching.value = false;
  }
};

// 暴露方法给父组件
defineExpose({
  clearResults: () => {
    searchResult.value = null;
    searchForm.keyword = "";
  },
});
</script>

<style lang="scss" scoped>
.course-search {
  margin-bottom: 20px;

  .search-card {
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

  .search-form {
    margin-bottom: 16px;
  }

  .search-tips {
    margin-bottom: 20px;
  }

  .search-results {
    .course-item {
      margin-bottom: 16px;

      .course-content {
        display: flex;
        gap: 20px;
        align-items: flex-start;

        .course-main {
          flex: 1;

          .course-name {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 0 0 12px 0;
            color: var(--el-text-color-primary);
            font-size: 1.1rem;
            font-weight: 600;
          }

          .course-details {
            :deep(.el-descriptions__body) {
              background: transparent;
            }
          }
        }

        .course-status {
          flex-shrink: 0;
          width: 200px;

          :deep(.el-alert) {
            --el-alert-padding: 12px;

            .el-alert__content {
              font-size: 0.85rem;

              p {
                margin: 0;
              }
            }
          }
        }
      }
    }

    .more-results {
      text-align: center;
      padding: 10px;
      border-top: 1px solid var(--el-border-color-light);
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .course-search .search-results .course-item .course-content {
    flex-direction: column;

    .course-status {
      width: 100%;
    }
  }
}
</style>
