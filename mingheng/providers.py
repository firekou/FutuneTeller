"""LLM Provider 介接。依設定注入；密鑰只從環境變數讀取，不傳給前端。

MINGHENG_PROVIDER:
  claude_cli         呼叫本機已登入的 Claude Code CLI（`claude -p`），不需額外密鑰
  anthropic          Anthropic Messages API，需 ANTHROPIC_API_KEY
  openai_compatible  OpenAI 相容 /chat/completions，需 MINGHENG_OPENAI_BASE_URL 與
                     MINGHENG_OPENAI_KEY_ENV 指向的環境變數
  none               不呼叫模型；諮詢回覆標為 BLOCKED，只提供檢索結果
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass


class ProviderError(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    raw_meta: dict


class Provider:
    name = "base"
    model = ""

    def available(self) -> tuple[bool, str]:
        raise NotImplementedError

    def complete(self, system: str, messages: list[dict]) -> LLMResult:
        raise NotImplementedError


def _flatten(messages: list[dict]) -> str:
    """CLI 只接受單一 prompt：以清楚的角色標記串接多輪。"""
    parts = []
    for m in messages:
        tag = "使用者" if m["role"] == "user" else "明衡（先前回覆）"
        parts.append(f"<<{tag}>>\n{m['content']}")
    parts.append("<<請以明衡身分回覆最後一則使用者訊息>>")
    return "\n\n".join(parts)


class ClaudeCLIProvider(Provider):
    name = "claude_cli"

    def __init__(self, model: str | None = None, timeout: int = 240):
        self.model = model or os.getenv("MINGHENG_MODEL", "")
        self.timeout = timeout
        self.bin = shutil.which("claude")

    def available(self):
        return (bool(self.bin), "claude CLI found" if self.bin else "找不到 claude CLI")

    def complete(self, system, messages):
        if not self.bin:
            raise ProviderError("claude CLI 不存在")
        cmd = [self.bin, "-p", "--output-format", "json", "--max-turns", "1",
               "--tools", "", "--system-prompt", system]
        if self.model:
            cmd += ["--model", self.model]
        # 在空目錄執行，避免讀入任何專案 CLAUDE.md／AGENTS.md
        with tempfile.TemporaryDirectory() as cwd:
            p = subprocess.run(cmd, input=_flatten(messages), capture_output=True, text=True,
                               timeout=self.timeout, cwd=cwd)
        if p.returncode != 0:
            raise ProviderError(f"claude CLI exit {p.returncode}: {p.stderr[-500:]}")
        try:
            data = json.loads(p.stdout)
        except json.JSONDecodeError as e:
            raise ProviderError(f"無法解析 CLI 輸出：{p.stdout[:300]}") from e
        if data.get("is_error"):
            raise ProviderError(f"CLI 回報錯誤：{data.get('result')}")
        models = list((data.get("modelUsage") or {}).keys())
        return LLMResult(data.get("result", ""), self.name, ",".join(models) or self.model or "default",
                         {"duration_api_ms": data.get("duration_api_ms"),
                          "usage": data.get("usage", {}).get("output_tokens"),
                          "session_id": data.get("session_id")})


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("MINGHENG_MODEL", "claude-sonnet-5-5")

    def available(self):
        ok = bool(os.getenv("ANTHROPIC_API_KEY"))
        return ok, "ANTHROPIC_API_KEY set" if ok else "未設定 ANTHROPIC_API_KEY"

    def complete(self, system, messages):
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ProviderError("未設定 ANTHROPIC_API_KEY")
        base = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
        body = json.dumps({"model": self.model, "max_tokens": 2000, "system": system,
                           "messages": messages}).encode()
        req = urllib.request.Request(f"{base}/v1/messages", data=body, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read())
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return LLMResult(text, self.name, data.get("model", self.model), {"usage": data.get("usage")})


class OpenAICompatibleProvider(Provider):
    name = "openai_compatible"

    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("MINGHENG_MODEL", "")
        self.base = os.getenv("MINGHENG_OPENAI_BASE_URL", "").rstrip("/")
        self.key_env = os.getenv("MINGHENG_OPENAI_KEY_ENV", "OPENAI_API_KEY")

    def available(self):
        if not self.base:
            return False, "未設定 MINGHENG_OPENAI_BASE_URL"
        if not os.getenv(self.key_env):
            return False, f"未設定 {self.key_env}"
        if not self.model:
            return False, "未設定 MINGHENG_MODEL"
        return True, "configured"

    def complete(self, system, messages):
        ok, why = self.available()
        if not ok:
            raise ProviderError(why)
        body = json.dumps({"model": self.model, "messages": [{"role": "system", "content": system}] + messages,
                           "max_tokens": 2000}).encode()
        req = urllib.request.Request(f"{self.base}/chat/completions", data=body, headers={
            "authorization": f"Bearer {os.getenv(self.key_env)}", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read())
        return LLMResult(data["choices"][0]["message"]["content"], self.name, data.get("model", self.model),
                         {"usage": data.get("usage")})


class NoProvider(Provider):
    name = "none"

    def available(self):
        return False, "MINGHENG_PROVIDER=none：模型諮詢未啟用（BLOCKED），只提供檢索"

    def complete(self, system, messages):
        raise ProviderError("模型未啟用")


def get_provider(name: str | None = None) -> Provider:
    name = name or os.getenv("MINGHENG_PROVIDER", "claude_cli")
    return {"claude_cli": ClaudeCLIProvider, "anthropic": AnthropicProvider,
            "openai_compatible": OpenAICompatibleProvider, "none": NoProvider}.get(name, NoProvider)()
