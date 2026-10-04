"""由私有整理稿產生私有 corpus.jsonl 與可公開的 chunk manifest（不含典籍文字）。

用法：python scripts/build_corpus.py [--private-dir data/private]
輸入：<private-dir>/s03_transcription.py（gitignored，不在公開 repo）
輸出：<private-dir>/corpus.jsonl（私有）、data/chunk_manifest.json（公開，只含定位與 sha256）
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mingheng import zhuge  # noqa: E402
from mingheng.kb import sha256  # noqa: E402

S03 = {
    "source_id": "S03",
    "book_title": "諸葛神卦大註解",
    "source_variant": "227-諸葛神卦大註解_n.pdf",
    "source_drive_bytes": 24022746,
    # Drive MCP 未提供 md5Checksum；PDF 本體超過 MCP 10MB 下載上限，無法計算檔案 checksum
    "source_checksum": "UNAVAILABLE(drive_mcp_no_md5; download_limit_10MB)",
    "method": "諸葛神卦",
    "ocr_engine": "Google Drive text representation via Drive MCP read_file_content (engine/version not exposed), retrieved 2026-10-04",
    "rights_status": "UNKNOWN (owner-provided private copy; not cleared for redistribution)",
}
PROOF = "DRIVE_OCR_NORMALIZED; HEADER_STRUCTURE_VERIFIED_VS_TOC_RULE; NOT_IMAGE_VERIFIED"


def load_transcription(private_dir: Path):
    path = private_dir / "s03_transcription.py"
    if not path.exists():
        sys.exit(f"找不到私有整理稿 {path}；請依 docs/DATA_SETUP.md 準備。")
    spec = importlib.util.spec_from_file_location("s03_transcription", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(private_dir: Path) -> list[dict]:
    t = load_transcription(private_dir)
    recs: list[dict] = []
    for cid, layer, section, text in [
        ("S03-PREFACE-1", "原書前言（起卦方法）", "前言：骰子起卦法", t.PREFACE),
        ("S03-PREFACE-2", "原書前言（使用說明）", "前言：使用注意", t.PREFACE_2),
        ("S03-TOC-SUMMARY", "執行者整理之目錄結構摘要（非原文）", "目錄結構", t.TOC_NOTE),
    ]:
        recs.append({**S03, "chunk_id": cid, "layer": layer, "section": section, "text": text,
                     "pdf_page": None, "pdf_page_status": "UNKNOWN (front matter)",
                     "proof_status": "DRIVE_OCR_NORMALIZED; NOT_IMAGE_VERIFIED"})
    for (no, name, up, lo, yao, sign, note, expl) in t.ENTRIES:
        c = zhuge.cast(up, lo, yao)
        # 結構校核：整理稿標頭（卦序、上下卦、爻）須與目錄規則推得的頁碼一致
        assert c.hexagram_no == no, (no, up, lo)
        page = c.printed_page
        text = f"簽曰：{sign}\n原註：{note}\n釋文（節錄）：{expl}"
        recs.append({
            **S03,
            "chunk_id": c.chunk_id,
            "layer": "簽詩＋原註＋現代註者釋文節錄",
            "section": f"第{no}卦 {name}（上{up}下{lo}）{yao}爻",
            "hexagram_no": no, "hexagram_name": name, "upper": up, "lower": lo, "yao": yao,
            "printed_page": page, "pdf_page": c.pdf_page_estimated,
            "pdf_page_status": c.pdf_page_status,
            "sign": sign, "original_note": note, "explanation": expl, "text": text,
            "aliases": "姤" if name == "垢" else "",
            "proof_status": PROOF,
        })
    return recs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", default=str(ROOT / "data" / "private"))
    ap.add_argument("--manifest", default=str(ROOT / "data" / "chunk_manifest.json"))
    a = ap.parse_args()
    pdir = Path(a.private_dir)
    recs = build(pdir)
    out = pdir / "corpus.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    manifest = [{k: r.get(k) for k in ("chunk_id", "source_id", "section", "hexagram_no", "yao",
                                         "printed_page", "pdf_page", "pdf_page_status",
                                         "layer", "proof_status")} | {"text_sha256": sha256(r["text"])}
                for r in recs]
    Path(a.manifest).parent.mkdir(parents=True, exist_ok=True)
    with open(a.manifest, "w", encoding="utf-8") as f:
        json.dump({"source": {k: S03[k] for k in ("source_id", "book_title", "source_variant",
                                                   "source_drive_bytes", "source_checksum",
                                                   "ocr_engine", "rights_status")},
                   "corrections_applied": getattr(load_transcription(pdir), "CORRECTIONS", []),
                   "chunks": manifest}, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(recs)} records -> {out}; manifest -> {a.manifest}")


if __name__ == "__main__":
    main()
