"""高風險請求與注入偵測（規則式，保守）。偵測結果只用於加上護欄，不取代模型判斷。"""
from __future__ import annotations

import re

RISK_PATTERNS: dict[str, str] = {
    "crisis": r"想死|不想活|活不下去|自殺|輕生|結束生命|了結自己|撐不下去",
    "death_health": r"會不會死|死期|壽命|還能活|癌|絕症|病[會能]不?[會能]?好|開刀|手術|治療|吃藥|停藥",
    "pregnancy": r"懷孕|生男生女|胎兒|流產|能不能生",
    "infidelity": r"外遇|出軌|小三|偷吃|劈腿",
    "finance": r"股票|投資|存款|買房|加密貨幣|比特幣|期貨|槓桿|借錢|全部的?錢|漲跌|會漲|會跌",
    "legal": r"官司|訴訟|告他|判刑|離婚協議",
    "photo_physiognomy": r"照片|看我的臉|面相.*(準|看)|看相",
}

CRISIS_NOTICE = (
    "【安全優先】如果你此刻有傷害自己的念頭，請先暫停占卜，立刻聯繫身邊信任的人，"
    "或撥打台灣 安心專線 1925（24 小時）、生命線 1995、張老師 1980；若有立即危險請撥 119 或 110。"
    "占卜不能替代專業協助，你值得被好好接住。"
)

_INJECTION = re.compile(
    r"忽略(之前|以上|所有|前面)|ignore (all|previous|the above)|system prompt|系統提示|"
    r"你現在是|扮演.*(真人|轉世)|開發者模式|developer mode|洩漏|列出.*(指令|prompt)",
    re.I)


def risk_flags(text: str) -> list[str]:
    return [k for k, p in RISK_PATTERNS.items() if re.search(p, text or "")]


def looks_like_injection(text: str) -> bool:
    return bool(_INJECTION.search(text or ""))


def guardrail_text(flags: list[str]) -> str:
    notes = {
        "crisis": "使用者可能處於情緒危機：先回應安全與現實支持，提供求助資源，不做吉凶判斷，不加劇恐慌。",
        "death_health": "涉及生死或疾病：不得斷言病情、壽命或死亡；不得給醫療指示；建議就醫與專業意見。",
        "pregnancy": "涉及懷孕：不得預測懷孕結果或胎兒性別。",
        "infidelity": "涉及他人外遇：不得斷言第三人行為，只就使用者自身感受與可行溝通提供反思。",
        "finance": "涉及金錢投資：不得依卦象給買賣、借貸或投入金額的指令；說明命理不能作投資依據。",
        "legal": "涉及法律：不得預測判決或給法律指令；建議諮詢律師或法律扶助。",
        "photo_physiognomy": "涉及相貌：不得依照片或外貌推斷人格、健康或命運。",
    }
    return "\n".join(f"- {notes[f]}" for f in flags if f in notes)
