#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape.py — 各護理公會／學會課程抓取框架（scaffold）。

現況與限制
----------
台灣多數護理公會／學會的課程列表「需登入會員」才能查詢，公開頁面往往僅顯示
精選或近期課程；部分查詢頁另有圖形驗證碼。因此本框架採「盡力而為」策略：
  - 對於有公開課程頁的來源，於對應函式實作解析邏輯。
  - 對於需登入者，回傳空清單並記錄提示（可改以人工維護 data/events.json）。

每個抓取函式須回傳符合下列結構的 dict 清單：
  {
    "date": "YYYY-MM-DD", "title": str, "location": str,
    "credits": {"nurse": 6, "np": 6, ...},   # 僅列出點數 > 0 的積分別
    "cat": "pro|quality|ethics|law|other",
    "src": "<來源代碼>", "online": bool,
    "region": "north|central|south|east|online|other",
    "ctext": str, "url": str
  }

實作真實爬蟲時，建議使用 requests + BeautifulSoup（見 requirements.txt）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sources import SOURCES  # noqa: E402

try:
    import requests  # noqa: F401
    from bs4 import BeautifulSoup  # noqa: F401
    HAS_DEPS = True
except Exception:
    HAS_DEPS = False

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NurseCNTBot/1.0; +aggregator)"}
TIMEOUT = 20


def _fetch(url: str):
    """取回頁面 HTML；失敗回傳 None（不中斷整體流程）。"""
    if not HAS_DEPS or not url:
        return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text
    except Exception as ex:  # noqa: BLE001
        print(f"[scrape] 取回失敗 {url}: {ex}")
        return None


# --- 各來源抓取函式（stub） ------------------------------------------------
# 待實作：依各站 HTML 結構解析課程。以下為統一介面，預設回傳空清單。

def scrape_tmcs():
    """台灣醫療繼續教育推廣學會（公開課程頁，login=False）。
    TODO: 解析課程表；範例選擇器需依實際頁面調整。"""
    html = _fetch(SOURCES["tmcs"]["url"])
    if not html:
        return []
    # soup = BeautifulSoup(html, "html.parser")
    # for row in soup.select("..."): ...
    return []


def scrape_generic(code: str):
    """需登入或尚未實作者：回傳空清單並提示。"""
    s = SOURCES[code]
    tag = "需登入會員" if s.get("login") else "尚未實作"
    print(f"[scrape] {code} {s['label']}：{tag}，略過（可人工維護 data/events.json）")
    return []


# 來源代碼 -> 抓取函式
SCRAPERS = {code: (scrape_tmcs if code == "tmcs" else (lambda c=code: scrape_generic(c)))
            for code in SOURCES}


def scrape_all() -> list:
    """執行所有來源的抓取，彙整為單一清單。"""
    all_events = []
    for code, fn in SCRAPERS.items():
        try:
            items = fn()
            for e in items:
                e.setdefault("src", code)
            all_events.extend(items)
            if items:
                print(f"[scrape] {code}: {len(items)} 筆")
        except Exception as ex:  # noqa: BLE001
            print(f"[scrape] {code} 發生錯誤：{ex}")
    return all_events


if __name__ == "__main__":
    if not HAS_DEPS:
        print("[scrape] 未安裝 requests / beautifulsoup4，請先 pip install -r requirements.txt")
    events = scrape_all()
    print(f"[scrape] 合計 {len(events)} 筆（stub 狀態下多數來源為 0）")
