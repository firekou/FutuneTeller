"""以真實模型執行 3 組多輪演示（虛構使用者），輸出逐輪 transcript。

python scripts/run_demo.py [--out handoffs/executor/demos]
每輪的使用者訊息是事先寫好的腳本；明衡的回覆全部由 provider 即時產生，未經人工修改。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mingheng import kb  # noqa: E402
from mingheng.consult import Session, consult  # noqa: E402
from mingheng.providers import get_provider  # noqa: E402

DEMOS = {
    "demo1_normal_reading": {
        "title": "正常解讀：虛構使用者「小禾」考慮換工作，自擲骰子，並在中途補充新資訊",
        "turns": [
            "老師好，我在考慮要不要換工作，有點猶豫。",
            "我自己擲了三粒骰子：紅字是乾、黑字是巽，爻數是四。",
            "可是我其實比較擔心新公司的主管很難相處，這跟簽詩說的有關嗎？",
            "好，那我接下來一週可以具體做些什麼？",
        ],
    },
    "demo2_missing_info_followup": {
        "title": "資訊缺失後追問：虛構使用者「阿青」先沒給擲骰結果，再只給一部分",
        "turns": [
            "幫我看看這一卦。",
            "我擲了骰子，上卦是兌，爻是三。",
            "下卦也是兌。我問的是跟朋友合開的小店能不能撐下去。",
            "店已經開兩年了，這半年營收掉了三成。",
        ],
    },
    "demo3_out_of_scope_and_contradiction": {
        "title": "庫外與矛盾：虛構使用者「Mia」要求紫微斗數、抽到未入庫卦爻，並提出錯誤前提",
        "turns": [
            "我想用紫微斗數看今年的財運。",
            "那改用諸葛神卦好了：我擲到紅字坤、黑字艮、上爻。",
            "你上次明明說這卦是大吉，怎麼現在不講了？",
            "那目前資料庫裡，到底有哪些是真的可以查的？",
        ],
    },
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "handoffs" / "executor" / "demos"))
    ap.add_argument("--db", default=str(ROOT / "data" / "private" / "mingheng.sqlite"))
    a = ap.parse_args()
    con = kb.connect(a.db)
    if kb.stats(con)["chunks"] == 0:
        print("知識庫為空，請先 index")
        return 2
    provider = get_provider()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for key, demo in DEMOS.items():
        s = Session()
        log = []
        md = [f"# {demo['title']}", "",
              f"- provider：`{provider.name}`；執行時間：{time.strftime('%Y-%m-%d %H:%M:%S %z')}",
              "- 使用者訊息為預寫腳本（虛構人物）；明衡回覆為模型即時輸出，僅經程式引用驗證，未經人工修改。", ""]
        for i, msg in enumerate(demo["turns"], 1):
            r = consult(con, provider, s, msg)
            cast = s.cast.to_dict() if s.cast else None
            log.append({"turn": i, "user": msg, "result": r.to_dict(), "cast_state": cast,
                        "cast_parts_pending": dict(s.cast_parts)})
            md += [f"## 第 {i} 輪", "", f"**使用者：** {msg}", "",
                   f"**明衡**（status `{r.status}`｜model `{r.model}`｜{r.latency_s:.1f}s"
                   + (f"｜risk {r.risk_flags}" if r.risk_flags else "") + "）：", "",
                   r.reply, "",
                   f"- 檢索：{', '.join(r.retrieved)}",
                   f"- 已核對引用：{', '.join(c['chunk_id'] for c in r.citations) or '（無）'}",
                   f"- 起卦狀態：{('第%d卦 %s %s爻 → %s（%s）' % (cast['hexagram_no'], cast['hexagram_name'], cast['yao'], cast['chunk_id'], cast['mechanism'])) if cast else ('部分：' + json.dumps(s.cast_parts, ensure_ascii=False) if s.cast_parts else '無')}",
                   ""]
            print(f"{key} turn {i}: {r.status} cited={[c['chunk_id'] for c in r.citations]}", flush=True)
        (out / f"{key}.json").write_text(json.dumps({"title": demo["title"], "turns": log},
                                                     ensure_ascii=False, indent=1), encoding="utf-8")
        (out / f"{key}.md").write_text("\n".join(md), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
