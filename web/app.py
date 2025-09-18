"""
北航选课系统 Web应用主入口
基于FastAPI框架提供RESTful API和WebSocket双向实时通信服务
整合了原web_app.py和web_api.py的功能
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import asyncio
import json
from typing import Optional, Dict, List
import uuid
import sys
import os
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from src.course_service import CourseService
from src.logger import get_logger

# FastAPI应用实例
app = FastAPI(
    title="北航选课系统",
    description="基于FastAPI的自动化选课Web界面",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 静态文件服务
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "static")), name="static")

# 模板引擎
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

# 全局用户会话存储
user_sessions: Dict[str, CourseService] = {}

# 后台任务管理
background_tasks: Dict[str, asyncio.Task] = {}

# 日志器
logger = get_logger("web_app")

# WebSocket连接管理器
class ConnectionManager:
    """WebSocket连接管理器，处理实时通信"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket连接建立: {session_id}")

    def disconnect(self, session_id: str):
        """断开WebSocket连接"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket连接断开: {session_id}")

    async def send_personal_message(self, message: str, session_id: str):
        """发送个人消息"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"发送WebSocket消息失败: {e}")
                self.disconnect(session_id)

    async def send_status_update(self, session_id: str, status: dict):
        """发送状态更新"""
        message = json.dumps({
            "type": "status_update",
            "data": status
        }, ensure_ascii=False)
        await self.send_personal_message(message, session_id)

    async def send_progress_update(self, session_id: str, progress: dict):
        """发送进度更新"""
        message = json.dumps({
            "type": "progress_update",
            "data": progress
        }, ensure_ascii=False)
        await self.send_personal_message(message, session_id)

# WebSocket管理器实例
manager = ConnectionManager()

# 数据模型
class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str

class SearchRequest(BaseModel):
    """搜索请求模型"""
    session_id: str
    keyword: Optional[str] = ""

class SelectCourseRequest(BaseModel):
    """选课请求模型"""
    session_id: str
    course_name: Optional[str] = ""
    auto_retry: bool = False
    max_attempts: int = 50

class ApiResponse(BaseModel):
    """API响应模型"""
    success: bool
    message: str
    data: Optional[dict] = None

# 页面路由
@app.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request):
    """返回主页面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "active_sessions": len(user_sessions),
        "websocket_connections": len(manager.active_connections)
    }

# API路由
@app.post("/api/login", response_model=ApiResponse)
async def api_login(request: LoginRequest):
    """用户登录接口"""
    try:
        session_id = str(uuid.uuid4())
        logger.info(f"用户尝试登录: {request.username}")
        
        # 创建CourseService实例
        course_service = CourseService(
            username=request.username,
            password=request.password,
            config_file=str(PROJECT_ROOT / "config.json")
        )
        
        # 执行登录
        login_success = course_service.login()
        
        if login_success:
            # 存储会话
            user_sessions[session_id] = course_service
            
            # 建立认证服务和课程服务的关联，供自动选课停止检查使用
            if course_service.auth_service:
                course_service.auth_service.course_service = course_service
            
            # 获取认证信息
            auth_service = course_service.auth_service
            batch_id = auth_service.get_batch_id() if auth_service else "未知"
            token = auth_service.get_token() if auth_service else "未知"
            token_display = token[:20] + "..." if token and len(token) > 20 else token
            
            logger.info(f"用户登录成功: {request.username}, 会话ID: {session_id}")
            
            return ApiResponse(
                success=True,
                message="登录成功！",
                data={
                    "session_id": session_id,
                    "batch_id": batch_id,
                    "token": token_display,
                    "username": request.username
                }
            )
        else:
            logger.error(f"用户登录失败: {request.username}")
            raise HTTPException(status_code=401, detail="登录失败，请检查学号和密码")
            
    except ValueError as e:
        logger.error(f"登录参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"登录过程出错: {e}")
        raise HTTPException(status_code=500, detail=f"登录过程出错: {str(e)}")

@app.post("/api/search", response_model=ApiResponse)
async def api_search(request: SearchRequest):
    """搜索课程接口"""
    try:
        if request.session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="会话无效，请重新登录")
        
        course_service = user_sessions[request.session_id]
        logger.info(f"搜索课程: {request.keyword}, 会话: {request.session_id}")
        
        # 执行搜索
        search_result = course_service.search_course(request.keyword or "")
        
        if search_result.get('success', True):
            # 获取搜索结果详情
            course_search = course_service.course_search
            
            search_data = {
                "has_results": course_search.has_search_results() if course_search else False,
                "course_count": len(course_search.search_results) if course_search else 0,
                "secret_val": course_search.get_secret_val() if course_search else None,
                "classid": course_search.get_classid() if course_search else None,
                "courses": course_search.search_results[:5] if course_search else []
            }
            
            logger.info(f"搜索完成: 找到{search_data['course_count']}门课程")
            
            return ApiResponse(
                success=True,
                message=f"搜索完成，找到 {search_data['course_count']} 门课程",
                data=search_data
            )
        else:
            error_msg = search_result.get('error', '搜索失败')
            logger.error(f"搜索失败: {error_msg}")
            return ApiResponse(
                success=False,
                message=error_msg
            )
        
    except Exception as e:
        logger.error(f"搜索过程出错: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@app.post("/api/select", response_model=ApiResponse)
async def api_select(request: SelectCourseRequest):
    """选课接口（异步版本）"""
    try:
        if request.session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="会话无效，请重新登录")
        
        course_service = user_sessions[request.session_id]
        logger.info(f"开始选课: 自动重试={request.auto_retry}")
        
        if request.auto_retry:
            # 自动重试选课模式 - 使用异步后台任务
            logger.info(f"启动异步自动选课模式")
            
            # 检查是否已有后台任务在运行
            if request.session_id in background_tasks:
                existing_task = background_tasks[request.session_id]
                if not existing_task.done():
                    return ApiResponse(
                        success=False,
                        message="已有自动选课任务在运行中"
                    )
            
            # 清除停止标志（如果之前有设置）
            course_service.clear_stop_auto_select_flag()
            
            # 创建异步后台任务
            async def run_auto_select_task():
                try:
                    result = await course_service.auto_select_course_async(
                        retry_interval=1,
                        websocket_manager=manager,
                        session_id=request.session_id
                    )
                    
                    # 任务完成后发送状态更新
                    if result['success']:
                        await manager.send_status_update(request.session_id, {
                            "type": "task_completed",
                            "message": "✅ 自动选课任务成功完成！"
                        })
                    else:
                        await manager.send_status_update(request.session_id, {
                            "type": "task_completed", 
                            "message": f"❌ 自动选课任务失败: {result.get('error', '未知错误')}"
                        })
                        
                finally:
                    # 清理任务引用
                    if request.session_id in background_tasks:
                        del background_tasks[request.session_id]
                    # 清除停止标志
                    course_service.clear_stop_auto_select_flag()
            
            task = asyncio.create_task(run_auto_select_task())
            
            # 存储任务引用
            background_tasks[request.session_id] = task
            
            # 立即返回，不等待任务完成
            return ApiResponse(
                success=True,
                message="异步自动选课已启动，请通过日志监控进度",
                data={"method": "async_auto", "task_id": request.session_id}
            )
        else:
            # 执行单次选课
            select_result = course_service.select_course()
            
            if select_result['success']:
                logger.info("单次选课成功")
                return ApiResponse(
                    success=True,
                    message="选课成功！",
                    data={"method": "single"}
                )
            else:
                error_msg = select_result.get('error', '选课失败')
                logger.error(f"单次选课失败: {error_msg}")
                return ApiResponse(
                    success=False,
                    message=f"选课失败: {error_msg}"
                )
            
    except Exception as e:
        logger.error(f"选课过程出错: {e}")
        raise HTTPException(status_code=500, detail=f"选课失败: {str(e)}")

@app.post("/api/stop-select/{session_id}", response_model=ApiResponse)
async def api_stop_auto_select(session_id: str):
    """停止自动选课接口"""
    try:
        if session_id not in user_sessions:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        course_service = user_sessions[session_id]
        logger.info(f"用户请求停止自动选课: {session_id}")
        
        # 设置停止标志
        course_service.set_stop_auto_select_flag()
        
        # 棆消后台任务（如果存在）
        if session_id in background_tasks:
            task = background_tasks[session_id]
            if not task.done():
                task.cancel()  # 取消任务
                logger.info(f"已取消后台任务: {session_id}")
            del background_tasks[session_id]
        
        # 通过WebSocket通知前端
        await manager.send_status_update(session_id, {
            "type": "stop_auto_select_requested",
            "message": "正在停止自动选课，请稍候..."
        })
        
        # 延迟发送停止完成通知，让前端恢复按钮状态
        async def notify_stop_completed():
            await asyncio.sleep(1)  # 等待一下让停止操作生效
            await manager.send_status_update(session_id, {
                "type": "auto_select_stopped",
                "message": "✅ 自动选课已停止，可以重新开始"
            })
        
        # 创建通知任务
        asyncio.create_task(notify_stop_completed())
        
        logger.info(f"自动选课停止标志已设置: {session_id}")
        
        return ApiResponse(
            success=True,
            message="停止请求已提交，等待当前选课请求完成",
            data={"session_id": session_id}
        )
        
    except Exception as e:
        logger.error(f"停止自动选课失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止失败: {str(e)}")

@app.get("/api/status/{session_id}")
async def api_get_status(session_id: str):
    """获取会话状态"""
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    course_service = user_sessions[session_id]
    
    # 构建状态信息
    status = {
        "authenticated": course_service.auth_service is not None,
        "search_ready": course_service.course_search is not None,
        "selector_ready": course_service.course_selector is not None,
        "has_search_results": (
            course_service.course_search.has_search_results() 
            if course_service.course_search else False
        )
    }
    
    return ApiResponse(
        success=True,
        message="状态获取成功",
        data=status
    )

@app.post("/api/shutdown", response_model=ApiResponse)
async def api_shutdown():
    """关闭整个Web应用"""
    logger.info("收到关闭Web应用请求")
    
    try:
        # 清理所有后台任务
        for session_id in list(background_tasks.keys()):
            task = background_tasks[session_id]
            if not task.done():
                task.cancel()
                logger.info(f"关闭时取消后台任务: {session_id}")
            del background_tasks[session_id]
        
        # 清理所有会话
        for session_id in list(user_sessions.keys()):
            course_service = user_sessions[session_id]
            if hasattr(course_service, 'cleanup'):
                course_service.cleanup()
            del user_sessions[session_id]
        
        # 断开所有WebSocket连接
        for session_id in list(manager.active_connections.keys()):
            manager.disconnect(session_id)
        
        logger.info("清理完成，准备关闭服务器")
        
        # 延迟关闭服务器
        import asyncio
        asyncio.create_task(shutdown_server())
        
        return ApiResponse(
            success=True,
            message="Web应用正在关闭...",
            data={"status": "shutting_down"}
        )
        
    except Exception as e:
        logger.error(f"关闭过程出错: {e}")
        # 即使出错也要强制关闭
        import asyncio
        asyncio.create_task(shutdown_server())
        raise HTTPException(status_code=500, detail=f"关闭失败: {str(e)}")

async def shutdown_server():
    """延迟关闭服务器"""
    await asyncio.sleep(1)  # 给响应一点时间返回
    logger.info("强制终止程序")
    import os
    os._exit(0)  # 强制终止程序

@app.delete("/api/logout/{session_id}")
async def api_logout(session_id: str):
    """登出接口"""
    if session_id in user_sessions:
        # 清理后台任务
        if session_id in background_tasks:
            task = background_tasks[session_id]
            if not task.done():
                task.cancel()
                logger.info(f"登出时取消后台任务: {session_id}")
            del background_tasks[session_id]
        
        # 清理资源
        course_service = user_sessions[session_id]
        if hasattr(course_service, 'cleanup'):
            course_service.cleanup()
        
        # 删除会话
        del user_sessions[session_id]
        manager.disconnect(session_id)
        
        logger.info(f"用户登出: 会话 {session_id}")
        return {"message": "登出成功"}
    else:
        raise HTTPException(status_code=404, detail="会话不存在")

# WebSocket路由
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket连接，用于实时推送选课状态"""
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # 保持连接，等待消息
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await manager.send_personal_message("pong", session_id)
                elif message.get("type") == "get_status":
                    # 返回当前状态
                    if session_id in user_sessions:
                        service = user_sessions[session_id]
                        status = {
                            "authenticated": service.auth_service is not None,
                            "search_ready": service.course_search is not None,
                            "selector_ready": service.course_selector is not None
                        }
                        await manager.send_status_update(session_id, status)
                        
            except json.JSONDecodeError:
                logger.error(f"WebSocket消息格式错误: {data}")
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(session_id)

# 异常处理
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """404错误处理"""
    if request.url.path.startswith("/api/"):
        return {"error": "API端点不存在", "status_code": 404}
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """500错误处理"""
    logger.error(f"内部服务器错误: {exc}")
    if request.url.path.startswith("/api/"):
        return {"error": "内部服务器错误", "status_code": 500}
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 启动北航选课系统Web服务...")
    print("=" * 50)
    print("🌐 访问地址: http://127.0.0.1:8000")
    print("📚 API文档: http://127.0.0.1:8000/api/docs") 
    print("⚠️ 按 Ctrl+C 停止服务")
    print("=" * 50)
    
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
