import json
from pathlib import Path
from typing import Any, Dict

from src.config.paths import LOG_DIR
from src.utils.time_ops import compact_timestamp, utc_now_iso


def append_log(event: str, payload: Dict[str, Any]) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / "cargas.log"
    record = {
        "timestamp": utc_now_iso(),
        "event": event,
        **payload,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def dump_json_report(name_prefix: str, data: Dict[str, Any]) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"{name_prefix}_{compact_timestamp()}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path
