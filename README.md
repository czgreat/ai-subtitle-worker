# AI Subtitle Worker

[![CI](https://github.com/czgreat/ai-subtitle-worker/actions/workflows/ci.yml/badge.svg)](https://github.com/czgreat/ai-subtitle-worker/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Language:** English | [中文](README.zh-CN.md)

Self-hosted worker for downloading allowed media, extracting audio, transcribing speech, and producing subtitle/document artifacts.

## Overview

AI Subtitle Worker exposes a small HTTP service around yt-dlp, ffmpeg, faster-whisper, artifact rendering, and optional callback delivery.

## Key Features

- Download pipeline based on yt-dlp
- Audio extraction through ffmpeg
- faster-whisper transcription with CPU/GPU configuration
- Outputs text, Markdown, DOCX, script Markdown, JSON, and downloadable artifacts
- Optional webhook callback and optional LLM post-processing

## Current Public Release

Ready to use:

- Run the worker in Docker on port 8090
- Submit jobs through the dispatch API
- Download generated artifacts
- Use CPU defaults for small deployments

You must provide locally:

- Only process media you own or have permission to process
- Install ffmpeg if running manually
- Provide cookies/proxy only if the target site permits it
- Provide your own optional LLM endpoint and API key if post-processing is enabled

## Quick Start

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

For Python projects on Windows, activate the virtual environment with `.venv\Scripts\Activate.ps1` instead of `. .venv/bin/activate`.

## Docker Deployment

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
curl http://localhost:8090/health
```

## Manual Deployment

- Install Python 3.11, ffmpeg, and system packages needed by faster-whisper.
- Create a virtual environment and run `pip install -e .`.
- Set variables from `.env.example`.
- Run `uvicorn app.main:app --host 0.0.0.0 --port 8090`.

## Configuration

- `DATA_DIR`: persistent artifacts directory
- `PUBLIC_BASE_URL`: URL used in callbacks and artifact links
- `WEBHOOK_BEARER_TOKEN`: shared secret for protected dispatches
- `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`: transcription runtime
- `NEWAPI_BASE_URL`, `NEWAPI_API_KEY`, `NEWAPI_MODEL`: optional LLM post-processing

## API Surface

- `GET /health` for health checks
- `GET /api/jobs` to list jobs
- `GET /api/jobs/{job_id}` for job detail
- `POST /api/wechat/dispatch` to create a job
- `GET /artifacts/{job_id}/{file_name}` to download artifacts

## Validation

```bash
python -m compileall app tests
curl http://localhost:8090/health
```

## Repository Layout

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI app, job lifecycle, and HTTP routes |
| `app/commands.py` | Command construction and execution helpers |
| `app/renderers.py` | Output renderers |
| `app/settings.py` | Environment-based settings |
| `tests/` | Unit tests for command, config, and job behavior |

## Documentation

| Topic | English | Chinese |
|---|---|---|
| Deployment | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | [docs/DEPLOYMENT.zh-CN.md](docs/DEPLOYMENT.zh-CN.md) |
| AI handoff | [docs/AI_HANDOFF.md](docs/AI_HANDOFF.md) | [docs/AI_HANDOFF.zh-CN.md](docs/AI_HANDOFF.zh-CN.md) |
| Roadmap | [docs/ROADMAP.md](docs/ROADMAP.md) | [docs/ROADMAP.zh-CN.md](docs/ROADMAP.zh-CN.md) |

## AI-Assisted Development

This public release was prepared with Codex using GPT-5.4 and GPT-5.5 assistance. The source code, docs, and public-release cleanup were reviewed for public sharing, but this is a community project and not an official OpenAI product.

Good next tasks for an AI coding assistant:

- Add OpenAPI examples for dispatch payloads
- Add queue persistence tests
- Improve failure classification and retry behavior
- Add deployment recipes for GPU hosts

## Privacy and Secrets

Do not commit real `.env` files, API keys, webhook secrets, cookies, private media, production databases, logs, generated artifacts, or personal data. Start from the example config files and keep private values outside Git.

## License

MIT
