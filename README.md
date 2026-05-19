# AI Subtitle Worker

A self-hosted worker for downloading video/audio URLs, extracting audio, generating transcripts with faster-whisper, and rendering subtitle/document outputs.

## Features

- `yt-dlp` download pipeline
- `ffmpeg` audio extraction
- faster-whisper transcription
- Output formats: `txt`, `md`, `docx`, `script.md`, and `json`
- Optional webhook callback for automation systems
- Docker-friendly runtime layout

## Quick Start

```bash
cp .env.example .env
cp docker-compose.example.yml docker-compose.yml
docker compose up --build
```

Submit jobs through the HTTP API after configuring your bearer token.

## Responsible Use

Only download and process media that you own or are allowed to process. Some platforms restrict automated downloads.
