from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


def _normalize_domain(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"^https?://", "", text)
    text = text.split("/")[0]
    return text.strip()


def _normalize_app(value: str) -> str:
    return value.strip().lower()


@dataclass
class PolicyUsuario:
    blocked_domains: set[str] = field(default_factory=set)
    blocked_apps: set[str] = field(default_factory=set)


class PolicyUsuarioStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> PolicyUsuario:
        if not self.path.exists():
            return PolicyUsuario()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return PolicyUsuario()

        domains = {
            _normalize_domain(item)
            for item in payload.get("blocked_domains", [])
            if str(item).strip()
        }
        apps = {
            _normalize_app(item)
            for item in payload.get("blocked_apps", [])
            if str(item).strip()
        }
        return PolicyUsuario(blocked_domains=domains, blocked_apps=apps)

    def save(self, policy: PolicyUsuario) -> None:
        payload = {
            "blocked_domains": sorted(policy.blocked_domains),
            "blocked_apps": sorted(policy.blocked_apps),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
        tmp_path.replace(self.path)

    def add_blocked_domain(self, value: str) -> PolicyUsuario:
        policy = self.load()
        domain = _normalize_domain(value)
        if domain:
            policy.blocked_domains.add(domain)
            self.save(policy)
        return policy

    def remove_blocked_domain(self, value: str) -> PolicyUsuario:
        policy = self.load()
        domain = _normalize_domain(value)
        if domain and domain in policy.blocked_domains:
            policy.blocked_domains.remove(domain)
            self.save(policy)
        return policy

    def add_blocked_app(self, value: str) -> PolicyUsuario:
        policy = self.load()
        app = _normalize_app(value)
        if app:
            policy.blocked_apps.add(app)
            self.save(policy)
        return policy

    def remove_blocked_app(self, value: str) -> PolicyUsuario:
        policy = self.load()
        app = _normalize_app(value)
        if app and app in policy.blocked_apps:
            policy.blocked_apps.remove(app)
            self.save(policy)
        return policy
