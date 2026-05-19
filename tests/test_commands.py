import unittest

from app.commands import build_menu_text, parse_command, parse_dispatch_command


class ParseCommandTest(unittest.TestCase):
    def test_menu_command(self) -> None:
        parsed = parse_command("视频")
        self.assertEqual(parsed.intent, "menu")

    def test_mode_switch(self) -> None:
        parsed = parse_command("字幕")
        self.assertEqual(parsed.intent, "set_mode")
        self.assertEqual(parsed.mode, "subtitle")

    def test_direct_download(self) -> None:
        parsed = parse_command("下载 https://example.com/video")
        self.assertEqual(parsed.intent, "queue_job")
        self.assertEqual(parsed.mode, "download")
        self.assertEqual(parsed.url, "https://example.com/video")

    def test_link_uses_current_mode(self) -> None:
        parsed = parse_command("https://example.com/video", current_mode="subtitle")
        self.assertEqual(parsed.intent, "queue_job")
        self.assertEqual(parsed.mode, "subtitle")

    def test_link_without_mode_requires_choice(self) -> None:
        parsed = parse_command("https://example.com/video")
        self.assertEqual(parsed.intent, "need_mode")

    def test_exit_command(self) -> None:
        parsed = parse_command("退出")
        self.assertEqual(parsed.intent, "clear_session")

    def test_gateway_alias_with_url_routes_to_subtitle(self) -> None:
        parsed = parse_dispatch_command(
            command_text="https://example.com/video",
            raw_text="zimu https://example.com/video",
            current_mode=None,
        )
        self.assertEqual(parsed.intent, "queue_job")
        self.assertEqual(parsed.mode, "subtitle")
        self.assertEqual(parsed.url, "https://example.com/video")

    def test_gateway_chinese_alias_with_url_routes_to_subtitle(self) -> None:
        parsed = parse_dispatch_command(
            command_text="https://example.com/video",
            raw_text="字幕 https://example.com/video",
            current_mode=None,
        )
        self.assertEqual(parsed.intent, "queue_job")
        self.assertEqual(parsed.mode, "subtitle")

    def test_gateway_download_alias_with_url_routes_to_download(self) -> None:
        parsed = parse_dispatch_command(
            command_text="https://example.com/video",
            raw_text="下载 https://example.com/video",
            current_mode=None,
        )
        self.assertEqual(parsed.intent, "queue_job")
        self.assertEqual(parsed.mode, "download")

    def test_gateway_audio_alias_with_url_routes_to_audio(self) -> None:
        parsed = parse_dispatch_command(
            command_text="音频 https://example.com/video",
            raw_text="zm 音频 https://example.com/video",
            current_mode=None,
        )
        self.assertEqual(parsed.intent, "queue_job")
        self.assertEqual(parsed.mode, "audio")

    def test_gateway_alias_without_url_sets_mode(self) -> None:
        parsed = parse_dispatch_command(
            command_text="",
            raw_text="zimu",
            current_mode=None,
        )
        self.assertEqual(parsed.intent, "set_mode")
        self.assertEqual(parsed.mode, "subtitle")

    def test_md_and_word_options_are_captured(self) -> None:
        parsed = parse_dispatch_command(
            command_text="md word https://example.com/video",
            raw_text="字幕 md word https://example.com/video",
            current_mode=None,
        )
        self.assertEqual(parsed.intent, "queue_job")
        self.assertEqual(parsed.mode, "subtitle")
        self.assertEqual(parsed.output_formats, ("txt", "md", "docx"))

    def test_menu_text_mentions_direct_aliases_and_outputs(self) -> None:
        menu = build_menu_text("subtitle")
        self.assertIn("帮助命令：", menu)
        self.assertIn("zm <链接>                 默认回 txt", menu)
        self.assertIn("zm md <链接>              回 txt + md", menu)
        self.assertIn("zm word <链接>            回 txt + docx", menu)
        self.assertIn("zm md word <链接>         回 txt + md + docx", menu)
        self.assertIn("字幕 <链接>", menu)


if __name__ == "__main__":
    unittest.main()
