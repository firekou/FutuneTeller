# 私有資料準備（FT-MVP-001）

本 repo 是 public。原書 PDF、OCR 全文、整理後的典籍文字**一律不提交**，放在 `data/private/`（已 gitignore）。

## 目前的私有資料
| 檔案 | 內容 | 產生方式 |
| --- | --- | --- |
| `data/private/s03_transcription.py` | S03《諸葛神卦大註解》_n 版：前言（起卦法）、目錄結構摘要、第 1–9 卦 54 爻之簽曰／原註全文與釋文節錄 | 執行者由 Google Drive 文字表示（Drive MCP `read_file_content`）整理，修正明顯 OCR 字形錯誤，修正清單見 `data/chunk_manifest.json` 的 `corrections_applied` |
| `data/private/corpus.jsonl` | 57 個引用單位（含 metadata） | `python scripts/build_corpus.py` |
| `data/private/mingheng.sqlite` | SQLite + FTS5 索引 | `python -m mingheng.cli index` |

公開 repo 只保留 `data/chunk_manifest.json`：每段的 chunk_id、卦爻、印刷頁、推估 PDF 頁、校對狀態與文字 sha256（不含文字），讓 reviewer 用自己的授權副本重建後比對雜湊。

## Reviewer／Owner 重建步驟
1. 以既有授權開啟 Owner 的 Drive 資料夾（不要更改分享設定）。
2. 取得 S03 `227-諸葛神卦大註解_n.pdf` 的文字：Drive MCP `read_file_content(fileId=1467XNln1cLfz7SvFzPuCG7gx3gxdmPUf)`，或下載 PDF 後自行 OCR。
3. 依 `data/chunk_manifest.json` 的段落定位，建立 `data/private/s03_transcription.py`（格式見 `scripts/build_corpus.py`），再執行
   `python scripts/build_corpus.py && python -m mingheng.cli index`。
4. 比對 `data/chunk_manifest.json` 的 `text_sha256`：若你沿用執行者的整理稿可完全一致；若自行 OCR，雜湊會不同，請改以頁面對照檢查內容。
5. 頁面對照（需本地 PDF 與 pymupdf）：
   `python scripts/verify_pages.py --pdf data/private/227-諸葛神卦大註解_n.pdf --chunks S03-P0018 S03-P0035 ...`

## 已知限制
- Drive MCP 單檔下載上限 10MB，9 份 PDF 皆超過，執行者**無法下載 PDF 本體**，因此沒有檔案 checksum，也沒有逐頁圖像校對；校對狀態標為 `NOT_IMAGE_VERIFIED`。
- Drive 文字表示在約印刷頁 58 處截斷；第 10 卦以後未入庫。
- 印刷頁→PDF 頁的位移 22 只有一個錨點（SOURCE_AUDIT 記錄 PDF 40 = 印刷 18），其餘為推估。
