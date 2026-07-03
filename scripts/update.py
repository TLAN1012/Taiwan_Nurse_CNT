#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update.py — 每週自動更新入口（由 GitHub Actions 呼叫）。

流程：
  1. 執行各來源爬蟲（scrape.py）
  2. 與現有 data/events.json 合併、去重
  3. 過濾：只保留「未結束」及未來約 3 個月內的課程
  4. 寫回 data/events.json
  5. 呼叫 build.py 將資料注入 index.html

設計上為「安全冪等」：若爬蟲為 stub（回傳空清單），
現有人工維護的 data/events.json 不會被清空，只會重新排序與注入。
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "events.json"
TZ = timezone(timedelta(hours=8))
WINDOW_DAYS = 100          # 保留未來約 3 個月
KEEP_PAST_DAYS = 3         # 已結束課程保留天數（緩衝）

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape import scrape_all  # noqa: E402


def norm_key(e: dict):
    return (e.get("date", ""), re.sub(r"\s+", "", e.get("title", ""))[:20])


def load_doc() -> dict:
    if DATA.exists():
        return json.loads(DATA.read_text(encoding="utf-8"))
    return {"meta": {}, "events": []}


def main():
    doc = load_doc()
    existing = doc.get("events", [])

    scraped = scrape_all()

    # 合併：以現有資料為底，爬到的新資料覆蓋同 key 者
    merged = {norm_key(e): e for e in existing}
    for e in scraped:
        merged[norm_key(e)] = e
    events = list(merged.values())

    # 過濾時間窗
    today = datetime.now(TZ).date()
    lo = today - timedelta(days=KEEP_PAST_DAYS)
    hi = today + timedelta(days=WINDOW_DAYS)
    kept = []
    for e in events:
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except Exception:  # noqa: BLE001
            continue
        if lo <= d <= hi:
            kept.append(e)
    # 若過濾後為空（例如範例資料已全部過期），則不套用時間窗，保留原資料避免清空
    if not kept and events:
        print("[update] 時間窗過濾後為空，保留原始資料（可能為過期範例）")
        kept = events

    kept.sort(key=lambda e: e["date"])
    doc["events"] = kept
    doc.setdefault("meta", {})["generated"] = datetime.now(TZ).isoformat(timespec="seconds")
    DATA.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[update] data/events.json 共 {len(kept)} 筆")

    # 注入 index.html
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py")], check=True)


if __name__ == "__main__":
    main()
