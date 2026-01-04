import tempfile
import unittest
from pathlib import Path

from jarvis.comunicacao.chat_log import ChatLog


class TestChatLog(unittest.TestCase):
    def test_append_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "chat.jsonl"
            chat = ChatLog(path, auto_open=False)
            chat.append("jarvis", "parou", {"reason": "test"})
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertIn("jarvis", lines[0])
            self.assertIn("parou", lines[0])
            self.assertIn("reason", lines[0])


if __name__ == "__main__":
    unittest.main()
