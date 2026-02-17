import docker
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Claude Code Workshop")

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = docker.from_env()

# 定义请求数据结构
class TaskRequest(BaseModel):
    project_name: str
    prompt: str

# 1. 根路由：返回前端页面
@app.get("/")
async def read_index():
    if os.path.exists("index.html"):
        return FileResponse('index.html')
    return {"error": "index.html not found. Please make sure it's in the same directory."}

# 2. 核心路由：运行 Claude Code
@app.post("/run-claude")
async def run_claude_task(request: TaskRequest):
    # 项目存储在 stonelee 的主目录下
    base_path = f"/home/stonelee/projects/{request.project_name}"
    
    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)

    # 环境变量配置 (从宿主机获取，保持安全性)
    env_vars = {
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
        "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
        "ANTHROPIC_AUTH_TOKEN": os.getenv("OPENROUTER_API_KEY"),
        "ANTHROPIC_API_KEY": "" # 必须为空以启用 OpenRouter 路由
    }

    if not env_vars["OPENROUTER_API_KEY"]:
        raise HTTPException(status_code=500, detail="Missing OPENROUTER_API_KEY in environment")

    try:
        # 启动容器执行任务
        container_output = client.containers.run(
            image="claude-executor",
            command=f'--dangerously-skip-permissions -p "{request.prompt}"',
            volumes={base_path: {'bind': '/app', 'mode': 'rw'}},
            environment=env_vars,
            working_dir="/app",
            detach=False,
            stdout=True,
            stderr=True,
            remove=True,
            user=f"{os.getuid()}:{os.getgid()}" # 以当前用户身份运行，避免产生 root 权限文件
        )
        
        return {"status": "success", "log": container_output.decode('utf-8')}
    
    except Exception as e:
        return {"status": "error", "log": str(e)}

if __name__ == "__main__":
    import uvicorn
    # 监听 0.0.0.0 确保外网可以访问，端口 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
