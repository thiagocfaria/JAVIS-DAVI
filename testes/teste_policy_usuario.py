import tempfile
import unittest
from pathlib import Path

from jarvis.seguranca.policy_usuario import PolicyUsuarioStore


class TestPolicyUsuarioStore(unittest.TestCase):
    def test_block_unblock_domain(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "policy_user.json"
            store = PolicyUsuarioStore(path)
            store.add_blocked_domain("https://Example.com/path")
            policy = store.load()
            self.assertIn("example.com", policy.blocked_domains)

            store.remove_blocked_domain("example.com")
            policy = store.load()
            self.assertNotIn("example.com", policy.blocked_domains)

    def test_block_unblock_app(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "policy_user.json"
            store = PolicyUsuarioStore(path)
            store.add_blocked_app("Firefox")
            policy = store.load()
            self.assertIn("firefox", policy.blocked_apps)

            store.remove_blocked_app("firefox")
            policy = store.load()
            self.assertNotIn("firefox", policy.blocked_apps)


if __name__ == "__main__":
    unittest.main()
