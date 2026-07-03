#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape.py — 各護理公會／學會課程抓取。

策略
----
台灣多數護理公會／學會的課程列表需登入會員才能查詢；本模組只抓取「公開頁面」
可取得的課程（例如全聯會的研習活動報名表、麻醉專科護理學會的線上課程、
精神衛生護理學會的研習會公告）。需登入者僅能取得精選／公告課程，抓不到的來源
回傳空清單，可改以人工維護 data/events.json。

每個抓取函式回傳 dict 清單，欄位見 data/events.json 說明。
"""
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sources import SOURCES  # noqa: E402

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except Exception:
    HAS_DEPS = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}
TIMEOUT = 25
# 只保留今日往前 3 天以後的課程（過往課程略過）
CUTOFF = date.today().toordinal() - 3

# --- 區域判斷 ---------------------------------------------------------------
REGION_KEYS = [
    ("east",    ["花蓮", "臺東", "台東", "宜蘭"]),
    ("south",   ["高雄", "臺南", "台南", "嘉義", "屏東", "朴子", "岡山", "三民", "永康"]),
    ("central", ["臺中", "台中", "彰化", "南投", "苗栗", "雲林", "潭子"]),
    ("north",   ["臺北", "台北", "新北", "基隆", "桃園", "新竹", "板橋", "永和",
                 "龜山", "北投", "內湖", "汐止", "中正", "萬華", "土城", "林口"]),
    ("other",   ["金門", "澎湖", "連江", "馬祖"]),
]


def infer_region(text: str, online: bool):
    for region, keys in REGION_KEYS:
        if any(k in text for k in keys):
            return region
    return "online" if online else "other"


def is_online(text: str) -> bool:
    return bool(re.search(r"線上|直播|webex|Webex|遠距|視訊", text))


def _fetch(url: str):
    if not HAS_DEPS or not url:
        return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text
    except Exception as ex:  # noqa: BLE001
        print(f"[scrape] 取回失敗 {url}: {type(ex).__name__} {str(ex)[:60]}")
        return None


def _soup(html):
    return BeautifulSoup(html, "html.parser")


def _ordinal(d: str):
    try:
        y, m, dd = map(int, d.split("-"))
        return date(y, m, dd).toordinal()
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# 全聯會（護理師護士公會全國聯合會）研習活動報名表  ── 主要來源
# 公開表格：舉辦日期 | 研習會活動名稱 | 活動地點 | 開放報名期間 | 課程積分 | ...
# 課程積分格式例：「7.2 專業: 1.8, 法規: 3.6, 法規(性別): 1.8,」
# ---------------------------------------------------------------------------
CAT_MAP = {"專業": "pro", "品質": "quality", "倫理": "ethics", "法規": "law"}


def parse_credit_cell(cell: str):
    """回傳 (總積分, 主類別代碼, 備註)。"""
    cell = cell.replace("\xa0", " ").strip()
    total_m = re.search(r"[\d.]+", cell)
    total = float(total_m.group()) if total_m else 0.0
    buckets = {}
    notes = []
    for name, pts in re.findall(r"([一-鿿()（）]+)\s*[:：]\s*([\d.]+)", cell):
        base = name[:2]
        code = CAT_MAP.get(base)
        if code:
            buckets[code] = buckets.get(code, 0) + float(pts)
        if "性別" in name:
            notes.append("含性別議題")
        if "感染" in name:
            notes.append("含感染管制")
        if "倫理" in name:
            notes.append("含醫學倫理")
    cat = max(buckets, key=buckets.get) if buckets else "pro"
    ctext = "、".join(dict.fromkeys(notes))
    return total, cat, ctext


def scrape_nuna():
    html = _fetch("https://www.nurse.org.tw/publicUI/D/D101.aspx")
    if not html:
        return []
    soup = _soup(html)
    out = []
    for tr in soup.find_all("tr"):
        cells = [" ".join(td.get_text().split()) for td in tr.find_all("td")]
        cells = [c for c in cells if c]
        if len(cells) < 3:
            continue
        d = cells[0]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            continue
        o = _ordinal(d)
        if o is None or o < CUTOFF:
            continue
        title = cells[1]
        loc = cells[2] if len(cells) > 2 else ""
        credit_cell = cells[4] if len(cells) > 4 else ""
        total, cat, ctext = parse_credit_cell(credit_cell)
        online = is_online(title + loc)
        out.append({
            "date": d, "title": title, "location": loc,
            "credits": ({"nurse": _num(total)} if total else {}),
            "cat": cat, "src": "nuna", "online": online,
            "region": infer_region(loc, online), "ctext": ctext,
            "url": "https://www.nurse.org.tw/publicUI/D/D101.aspx",
        })
    return out


# ---------------------------------------------------------------------------
# 台灣麻醉專科護理學會  ── 線上影像學習課程（隨選，含積分）
# 標題內含積分，例：「… (專師1積分；護理師／護士1積分)」
# 「專師」在本會脈絡即麻醉專科護理師，對應積分別 anes。
# ---------------------------------------------------------------------------
def scrape_tana():
    html = _fetch("https://www.tana.org.tw/ecu/vedio_list.asp")
    if not html:
        return []
    soup = _soup(html)
    out = []
    seen = set()
    for s in soup.find_all(string=re.compile("積分")):
        txt = " ".join(s.split())
        if "課程" not in txt or "積分" not in txt:
            continue
        if not re.search(r"[（(].*積分", txt):
            continue
        title = re.sub(r"\s*[（(].*?積分.*?[)）]\s*", "", txt).strip()
        if not title or title in seen:
            continue
        seen.add(title)
        credits = {}
        m = re.search(r"專師\s*([\d.]+)\s*積分", txt)
        if m:
            credits["anes"] = _num(float(m.group(1)))
        m = re.search(r"護理師[／/]?護士\s*([\d.]+)\s*積分", txt)
        if m:
            credits["nurse"] = _num(float(m.group(1)))
        if not credits:          # 濾掉說明文字（非真正課程）
            continue
        out.append({
            "date": f"{date.today().year}-12-31", "title": title,
            "location": "台灣麻醉專科護理學會 / 線上影像學習課程",
            "credits": credits, "cat": "pro", "src": "tana", "online": True,
            "ondemand": True, "region": "online", "ctext": "線上隨選課程，年底前完成",
            "url": "https://www.tana.org.tw/ecu/vedio_list.asp",
        })
    return out


# ---------------------------------------------------------------------------
# 中華民國精神衛生護理學會  ── 研習會公告（含日期，積分依公告）
# ---------------------------------------------------------------------------
def _roc_to_date(s: str):
    m = re.search(r"(1[01][0-9])\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", s)
    if not m:
        return None
    y, mo, d = int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3))
    try:
        return f"{y:04d}-{mo:02d}-{d:02d}"
    except Exception:  # noqa: BLE001
        return None


def scrape_psy():
    html = _fetch("https://www.psynurse.org.tw/news.aspx")
    if not html:
        return []
    soup = _soup(html)
    out = []
    for a in soup.find_all("a", href=True):
        t = " ".join(a.get_text().split())
        if "研習" not in t:
            continue
        d = _roc_to_date(t)
        if not d:
            continue
        o = _ordinal(d)
        if o is None or o < CUTOFF:
            continue
        title = re.sub(r"【本會研習會訊息】", "", t)
        title = re.sub(r"1[01][0-9]\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日", "", title)
        title = title.replace("【", "").replace("】", "").strip()
        online = is_online(t)
        cat = "law" if re.search(r"法|權益|制度|倫理", title) else "pro"
        out.append({
            "date": d, "title": title or t,
            "location": "中華民國精神衛生護理學會" + ("（線上）" if online else ""),
            "credits": {}, "cat": cat, "src": "psy", "online": online,
            "region": "online" if online else "other",
            "ctext": "積分依主辦公告", "url": "https://www.psynurse.org.tw/news.aspx",
        })
    return out


def _slash_roc(s: str):
    """民國斜線日期 115/9/4 -> 2026-09-04。"""
    m = re.search(r"(1[01][0-9])/(\d{1,2})/(\d{1,2})", s)
    if not m:
        return None
    return f"{int(m.group(1))+1911:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


# ---------------------------------------------------------------------------
# 中華民國急重症護理學會（taccn）── 教育訓練課程（公開，含日期與積分）
# ---------------------------------------------------------------------------
def _region_from_zone(title: str):
    for kw, rg in (("北區", "north"), ("中區", "central"), ("南區", "south"), ("東區", "east")):
        if kw in title:
            return rg
    return None


def scrape_critical():
    html = _fetch("https://www.taccn.org.tw/activity/list/2")
    if not html:
        return []
    soup = _soup(html)
    seen = {}
    for a in soup.find_all("a", href=True):
        m = re.search(r"/activity/detail/(\d+)", a["href"])
        title = " ".join(a.get_text().split())
        if m and len(title) >= 6:
            seen.setdefault(m.group(1), title)
    out = []
    for aid, title in seen.items():
        d_html = _fetch(f"https://www.taccn.org.tw/activity/detail/{aid}")
        if not d_html:
            continue
        body = " ".join(_soup(d_html).get_text().split())
        dm = re.search(r"20\d{2}-\d{2}-\d{2}", body)
        if not dm:
            continue
        d = dm.group()
        o = _ordinal(d)
        if o is None or o < CUTOFF:
            continue
        credits = {}
        cm = re.search(r"專師\s*(\d+(?:\.\d+)?)", body)
        if cm:
            credits["np"] = _num(float(cm.group(1)))
        cm = re.search(r"(?:護理師[／/]?護士\s*|積分\s*)(\d+(?:\.\d+)?)", body)
        if cm:
            credits["nurse"] = _num(float(cm.group(1)))
        online = is_online(title + " " + body[:200])
        cat = "law" if re.search(r"倫理|法規|法律", title) else "pro"
        region = "online" if online else (_region_from_zone(title) or "other")
        out.append({
            "date": d, "title": title,
            "location": "中華民國急重症護理學會" + ("（線上直播）" if online else ""),
            "credits": credits, "cat": cat, "src": "critical", "online": online,
            "region": region, "ctext": "",
            "url": f"https://www.taccn.org.tw/activity/detail/{aid}",
        })
    return out


# ---------------------------------------------------------------------------
# 台灣手術全期護理學會（torna）── 首頁公開公告之精選課程（完整課表需登入）
# ---------------------------------------------------------------------------
def scrape_perio():
    html = _fetch("https://www.torna.org.tw/")
    if not html:
        return []
    soup = _soup(html)
    out, seen = [], set()
    for el in soup.find_all(["a", "li", "p"]):
        t = " ".join(el.get_text().split())
        if len(t) > 120 or not re.search(r"(研習|課程|訓練|開課|舉辦|手術|安全)", t):
            continue
        d = _roc_to_date(t) or _slash_roc(t)
        if not d:
            continue
        o = _ordinal(d)
        if o is None or o < CUTOFF:
            continue
        qm = re.search(r"「([^」]{4,45})」", t)   # 優先取「」內課程名稱
        if qm:
            title = qm.group(1)
        else:
            title = re.sub(r"^.*?(舉辦|辦理|開課預告[:：]?)", "", t).strip()[:50] or t[:50]
        key = (d, title[:12])
        if not title or key in seen:
            continue
        seen.add(key)
        online = is_online(t)
        out.append({
            "date": d, "title": title, "location": "台灣手術全期護理學會",
            "credits": {}, "cat": "pro", "src": "perio", "online": online,
            "region": "online" if online else "other",
            "ctext": "精選公告，詳見學會", "url": "https://www.torna.org.tw/",
        })
    return out


# ---------------------------------------------------------------------------
# 中華民國助產師助產士公會全聯會（midwife）── 公開消息之精選研習（完整需登入）
# ---------------------------------------------------------------------------
def scrape_midwife():
    out = []
    for url in ("http://www.midwifery.org.tw/modules/Content/C226.html",
                "http://www.midwifery.org.tw/modules/Content/C229.html"):
        html = _fetch(url)
        if not html:
            continue
        for el in _soup(html).find_all(["a", "li", "p", "tr"]):
            t = " ".join(el.get_text().split())
            if len(t) > 120 or not re.search(r"(研習|課程|繼續教育|講習|訓練)", t):
                continue
            d = _roc_to_date(t) or _slash_roc(t)
            if not d or (_ordinal(d) or 0) < CUTOFF:
                continue
            online = is_online(t)
            out.append({
                "date": d, "title": t[:50],
                "location": "中華民國助產師助產士公會全聯會",
                "credits": {}, "cat": "pro", "src": "midwife", "online": online,
                "region": "online" if online else "other",
                "ctext": "精選公告，詳見學會", "url": url,
            })
    uniq = {}
    for e in out:
        uniq[(e["date"], e["title"][:12])] = e
    return list(uniq.values())


def _num(v):
    return int(v) if float(v).is_integer() else round(float(v), 1)


# 來源代碼 -> 抓取函式（未實作或需登入者省略）
SCRAPERS = {
    "nuna": scrape_nuna,
    "tana": scrape_tana,
    "psy": scrape_psy,
    "critical": scrape_critical,
    "perio": scrape_perio,
    "midwife": scrape_midwife,
}


def scrape_all() -> list:
    if not HAS_DEPS:
        print("[scrape] 未安裝 requests / beautifulsoup4，請先 pip install -r requirements.txt")
        return []
    all_events = []
    for code in SOURCES:
        fn = SCRAPERS.get(code)
        if not fn:
            login = SOURCES[code].get("login")
            print(f"[scrape] {code} {SOURCES[code]['label']}："
                  f"{'需登入會員' if login else '無公開課程頁'}，略過")
            continue
        try:
            items = fn()
            for e in items:
                e.setdefault("src", code)
            all_events.extend(items)
            print(f"[scrape] {code} {SOURCES[code]['label']}: {len(items)} 筆")
        except Exception as ex:  # noqa: BLE001
            print(f"[scrape] {code} 發生錯誤：{type(ex).__name__} {ex}")
    return all_events


if __name__ == "__main__":
    events = scrape_all()
    print(f"[scrape] 合計 {len(events)} 筆")
    for e in events[:60]:
        cr = "、".join(f"{k}{v}" for k, v in e["credits"].items()) or "—"
        print(f"  {e['date']}  [{e['src']}/{e['cat']}/{e['region']}]  {cr}  {e['title'][:42]}")
