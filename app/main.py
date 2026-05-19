from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import mimetypes
import os
from pathlib import Path
import re
import traceback
from typing import Any
from urllib.parse import quote
import uuid

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
import httpx
from pydantic import BaseModel

from .commands import build_menu_text, mode_label, parse_dispatch_command
from .renderers import (
    TranscriptParagraph,
    TranscriptSegment,
    merge_segments,
    write_transcript_bundle,
)
from .settings import Settings


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def trim_text(value: str, limit: int = 800) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def sanitize_name(value: str, fallback: str = "artifact.bin") -> str:
    raw = Path(str(value or "").strip()).name or fallback
    return raw.replace("/", "_").replace("\\", "_").replace("\x00", "_")[:180] or fallback


RATE_RE = re.compile(r"\bat\s+([0-9.]+)\s*([KMGTP]?i?B/s)\b", re.IGNORECASE)


def parse_transfer_rate_bytes(line: str) -> float | None:
    match = RATE_RE.search(str(line or ""))
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2).lower()
    multipliers = {
        "b/s": 1,
        "kib/s": 1024,
        "kb/s": 1000,
        "mib/s": 1024**2,
        "mb/s": 1000**2,
        "gib/s": 1024**3,
        "gb/s": 1000**3,
        "tib/s": 1024**4,
        "tb/s": 1000**4,
        "pib/s": 1024**5,
        "pb/s": 1000**5,
    }
    multiplier = multipliers.get(unit)
    if multiplier is None:
        return None
    return value * multiplier


def line_indicates_slow_download(line: str, floor_bytes: int) -> bool:
    lowered = str(line or "").lower()
    if "[download]" not in lowered:
        return False

    if any(marker in lowered for marker in ("0.00b/s", "0.0b/s", "0 b/s", "unknown speed", "n/a")):
        return True

    rate = parse_transfer_rate_bytes(lowered)
    if rate is None:
        return False
    return rate < max(1, floor_bytes)


PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
    "YTDLP_PROXY",
)


def build_subprocess_env(*, clear_proxy_env: bool) -> dict[str, str]:
    child_env = os.environ.copy()
    if clear_proxy_env:
        for key in PROXY_ENV_KEYS:
            child_env.pop(key, None)
    return child_env


def json_load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class DispatchPayload(BaseModel):
    correlationId: str = ""
    integrationId: str = ""
    integrationAlias: str = ""
    source: str = ""
    botId: str = ""
    targetId: str = ""
    rawText: str = ""
    commandText: str = ""
    receivedAt: str = ""
    replyWebhookUrl: str = ""


@dataclass
class SessionState:
    mode: str | None = None
    output_formats: list[str] = field(default_factory=lambda: ["txt"])
    updated_at: str = field(default_factory=now_iso)


@dataclass
class JobArtifact:
    name: str
    path: str
    url: str
    kind: str
    size_bytes: int
    content_type: str


@dataclass
class JobRecord:
    id: str
    correlation_id: str
    integration_id: str
    integration_alias: str
    bot_id: str
    target_id: str
    raw_text: str
    command_text: str
    action: str
    source_url: str
    status: str
    created_at: str
    updated_at: str
    received_at: str
    reply_webhook_url: str
    request_base_url: str
    output_formats: list[str] = field(default_factory=list)
    message: str = ""
    error: str = ""
    files: list[JobArtifact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DownloadResult:
    media_paths: list[Path]
    title: str
    webpage_url: str
    uploader: str
    duration_seconds: float
    extractor: str
    info_json_path: str = ""


def build_audio_file_base_name(title: str) -> str:
    return sanitize_name(f"{title} 音频", "audio")


class VideoWorkerService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jobs: dict[str, JobRecord] = {}
        self.sessions: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
        self._tasks: set[asyncio.Task] = set()
        self._whisper_model = None
        self._whisper_lock = asyncio.Lock()

    async def startup(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.jobs_dir.mkdir(parents=True, exist_ok=True)
        await self._load_state()

    async def shutdown(self) -> None:
        await self._persist_jobs()
        await self._persist_sessions()

    async def _load_state(self) -> None:
        jobs_payload = json_load(self.settings.jobs_file, [])
        sessions_payload = json_load(self.settings.sessions_file, {})
        self.jobs = {}
        for item in jobs_payload if isinstance(jobs_payload, list) else []:
            try:
                files = [
                    JobArtifact(**artifact)
                    for artifact in item.get("files", [])
                    if isinstance(artifact, dict)
                ]
                self.jobs[item["id"]] = JobRecord(
                    id=item["id"],
                    correlation_id=item.get("correlation_id", ""),
                    integration_id=item.get("integration_id", ""),
                    integration_alias=item.get("integration_alias", ""),
                    bot_id=item.get("bot_id", ""),
                    target_id=item.get("target_id", ""),
                    raw_text=item.get("raw_text", ""),
                    command_text=item.get("command_text", ""),
                    action=item.get("action", ""),
                    source_url=item.get("source_url", ""),
                    status=item.get("status", ""),
                    created_at=item.get("created_at", now_iso()),
                    updated_at=item.get("updated_at", now_iso()),
                    received_at=item.get("received_at", ""),
                    reply_webhook_url=item.get("reply_webhook_url", ""),
                    request_base_url=item.get("request_base_url", ""),
                    output_formats=list(item.get("output_formats", ["txt"] if item.get("action") == "subtitle" else [])),
                    message=item.get("message", ""),
                    error=item.get("error", ""),
                    files=files,
                    metadata=item.get("metadata", {}) if isinstance(item.get("metadata", {}), dict) else {},
                )
            except Exception:
                continue

        self.sessions = {}
        if isinstance(sessions_payload, dict):
            for key, value in sessions_payload.items():
                if not isinstance(value, dict):
                    continue
                self.sessions[str(key)] = SessionState(
                    mode=value.get("mode"),
                    output_formats=list(value.get("output_formats", ["txt"])),
                    updated_at=value.get("updated_at", now_iso()),
                )

    async def _persist_jobs(self) -> None:
        payload = [asdict(item) for item in sorted(self.jobs.values(), key=lambda job: job.created_at)]
        await asyncio.to_thread(json_dump, self.settings.jobs_file, payload)

    async def _persist_sessions(self) -> None:
        payload = {key: asdict(value) for key, value in self.sessions.items()}
        await asyncio.to_thread(json_dump, self.settings.sessions_file, payload)

    def list_jobs(self, target_id: str = "", limit: int = 20) -> list[JobRecord]:
        target = str(target_id or "").strip()
        items = sorted(self.jobs.values(), key=lambda job: job.created_at, reverse=True)
        if target:
            items = [item for item in items if item.target_id == target]
        return items[:limit]

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.jobs.get(job_id)

    def get_artifact(self, job_id: str, file_name: str) -> JobArtifact | None:
        job = self.jobs.get(job_id)
        if not job:
            return None
        normalized = sanitize_name(file_name)
        for artifact in job.files:
            if sanitize_name(artifact.name) == normalized:
                return artifact
        return None

    async def handle_dispatch(self, payload: DispatchPayload, base_url: str) -> dict[str, Any]:
        target_id = payload.targetId.strip()
        if not target_id:
            return {
                "replyText": "缺少 targetId，无法建立视频会话。",
                "sessionAction": "clear",
            }

        current_session = self.sessions.get(target_id)
        current_mode = current_session.mode if current_session else None
        command_text = (payload.commandText or "").strip()
        raw_text = (payload.rawText or "").strip()
        parsed = parse_dispatch_command(
            command_text=command_text,
            raw_text=raw_text,
            current_mode=current_mode,
        )

        if parsed.intent == "menu":
            await self._touch_session(target_id, current_mode)
            return {
                "replyText": build_menu_text(current_mode),
                "sessionAction": "activate",
            }

        if parsed.intent == "set_mode":
            await self._set_session_preferences(
                target_id,
                mode=parsed.mode,
                output_formats=list(parsed.output_formats),
            )
            formats_label = ", ".join(parsed.output_formats)
            return {
                "replyText": f"已切换到{mode_label(parsed.mode)}模式，输出格式：{formats_label}。直接发送视频链接即可。",
                "sessionAction": "activate",
            }

        if parsed.intent == "clear_session":
            await self._clear_session(target_id)
            return {
                "replyText": "已退出视频菜单。下次发送“视频”可重新进入。",
                "sessionAction": "clear",
            }

        if parsed.intent == "list_jobs":
            await self._touch_session(target_id, current_mode)
            return {
                "replyText": self._build_recent_jobs_text(target_id),
                "sessionAction": "activate",
            }

        if parsed.intent == "need_mode":
            await self._touch_session(target_id, current_mode)
            return {
                "replyText": "先发送“下载”或“字幕”选择模式，再贴链接。\n\n" + build_menu_text(current_mode),
                "sessionAction": "activate",
            }

        if parsed.intent == "unknown":
            await self._touch_session(target_id, current_mode)
            return {
                "replyText": "没识别出命令。\n\n" + build_menu_text(current_mode),
                "sessionAction": "activate",
            }

        if parsed.intent != "queue_job" or not parsed.mode or not parsed.url:
            raise HTTPException(status_code=400, detail="不支持的命令")

        effective_output_formats = list(parsed.output_formats)
        if (
            parsed.mode == "subtitle"
            and current_session
            and raw_text == parsed.url
            and command_text == parsed.url
            and current_session.output_formats
        ):
            effective_output_formats = list(current_session.output_formats)

        job = JobRecord(
            id=uuid.uuid4().hex,
            correlation_id=payload.correlationId.strip(),
            integration_id=payload.integrationId.strip(),
            integration_alias=payload.integrationAlias.strip(),
            bot_id=payload.botId.strip(),
            target_id=target_id,
            raw_text=raw_text,
            command_text=command_text,
            action=parsed.mode,
            source_url=parsed.url,
            status="queued",
            created_at=now_iso(),
            updated_at=now_iso(),
            received_at=payload.receivedAt.strip(),
            reply_webhook_url=(payload.replyWebhookUrl or "").strip(),
            request_base_url=base_url.rstrip("/"),
            output_formats=effective_output_formats if parsed.mode == "subtitle" else [],
            message="已入队，等待执行。",
        )

        async with self._lock:
            self.jobs[job.id] = job
            await self._persist_jobs()
            self.sessions[target_id] = SessionState(
                mode=parsed.mode,
                output_formats=effective_output_formats if parsed.mode == "subtitle" else ["txt"],
                updated_at=now_iso(),
            )
            await self._persist_sessions()

        self._spawn_job(job.id)

        action_label = mode_label(parsed.mode)
        intro = (
            "已接收字幕任务，开始下载并识别。"
            if parsed.mode == "subtitle"
            else "已接收下载任务，开始下载视频。"
        )
        if parsed.mode == "audio":
            intro = "已接收音频提取任务，开始处理。"
        formats_line = ""
        if parsed.mode == "subtitle":
            formats_line = f"输出：{', '.join(effective_output_formats)}\n"
        return {
            "replyText": (
                f"{intro}\n"
                f"任务号：{job.id[:8]}\n"
                f"模式：{action_label}\n"
                f"{formats_line}"
                f"链接：{parsed.url}\n"
                f"完成后会自动回传到当前微信会话。"
            ),
            "sessionAction": "activate",
            "jobId": job.id,
        }

    async def _touch_session(self, target_id: str, mode: str | None) -> None:
        async with self._lock:
            previous_formats = self.sessions.get(target_id).output_formats if target_id in self.sessions else ["txt"]
            self.sessions[target_id] = SessionState(
                mode=mode,
                output_formats=previous_formats,
                updated_at=now_iso(),
            )
            await self._persist_sessions()

    async def _set_session_preferences(
        self,
        target_id: str,
        *,
        mode: str | None,
        output_formats: list[str] | tuple[str, ...],
    ) -> None:
        async with self._lock:
            self.sessions[target_id] = SessionState(
                mode=mode,
                output_formats=list(output_formats),
                updated_at=now_iso(),
            )
            await self._persist_sessions()

    async def _clear_session(self, target_id: str) -> None:
        async with self._lock:
            self.sessions.pop(target_id, None)
            await self._persist_sessions()

    def _spawn_job(self, job_id: str) -> None:
        task = asyncio.create_task(self._process_job(job_id))
        self._tasks.add(task)

        def _cleanup(done_task: asyncio.Task) -> None:
            self._tasks.discard(done_task)
            if done_task.cancelled():
                return
            error = done_task.exception()
            if error:
                traceback.print_exception(error)

        task.add_done_callback(_cleanup)

    async def _update_job(self, job_id: str, **patch: Any) -> JobRecord:
        async with self._lock:
            job = self.jobs[job_id]
            for key, value in patch.items():
                setattr(job, key, value)
            job.updated_at = now_iso()
            await self._persist_jobs()
            return job

    async def _process_job(self, job_id: str) -> None:
        async with self._semaphore:
            job = await self._update_job(job_id, status="running", message="正在下载媒体文件。")
            try:
                job_dir = self.settings.jobs_dir / job.id
                download_dir = job_dir / "downloads"
                artifact_dir = job_dir / "artifacts"
                work_dir = job_dir / "work"
                download_dir.mkdir(parents=True, exist_ok=True)
                artifact_dir.mkdir(parents=True, exist_ok=True)
                work_dir.mkdir(parents=True, exist_ok=True)

                download_result = await self._download_media(job.source_url, download_dir)
                primary_media = download_result.media_paths[0]
                files: list[JobArtifact] = []
                if job.action == "download" or self.settings.send_video_file_for_subtitle:
                    files.append(self._build_artifact(job, primary_media, "video"))

                metadata = {
                    "title": download_result.title,
                    "webpage_url": download_result.webpage_url or job.source_url,
                    "uploader": download_result.uploader,
                    "duration_seconds": download_result.duration_seconds,
                    "extractor": download_result.extractor,
                }

                if job.action == "subtitle":
                    await self._update_job(job_id, message="正在抽取音频并执行 AI 转写。")
                    audio_path = work_dir / "audio.wav"
                    await self._extract_audio(primary_media, audio_path)
                    transcript = await self._transcribe_audio(audio_path)
                    title = download_result.title or primary_media.stem
                    raw_paragraphs = merge_segments(transcript["segments"])
                    polished_paragraphs = await self._postprocess_transcript(
                        title=title,
                        source_url=download_result.webpage_url or job.source_url,
                        paragraphs=raw_paragraphs,
                    )
                    bundle = await asyncio.to_thread(
                        write_transcript_bundle,
                        artifact_dir,
                        title,
                        download_result.webpage_url or job.source_url,
                        transcript["language"],
                        transcript["duration_seconds"],
                        transcript["segments"],
                        paragraphs=polished_paragraphs,
                        output_formats=job.output_formats or ["txt"],
                    )
                    files.extend(self._build_artifact(job, path, "transcript") for path in bundle["paths"])
                    metadata.update(
                        {
                            "language": transcript["language"],
                            "segment_count": bundle["segment_count"],
                            "paragraph_count": bundle["paragraph_count"],
                            "output_formats": job.output_formats or ["txt"],
                            "postprocess_model": self.settings.newapi_model or "",
                            "postprocess_enabled": bool(self.settings.newapi_base_url and self.settings.newapi_api_key),
                        }
                    )
                elif job.action == "audio":
                    await self._update_job(job_id, message="正在提取音频并准备回传。")
                    audio_path = work_dir / "audio.mp3"
                    await self._extract_audio_mp3(primary_media, audio_path)
                    audio_parts = await self._prepare_audio_parts(
                        audio_path=audio_path,
                        output_dir=artifact_dir,
                        title=download_result.title or primary_media.stem,
                        duration_seconds=download_result.duration_seconds,
                    )
                    files.extend(self._build_artifact(job, path, "audio") for path in audio_parts)
                    metadata.update(
                        {
                            "audio_parts": len(audio_parts),
                            "audio_bitrate_kbps": self.settings.audio_export_bitrate_kbps,
                        }
                    )

                await self._update_job(
                    job_id,
                    status="completed",
                    message="任务完成。",
                    files=files,
                    metadata=metadata,
                )
                job = self.jobs[job_id]
                try:
                    await self._send_completion_replies(job)
                except Exception as reply_error:
                    await self._update_job(
                        job_id,
                        message=f"任务完成，但回传失败：{trim_text(reply_error, 300)}",
                    )
            except Exception as error:
                await self._update_job(
                    job_id,
                    status="failed",
                    message="任务失败。",
                    error=trim_text(error, 1200),
                )
                job = self.jobs[job_id]
                try:
                    await self._send_failure_reply(job)
                except Exception:
                    pass

    async def _download_media(self, url: str, download_dir: Path) -> DownloadResult:
        command = [
            self.settings.python_bin,
            "-m",
            "yt_dlp",
            "--no-playlist",
            "--newline",
            "--restrict-filenames",
            "--merge-output-format",
            "mp4",
            "--socket-timeout",
            "20",
            "--retries",
            "1",
            "--fragment-retries",
            "1",
            "--format",
            "bv*+ba/b/best",
            "--paths",
            str(download_dir),
            "--output",
            "%(title).120B [%(id)s].%(ext)s",
            "--write-info-json",
            "--print",
            "after_move:filepath",
            url,
        ]
        if self.settings.ytdlp_cookies_file:
            command[3:3] = ["--cookies", self.settings.ytdlp_cookies_file]
        stdout, stderr = await self._run_monitored_command(
            command,
            read_timeout_seconds=self.settings.download_read_timeout_seconds,
            slow_rate_floor_bytes=self.settings.download_speed_floor_bytes,
            slow_abort_seconds=self.settings.download_stall_abort_seconds,
            clear_proxy_env=True,
        )
        candidate_paths: list[Path] = []
        for line in stdout.splitlines():
            text = line.strip()
            if not text:
                continue
            path = Path(text)
            if path.exists() and path.is_file():
                candidate_paths.append(path)

        if not candidate_paths:
            candidate_paths = [
                path
                for path in sorted(download_dir.iterdir())
                if path.is_file() and not path.name.endswith(".info.json") and not path.name.endswith(".part")
            ]

        if not candidate_paths:
            raise RuntimeError(trim_text(stderr or stdout or "yt-dlp 未返回输出文件"))

        info_json_path = ""
        info_payload = {}
        info_candidates = sorted(download_dir.glob("*.info.json"))
        if info_candidates:
            info_json_path = str(info_candidates[0])
            info_payload = json_load(info_candidates[0], {})

        title = str(info_payload.get("title") or candidate_paths[0].stem)
        webpage_url = str(info_payload.get("webpage_url") or url)
        uploader = str(info_payload.get("uploader") or info_payload.get("channel") or "")
        duration_seconds = float(info_payload.get("duration") or 0.0)
        extractor = str(info_payload.get("extractor_key") or info_payload.get("extractor") or "")

        return DownloadResult(
            media_paths=candidate_paths,
            title=title,
            webpage_url=webpage_url,
            uploader=uploader,
            duration_seconds=duration_seconds,
            extractor=extractor,
            info_json_path=info_json_path,
        )

    async def _extract_audio(self, media_path: Path, audio_path: Path) -> None:
        command = [
            self.settings.ffmpeg_bin,
            "-y",
            "-i",
            str(media_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(audio_path),
        ]
        _stdout, stderr = await self._run_command(command)
        if not audio_path.exists():
            raise RuntimeError(trim_text(stderr or "ffmpeg 未生成音频文件"))

    async def _extract_audio_mp3(self, media_path: Path, audio_path: Path) -> None:
        command = [
            self.settings.ffmpeg_bin,
            "-y",
            "-i",
            str(media_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "22050",
            "-c:a",
            "libmp3lame",
            "-b:a",
            f"{self.settings.audio_export_bitrate_kbps}k",
            str(audio_path),
        ]
        _stdout, stderr = await self._run_command(command)
        if not audio_path.exists():
            raise RuntimeError(trim_text(stderr or "ffmpeg 未生成 mp3 音频文件"))

    async def _prepare_audio_parts(
        self,
        *,
        audio_path: Path,
        output_dir: Path,
        title: str,
        duration_seconds: float,
    ) -> list[Path]:
        max_bytes = self.settings.audio_chunk_max_bytes
        if audio_path.stat().st_size <= max_bytes:
            final_path = output_dir / f"{build_audio_file_base_name(title)}01.mp3"
            audio_path.replace(final_path)
            return [final_path]

        segment_dir = output_dir / "audio_parts"
        segment_dir.mkdir(parents=True, exist_ok=True)
        ratio = max_bytes / max(audio_path.stat().st_size, 1)
        segment_seconds = max(30, int(duration_seconds * ratio * 0.92))
        pattern = segment_dir / "part%02d.mp3"
        command = [
            self.settings.ffmpeg_bin,
            "-y",
            "-i",
            str(audio_path),
            "-f",
            "segment",
            "-segment_time",
            str(segment_seconds),
            "-reset_timestamps",
            "1",
            "-c",
            "copy",
            str(pattern),
        ]
        _stdout, stderr = await self._run_command(command)
        segment_files = sorted(segment_dir.glob("part*.mp3"))
        if not segment_files:
            raise RuntimeError(trim_text(stderr or "音频分段失败"))

        final_paths: list[Path] = []
        base_name = build_audio_file_base_name(title)
        for index, path in enumerate(segment_files, start=1):
            target = output_dir / f"{base_name}{index:02d}.mp3"
            path.replace(target)
            final_paths.append(target)

        return final_paths

    async def _transcribe_audio(self, audio_path: Path) -> dict[str, Any]:
        model = await self._get_whisper_model()

        def _transcribe() -> dict[str, Any]:
            segments_iter, info = model.transcribe(
                str(audio_path),
                beam_size=5,
                vad_filter=True,
                language=self.settings.whisper_language or None,
            )
            segments = [
                TranscriptSegment(
                    start=float(segment.start),
                    end=float(segment.end),
                    text=str(segment.text or "").strip(),
                )
                for segment in segments_iter
            ]
            return {
                "language": str(getattr(info, "language", "") or self.settings.whisper_language or ""),
                "duration_seconds": float(getattr(info, "duration", 0.0) or 0.0),
                "segments": segments,
            }

        return await asyncio.to_thread(_transcribe)

    async def _postprocess_transcript(
        self,
        *,
        title: str,
        source_url: str,
        paragraphs: list[TranscriptParagraph],
    ) -> list[TranscriptParagraph]:
        if not self.settings.newapi_base_url or not self.settings.newapi_api_key or not paragraphs:
            return paragraphs

        request_body = {
            "title": title,
            "source_url": source_url,
            "paragraphs": [
                {
                    "index": index,
                    "start": paragraph.start,
                    "end": paragraph.end,
                    "text": paragraph.text,
                }
                for index, paragraph in enumerate(paragraphs)
            ],
        }
        prompt = (
            "你是中文转写稿编辑。请对 ASR 草稿做保守纠错、标点恢复和段落优化，"
            "让文本读起来像自然中文口语稿件。"
            "不要编造事实，不要删除关键信息。"
            "保持段落顺序和段落数量不变。"
            "不要输出时间轴，不要输出编号。"
            "每段 text 内部允许用\\n\\n切成 1 到 2 个自然小段。"
            "整体风格应像适合阅读和转发的整理稿，而不是逐句字幕。"
            "输出严格 JSON：{\"paragraphs\":[{\"index\":0,\"text\":\"...\"}]}"
        )

        chat_payload = {
            "model": self.settings.newapi_model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(request_body, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 4096,
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.newapi_timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.newapi_base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.newapi_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=chat_payload,
                )
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                optimized = parsed.get("paragraphs", [])
        except Exception:
            return paragraphs

        updated: list[TranscriptParagraph] = []
        for original, item in zip(paragraphs, optimized):
            text = str(item.get("text", "")).strip()
            updated.append(
                TranscriptParagraph(
                    start=original.start,
                    end=original.end,
                    text=text or original.text,
                )
            )

        return updated if len(updated) == len(paragraphs) else paragraphs

    async def _get_whisper_model(self):
        async with self._whisper_lock:
            if self._whisper_model is None:
                from faster_whisper import WhisperModel

                self._whisper_model = WhisperModel(
                    self.settings.whisper_model,
                    device=self.settings.whisper_device,
                    compute_type=self.settings.whisper_compute_type,
                )
            return self._whisper_model

    async def _run_command(
        self,
        command: list[str],
        *,
        clear_proxy_env: bool = False,
    ) -> tuple[str, str]:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=build_subprocess_env(clear_proxy_env=clear_proxy_env),
        )
        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        if process.returncode != 0:
            raise RuntimeError(trim_text(stderr_text or stdout_text or f"命令执行失败: {' '.join(command)}"))
        return stdout_text, stderr_text

    async def _run_monitored_command(
        self,
        command: list[str],
        *,
        read_timeout_seconds: int,
        slow_rate_floor_bytes: int,
        slow_abort_seconds: int,
        clear_proxy_env: bool = False,
    ) -> tuple[str, str]:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=build_subprocess_env(clear_proxy_env=clear_proxy_env),
        )
        if process.stdout is None:
            raise RuntimeError("命令未产生可读输出")

        output_lines: list[str] = []
        first_download_line_seen = False
        slow_since: float | None = None

        while True:
            try:
                raw_line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=max(1, read_timeout_seconds),
                )
            except asyncio.TimeoutError:
                if first_download_line_seen and slow_since is not None:
                    elapsed = asyncio.get_running_loop().time() - slow_since
                    if elapsed >= slow_abort_seconds:
                        process.kill()
                        await process.wait()
                        raise RuntimeError(
                            f"下载速度持续低于 {slow_rate_floor_bytes} B/s 超过 {slow_abort_seconds}s，已中止"
                        )
                continue

            if not raw_line:
                break

            line = raw_line.decode("utf-8", errors="replace")
            output_lines.append(line)
            lowered = line.lower()

            if "[download]" in lowered:
                first_download_line_seen = True
                if line_indicates_slow_download(line, slow_rate_floor_bytes):
                    slow_since = slow_since or asyncio.get_running_loop().time()
                else:
                    slow_since = None
            elif any(marker in lowered for marker in ("merging formats", "destination:", "has already been downloaded")):
                slow_since = None

        return_code = await process.wait()
        stdout_text = "".join(output_lines)
        stderr_text = ""
        if return_code != 0:
            raise RuntimeError(trim_text(stdout_text or f"命令执行失败: {' '.join(command)}", 1200))
        return stdout_text, stderr_text

    def _artifact_base_url(self, job: JobRecord) -> str:
        return self.settings.public_base_url or job.request_base_url

    def _build_artifact(self, job: JobRecord, path: Path, kind: str) -> JobArtifact:
        resolved = path.resolve()
        media_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
        base_url = self._artifact_base_url(job).rstrip("/")
        url = f"{base_url}/artifacts/{job.id}/{quote(sanitize_name(resolved.name))}" if base_url else ""
        return JobArtifact(
            name=sanitize_name(resolved.name),
            path=str(resolved),
            url=url,
            kind=kind,
            size_bytes=resolved.stat().st_size,
            content_type=media_type,
        )

    def _build_recent_jobs_text(self, target_id: str) -> str:
        jobs = self.list_jobs(target_id=target_id, limit=5)
        if not jobs:
            return "最近没有视频任务。"
        lines = ["最近任务"]
        for job in jobs:
            lines.append(
                f"{job.id[:8]}  {mode_label(job.action)}  {job.status}  {job.source_url}"
            )
            if job.error:
                lines.append(f"错误：{trim_text(job.error, 160)}")
        return "\n".join(lines)

    async def _send_completion_replies(self, job: JobRecord) -> None:
        if not job.reply_webhook_url:
            return

        title = "字幕任务完成" if job.action == "subtitle" else "下载任务完成"
        if job.action == "audio":
            title = "音频已完成"
        lines = [
            f"任务号：{job.id[:8]}",
            f"模式：{mode_label(job.action)}",
            f"标题：{job.metadata.get('title') or job.source_url}",
            f"来源：{job.metadata.get('webpage_url') or job.source_url}",
        ]
        if job.metadata.get("uploader"):
            lines.append(f"作者：{job.metadata['uploader']}")
        if job.metadata.get("language"):
            lines.append(f"语言：{job.metadata['language']}")
        if job.metadata.get("paragraph_count"):
            lines.append(f"段落：{job.metadata['paragraph_count']}")
        if job.metadata.get("segment_count"):
            lines.append(f"分段：{job.metadata['segment_count']}")
        if job.metadata.get("audio_parts"):
            lines.append(f"音频分段：{job.metadata['audio_parts']}")
        lines.append(f"输出文件：{len(job.files)}")

        await self._post_reply(
            job,
            {
                "title": title,
                "content": "\n".join(lines),
            },
        )

        for artifact in job.files:
            if not artifact.url:
                continue
            await self._post_reply(
                job,
                {
                    "title": "任务文件",
                    "content": artifact.name if job.action != "audio" else "音频已提取，正在回传微信。",
                    "fileUrl": artifact.url,
                    "fileName": artifact.name,
                },
            )

    async def _send_failure_reply(self, job: JobRecord) -> None:
        if not job.reply_webhook_url:
            return

        await self._post_reply(
            job,
            {
                "title": "视频任务失败",
                "content": "\n".join(
                    [
                        f"任务号：{job.id[:8]}",
                        f"模式：{mode_label(job.action)}",
                        f"链接：{job.source_url}",
                        f"错误：{trim_text(job.error or job.message, 600)}",
                    ]
                ),
            },
        )

    async def _post_reply(self, job: JobRecord, payload: dict[str, Any]) -> None:
        request_payload = {
            "correlationId": job.correlation_id,
            "botId": job.bot_id,
            "targetId": job.target_id,
            **payload,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(job.reply_webhook_url, json=request_payload)
            response.raise_for_status()


settings = Settings.from_env()
service = VideoWorkerService(settings)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await service.startup()
    yield
    await service.shutdown()


app = FastAPI(title="Video Subtitle Worker", lifespan=lifespan)


def require_bearer_token(authorization: str | None) -> None:
    expected = settings.webhook_bearer_token
    if not expected:
        return
    header = (authorization or "").strip()
    prefix = "Bearer "
    if not header.startswith(prefix) or header[len(prefix) :].strip() != expected:
        raise HTTPException(status_code=401, detail="invalid bearer token")


@app.get("/health")
async def health() -> dict[str, Any]:
    jobs = list(service.jobs.values())
    return {
        "ok": True,
        "queued": sum(1 for job in jobs if job.status == "queued"),
        "running": sum(1 for job in jobs if job.status == "running"),
        "completed": sum(1 for job in jobs if job.status == "completed"),
        "failed": sum(1 for job in jobs if job.status == "failed"),
    }


@app.get("/api/jobs")
async def list_jobs(target_id: str = "", limit: int = 20) -> dict[str, Any]:
    return {"items": [asdict(item) for item in service.list_jobs(target_id=target_id, limit=limit)]}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return asdict(job)


@app.post("/api/wechat/dispatch")
async def dispatch(
    payload: DispatchPayload,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    require_bearer_token(authorization)
    return await service.handle_dispatch(payload, str(request.base_url))


@app.get("/artifacts/{job_id}/{file_name:path}")
async def download_artifact(job_id: str, file_name: str) -> FileResponse:
    artifact = service.get_artifact(job_id, file_name)
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    path = Path(artifact.path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="artifact file missing")
    return FileResponse(path, media_type=artifact.content_type, filename=artifact.name)
