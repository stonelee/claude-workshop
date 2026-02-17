# 使用 Node 镜像作为基础
FROM node:20-slim

# 安装基础开发工具：git, python, sudo
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# 全局安装 Claude Code
RUN npm install -g @anthropic-ai/claude-code

# 设置工作目录
WORKDIR /app

# 容器启动时默认运行 claude
# 注意：我们在这里不写死参数，参数由后端 API 动态传入
ENTRYPOINT ["claude"]
