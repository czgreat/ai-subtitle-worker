# Deployment Guide

Self-hosted worker for downloading media links, extracting audio, transcribing speech, and rendering subtitle/document outputs.

## What is already usable

- HTTP worker service is included
- yt-dlp, ffmpeg, and faster-whisper pipeline is represented in code
- Webhook callback is optional
- Docker example is included

## What you must provide

- Enough CPU/RAM for chosen whisper model
- ffmpeg and yt-dlp in runtime
- Optional cookies file for authenticated downloads
- Optional LLM provider for post-processing

## Local development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8090
```

## Validation checks

```bash
python -m compileall app tests
```

## Docker deployment

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

## Manual deployment

Install Python dependencies, ensure `ffmpeg` is on PATH, set a bearer token in `.env`, and run `uvicorn app.main:app --host 0.0.0.0 --port 8090` behind your preferred reverse proxy.

## Production checklist

- Keep `.env` private and never commit it.
- Replace all placeholder secrets before exposing the service.
- Mount runtime data outside the repository.
- Put the service behind HTTPS if it is reachable from other machines.
- Back up persistent data before upgrades.
- Review logs after the first startup.

