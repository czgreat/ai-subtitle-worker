from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _clean_base_url(value: str) -> str:
    return value.strip().rstrip("/")


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    public_base_url: str
    webhook_bearer_token: str
    max_concurrent_jobs: int
    whisper_model: str
    whisper_device: str
    whisper_compute_type: str
    whisper_language: str
    ffmpeg_bin: str
    python_bin: str
    ytdlp_cookies_file: str
    ytdlp_proxy: str
    download_speed_floor_bytes: int
    download_stall_abort_seconds: int
    download_read_timeout_seconds: int
    newapi_base_url: str
    newapi_api_key: str
    newapi_model: str
    newapi_timeout_seconds: int
    audio_export_bitrate_kbps: int
    audio_chunk_max_bytes: int
    send_video_file_for_subtitle: bool

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def sessions_file(self) -> Path:
        return self.data_dir / "sessions.json"

    @property
    def jobs_file(self) -> Path:
        return self.data_dir / "jobs.json"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", "/data")).resolve(),
            public_base_url=_clean_base_url(os.getenv("PUBLIC_BASE_URL", "")),
            webhook_bearer_token=os.getenv("WEBHOOK_BEARER_TOKEN", "").strip(),
            max_concurrent_jobs=_int_env("MAX_CONCURRENT_JOBS", 1),
            whisper_model=os.getenv("WHISPER_MODEL", "small").strip() or "small",
            whisper_device=os.getenv("WHISPER_DEVICE", "cpu").strip() or "cpu",
            whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8").strip() or "int8",
            whisper_language=os.getenv("WHISPER_LANGUAGE", "").strip(),
            ffmpeg_bin=os.getenv("FFMPEG_BIN", "ffmpeg").strip() or "ffmpeg",
            python_bin=os.getenv("PYTHON_BIN", sys.executable).strip() or sys.executable,
            ytdlp_cookies_file=os.getenv("YTDLP_COOKIES_FILE", "").strip(),
            ytdlp_proxy=os.getenv("YTDLP_PROXY", "").strip(),
            download_speed_floor_bytes=_int_env("DOWNLOAD_SPEED_FLOOR_BYTES", 32768),
            download_stall_abort_seconds=_int_env("DOWNLOAD_STALL_ABORT_SECONDS", 45),
            download_read_timeout_seconds=_int_env("DOWNLOAD_READ_TIMEOUT_SECONDS", 15),
            newapi_base_url=_clean_base_url(os.getenv("NEWAPI_BASE_URL", "")),
            newapi_api_key=os.getenv("NEWAPI_API_KEY", "").strip(),
            newapi_model=os.getenv("NEWAPI_MODEL", "gpt-5.5").strip() or "gpt-5.5",
            newapi_timeout_seconds=_int_env("NEWAPI_TIMEOUT_SECONDS", 90),
            audio_export_bitrate_kbps=_int_env("AUDIO_EXPORT_BITRATE_KBPS", 64),
            audio_chunk_max_bytes=_int_env("AUDIO_CHUNK_MAX_BYTES", 20 * 1024 * 1024),
            send_video_file_for_subtitle=_bool_env("SEND_VIDEO_FILE_FOR_SUBTITLE", False),
        )
