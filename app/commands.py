from __future__ import annotations

from dataclasses import dataclass
import re

URL_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)

HELP_ALIASES = {"", "help", "menu", "帮助", "菜单", "视频", "zm"}
LIST_ALIASES = {"jobs", "job", "list", "最近", "任务", "列表"}
CLEAR_ALIASES = {"exit", "quit", "stop", "cancel", "结束", "退出", "关闭"}

MODE_ALIASES = {
    "download": {"download", "dl", "下载"},
    "subtitle": {"subtitle", "sub", "transcribe", "caption", "字幕", "转写", "识别", "台本", "zimu", "zm"},
    "audio": {"audio", "音频"},
}


@dataclass(frozen=True)
class ParsedCommand:
    intent: str
    mode: str | None = None
    url: str | None = None
    text: str = ""
    output_formats: tuple[str, ...] = ("txt",)


def _normalize_token(value: str) -> str:
    return str(value or "").strip().lower()


def _normalize_url(url: str) -> str:
    return url.rstrip(".,;!?)，。；！）》】」'")


def extract_first_url(text: str) -> str:
    match = URL_RE.search(text or "")
    return _normalize_url(match.group(0)) if match else ""


OUTPUT_FORMAT_ALIASES = {
    "txt": "txt",
    "text": "txt",
    "md": "md",
    "markdown": "md",
    "word": "docx",
    "doc": "docx",
    "docx": "docx",
}


def normalize_output_format(token: str) -> str | None:
    return OUTPUT_FORMAT_ALIASES.get(_normalize_token(token))


def extract_output_formats(text: str, default: tuple[str, ...] = ("txt",)) -> tuple[str, ...]:
    values = list(default)
    for token in str(text or "").split():
        fmt = normalize_output_format(token)
        if fmt and fmt not in values:
            values.append(fmt)
    return tuple(values)


def normalize_mode(token: str) -> str | None:
    normalized = _normalize_token(token)
    for mode, aliases in MODE_ALIASES.items():
        if normalized in aliases:
            return mode
    return None


def mode_label(mode: str | None) -> str:
    if mode == "download":
        return "下载"
    if mode == "subtitle":
        return "字幕"
    if mode == "audio":
        return "音频"
    return "未选择"


def build_menu_text(current_mode: str | None = None) -> str:
    lines = [
        "视频菜单",
        f"当前模式：{mode_label(current_mode)}",
        "",
        "帮助命令：",
        "help / 帮助 / 菜单 / zm",
        "",
        "可发送：",
        "下载           切换到下载模式",
        "字幕           切换到字幕模式",
        "最近           查看最近任务",
        "退出           退出视频菜单",
        "",
        "直接命令：",
        "zm <链接>                 默认回 txt",
        "zm md <链接>              回 txt + md",
        "zm word <链接>            回 txt + docx",
        "zm md word <链接>         回 txt + md + docx",
        "zm 下载 <链接>            只下载视频",
        "zm 音频 <链接>            提取 mp3 音频并回传",
        "",
        "兼容旧写法：",
        "下载 <链接>",
        "视频 下载 <链接>",
        "字幕 <链接>",
        "字幕 md <链接>",
        "字幕 word <链接>",
        "字幕 md word <链接>",
        "音频 <链接>",
        "",
        "进入菜单后，也可以先发“下载”或“字幕”，再直接贴视频链接。",
    ]
    return "\n".join(lines)


def parse_command(text: str, current_mode: str | None = None) -> ParsedCommand:
    raw_text = str(text or "").strip()
    if not raw_text:
        return ParsedCommand(intent="menu", text=raw_text)

    pieces = raw_text.split()
    first_token = _normalize_token(pieces[0])
    selected_mode = normalize_mode(first_token)
    url = extract_first_url(raw_text)
    output_formats = extract_output_formats(raw_text)

    if first_token in CLEAR_ALIASES and not url:
        return ParsedCommand(intent="clear_session", text=raw_text)

    if first_token in LIST_ALIASES and not url:
        return ParsedCommand(intent="list_jobs", text=raw_text)

    if first_token in HELP_ALIASES and not url:
        return ParsedCommand(intent="menu", text=raw_text)

    if selected_mode and url:
        return ParsedCommand(
            intent="queue_job",
            mode=selected_mode,
            url=url,
            text=raw_text,
            output_formats=output_formats,
        )

    if selected_mode:
        return ParsedCommand(
            intent="set_mode",
            mode=selected_mode,
            text=raw_text,
            output_formats=output_formats,
        )

    if url and current_mode:
        return ParsedCommand(
            intent="queue_job",
            mode=current_mode,
            url=url,
            text=raw_text,
            output_formats=output_formats,
        )

    if url:
        return ParsedCommand(intent="need_mode", url=url, text=raw_text, output_formats=output_formats)

    return ParsedCommand(intent="unknown", text=raw_text, output_formats=output_formats)


def parse_dispatch_command(
    command_text: str,
    raw_text: str,
    current_mode: str | None = None,
) -> ParsedCommand:
    normalized_command_text = str(command_text or "").strip()
    normalized_raw_text = str(raw_text or "").strip()

    if normalized_command_text:
        parsed = parse_command(normalized_command_text, current_mode=current_mode)
        if parsed.intent == "need_mode" and parsed.url:
            raw_first_token = normalized_raw_text.split()[0] if normalized_raw_text.split() else ""
            raw_mode = normalize_mode(raw_first_token)
            if raw_mode:
                return ParsedCommand(
                    intent="queue_job",
                    mode=raw_mode,
                    url=parsed.url,
                    text=normalized_raw_text or normalized_command_text,
                    output_formats=extract_output_formats(normalized_command_text or normalized_raw_text),
                )
        return parsed

    return parse_command(normalized_raw_text, current_mode=current_mode)
