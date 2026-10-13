"""분기: 통과 → SQLite + 유형별 CSV 저장 / 실패·애매 → review_queue.csv + 알림(콘솔, 웹훅 선택).

저장소와 확인 대기열은 둘 중 한 곳에만 들어간다. 확인 대기열 건은 저장소에 쓰지 않으므로
사람이 확인하기 전까지 잘못된 값이 다음 업무(정산·계약 관리)로 넘어가지 않는다.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from schemas import TYPE_LABEL, field_names

REASONS = {
    "TEXT_EXTRACTION_FAILED": "텍스트 추출 실패",
    "CLASSIFICATION_UNCERTAIN": "유형 판별 불가",
    "PROVIDER_ERROR": "공급자 오류",
    "SCHEMA_MISMATCH": "스키마 불일치",
    "RULE_VIOLATION": "규칙 위반",
    "LOW_CONFIDENCE": "확신 낮음",
}
QUEUE_COLUMNS = ["queued_at", "doc_id", "file", "doc_type", "reason_code", "reason_label", "detail", "provider",
                 "data_json"]


@dataclass
class Notifier:
    """확인 대기열에 들어간 건을 알린다. 웹훅 URL(DOCPIPE_WEBHOOK_URL)이 있으면 JSON POST(Slack·Discord 호환)."""

    console: Callable[[str], None] | None = print
    webhook_url: str | None = field(default_factory=lambda: os.environ.get("DOCPIPE_WEBHOOK_URL") or None)
    timeout: float = 5.0
    sent: list[str] = field(default_factory=list)
    webhook_errors: list[str] = field(default_factory=list)

    def alert(self, doc_id: str, reason_code: str, detail: str) -> None:
        msg = f"[확인 필요] {doc_id} · {REASONS.get(reason_code, reason_code)}({reason_code}) · {detail}"
        self.sent.append(msg)
        if self.console:
            self.console(msg)
        if self.webhook_url:
            body = json.dumps({"text": msg, "content": msg, "doc_id": doc_id, "reason_code": reason_code},
                              ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(self.webhook_url, data=body, method="POST",
                                         headers={"Content-Type": "application/json; charset=utf-8"})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    resp.read()
            except Exception as e:  # 알림 실패가 파이프라인을 멈추지 않게 한다
                self.webhook_errors.append(f"{doc_id}: {type(e).__name__}")


class Router:
    def __init__(self, out_dir: Path, notifier: Notifier | None = None):
        self.out_dir = out_dir
        self.notifier = notifier or Notifier()
        out_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = out_dir / "docpipe.sqlite3"
        self.queue_path = out_dir / "review_queue.csv"
        self.csv_dir = out_dir / "extracted"
        self.db = sqlite3.connect(self.db_path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY, doc_type TEXT NOT NULL, file TEXT NOT NULL, provider TEXT NOT NULL,
            data_json TEXT NOT NULL, saved_at TEXT NOT NULL)""")
        self.db.commit()

    def reset(self) -> None:
        """새 실행 전에 이전 결과를 비운다(데모를 여러 번 돌려도 같은 결과)."""
        self.db.execute("DELETE FROM documents")
        self.db.commit()
        if self.queue_path.exists():
            self.queue_path.unlink()
        if self.csv_dir.exists():
            for p in self.csv_dir.glob("*.csv"):
                p.unlink()

    def save(self, *, doc_id: str, doc_type: str, file: str, provider: str, data: dict[str, Any]) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self.db.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?)",
                        (doc_id, doc_type, file, provider, json.dumps(data, ensure_ascii=False), now))
        self.db.commit()
        self.csv_dir.mkdir(parents=True, exist_ok=True)
        path = self.csv_dir / f"{doc_type}.csv"
        cols = ["doc_id", "file", *field_names(doc_type)]
        new = not path.exists()
        with path.open("a", newline="", encoding="utf-8-sig" if new else "utf-8") as fp:
            w = csv.DictWriter(fp, fieldnames=cols)
            if new:
                w.writeheader()
            row = {"doc_id": doc_id, "file": file}
            for k in field_names(doc_type):
                v = data.get(k)
                row[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, list | dict) else ("" if v is None else v)
            w.writerow(row)

    def queue(self, *, doc_id: str, doc_type: str | None, file: str, provider: str, reason_code: str, detail: str,
              data: dict[str, Any] | None) -> None:
        new = not self.queue_path.exists()
        with self.queue_path.open("a", newline="", encoding="utf-8-sig" if new else "utf-8") as fp:
            w = csv.DictWriter(fp, fieldnames=QUEUE_COLUMNS)
            if new:
                w.writeheader()
            w.writerow({"queued_at": datetime.now().isoformat(timespec="seconds"), "doc_id": doc_id, "file": file,
                        "doc_type": TYPE_LABEL.get(doc_type or "", "알 수 없음"), "reason_code": reason_code,
                        "reason_label": REASONS[reason_code], "detail": detail, "provider": provider,
                        "data_json": json.dumps(data, ensure_ascii=False) if data is not None else ""})
        self.notifier.alert(doc_id, reason_code, detail)

    def saved_count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    def close(self) -> None:
        self.db.close()
