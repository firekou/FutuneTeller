"""能力登錄表：每項方法標記 enabled／reference-only／unavailable 與原因。"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Capability:
    key: str
    name: str
    status: str  # enabled | reference-only | unavailable
    reason: str
    sources: tuple[str, ...] = ()


def registry(kb_chunks: int) -> list[Capability]:
    kb_ready = kb_chunks > 0
    return [
        Capability(
            "zhuge_qa", "諸葛神卦：典籍問答與卦爻解說",
            "enabled" if kb_ready else "unavailable",
            ("已入庫 S03 前言（起卦法）與第 1–9 卦共 54 爻（印刷頁 1–54，占全書 384 爻之 14%）；"
             "文字取自 Drive OCR 並校正標頭結構，尚未逐頁對原圖校對。其餘 330 爻未入庫。")
            if kb_ready else "知識庫未匯入（data/private/corpus.jsonl 不存在或為空）",
            ("S03",)),
        Capability(
            "zhuge_cast", "諸葛神卦：三骰起卦查表",
            "enabled",
            ("依 S03 前言『紅字上卦、黑字下卦、一粒爻數』與目錄卦序推得確定性規則；"
             "可接受使用者自擲結果，或以明示的電腦亂數模擬。卦爻頁若未入庫，只回報卦名與頁碼，不解讀。"),
            ("S03",)),
        Capability("chaizi", "拆字／測字", "unavailable",
                   "S07 Drive 文字層僅回傳約前 62 頁且未入庫；書中為軼事選集，無逐步方法，暫不提供拆字判斷。",
                   ("S07",)),
        Capability("naming", "取名", "unavailable",
                   "S08 無文字層（Drive 回傳空白），未 OCR；S09 為封面。不提供筆畫吉凶。", ("S08", "S09")),
        Capability("fengshui", "風水", "unavailable",
                   "S01 無文字層（僅版權頁），未 OCR；S02 為封面。不臆測現場。", ("S01", "S02")),
        Capability("physiognomy", "相術／冰鑑", "reference-only",
                   "S05 文字層部分可讀但未入庫；即使入庫也只做典籍文化解說，絕不依照片判斷人格、健康或命運。",
                   ("S05", "S06")),
        Capability("bazi_ziwei", "八字／紫微斗數排盤", "unavailable",
                   "資料庫沒有相關典籍，也沒有經驗證的排盤工具。", ()),
    ]


def as_dicts(kb_chunks: int) -> list[dict]:
    return [asdict(c) for c in registry(kb_chunks)]


def render_for_prompt(kb_chunks: int) -> str:
    lines = [f"- [{c.status}] {c.name}：{c.reason}" for c in registry(kb_chunks)]
    return "\n".join(lines)
