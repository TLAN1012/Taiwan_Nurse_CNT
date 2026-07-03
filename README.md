# 🩺 護理繼續教育積分課程全集 · Taiwan_Nurse_CNT

聚合台灣各**護理公會／學會**的繼續教育積分課程資訊，讓護理人員能在同一頁面
比較不同**積分別**、**積分類別**、**來源**與**區域**的課程。

架構參考自 [基層神經科醫師教育活動全集（Taiwan_Neurology）](https://tlan1012.github.io/Taiwan_Neurology/)，
並針對「護理積分」的特性做了重要延伸。

> ⚠️ 目前 `data/events.json` 內為**範例資料**，用於展示聚合架構。實際課程、日期、
> 學分數與適用積分別，**一律以各主辦公會／學會之官方公告為準**。

---

## 為什麼護理課程需要不同的資料模型？

醫師課程通常只有「一種」繼續教育積分（一個數字）。但**護理課程往往同時具備多種積分**，
且各積分別點數可能不同。例如台灣麻醉專科護理學會的一堂課，可能同時給：

> 麻醉專科護理 1 點、專科護理師 1 點、護理師/護士 1 點

因此本專案將 `credits` 設計為**物件**（可同時容納多種積分別），而非單一數字，
並以彩色標籤分別呈現。

---

## 積分別（credit types）

| 代碼 | 名稱 | 說明 |
|------|------|------|
| `nurse` | 護理師/護士 | 一般護理繼續教育積分；執業執照更新需 **6 年 120 點** |
| `np` | 專科護理師 | 專科護理師**證書效期展延**所需積分（台灣專科護理師學會 TNPA） |
| `anes` | 麻醉專科護理 | 麻醉護理積分（台灣麻醉專科護理學會 TANA） |
| `ltc` | 長期照顧 | 長期照顧服務人員繼續教育積分 |
| `midwife` | 助產師 | 助產師/助產士繼續教育積分 |

## 積分類別（categories）

依衛福部[《醫事人員執業登記及繼續教育辦法》](https://law.moj.gov.tw/LawClass/LawAll.aspx?PCode=L0020181)，
繼續教育分四大類別；其中「專業品質＋專業倫理＋專業法規」合計至少 15 點、上限 30 點，
且**感染管制**與**性別議題**課程各須至少上過一次。

| 代碼 | 類別 | 備註 |
|------|------|------|
| `pro` | 專業課程 | 佔多數 |
| `quality` | 專業品質 | 含**感染管制**、病人安全 |
| `ethics` | 專業倫理 | 含**性別議題**、醫學倫理、多元文化 |
| `law` | 專業法規 | 醫事法規 |
| `other` | 其他 | — |

## 來源（sources）

涵蓋全國性學會、各縣市公會與各專科護理學會（詳見 `scripts/sources.py`）：

護理師護士公會全聯會 · 台灣護理學會 · 台灣專科護理師學會 · 台灣麻醉專科護理學會 ·
台灣醫療繼續教育推廣學會 · 精神衛生護理學會 · 腫瘤護理學會 · 手術全期護理學會 ·
急重症護理學會 · 婦產科護理學會 · 助產師公會全聯會 · 各縣市護理師護士公會

> 註：多數學會課程列表**需登入會員**才能查詢，公開頁面往往僅顯示精選課程。

## 區域（regions）

北部 · 中部 · 南部 · 東部 · 線上 · 其他

---

## 檔案結構

```
Taiwan_Nurse_CNT/
├── index.html               # 單一自包含頁面（可直接開啟，亦可部署 GitHub Pages）
├── data/
│   └── events.json          # 課程資料（單一事實來源）
├── scripts/
│   ├── sources.py           # 來源／積分別／類別登錄表
│   ├── scrape.py            # 各公會／學會課程抓取框架（scaffold）
│   ├── build.py             # 將 events.json 注入 index.html
│   └── update.py            # 每週更新入口：scrape → 合併去重 → build
├── requirements.txt         # 爬蟲相依套件
└── .github/workflows/
    └── update.yml           # 每週日 15:00（台北）自動更新
```

## 資料格式（`data/events.json`）

```jsonc
{
  "date": "2026-07-05",
  "title": "115年麻醉護理臨床實務研討會 — 動脈血氣體分析與酸鹼平衡",
  "location": "台灣麻醉專科護理學會 / 台大醫院國際會議中心",
  "credits": { "anes": 6, "nurse": 6 },   // 只列出點數 > 0 的積分別
  "cat": "pro",                             // pro|quality|ethics|law|other
  "src": "tana",                            // 對應 scripts/sources.py
  "online": false,
  "region": "north",                        // north|central|south|east|online|other
  "ctext": "含感染管制 3 點",                // 積分備註（可空字串）
  "url": "https://www.tana.org.tw/"
}
```

## 更新資料

```bash
# 1) 手動編輯 data/events.json，或實作 scripts/scrape.py 內各來源的抓取邏輯
pip install -r requirements.txt          # 僅爬蟲需要

# 2) 一鍵更新（抓取 → 合併去重 → 注入 index.html）
python scripts/update.py

# 或僅將現有 events.json 注入 index.html（不抓取）
python scripts/build.py
```

`index.html` 內以 `/* EVENTS:START */ … /* EVENTS:END */` 與 `/* TODAY:AUTO */`
標記，供 `build.py` 自動替換；未跑腳本前，`index.html` 內建的範例資料仍可正常顯示。

## 自動更新

`.github/workflows/update.yml` 於**每週日 15:00（台北時間）**執行 `scripts/update.py`，
若資料有變更則自動 commit 並 push。亦可於 Actions 頁面手動觸發（workflow_dispatch）。

## 部署至 GitHub Pages

於 GitHub 專案的 **Settings → Pages**，將來源設為 `main` 分支根目錄即可，
網址形如 `https://<帳號>.github.io/Taiwan_Nurse_CNT/`。

---

## 免責聲明

本站為便民查詢工具，課程資料著作權屬各主辦單位所有。實際場地、學分數與積分別
以主辦公會／學會之公告為準。
