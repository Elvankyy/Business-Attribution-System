import asyncio
import json
from uuid import uuid4

import httpx

from app.core.config import get_settings


def candidate_roots(base_url: str) -> list[str]:
    base = base_url.rstrip("/")
    roots = [base]
    if not base.endswith("/v1"):
        roots.append(f"{base}/v1")
    return roots


def test_models(client: httpx.Client, base_url: str, headers: dict) -> None:
    for root in candidate_roots(base_url):
        url = f"{root}/models"
        try:
            response = client.get(url, headers=headers)
            print(f"GET {url} -> {response.status_code}")
            if response.status_code == 200:
                print(response.text[:1000])
        except Exception as exc:  # noqa: BLE001
            print(f"GET {url} -> {type(exc).__name__}: {exc}")


def test_chat(
    client: httpx.Client,
    base_url: str,
    headers: dict,
    model: str,
) -> bool:
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Reply with the single word: OK"}
        ],
        "max_tokens": 16,
        "temperature": 0,
    }
    for root in candidate_roots(base_url):
        url = f"{root}/chat/completions"
        try:
            response = client.post(url, headers=headers, json=payload)
            print(f"POST {url} -> {response.status_code}")
            print(response.text[:1000])
            if response.status_code == 200:
                return True
        except Exception as exc:  # noqa: BLE001
            print(f"POST {url} -> {type(exc).__name__}: {exc}")
    return False


def test_langchain() -> None:
    from app.analysis.agent.factory import create_model

    model = create_model()
    result = asyncio.run(model.ainvoke("Reply with the single word: OK"))
    print(f"langchain_content={result.content!r}")


def main() -> None:
    settings = get_settings()
    print(f"base_url={settings.deepseek_base_url}")
    print(f"model={settings.deepseek_model}")
    print(f"api_key_configured={bool(settings.deepseek_api_key.strip())}")

    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
        "x-opencode-session": f"bas-{uuid4().hex}",
    }
    with httpx.Client(trust_env=False, timeout=60) as client:
        test_models(client, settings.deepseek_base_url, headers)
        ok = test_chat(
            client,
            settings.deepseek_base_url,
            headers,
            settings.deepseek_model,
        )

    print(json.dumps({"connection_ok": ok}, ensure_ascii=False))
    test_langchain()


if __name__ == "__main__":
    main()
