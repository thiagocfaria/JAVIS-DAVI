import tempfile
import unittest
from pathlib import Path

from jarvis.seguranca.kill_switch import stop_requested


class TestKillSwitch(unittest.TestCase):
    def test_stop_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stop_path = Path(tmpdir) / "STOP"
            self.assertFalse(stop_requested(stop_path))
            stop_path.write_text("1", encoding="utf-8")
            self.assertTrue(stop_requested(stop_path))


if __name__ == "__main__":
    unittest.main()
