# 部署说明

**语言：** [English](DEPLOYMENT.md) | 中文

本文说明如何在本地、Docker 或手工服务模式下运行 `ai-subtitle-worker`。默认你已经 clone 了 GitHub 仓库，并在仓库根目录操作。

## 已经可以使用

- 可用 Docker 在 8090 端口运行 worker
- 可通过 dispatch API 提交任务
- 可下载生成的产物
- 小规模部署可使用 CPU 默认配置

## 你需要自己提供

- 只处理你拥有或获授权处理的媒体
- 手工部署时需要安装 ffmpeg
- 只有目标网站允许时才配置 cookies/proxy
- 如启用后处理，提供自己的 LLM endpoint 和 API key

## 本地开发

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

如果命令里出现 `. .venv/bin/activate`，Windows PowerShell 下请改用 `.venv\Scripts\Activate.ps1`。

## Docker 部署

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
curl http://localhost:8090/health
```

运行 Docker 前，请先检查所有 volume 映射和 `.env`。示例 compose 文件只提供通用起点，需要按你的主机路径和端口修改。

## 手工部署

- 安装 Python 3.11、ffmpeg，以及 faster-whisper 需要的系统依赖。
- 创建虚拟环境并执行 `pip install -e .`。
- 按 `.env.example` 设置环境变量。
- 执行 `uvicorn app.main:app --host 0.0.0.0 --port 8090`。

## 配置检查清单

- `DATA_DIR`：持久化产物目录
- `PUBLIC_BASE_URL`：回调和产物链接使用的公开地址
- `WEBHOOK_BEARER_TOKEN`：受保护 dispatch 使用的共享密钥
- `WHISPER_MODEL`、`WHISPER_DEVICE`、`WHISPER_COMPUTE_TYPE`：转写运行配置
- `NEWAPI_BASE_URL`、`NEWAPI_API_KEY`、`NEWAPI_MODEL`：可选 LLM 后处理配置

## 验证命令

```bash
python -m compileall app tests
curl http://localhost:8090/health
```

## 生产检查清单

- 真实使用前替换所有占位密钥。
- 私有配置、生成数据、日志、上传文件和产物不要放进 Git。
- 如果服务会被其他设备访问，请放到启用 HTTPS 的反向代理后面。
- 私有 API 暴露到 localhost 以外前，请先增加鉴权。
- 为数据库、状态目录、上传文件和生成产物配置备份。
- 处理安全问题前先阅读 `SECURITY.md`。

## 排障建议

- 先复查 `.env` 和 volume 路径；多数部署问题来自路径或权限。
- 用 `README.md` 里列出的健康检查接口区分进程启动问题和业务问题。
- 修改部署基础设施前，先跑验证命令。
- 让 AI assistant 帮忙时，提供操作系统、运行时版本、完整命令、去敏日志和部署模式。
