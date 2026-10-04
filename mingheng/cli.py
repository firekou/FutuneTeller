"""命令列介面：import／index、search、cast、consult、stats。

python -m mingheng.cli index   [--corpus data/private/corpus.jsonl] [--db data/private/mingheng.sqlite]
python -m mingheng.cli search  "第三卦同人上爻"
python -m mingheng.cli cast    --upper 乾 --lower 離 --yao 上
python -m mingheng.cli consult "我想問合作的事"
python -m mingheng.cli stats
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import capabilities, kb, zhuge
from .consult import Session, consult
from .providers import get_provider

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = os.getenv("MINGHENG_DB", str(ROOT / "data" / "private" / "mingheng.sqlite"))
DEFAULT_CORPUS = os.getenv("MINGHENG_CORPUS", str(ROOT / "data" / "private" / "corpus.jsonl"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mingheng")
    ap.add_argument("--db", default=DEFAULT_DB)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("index")
    p.add_argument("--corpus", default=DEFAULT_CORPUS)
    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("-k", type=int, default=5)
    p = sub.add_parser("cast")
    p.add_argument("--upper")
    p.add_argument("--lower")
    p.add_argument("--yao")
    p.add_argument("--random", action="store_true")
    p = sub.add_parser("consult")
    p.add_argument("message")
    sub.add_parser("stats")
    a = ap.parse_args(argv)

    if a.cmd == "cast":
        c = zhuge.random_cast() if a.random else zhuge.cast(a.upper, a.lower, a.yao)
        print(json.dumps(c.to_dict(), ensure_ascii=False, indent=1))
        return 0

    con = kb.connect(a.db)
    if a.cmd == "index":
        if not Path(a.corpus).exists():
            print(f"corpus 不存在：{a.corpus}（請先執行 scripts/build_corpus.py）")
            return 2
        con.execute("DELETE FROM chunks")
        con.execute("DELETE FROM chunks_fts")
        n = kb.ingest(con, kb.load_jsonl(a.corpus))
        print(f"indexed {n} chunks -> {a.db}")
    elif a.cmd == "search":
        for h in kb.search(con, a.query, k=a.k):
            print(f"{h.score:8.2f}  {h.chunk_id:16s} {h.row.get('section')}  [{h.reason[:40]}]")
    elif a.cmd == "stats":
        s = kb.stats(con)
        print(json.dumps(s | {"capabilities": capabilities.as_dicts(s["chunks"])}, ensure_ascii=False, indent=1))
    elif a.cmd == "consult":
        r = consult(con, get_provider(), Session(), a.message)
        print(json.dumps(r.to_dict(), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
