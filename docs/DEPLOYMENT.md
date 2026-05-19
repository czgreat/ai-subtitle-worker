# Deployment Guide

**Language:** English | [中文](DEPLOYMENT.zh-CN.md)

This guide explains how to run `ai-subtitle-worker` locally, in Docker, or with a manual service setup. It assumes you cloned the GitHub repository and are working from the repository root.

## What Is Already Usable

- Run the worker in Docker on port 8090
- Submit jobs through the dispatch API
- Download generated artifacts
- Use CPU defaults for small deployments

## What You Must Provide

- Only process media you own or have permission to process
- Install ffmpeg if running manually
- Provide cookies/proxy only if the target site permits it
- Provide your own optional LLM endpoint and API key if post-processing is enabled

## Local Development

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

If the command uses `. .venv/bin/activate`, use `.venv\Scripts\Activate.ps1` on Windows PowerShell.

## Docker Deployment

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
curl http://localhost:8090/health
```

Before running Docker, review every bind mount and every value in `.env`. Example compose files are intentionally generic and should be adjusted to your host paths and ports.

## Manual Deployment

- Install Python 3.11, ffmpeg, and system packages needed by faster-whisper.
- Create a virtual environment and run `pip install -e .`.
- Set variables from `.env.example`.
- Run `uvicorn app.main:app --host 0.0.0.0 --port 8090`.

## Configuration Checklist

- `DATA_DIR`: persistent artifacts directory
- `PUBLIC_BASE_URL`: URL used in callbacks and artifact links
- `WEBHOOK_BEARER_TOKEN`: shared secret for protected dispatches
- `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`: transcription runtime
- `NEWAPI_BASE_URL`, `NEWAPI_API_KEY`, `NEWAPI_MODEL`: optional LLM post-processing

## Validation Checks

```bash
python -m compileall app tests
curl http://localhost:8090/health
```

## Production Checklist

- Replace all placeholder secrets before real use.
- Keep private config, generated data, logs, uploaded media, and generated artifacts outside Git.
- Put the service behind a reverse proxy with HTTPS if it is reachable from other devices.
- Add authentication before exposing private APIs beyond localhost.
- Configure backups for any database, state directory, uploaded files, and generated artifacts.
- Read `SECURITY.md` before reporting or triaging security issues.

## Troubleshooting

- Re-check `.env` and volume paths first; most deployment failures are path or permission issues.
- Use the health endpoint listed in `README.md` to separate process startup issues from application behavior.
- Run the validation commands before changing deployment infrastructure.
- When asking an AI assistant for help, include OS, runtime versions, exact command, sanitized logs, and deployment mode.
