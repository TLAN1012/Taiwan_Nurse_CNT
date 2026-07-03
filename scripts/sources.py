#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sources.py — 護理繼續教育積分課程「來源」與「積分別」登錄表。

此檔為單一事實來源（single source of truth）：
  - index.html 的 SRC_LABELS / CREDIT_LABELS / CAT_LABELS 應與此處一致。
  - 爬蟲（scrape.py）依 SOURCES 逐一抓取各公會／學會課程。

新增來源：於 SOURCES 加一筆，並在 scrape.py 實作對應的抓取函式即可。
"""

# 積分別（護理課程可同時具備多種積分，這是與醫師課程最大的差異）
CREDIT_TYPES = {
    "nurse":   {"label": "護理師/護士", "note": "一般護理繼續教育積分；執業執照更新需 6 年 120 點"},
    "np":      {"label": "專科護理師",   "note": "專科護理師證書效期展延所需積分"},
    "anes":    {"label": "麻醉專科護理", "note": "台灣麻醉專科護理學會之麻醉護理積分"},
    "ltc":     {"label": "長期照顧",     "note": "長期照顧服務人員繼續教育積分"},
    "midwife": {"label": "助產師",       "note": "助產師/助產士繼續教育積分"},
}

# 積分類別（衛福部「醫事人員執業登記及繼續教育辦法」四大類別）
CATEGORIES = {
    "pro":     "專業課程",
    "quality": "專業品質（含感染管制）",
    "ethics":  "專業倫理（含性別議題、醫學倫理、多元文化）",
    "law":     "專業法規",
    "other":   "其他",
}

# 課程來源（公會／學會）
# login: True 代表課程列表需登入會員才能查詢，公開頁面通常僅有精選課程。
SOURCES = {
    "nuna":     {"label": "護理師護士公會全聯會", "url": "https://www.nurse.org.tw/",            "credits": ["nurse"],            "login": True},
    "twna":     {"label": "台灣護理學會",         "url": "https://www.twna.org.tw/",             "credits": ["nurse"],            "login": True},
    "tnpa":     {"label": "台灣專科護理師學會",   "url": "https://www.tnpa.org.tw/",             "credits": ["np", "nurse"],      "login": True},
    "tana":     {"label": "台灣麻醉專科護理學會", "url": "https://www.tana.org.tw/",             "credits": ["anes", "np", "nurse"], "login": True},
    "tmcs":     {"label": "台灣醫療繼續教育推廣學會", "url": "http://www.tmcs-edu.org.tw/",      "credits": ["nurse", "ltc"],     "login": False},
    "psy":      {"label": "精神衛生護理學會",     "url": "https://www.psynurse.org.tw/",         "credits": ["nurse"],            "login": True},
    "onco":     {"label": "腫瘤護理學會",         "url": "https://www.twna-oncology.org.tw/",    "credits": ["nurse", "np"],      "login": True},
    "perio":    {"label": "手術全期護理學會",     "url": "https://www.aorn.org.tw/",             "credits": ["nurse"],            "login": True},
    "critical": {"label": "急重症護理學會",       "url": "https://www.tanem.org.tw/",            "credits": ["nurse", "np"],      "login": True},
    "ob":       {"label": "婦產科護理學會",       "url": "https://www.twaogn.org.tw/",           "credits": ["nurse"],            "login": True},
    "midwife":  {"label": "助產師公會全聯會",     "url": "http://www.midwifery.org.tw/",         "credits": ["midwife", "nurse"], "login": True},
    "local":    {"label": "各縣市護理師護士公會", "url": "https://www.nurse.org.tw/",            "credits": ["nurse"],            "login": True},
    "other":    {"label": "其他單位",             "url": "",                                     "credits": ["nurse"],            "login": False},
}
