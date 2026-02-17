# Claude Code Workshop

基于 Docker 的 Claude Code 自动化编程平台。通过 Web 界面提交自然语言需求，后端在隔离的 Docker 容器中运行 Claude Code 完成代码生成，结果写入指定项目目录。

## 架构

```
浏览器 (index.html)
  │
  │  POST /run-claude { project_name, prompt }
  ▼
FastAPI 后端 (main.py :8000)
  │
  │  docker run claude-executor -p --dangerously-skip-permissions "<prompt>"
  ▼
Docker 容器 (claude-executor)
  │  挂载 ~/projects/<project_name> → /app
  │  通过 OpenRouter API 调用 Claude
  ▼
生成的代码写入 ~/projects/<project_name>/
```

## 项目结构

```
claude-workshop/
├── main.py        # FastAPI 后端，负责启动 Docker 容器执行 Claude Code
├── index.html     # 前端页面，提供项目名和需求输入
└── Dockerfile     # claude-executor 镜像定义（Node 20 + Claude Code CLI）
```

## 前置条件

- Docker
- Python 3 + pip
- OpenRouter API Key

## 快速开始

### 1. 构建 Docker 镜像

```bash
docker build -t claude-executor .
```

### 2. 设置环境变量

```bash
export OPENROUTER_API_KEY="sk-or-v1-xxxx"
```

### 3. 安装依赖并启动

```bash
pip install fastapi uvicorn docker
python main.py
```

访问 http://localhost:8000 即可使用。

## API

### POST /run-claude

请求：

```json
{
  "project_name": "my-app",
  "prompt": "创建一个 python 文件，叫 1.py，内容是 print hello world"
}
```

响应（成功）：

```json
{
  "status": "success",
  "log": "Claude Code 的执行日志..."
}
```

响应（失败）：

```json
{
  "status": "error",
  "log": "错误信息...",
  "exit_code": 1
}
```

## 关键设计说明

| 要点 | 说明 |
|------|------|
| 隔离执行 | 每次任务在独立 Docker 容器中运行，容器执行完毕后自动清理 |
| 非 root 运行 | 容器以宿主机当前用户 UID/GID 运行，生成文件权限与宿主机一致 |
| HOME=/tmp | 非 root 用户在容器内无 home 目录，需设置 `HOME=/tmp` 否则 Claude Code 会静默失败 |
| -p 模式 | 使用 `claude -p` 非交互模式执行，单次输出后退出 |
| OpenRouter 代理 | 通过设置 `ANTHROPIC_BASE_URL` 和 `ANTHROPIC_AUTH_TOKEN` 走 OpenRouter 转发请求 |
