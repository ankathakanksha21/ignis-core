"""One call to the language model. The key comes from the environment or .env."""

import json
import os
import urllib.request

from ignis_ml import raw

_NAMES = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")


def settings() -> dict[str, str]:
    found = {name: os.environ.get(name, "") for name in _NAMES}
    env_file = raw.repo_root() / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() in _NAMES and not found[name.strip()]:
                found[name.strip()] = value.strip()
    missing = [name for name in _NAMES if not found[name]]
    if missing:
        raise RuntimeError("Set " + ", ".join(missing) + " in .env (see .env.example)")
    return found


def chat(messages: list[dict], *, max_tokens: int = 700) -> str:
    env = settings()
    body = {"model": env["LLM_MODEL"], "messages": messages, "temperature": 0, "max_tokens": max_tokens}
    request = urllib.request.Request(
        env["LLM_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {env['LLM_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read())["choices"][0]["message"]["content"]
