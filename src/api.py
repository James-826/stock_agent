"""FastAPI 后端：把 Agent Loop 暴露为 API。

前端通过 HTTP 请求调用这个 API，
后端执行 Agent Loop，返回结果。

对应 Phase 4 的 Runtime 层：FastAPI 作为 Web 服务器。
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from .agent.loop import AgentLoop
from .session.store import create_session, write_message, read_session

# 加载 .env 文件
load_dotenv()

app = FastAPI(title="Stock Agent API", version="0.1.0")

# CORS 配置：允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 Agent 实例
agent = None


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str
    session_id: str


@app.on_event("startup")
async def startup():
    """启动时初始化 Agent"""
    global agent
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    base_url = os.environ.get("BASE_URL")
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    
    if not api_key:
        raise ValueError("请设置环境变量 ANTHROPIC_API_KEY")
    
    agent = AgentLoop(api_key=api_key, model=model, base_url=base_url)
    print(f"Agent 初始化完成: model={model}, base_url={base_url}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求
    
    前端发送：{"message": "茅台现在多少钱"}
    后端返回：{"response": "茅台现在的价格是...", "session_id": "..."}
    """
    global agent
    
    # 获取或创建 session
    session_id = request.session_id or create_session()
    
    # 记录用户消息
    write_message(session_id, {"role": "user", "content": request.message})
    
    try:
        # 执行 Agent Loop
        response = await agent.run(request.message)
        
        # 记录 Agent 回答
        write_message(session_id, {"role": "assistant", "content": response})
        
        return ChatResponse(response=response, session_id=session_id)
    except Exception as e:
        error_msg = f"处理出错: {str(e)}"
        write_message(session_id, {"role": "system", "content": error_msg})
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """获取会话历史"""
    messages = read_session(session_id)
    return {"session_id": session_id, "messages": messages}


@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok", "agent_initialized": agent is not None}
