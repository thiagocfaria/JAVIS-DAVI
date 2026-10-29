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


if __name__ == "__main__":
    unittest.main()
