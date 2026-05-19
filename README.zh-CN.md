# AI Subtitle Worker / AI 字幕处理服务

[English](README.md) | [中文](README.zh-CN.md)

AI Subtitle Worker 是一个自托管任务服务，用于下载媒体链接、抽取音频、语音转写并生成字幕/文档输出。它面向自动化场景，可以被机器人、内部工具或其他 HTTP 客户端调用。


## AI 辅助开发说明

这个公开版由 Codex 在 GPT-5.4 / GPT-5.5 辅助下整理完成。代码、文档和公开前清理已按公开仓库标准处理，但本项目不是 OpenAI 官方产品。


## 功能

- 基于 `yt-dlp` 的下载流程
- 使用 `ffmpeg` 抽取音频
- 使用 faster-whisper 做语音转写
- 输出纯文本、Markdown、DOCX、脚本 Markdown、JSON
- 任务完成后可选 webhook 回调
- 下载卡顿检测和保守并发控制
- Docker 部署，使用简单的数据目录

## 合规使用

只处理你拥有或有权处理的媒体内容。部分网站禁止自动下载或二次分发。

## 快速开始

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

示例 compose 默认监听 `8090`。

## 配置

核心环境变量：

- `WEBHOOK_BEARER_TOKEN`
- `WHISPER_MODEL`
- `WHISPER_DEVICE`
- `WHISPER_COMPUTE_TYPE`
- `YTDLP_PROXY`
- `YTDLP_COOKIES_FILE`
- `NEWAPI_BASE_URL` 和 `NEWAPI_API_KEY`，用于可选 LLM 后处理

## 开发

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m compileall app tests
```

## License

MIT

## 更多文档

- [部署说明](docs/DEPLOYMENT.md)
- [AI 接手说明](docs/AI_HANDOFF.md)
- [路线图](docs/ROADMAP.md)

