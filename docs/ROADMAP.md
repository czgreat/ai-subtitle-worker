# Roadmap

**Language:** English | [中文](ROADMAP.zh-CN.md)

This roadmap describes the public repository state for `ai-subtitle-worker`. It separates what is ready to use from what each user should complete in their own environment.

## Complete Enough To Use

- Download/transcribe/render pipeline
- Artifact storage
- Webhook callback support

## Needs Local Completion

- Add your own authentication policy before exposing publicly
- Choose CPU/GPU runtime settings for your host
- Tune downloader options for allowed sites

## Suggested Improvements

- Add OpenAPI examples for dispatch payloads
- Add queue persistence tests
- Improve failure classification and retry behavior
- Add deployment recipes for GPU hosts

## Documentation Still Worth Adding

- Screenshots or short screen recordings using non-private demo data.
- A fuller API example page for common requests and responses.
- Backup and restore notes for any persistent data path.
- A troubleshooting page based on real public issues once users start deploying it.

## Maintenance Notes

- Keep public examples generic.
- Keep English and Chinese instructions aligned.
- Prefer small issues and pull requests so AI-assisted contributors can work safely.
- Re-run sensitive-data scans before publishing new releases.
