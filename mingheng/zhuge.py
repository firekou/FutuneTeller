"""諸葛神卦：依 S03 原書前言與目錄推得之確定性起卦規則。

原書規則（S03 前言）：三粒骰子，兩粒刻卦名（紅字為上卦、黑字為下卦），一粒刻爻數
（初、二、三、四、五、上）；擲出後「於本書查該卦、該爻」。

目錄觀察（S03 前置頁 I–XVI）：
- 第 1–8 卦上卦皆乾，第 9–16 卦上卦皆兌……依「乾兌離震巽坎艮坤」每 8 卦一組。
- 每組內下卦從與上卦相同者起，依同一順序循環（例：上兌組為 兌、離、震、巽、坎、艮、坤、乾）。
- 每卦六頁，初爻至上爻依序；第 N 卦第 k 爻之印刷頁 = (N-1)*6 + k。

本模組只做查表與換算，不解讀吉凶；骰子結果由使用者提供，或由明示的電腦亂數模擬。
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, asdict

TRIGRAMS = ["乾", "兌", "離", "震", "巽", "坎", "艮", "坤"]
YAO = ["初", "二", "三", "四", "五", "上"]

# 書中卦名。status: toc = 目錄 OCR 可辨識；body = 釋文頁可辨識；
# inferred = 目錄 OCR 遺失，依上下卦對應通行卦名推定（未經原頁確認）。
HEXAGRAM_NAMES: dict[int, tuple[str, str]] = {
    1: ("乾", "toc"), 2: ("履", "toc"), 3: ("同人", "toc"), 4: ("无妄", "toc"),
    5: ("垢", "toc"), 6: ("訟", "toc"), 7: ("遯", "body"), 8: ("否", "body"),
    9: ("兌", "body"), 10: ("革", "toc"), 11: ("隨", "toc"), 12: ("大過", "toc"),
    13: ("困", "toc"), 14: ("咸", "toc"), 15: ("萃", "toc"), 16: ("夬", "inferred"),
    17: ("離", "inferred"), 18: ("噬嗑", "toc"), 19: ("鼎", "toc"), 20: ("未濟", "toc"),
    21: ("旅", "toc"), 22: ("晉", "toc"), 23: ("大有", "toc"), 24: ("睽", "inferred"),
    25: ("震", "toc"), 26: ("恆", "inferred"), 27: ("解", "toc"), 28: ("小過", "toc"),
    29: ("豫", "toc"), 30: ("大壯", "toc"), 31: ("歸妹", "toc"), 32: ("豐", "inferred"),
    33: ("巽", "toc"), 34: ("渙", "toc"), 35: ("漸", "toc"), 36: ("觀", "toc"),
    37: ("小畜", "toc"), 38: ("中孚", "toc"), 39: ("家人", "toc"), 40: ("益", "inferred"),
    41: ("坎", "toc"), 42: ("蹇", "toc"), 43: ("比", "toc"), 44: ("需", "toc"),
    45: ("節", "toc"), 46: ("既濟", "toc"), 47: ("屯", "toc"), 48: ("井", "toc"),
    49: ("艮", "inferred"), 50: ("剝", "inferred"), 51: ("大畜", "toc"), 52: ("損", "toc"),
    53: ("賁", "toc"), 54: ("頤", "toc"), 55: ("蠱", "inferred"), 56: ("蒙", "toc"),
    57: ("坤", "toc"), 58: ("泰", "toc"), 59: ("臨", "toc"), 60: ("明夷", "toc"),
    61: ("復", "inferred"), 62: ("升", "inferred"), 63: ("師", "toc"), 64: ("謙", "toc"),
}

# 印刷頁 → PDF 頁換算。唯一錨點：SOURCE_AUDIT 記錄 PDF 第 40 頁 = 印刷頁 18（同人上爻）。
# 其他頁採同一位移，尚未逐頁確認。
PDF_PAGE_OFFSET = 22
PDF_PAGE_STATUS = "ESTIMATED (offset 22; anchor PDF40=印刷18 observed in SOURCE_AUDIT)"


class RuleInputError(ValueError):
    pass


@dataclass(frozen=True)
class Cast:
    upper: str
    lower: str
    yao: str
    hexagram_no: int
    hexagram_name: str
    name_status: str
    printed_page: int
    pdf_page_estimated: int
    pdf_page_status: str
    chunk_id: str
    mechanism: str

    def to_dict(self) -> dict:
        return asdict(self)


def _idx(value: str, table: list[str], label: str) -> int:
    v = (value or "").strip().replace("爻", "")
    # 常見異體／OCR 字
    v = {"兑": "兌", "1": "初", "6": "上", "2": "二", "3": "三", "4": "四", "5": "五"}.get(v, v)
    if v not in table:
        raise RuleInputError(f"{label}「{value}」不在允許值 {table} 之中")
    return table.index(v)


def hexagram_number(upper: str, lower: str) -> int:
    u = _idx(upper, TRIGRAMS, "上卦")
    l = _idx(lower, TRIGRAMS, "下卦")
    return u * 8 + ((l - u) % 8) + 1


def trigrams_of(hexagram_no: int) -> tuple[str, str]:
    if not 1 <= hexagram_no <= 64:
        raise RuleInputError("卦序須在 1–64")
    u, r = divmod(hexagram_no - 1, 8)
    return TRIGRAMS[u], TRIGRAMS[(u + r) % 8]


def printed_page(hexagram_no: int, yao: str) -> int:
    k = _idx(yao, YAO, "爻") + 1
    if not 1 <= hexagram_no <= 64:
        raise RuleInputError("卦序須在 1–64")
    return (hexagram_no - 1) * 6 + k


def chunk_id_for_page(page: int) -> str:
    return f"S03-P{page:04d}"


def cast(upper: str, lower: str, yao: str, mechanism: str = "使用者自行擲骰後輸入") -> Cast:
    n = hexagram_number(upper, lower)
    y = YAO[_idx(yao, YAO, "爻")]
    p = printed_page(n, y)
    name, status = HEXAGRAM_NAMES[n]
    u, l = trigrams_of(n)
    return Cast(u, l, y, n, name, status, p, p + PDF_PAGE_OFFSET, PDF_PAGE_STATUS,
                chunk_id_for_page(p), mechanism)


_T = "乾兌兑離震巽坎艮坤"
_UPPER_PATS = [rf"紅[字色]?(?:骰子?)?(?:的)?(?:也|則|就|都)?(?:是|為|：|:)?\s*([{_T}])", rf"上卦(?:也|則|就|都)?(?:是|為|：|:)?\s*([{_T}])",
               rf"上([{_T}])下[{_T}]"]
_LOWER_PATS = [rf"黑[字色]?(?:骰子?)?(?:的)?(?:也|則|就|都)?(?:是|為|：|:)?\s*([{_T}])", rf"下卦(?:也|則|就|都)?(?:是|為|：|:)?\s*([{_T}])",
               rf"上[{_T}]下([{_T}])"]
_YAO_PATS = [r"爻(?:數)?(?:骰子?)?(?:也|則|就|都)?(?:是|為|：|:)?\s*([初二三四五上])", r"([初二三四五上])爻"]


def detect_cast_parts(text: str) -> dict[str, str]:
    """從使用者自述的擲骰結果抽出已提到的部分：upper／lower／yao。"""
    import re

    def first(pats):
        for p in pats:
            m = re.search(p, text or "")
            if m:
                return m.group(1)
        return None

    parts = {"upper": first(_UPPER_PATS), "lower": first(_LOWER_PATS), "yao": first(_YAO_PATS)}
    return {k: v for k, v in parts.items() if v}


def detect_cast_in_text(text: str, carry: dict[str, str] | None = None) -> Cast | None:
    """三者齊全（可合併先前輪次已給的部分 carry）才回傳 Cast。"""
    parts = dict(carry or {}) | detect_cast_parts(text)
    if {"upper", "lower", "yao"} <= parts.keys():
        return cast(parts["upper"], parts["lower"], parts["yao"],
                    mechanism="使用者自述的擲骰結果（由程式解析）")
    return None


def random_cast(rng: secrets.SystemRandom | None = None) -> Cast:
    """以作業系統亂數模擬三粒骰子。這是文化體驗的模擬，不代表任何超自然感應。"""
    r = rng or secrets.SystemRandom()
    return cast(r.choice(TRIGRAMS), r.choice(TRIGRAMS), r.choice(YAO),
                mechanism="電腦亂數模擬三粒骰子（secrets.SystemRandom），非天啟")
