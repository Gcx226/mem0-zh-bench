import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    env = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        if not env.get(k):
            env[k] = os.environ.get(k, "")
    env.setdefault("LLM_BASE_URL", "https://api.deepseek.com/v1")
    env.setdefault("LLM_MODEL", "deepseek-chat")
    return env


def chat(messages, temperature=0.9, max_retries=3):
    env = load_env()
    key = env.get("LLM_API_KEY", "")
    if not key:
        raise RuntimeError("LLM_API_KEY 未设置：请在 mem0-zh-bench/.env 填入密钥（参考 .env.example）")
    url = env["LLM_BASE_URL"].rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": env["LLM_MODEL"],
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    last = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=body, method="POST", headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            })
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, OSError) as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"LLM 调用失败（重试 {max_retries} 次）: {last}")


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())