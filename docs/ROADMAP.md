# Roadmap

This public release is a cleaned, source-focused baseline. It is intended to be usable by developers, but each deployment still needs local configuration.

## Complete enough to use

- HTTP worker service is included
- yt-dlp, ffmpeg, and faster-whisper pipeline is represented in code
- Webhook callback is optional
- Docker example is included

## Needs local completion

- Enough CPU/RAM for chosen whisper model
- ffmpeg and yt-dlp in runtime
- Optional cookies file for authenticated downloads
- Optional LLM provider for post-processing

## Suggested improvements

- Add a minimal web upload page
- Add task queue persistence for production
- Adapt webhook payloads for another chat platform
- Add GPU runtime documentation

## Documentation still worth adding

- Real screenshots or short demo videos.
- A known-good production deployment example for a generic Linux host.
- Troubleshooting notes collected from real user deployments.

