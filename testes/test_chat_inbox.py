import tempfile
import unittest
from pathlib import Path

from jarvis.comunicacao.chat_inbox import ChatInbox


class TestChatInbox(unittest.TestCase):
    def test_drain_reads_new_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "inbox.txt"
            inbox = ChatInbox(path)
            self.assertEqual(inbox.drain(), [])
            path.write_text("ola\n", encoding="utf-8")
            self.assertEqual(inbox.drain(), ["ola"])
            self.assertEqual(inbox.drain(), [])
            with path.open("a", encoding="utf-8") as handle:
                handle.write("teste\n")
            self.assertEqual(inbox.drain(), ["teste"])

    def test_drain_persists_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "inbox.txt"
            path.write_text("ola\n", encoding="utf-8")
            inbox = ChatInbox(path)
            self.assertEqual(inbox.drain(), ["ola"])

            # New instance should not re-read old lines.
            inbox2 = ChatInbox(path)
            self.assertEqual(inbox2.drain(), [])

            with path.open("a", encoding="utf-8") as handle:
                handle.write("novo\n")
            self.assertEqual(inbox2.drain(), ["novo"])


def test_append_line_writes() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "inbox.txt"
        from jarvis.comunicacao.chat_inbox import append_line

        assert append_line(path, "msg") is True
        assert path.read_text(encoding="utf-8").strip() == "msg"


def test_drain_debounce_max_lines(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_CHAT_INBOX_MAX_LINES", "2")
    path = tmp_path / "inbox.txt"
    path.write_text("a\nb\nc\n", encoding="utf-8")
    inbox = ChatInbox(path)
    assert inbox.drain() == ["b", "c"]
    assert inbox.drain() == []


if __name__ == "__main__":
    unittest.main()
