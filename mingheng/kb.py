"""知識庫：匯入（import）、索引（index）、檢索（search）。

SQLite + FTS5。中文以「二元字組（bigram）」切分後寫入 FTS5，查詢同樣切分並以 OR 結合、
bm25 排序；若查詢可解析出卦序／卦名／上下卦／爻位，結構化命中優先。
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import zhuge

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  book_title TEXT NOT NULL,
  source_variant TEXT,
  source_drive_bytes INTEGER,
  source_checksum TEXT,
  method TEXT NOT NULL,
  section TEXT,
  hexagram_no INTEGER,
  hexagram_name TEXT,
  upper TEXT,
  lower TEXT,
  yao TEXT,
  printed_page INTEGER,
  pdf_page INTEGER,
  pdf_page_status TEXT,
  layer TEXT NOT NULL,
  sign TEXT,
  original_note TEXT,
  explanation TEXT,
  text TEXT NOT NULL,
  text_sha256 TEXT NOT NULL,
  ocr_engine TEXT,
  proof_status TEXT NOT NULL,
  rights_status TEXT NOT NULL,
  aliases TEXT,
  is_test_fixture INTEGER NOT NULL DEFAULT 0
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED, tokens);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""

_CJK = re.compile(r"[㐀-鿿豈-﫿]")
_PUNCT = re.compile(r"[^㐀-鿿豈-﫿A-Za-z0-9]+")
_VARIANTS = str.maketrans({"兑": "兌", "裏": "裡", "旡": "无", "姤": "垢", "畜": "畜", "恒": "恆"})

# 太常見、對區分無幫助的二元字組
_STOP = {"什麼", "怎麼", "可以", "一下", "請問", "這個", "那個", "我們", "你們", "老師",
         "如果", "是不", "不是", "我的", "我想", "想問", "幫我", "一個", "會不", "不會",
         "有沒", "沒有", "的話", "因為", "所以", "還是", "這支", "這首", "意思", "代表",
         "諸葛", "葛神", "神卦"}


def normalize(text: str) -> str:
    return (text or "").translate(_VARIANTS)


def bigrams(text: str) -> list[str]:
    out: list[str] = []
    for seg in _PUNCT.split(normalize(text)):
        if not seg:
            continue
        if not _CJK.search(seg):
            out.append(seg.lower())
            continue
        if len(seg) == 1:
            out.append(seg)
        out.extend(seg[i:i + 2] for i in range(len(seg) - 1))
    return out


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Hit:
    chunk_id: str
    score: float
    reason: str
    row: dict

    def citation(self) -> str:
        r = self.row
        page = f"PDF 第 {r['pdf_page']} 頁（推估）" if r.get("pdf_page") else "PDF 頁未定"
        printed = f"、印刷頁 {r['printed_page']}" if r.get("printed_page") else ""
        return f"《{r['book_title']}》{r.get('section') or ''}｜{page}{printed}｜{r['chunk_id']}"


def connect(db_path: str | Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


REQUIRED = ("chunk_id", "source_id", "book_title", "method", "layer", "text",
            "proof_status", "rights_status")


def ingest(con: sqlite3.Connection, records: Iterable[dict]) -> int:
    n = 0
    for rec in records:
        missing = [k for k in REQUIRED if not rec.get(k)]
        if missing:
            raise ValueError(f"{rec.get('chunk_id')}: 缺少欄位 {missing}")
        rec = dict(rec)
        rec["text_sha256"] = sha256(rec["text"])
        rec.setdefault("is_test_fixture", 0)
        cols = [c for c in rec if c in _COLUMNS]
        con.execute(
            f"INSERT OR REPLACE INTO chunks ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [rec[c] if not isinstance(rec[c], (list, dict)) else json.dumps(rec[c], ensure_ascii=False)
             for c in cols])
        con.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (rec["chunk_id"],))
        index_text = " ".join(filter(None, [rec.get("section"), rec.get("hexagram_name"),
                                             rec.get("aliases") if isinstance(rec.get("aliases"), str)
                                             else " ".join(rec.get("aliases") or []),
                                             rec["text"]]))
        con.execute("INSERT INTO chunks_fts (chunk_id, tokens) VALUES (?, ?)",
                    (rec["chunk_id"], " ".join(bigrams(index_text))))
        n += 1
    con.commit()
    return n


_COLUMNS = {"chunk_id", "source_id", "book_title", "source_variant", "source_drive_bytes",
            "source_checksum", "method", "section", "hexagram_no", "hexagram_name", "upper",
            "lower", "yao", "printed_page", "pdf_page", "pdf_page_status", "layer", "sign",
            "original_note", "explanation", "text", "ocr_engine", "proof_status",
            "rights_status", "aliases", "is_test_fixture", "text_sha256"}


def load_jsonl(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def get(con: sqlite3.Connection, chunk_id: str) -> dict | None:
    r = con.execute("SELECT * FROM chunks WHERE chunk_id=?", (chunk_id,)).fetchone()
    return dict(r) if r else None


def stats(con: sqlite3.Connection) -> dict:
    q = lambda sql: con.execute(sql).fetchone()[0]
    return {
        "chunks": q("SELECT COUNT(*) FROM chunks WHERE is_test_fixture=0"),
        "test_fixtures": q("SELECT COUNT(*) FROM chunks WHERE is_test_fixture=1"),
        "sources": [dict(r) for r in con.execute(
            "SELECT source_id, book_title, COUNT(*) AS n, MIN(printed_page) AS p_min, "
            "MAX(printed_page) AS p_max FROM chunks WHERE is_test_fixture=0 GROUP BY source_id")],
        "proof_status": {r[0]: r[1] for r in con.execute(
            "SELECT proof_status, COUNT(*) FROM chunks GROUP BY proof_status")},
    }


# ---------- 結構化查詢解析 ----------
_NUM = {"〇": 0, "零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6,
        "七": 7, "八": 8, "九": 9}


def cn_to_int(s: str) -> int | None:
    if s.isdigit():
        return int(s)
    if not s or any(ch not in _NUM and ch != "十" for ch in s):
        return None
    if "十" in s:
        a, _, b = s.partition("十")
        return (_NUM.get(a, 1) if a else 1) * 10 + (_NUM.get(b, 0) if b else 0)
    v = 0
    for ch in s:
        v = v * 10 + _NUM[ch]
    return v


_NAME_TO_NO = {name: no for no, (name, _) in zhuge.HEXAGRAM_NAMES.items()}
_NAME_TO_NO["姤"] = 5


def parse_reference(query: str) -> dict:
    q = normalize(query)
    ref: dict = {}
    m = re.search(r"第([0-9〇零一二兩三四五六七八九十]+)卦", q)
    if m and (n := cn_to_int(m.group(1))) and 1 <= n <= 64:
        ref["hexagram_no"] = n
    m = re.search(r"上([乾兌離震巽坎艮坤])下([乾兌離震巽坎艮坤])", q)
    if m:
        ref["hexagram_no_from_trigrams"] = zhuge.hexagram_number(m.group(1), m.group(2))
    m = re.search(r"([初二三四五上六1-6])爻", q)
    if m:
        ref["yao"] = {"六": "上", "1": "初", "6": "上", "2": "二", "3": "三", "4": "四",
                      "5": "五"}.get(m.group(1), m.group(1))
    names = sorted((n for n in _NAME_TO_NO if n in q and len(n) >= 1), key=len, reverse=True)
    # 單字卦名太易誤判，只在後接「卦」時採用
    divination_ctx = bool(re.search(r"[卦爻簽籤]", q))
    for n in names:
        if re.search(re.escape(n) + r"卦", q) or (len(n) >= 2 and divination_ctx):
            ref["hexagram_no_from_name"] = _NAME_TO_NO[n]
            break
    return ref


# 小型口語→典籍用詞擴展（可審查、可測試；不含任何卦爻對應）
SYNONYMS = {
    "合夥": "合作", "夥伴": "合作", "搭檔": "合作", "合資": "合作",
    "不見": "失物", "弄丟": "失物", "遺失": "失物", "掉了": "失物",
    "考試": "升學", "考上": "升學", "升遷": "升遷", "加薪": "升遷",
    "結婚": "婚姻", "對象": "婚姻", "吵架": "是非", "官司": "訟事",
}


def expand_query(query: str) -> str:
    extra = [v for k, v in SYNONYMS.items() if k in query and v not in query]
    return query + (" " + " ".join(extra) if extra else "")


def search(con: sqlite3.Connection, query: str, k: int = 5,
           include_test_fixtures: bool = False) -> list[Hit]:
    hits: dict[str, Hit] = {}
    fixture_clause = "" if include_test_fixtures else " AND is_test_fixture=0"

    ref = parse_reference(query)
    nos = {ref.get("hexagram_no"), ref.get("hexagram_no_from_trigrams"), ref.get("hexagram_no_from_name")}
    nos.discard(None)
    if nos:
        no = ref.get("hexagram_no_from_trigrams") or ref.get("hexagram_no") or ref.get("hexagram_no_from_name")
        sql = "SELECT * FROM chunks WHERE hexagram_no=?" + fixture_clause
        args: list = [no]
        if ref.get("yao"):
            sql += " AND yao=?"
            args.append(ref["yao"])
        for r in con.execute(sql + " ORDER BY printed_page", args):
            hits[r["chunk_id"]] = Hit(r["chunk_id"], 100.0, f"structured:{ref}", dict(r))

    toks = [t for t in dict.fromkeys(bigrams(expand_query(query))) if t not in _STOP]
    if toks:
        match = " OR ".join('"' + t.replace('"', '') + '"' for t in toks)
        rows = con.execute(
            "SELECT c.*, bm25(chunks_fts) AS s FROM chunks_fts JOIN chunks c USING(chunk_id) "
            "WHERE chunks_fts MATCH ?" + fixture_clause.replace("is_test", "c.is_test") +
            " ORDER BY s LIMIT ?", (match, k * 4)).fetchall()
        for r in rows:
            if r["chunk_id"] not in hits:
                d = dict(r)
                s = -d.pop("s")
                hits[r["chunk_id"]] = Hit(r["chunk_id"], s, "fts_bigram_bm25", d)
    ordered = sorted(hits.values(), key=lambda h: -h.score)
    return ordered[:k]


def ensure_fixture_db(jsonl: str | Path, db_path: str | Path) -> None:
    """建立合成測試資料庫（只供測試模式使用）。"""
    if Path(db_path).exists():
        return
    con = connect(db_path)
    ingest(con, load_jsonl(jsonl))
    con.close()
