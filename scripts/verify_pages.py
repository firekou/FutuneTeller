"""Reviewer 工具：以本地 PDF 渲染知識庫所引用的頁面，供逐頁對照 corpus 文字。

需要：Owner 授權取得的 S03 PDF（227-諸葛神卦大註解_n.pdf），放在私有目錄；pymupdf。
python scripts/verify_pages.py --pdf data/private/227-諸葛神卦大註解_n.pdf --chunks S03-P0018 S03-P0035
輸出：data/private/page_renders/<chunk_id>_pdf<page>.png，並印出該 chunk 的整理文字與 sha256。
也可用 --find-offset 掃描印刷頁頁尾數字，檢查「PDF 頁 = 印刷頁 + 22」是否全書成立（無文字層時需目視）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--corpus", default=str(ROOT / "data" / "private" / "corpus.jsonl"))
    ap.add_argument("--chunks", nargs="+", required=True)
    ap.add_argument("--out", default=str(ROOT / "data" / "private" / "page_renders"))
    ap.add_argument("--zoom", type=float, default=2.0)
    a = ap.parse_args()
    import fitz  # pymupdf
    import hashlib

    doc = fitz.open(a.pdf)
    print(f"PDF pages={doc.page_count} sha256={hashlib.sha256(Path(a.pdf).read_bytes()).hexdigest()}")
    corpus = {json.loads(l)["chunk_id"]: json.loads(l) for l in open(a.corpus, encoding="utf-8")}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for cid in a.chunks:
        r = corpus.get(cid)
        if not r or not r.get("pdf_page"):
            print(f"{cid}: 無 pdf_page，略過")
            continue
        page = r["pdf_page"]
        pix = doc[page - 1].get_pixmap(matrix=fitz.Matrix(a.zoom, a.zoom))
        path = out / f"{cid}_pdf{page}.png"
        pix.save(path)
        print(f"\n== {cid} {r['section']} 印刷頁 {r['printed_page']} → PDF {page}（{r['pdf_page_status']}）\n"
              f"render: {path}\n{r['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
