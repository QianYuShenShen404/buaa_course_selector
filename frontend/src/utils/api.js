import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加请求头，如token等
    return config
  },
  (error) => {
    console.error('请求拦截器错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API请求错误:', error)
    
    let errorMessage = '网络请求失败'
    
    if (error.response) {
      // 服务器返回错误状态码
      switch (error.response.status) {
        case 401:
          errorMessage = '认证失败，请重新登录'
          break
        case 403:
          errorMessage = '权限不足'
          break
        case 404:
          errorMessage = 'API接口不存在'
          break
        case 500:
          errorMessage = '服务器内部错误'
          break
        default:
          errorMessage = error.response.data?.detail || error.response.data?.message || '请求失败'
      }
    } else if (error.request) {
      // 网络错误
      errorMessage = '网络连接失败，请检查网络状态'
    } else {
      // 其他错误
      errorMessage = error.message || '未知错误'
    }
    
    ElMessage.error(errorMessage)
    return Promise.reject(new Error(errorMessage))
  }
)

// API方法定义

/**
 * 用户登录
 * @param {Object} data - 登录数据 {username, password}
 * @returns {Promise}
 */
export const loginAPI = (data) => {
  return api.post('/login', data)
}

/**
 * 搜索课程
 * @param {Object} data - 搜索数据 {session_id, keyword}
 * @returns {Promise}
 */
export const searchCourseAPI = (data) => {
  return api.post('/search', data)
}

/**
 * 选课操作
 * @param {Object} data - 选课数据 {session_id, auto_retry}
 * @returns {Promise}
 */
export const selectCourseAPI = (data) => {
  return api.post('/select', data)
}

/**
 * 停止自动选课
 * @param {string} sessionId - 会话ID
 * @returns {Promise}
 */
export const stopAutoSelectAPI = (sessionId) => {
  return api.post(`/stop-select/${sessionId}`)
}

/**
 * 获取系统状态
 * @param {string} sessionId - 会话ID
 * @returns {Promise}
 */
export const getStatusAPI = (sessionId) => {
  return api.get(`/status/${sessionId}`)
}

/**
 * 用户登出
 * @param {string} sessionId - 会话ID
 * @returns {Promise}
 */
export const logoutAPI = (sessionId) => {
  return api.delete(`/logout/${sessionId}`)
}

/**
 * 关闭Web应用
 * @returns {Promise}
 */
export const shutdownAPI = () => {
  return api.post('/shutdown')
}

export default api