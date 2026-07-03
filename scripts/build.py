#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — 將 data/events.json 的課程資料注入 index.html。

流程：
  1. 讀取 data/events.json
  2. 依日期排序、去重
  3. 產生 JavaScript 的 EVENTS 陣列，替換 index.html 中 EVENTS:START / EVENTS:END 之間的內容
  4. 更新 TODAY:AUTO 標記所在行的「今天」日期（以台北時區當日為準）

用法：
  python scripts/build.py                # 使用 data/events.json
  python scripts/build.py --data path    # 指定其他資料檔

此腳本模仿 Taiwan_Neurology 的做法：以 Python 重新產生 index.html 內的資料區塊，
讓 index.html 維持單一自包含檔案（可直接開啟、亦可部署到 GitHub Pages）。
"""
import argparse
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
DEFAULT_DATA = ROOT / "data" / "events.json"
TZ = timezone(timedelta(hours=8))  # 台北時區

CREDIT_ORDER = ["nurse", "np", "anes", "ltc", "midwife"]
VALID_CATS = {"pro", "quality", "ethics", "law", "other"}
VALID_REGIONS = {"north", "central", "south", "east", "online", "other"}


def load_events(data_path: Path) -> list:
    doc = json.loads(data_path.read_text(encoding="utf-8"))
    events = doc["events"] if isinstance(doc, dict) else doc
    cleaned = []
    for e in events:
        if not e.get("date") or not e.get("title"):
            continue
        credits = {k: v for k, v in (e.get("credits") or {}).items()
                   if k in CREDIT_ORDER and isinstance(v, (int, float)) and v > 0}
        cleaned.append({
            "date": e["date"],
            "title": e["title"].strip(),
            "location": (e.get("location") or "").strip(),
            "credits": credits,
            "cat": e.get("cat") if e.get("cat") in VALID_CATS else "other",
            "src": e.get("src") or "other",
            "online": bool(e.get("online")),
            "region": e.get("region") if e.get("region") in VALID_REGIONS else "other",
            "ctext": (e.get("ctext") or "").strip(),
            "url": (e.get("url") or "").strip(),
        })
    return cleaned


def dedupe(events: list) -> list:
    """相同日期且標題高度相似者去重（保留先出現者）。"""
    seen = {}
    for e in events:
        key = (e["date"], re.sub(r"\s+", "", e["title"])[:20])
        if key not in seen:
            seen[key] = e
    return list(seen.values())


def js_event(e: dict) -> str:
    credits = "{" + ", ".join(f"{k}:{_num(e['credits'][k])}"
                              for k in CREDIT_ORDER if k in e["credits"]) + "}"
    return ("  {date:%s, title:%s, location:%s, credits:%s, cat:%s, src:%s, "
            "online:%s, region:%s, ctext:%s, url:%s}") % (
        _s(e["date"]), _s(e["title"]), _s(e["location"]), credits,
        _s(e["cat"]), _s(e["src"]), "true" if e["online"] else "false",
        _s(e["region"]), _s(e["ctext"]), _s(e["url"]))


def _s(v: str) -> str:
    return json.dumps(v, ensure_ascii=False)


def _num(v):
    return int(v) if float(v).is_integer() else v


def inject(html: str, events: list) -> str:
    block = "/* EVENTS:START — 此區塊由 scripts/build.py 依 data/events.json 自動產生，可手動編輯作為預設範例 */\n"
    block += "const EVENTS = [\n"
    block += ",\n".join(js_event(e) for e in events)
    block += "\n];\n/* EVENTS:END */"
    html = re.sub(r"/\* EVENTS:START.*?EVENTS:END \*/", lambda _: block, html, flags=re.S)

    today = datetime.now(TZ).strftime("%Y-%m-%d")
    html = re.sub(
        r"const TODAY = new Date\('[^']*'\); /\* TODAY:AUTO \*/",
        f"const TODAY = new Date('{today}T00:00:00+08:00'); /* TODAY:AUTO */",
        html)
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    args = ap.parse_args()

    events = dedupe(load_events(Path(args.data)))
    events.sort(key=lambda e: e["date"])

    html = INDEX.read_text(encoding="utf-8")
    html = inject(html, events)
    INDEX.write_text(html, encoding="utf-8")
    print(f"[build] 已注入 {len(events)} 筆課程至 index.html")


if __name__ == "__main__":
    main()
