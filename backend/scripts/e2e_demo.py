import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from websockets.asyncio.client import connect

SCENARIOS = {
    "product": ("商品目录优化", "为什么无线耳机最近销量下降？"),
    "customer": ("客户行为分析", "哪些客户有流失风险，原因是什么？"),
}


async def run_scenario(
    base_url: str,
    question: str,
    title: str,
    timeout: float,
) -> dict:
    async with httpx.AsyncClient(
        base_url=base_url,
        follow_redirects=False,
        timeout=30,
        trust_env=False,
    ) as client:
        login = await client.get("/auth/login")
        state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
        callback = await client.get(
            "/auth/callback",
            params={"code": "demo", "state": state},
        )
        token = callback.headers["location"].split("#token=", 1)[1]
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/api/chat/create",
            json={"title": title},
            headers=headers,
        )
        created.raise_for_status()
        conversation_id = created.json()["conversation_id"]

        token_response = await client.post(
            "/api/chat/ws-token",
            json={"conversation_id": conversation_id},
            headers=headers,
        )
        token_response.raise_for_status()
        websocket_token = token_response.json()["websocket_token"]

        ws_base = base_url.replace("https://", "wss://").replace(
            "http://", "ws://"
        )
        ws_url = (
            f"{ws_base}/api/chat/ws/chat"
            f"?websocket_token={websocket_token}"
            f"&conversation_id={conversation_id}"
        )

        events: list[dict] = []
        deltas: list[str] = []
        task_id = None
        timed_out = False
        connection_error = None

        try:
            async with connect(
                ws_url,
                open_timeout=10,
                close_timeout=5,
                max_size=20_000_000,
            ) as websocket:
                events.append(json.loads(await websocket.recv()))
                await websocket.send(
                    json.dumps(
                        {"type": "user_message", "content": question},
                        ensure_ascii=False,
                    )
                )

                while True:
                    try:
                        raw = await asyncio.wait_for(
                            websocket.recv(), timeout=timeout
                        )
                    except TimeoutError:
                        timed_out = True
                        break

                    event = json.loads(raw)
                    events.append(event)
                    if event.get("task_id"):
                        task_id = event["task_id"]
                    if event.get("type") == "message_delta":
                        deltas.append(event.get("delta_text", ""))
                    if event.get("type") == "done":
                        break
        except Exception as exc:  # noqa: BLE001
            connection_error = f"{type(exc).__name__}: {exc}"

        result = None
        task = None
        file_info = None
        if task_id:
            task_response = await client.get(
                f"/api/tasks/{task_id}", headers=headers
            )
            if task_response.status_code == 200:
                task = task_response.json()

            result_response = await client.get(
                f"/api/results/{task_id}", headers=headers
            )
            if result_response.status_code == 200:
                result = result_response.json()

            file_response = await client.get(
                f"/api/results/{task_id}/file", headers=headers
            )
            if file_response.status_code == 200:
                file_info = {
                    "status": file_response.status_code,
                    "bytes": len(file_response.content),
                    "preview": file_response.text[:500],
                }

        event_counts = Counter(event.get("type", "unknown") for event in events)
        return {
            "title": title,
            "question": question,
            "conversation_id": conversation_id,
            "task_id": task_id,
            "event_counts": dict(event_counts),
            "tool_starts": [
                event.get("tool_name")
                for event in events
                if event.get("type") == "tool_start"
            ],
            "tool_finishes": [
                event.get("tool_result_summary")
                for event in events
                if event.get("type") == "tool_finish"
            ],
            "errors": [
                event.get("error_message")
                for event in events
                if event.get("type") == "error"
            ],
            "delta_chars": sum(len(delta) for delta in deltas),
            "delta_preview": "".join(deltas)[:1000],
            "task": task,
            "result": result,
            "file": file_info,
            "timed_out": timed_out,
            "connection_error": connection_error,
            "events": events,
        }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8020")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--question")
    parser.add_argument("--title")
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.scenario:
        title, question = SCENARIOS[args.scenario]
    else:
        if not args.question:
            parser.error("--question is required when --scenario is not provided")
        title = args.title or "E2E 演示"
        question = args.question

    return args, title, question


def main() -> None:
    args, title, question = parse_args()
    summary = asyncio.run(
        run_scenario(args.base_url, question, title, args.timeout)
    )
    text = json.dumps(summary, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        status = summary["task"]["task_status"] if summary["task"] else None
        print(f"written={args.output}")
        print(f"task_id={summary['task_id']}")
        print(f"status={status}")
        print(f"events={summary['event_counts']}")
    else:
        print(text)


if __name__ == "__main__":
    main()
