# RAGFlow 节点流式输出与 Thinking 透传 - 部署指南

## 概述

本文档说明如何从 GitHub 拉取修改的代码，并部署到现有的 RAGFlow 服务中。

## 前置条件

- 已安装 Docker 和 Docker Compose
- 现有 RAGFlow 服务正在运行（基于官方镜像 `infiniflow/ragflow:v0.19.0`）
- 网络可访问 GitHub

## 部署步骤

### 1. 停止现有服务

```bash
cd /path/to/your/ragflow/deployment
docker-compose down
```

### 2. 创建代码目录并拉取修改

```bash
# 创建代码目录
mkdir -p ragflow-code && cd ragflow-code

# 初始化 git 仓库
git init

# 添加远程仓库
git remote add origin git@github.com:Kirito-10/ragflow-stream.git

# 拉取代码（只拉取最新提交）
git fetch origin main --depth=1

# 检出修改的三个目录
git checkout origin/main -- agent/ api/ rag/

# 返回上一级目录
cd ..
```

### 3. 修改 docker-compose.yml

添加 volume 挂载配置：

```yaml
services:
  ragflow:
    image: infiniflow/ragflow:v0.19.0
    volumes:
      # 挂载修改的代码目录
      - ./ragflow-code/agent:/ragflow/agent
      - ./ragflow-code/api:/ragflow/api
      - ./ragflow-code/rag:/ragflow/rag
      # 原有配置不变
      - ./ragflow-logs:/ragflow/logs
      - ./service_conf.yaml.template:/ragflow/conf/service_conf.yaml.template
    ports:
      - 9380:9380
    env_file: .env
    depends_on:
      - mysql
      - redis
      - minio
```

### 4. 启动服务

```bash
docker-compose up -d
```

### 5. 验证部署

```bash
# 查看容器日志
docker-compose logs -f ragflow

# 测试 API
curl -X POST http://localhost:9380/api/v1/agents/{agent_id}/completions \
  -H "Content-Type: application/json" \
  -d '{"question": "测试问题", "stream": true}'
```

## 目录结构

```
your-deployment/
├── ragflow-code/           # 从 GitHub 拉取的修改代码
│   ├── agent/              # 节点流式输出修改
│   ├── api/                # SSE 事件发送修改
│   └── rag/                # Thinking 透传修改
├── .env                    # 环境变量配置
├── docker-compose.yml      # Docker Compose 配置
├── init.sql                # MySQL 初始化脚本
└── service_conf.yaml.template  # 服务配置模板
```

## 完整 docker-compose.yml 示例

```yaml
services:
  ragflow:
    image: infiniflow/ragflow:v0.19.0
    container_name: ragflow-server
    ports:
      - ${SVR_HTTP_PORT}:9380
      - 80:80
      - 443:443
    volumes:
      # 挂载修改的代码
      - ./ragflow-code/agent:/ragflow/agent
      - ./ragflow-code/api:/ragflow/api
      - ./ragflow-code/rag:/ragflow/rag
      # 其他必要挂载
      - ./ragflow-logs:/ragflow/logs
      - ./service_conf.yaml.template:/ragflow/conf/service_conf.yaml.template
      - ./entrypoint.sh:/ragflow/entrypoint.sh
      - ./nginx/ragflow.conf:/etc/nginx/conf.d/ragflow.conf
      - ./nginx/proxy.conf:/etc/nginx/proxy.conf
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    env_file: .env
    environment:
      - TZ=${TIMEZONE}
      - HF_ENDPOINT=${HF_ENDPOINT}
    depends_on:
      mysql:
        condition: service_healthy
    networks:
      - ragflow
    restart: on-failure

  mysql:
    image: mysql:8.0.39
    container_name: ragflow-mysql
    env_file: .env
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_PASSWORD}
      - TZ=${TIMEZONE}
    command:
      --max_connections=1000
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_unicode_ci
      --default-authentication-plugin=mysql_native_password
      --tls_version="TLSv1.2,TLSv1.3"
      --init-file /data/application/init.sql
    ports:
      - ${MYSQL_PORT}:3306
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/data/application/init.sql
    networks:
      - ragflow
    healthcheck:
      test: ["CMD", "mysqladmin" ,"ping", "-uroot", "-p${MYSQL_PASSWORD}"]
      interval: 10s
      timeout: 10s
      retries: 3
    restart: on-failure

  redis:
    image: valkey/valkey:8
    container_name: ragflow-redis
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 128mb --maxmemory-policy allkeys-lru
    env_file: .env
    ports:
      - ${REDIS_PORT}:6379
    volumes:
      - redis_data:/data
    networks:
      - ragflow
    restart: on-failure

  minio:
    image: quay.io/minio/minio:RELEASE.2023-12-20T01-00-02Z
    container_name: ragflow-minio
    command: server --console-address ":9001" /data
    ports:
      - ${MINIO_PORT}:9000
      - ${MINIO_CONSOLE_PORT}:9001
    env_file: .env
    environment:
      - MINIO_ROOT_USER=${MINIO_USER}
      - MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}
      - TZ=${TIMEZONE}
    volumes:
      - minio_data:/data
    networks:
      - ragflow
    restart: on-failure

volumes:
  mysql_data:
    driver: local
  redis_data:
    driver: local
  minio_data:
    driver: local

networks:
  ragflow:
    driver: bridge
```

## 更新代码

当 GitHub 上有新的修改时，更新步骤：

```bash
cd ragflow-code

# 拉取最新代码
git fetch origin main

# 更新三个目录
git checkout origin/main -- agent/ api/ rag/

# 返回上一级并重启容器
cd ..
docker-compose restart ragflow
```

## 验证功能

### 测试节点流式输出

```python
import requests
import json

response = requests.post(
    "http://localhost:9380/api/v1/agents/{agent_id}/completions",
    json={"question": "什么是 RAGFlow？", "stream": True},
    stream=True
)

for chunk in response.iter_lines():
    if chunk:
        data = json.loads(chunk.decode("utf-8"))
        print(data)
```

### 预期输出

```json
{"code": 0, "data": {"type": "node_completed", "node_id": "Begin", "output": {...}}}
{"code": 0, "data": {"type": "node_completed", "node_id": "Generate", "output": {"content": "...", "reasoning_content": "<think>...</think>"}}}
{"code": 0, "data": {"type": "node_completed", "node_id": "Answer", "output": {...}}}
{"code": 0, "data": true}
```

## 故障排除

### 1. 容器启动失败

```bash
# 查看详细日志
docker-compose logs ragflow
```

### 2. 代码修改未生效

```bash
# 进入容器检查文件是否挂载成功
docker exec -it ragflow-server ls -la /ragflow/agent/
```

### 3. API 无响应

```bash
# 检查端口是否正常
curl http://localhost:9380/api/health
```

## 注意事项

1. **版本兼容性**：确保使用的是 RAGFlow v0.19.0 镜像
2. **配置文件**：`.env` 文件需要包含正确的数据库密码等配置
3. **网络权限**：确保服务器可以访问 GitHub
4. **数据备份**：部署前建议备份现有数据

## 总结

通过以上步骤，你可以：
1. 从 GitHub 拉取修改的代码
2. 通过 Docker Volume 挂载到现有服务
3. 实现节点流式输出和 Thinking 透传功能
4. 轻松更新代码

这种方式无需重新构建镜像，直接使用官方镜像运行，只替换修改的代码文件。