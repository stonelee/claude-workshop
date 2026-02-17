import docker
from docker.errors import ContainerError
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
        "ANTHROPIC_API_KEY": "", # 必须为空以启用 OpenRouter 路由
        "HOME": "/tmp" # 容器内非 root 用户没有 home 目录，设置为 /tmp 避免 Claude Code 静默失败
    }

    if not env_vars["OPENROUTER_API_KEY"]:
        raise HTTPException(status_code=500, detail="Missing OPENROUTER_API_KEY in environment")

    try:
        # 启动容器执行任务：使用分离模式以便流式读取日志
        print(f"Starting container for project: {request.project_name}")
        
        # 1. 启动容器 (detach=True)
        container = client.containers.run(
            image="claude-executor",
            # 使用列表格式传递命令参数，避免 shell 解析问题
            command=["-p", "--dangerously-skip-permissions", request.prompt],
            volumes={base_path: {'bind': '/app', 'mode': 'rw'}},
            environment=env_vars,
            working_dir="/app",
            detach=True,
            tty=False, # 关闭 TTY，避免缓冲问题
            user=f"{os.getuid()}:{os.getgid()}", # 以当前用户身份运行
            # 不使用缓冲
            stdout=True,
            stderr=True
        )

        # 2. 等待容器完成
        print(f"Container {container.id[:12]} started. Waiting for completion...")
        try:
            result = container.wait()
            exit_code = result.get('StatusCode', 0)

            # 3. 获取完整日志（stdout + stderr）
            final_log = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
            print(final_log)  # 打印到服务器控制台
            print(f"\nContainer finished with exit code: {exit_code}")

            if exit_code != 0:
                 print(f"\nContainer finished with error code: {exit_code}")
                 return {
                     "status": "error",
                     "log": final_log,
                     "exit_code": exit_code
                 }

            print("\nContainer finished successfully")
            return {"status": "success", "log": final_log}

        finally:
            # 确保容器被清理
            try:
                container.remove()
            except:
                pass

    except ContainerError as e:
        # 捕获容器退出非0的情况，提取 stderr/stdout
        # e.stderr 可能是 bytes
        error_msg = e.stderr.decode('utf-8', errors='replace') if e.stderr else ""
        if not error_msg and e.container:
             # 有时候 output 在 stdout 里
             try:
                 error_msg = client.containers.get(e.container.id).logs().decode('utf-8', errors='replace')
             except:
                 pass
        
        # 如果以上都没获取到，尝试 e.args
        if not error_msg:
             error_msg = str(e)

        return {"status": "error", "log": f"Container Exit Error: {error_msg}"}

    except Exception as e:
        return {"status": "error", "log": str(e)}

if __name__ == "__main__":
    import uvicorn
    # 监听 0.0.0.0 确保外网可以访问，端口 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
