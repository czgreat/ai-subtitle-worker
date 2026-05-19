# AI Subtitle Worker

[English](README.md) | [中文](README.zh-CN.md)

AI Subtitle Worker is a self-hosted worker for downloading media URLs, extracting audio, transcribing speech, and rendering subtitle/document outputs. It is designed as an automation-friendly HTTP service that can also be used from other bots or internal tools.


## AI-assisted development

This public release was prepared with Codex using GPT-5.4 and GPT-5.5 assistance. The code, documentation, and release cleanup were reviewed for public sharing, but the project is community-maintained and is not an official OpenAI product.


## Features

- `yt-dlp` based download pipeline
- `ffmpeg` audio extraction
- faster-whisper transcription
- Output formats: plain text, Markdown, DOCX, script Markdown, JSON
- Optional webhook callback after job completion
- Download stall detection and conservative concurrency controls
- Docker deployment with a simple data directory

## Responsible Use

Only download and process media you own or are allowed to process. Some websites prohibit automated downloads or redistribution.

## Quick Start

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

The service listens on `8090` by default in the example compose file.

## Configuration

Key environment variables:

- `WEBHOOK_BEARER_TOKEN`
- `WHISPER_MODEL`
- `WHISPER_DEVICE`
- `WHISPER_COMPUTE_TYPE`
- `YTDLP_PROXY`
- `YTDLP_COOKIES_FILE`
- `NEWAPI_BASE_URL` and `NEWAPI_API_KEY` for optional LLM post-processing

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m compileall app tests
```

## License

MIT

