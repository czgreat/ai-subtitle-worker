# AI Subtitle Worker / AI 字幕处理服务

[![CI](https://github.com/czgreat/ai-subtitle-worker/actions/workflows/ci.yml/badge.svg)](https://github.com/czgreat/ai-subtitle-worker/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**语言：** [English](README.md) | 中文

自托管字幕处理 worker，用于下载被允许处理的媒体、提取音频、转写语音并生成字幕/文档产物。

## 概览

AI Subtitle Worker 在 yt-dlp、ffmpeg、faster-whisper、产物渲染和可选回调之上提供 HTTP 服务。

## 主要功能

- 基于 yt-dlp 的下载流程
- 通过 ffmpeg 提取音频
- faster-whisper 转写，支持 CPU/GPU 配置
- 输出文本、Markdown、DOCX、脚本 Markdown、JSON 和可下载产物
- 可选 webhook 回调和可选 LLM 后处理

## 适合谁

- 需要自动处理授权媒体转文本任务的用户
- 需要 HTTP 转写 worker 的机器人开发者
- 评估 CPU/GPU 转写部署方案的开发者

## 不适合

- 下载或处理未授权媒体
- 未补自有鉴权和限速就公开部署
- 未按宿主机调优就运行长期 GPU 任务

## 当前公开版状态

已经可以使用：

- 可用 Docker 在 8090 端口运行 worker
- 可通过 dispatch API 提交任务
- 可下载生成的产物
- 小规模部署可使用 CPU 默认配置

需要你在本地补全：

- 只处理你拥有或获授权处理的媒体
- 手工部署时需要安装 ffmpeg
- 只有目标网站允许时才配置 cookies/proxy
- 如启用后处理，提供自己的 LLM endpoint 和 API key

## 快速开始

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

如果在 Windows PowerShell 使用 Python 虚拟环境，请用 `.venv\Scripts\Activate.ps1`，不要用 `. .venv/bin/activate`。

## Docker 部署

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
curl http://localhost:8090/health
```

## 手工部署

- 安装 Python 3.11、ffmpeg，以及 faster-whisper 需要的系统依赖。
- 创建虚拟环境并执行 `pip install -e .`。
- 按 `.env.example` 设置环境变量。
- 执行 `uvicorn app.main:app --host 0.0.0.0 --port 8090`。

## 配置说明

- `DATA_DIR`：持久化产物目录
- `PUBLIC_BASE_URL`：回调和产物链接使用的公开地址
- `WEBHOOK_BEARER_TOKEN`：受保护 dispatch 使用的共享密钥
- `WHISPER_MODEL`、`WHISPER_DEVICE`、`WHISPER_COMPUTE_TYPE`：转写运行配置
- `NEWAPI_BASE_URL`、`NEWAPI_API_KEY`、`NEWAPI_MODEL`：可选 LLM 后处理配置

## API 概览

- `GET /health` 健康检查
- `GET /api/jobs` 查看任务列表
- `GET /api/jobs/{job_id}` 查看任务详情
- `POST /api/wechat/dispatch` 创建任务
- `GET /artifacts/{job_id}/{file_name}` 下载产物

## 验证命令

```bash
python -m compileall app tests
curl http://localhost:8090/health
```

## 仓库结构

| 路径 | 说明 |
|---|---|
| `app/main.py` | FastAPI 应用、任务生命周期和 HTTP 路由 |
| `app/commands.py` | 命令构造和执行辅助逻辑 |
| `app/renderers.py` | 输出渲染器 |
| `app/settings.py` | 基于环境变量的设置 |
| `tests/` | 命令、配置和任务行为测试 |

## 更多文档

| 主题 | 中文 | English |
|---|---|---|
| 部署 | [docs/DEPLOYMENT.zh-CN.md](docs/DEPLOYMENT.zh-CN.md) | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| 使用/API 示例 | [docs/USAGE_EXAMPLES.zh-CN.md](docs/USAGE_EXAMPLES.zh-CN.md) | [docs/USAGE_EXAMPLES.md](docs/USAGE_EXAMPLES.md) |
| 截图 | [docs/SCREENSHOTS.zh-CN.md](docs/SCREENSHOTS.zh-CN.md) | [docs/SCREENSHOTS.md](docs/SCREENSHOTS.md) |
| AI 接手 | [docs/AI_HANDOFF.zh-CN.md](docs/AI_HANDOFF.zh-CN.md) | [docs/AI_HANDOFF.md](docs/AI_HANDOFF.md) |
| 路线图 | [docs/ROADMAP.zh-CN.md](docs/ROADMAP.zh-CN.md) | [docs/ROADMAP.md](docs/ROADMAP.md) |
| 更新日志 | [CHANGELOG.zh-CN.md](CHANGELOG.zh-CN.md) | [CHANGELOG.md](CHANGELOG.md) |

## AI 辅助开发说明

这个公开版由 Codex 使用 GPT-5.4 和 GPT-5.5 辅助整理完成。源码、文档和公开前清理都经过面向公开分享的复核，但本项目是社区项目，不是 OpenAI 官方产品。

适合继续交给 AI coding assistant 的任务：

- 补充 dispatch payload 的 OpenAPI 示例
- 增加队列持久化测试
- 改进失败分类和重试行为
- 补充 GPU 宿主部署示例

## 隐私和密钥

不要提交真实 `.env`、API key、webhook secret、cookies、私人媒体、生产数据库、日志、生成产物或个人数据。请从示例配置开始，把私有值保存在 Git 之外。

## License

MIT
