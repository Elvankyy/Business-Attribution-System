import json
from pathlib import Path

import yaml

from app.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
YAML_PATH = PROJECT_ROOT / "docs" / "page-interface.yaml"


def check_contract() -> dict:
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    openapi_paths = app.openapi().get("paths", {})

    summary = {
        "total": 0,
        "matched": 0,
        "extension": 0,
        "frontend_pending": 0,
        "missing": [],
    }

    for page in data.get("pages", []):
        for action in page.get("actions", []):
            method = action.get("method")
            path = action.get("path")
            if not method or not path:
                continue

            summary["total"] += 1
            status = action.get("status", "matched")
            method_key = str(method).lower()

            if path not in openapi_paths:
                summary["missing"].append(
                    {
                        "page": page.get("id"),
                        "action": action.get("name"),
                        "method": method,
                        "path": path,
                        "reason": "path not found",
                    }
                )
                continue
            if method_key not in openapi_paths[path]:
                summary["missing"].append(
                    {
                        "page": page.get("id"),
                        "action": action.get("name"),
                        "method": method,
                        "path": path,
                        "reason": "method not found",
                    }
                )
                continue

            if status in summary:
                summary[status] += 1
            else:
                summary["matched"] += 1

    return summary


def main() -> None:
    summary = check_contract()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["missing"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
