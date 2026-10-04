# FutuneTeller｜命理諮詢大師
以使用者提供的命理典籍資料庫，建立具一致人格、可追溯引用、可實際互動的 AI 命理諮詢服務。

## 專案入口
- [目標與完整藍圖](docs/PROJECT_PLAN.md)
- [資料庫盤點與閱讀證據](docs/SOURCE_AUDIT.md)（含 FT-MVP-001 執行者補充）
- [私有資料準備與重建](docs/DATA_SETUP.md)
- [命理大師人格 System Prompt](prompts/MASTER_SYSTEM_PROMPT.md)
- [交給 Claude 的完整執行 Prompt](prompts/CLAUDE_EXECUTION_PROMPT.md)
- [FT-MVP-001 執行報告](handoffs/executor/FT-MVP-001.md)
- [目前工作狀態](governance/state.json)
- [執行與覆核規則](AGENTS.md)

## 目前狀態
2026-10-04：FT-MVP-001 本地原型已實作，狀態 **READY_FOR_REVIEW**（尚未經獨立覆核，不得稱為已上線或已完成）。
- 已啟用：諸葛神卦三骰起卦查表（依原書前言與目錄推得之確定性規則）；S03 前言與第 1–9 卦 54 爻的典籍問答（引用經後端核對）。
- 未完成：其餘 330 爻、拆字、取名、風水、相術均未入庫；入庫文字取自 Drive OCR，**未逐頁對原圖校對**；無 PDF checksum（Drive MCP 10MB 下載上限）。
- 定位：傳統命理文化與象徵解讀，不保證預測準確。

## 快速開始（本地）
```bash
pip install -r requirements.txt            # 或 pip install -r requirements.lock
python scripts/build_corpus.py             # 需要私有整理稿 data/private/s03_transcription.py，見 docs/DATA_SETUP.md
python -m mingheng.cli index               # 建 SQLite FTS5 索引
python -m pytest -q                        # 單元測試（只用合成 fixture，不需私有資料）
streamlit run app/streamlit_app.py         # 開啟 http://localhost:8501
```
模型 provider 由環境變數 `MINGHENG_PROVIDER` 決定（`claude_cli`／`anthropic`／`openai_compatible`／`none`），見 `.env.example`。沒有私有資料時，UI 顯示「知識庫未就緒」；側欄「測試模式」只載入明示為虛構的合成資料。

其他命令：
```bash
python -m mingheng.cli search "第三卦同人上爻"
python -m mingheng.cli cast --upper 乾 --lower 離 --yao 上
python -m mingheng.cli consult "我想問合作的事"
python eval/run_eval.py                    # 20 題評估（真實模型）
python scripts/run_demo.py                 # 3 組多輪演示（真實模型）
python scripts/screenshot_ui.py            # 實際操作 UI 並截圖
```

## 架構
`mingheng/zhuge.py` 起卦規則 ｜ `kb.py` 匯入／索引／檢索（SQLite FTS5＋中文二元字組）｜ `capabilities.py` 能力登錄表 ｜ `safety.py` 高風險與注入偵測 ｜ `providers.py` 模型介接 ｜ `consult.py` 檢索→分層組裝→模型→引用驗證→降級 ｜ `app/streamlit_app.py` 本地 UI。

Repository 維持使用者指定拼字 FutuneTeller。
