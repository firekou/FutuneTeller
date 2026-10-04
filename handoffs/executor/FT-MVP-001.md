# FT-MVP-001 執行報告（Claude executor）

| 欄位 | 值 |
| --- | --- |
| work_id | FT-MVP-001 |
| role | executor（Claude）；不得自行核准 |
| base_sha | `071fe074fcf9e240613ab634c1343c18c79457d5`（origin/main，開工時 live 讀取） |
| tested content_head | `7b0c6ae4cb04cc5b79ebd9157f415d47aa509c82`（全部最終測試、評估、演示、截圖皆在此 commit 上執行；執行時程式目錄 dirty=0） |
| report/evidence commit | 在 content_head 之後另加，只新增 `handoffs/executor/**` 及更新 `governance/state.json`，不改程式；以 `git log` 為準 |
| branch / PR | `claude/trusting-archimedes-o0wvgy` → draft PR [firekou/FutuneTeller#1](https://github.com/firekou/FutuneTeller/pull/1) |
| 狀態 | READY_FOR_REVIEW |
| 日期 | 2026-10-04 |

> 分支說明：AGENTS.md 指定 `claude/ft-mvp-001`，但本次 Claude Code session 的系統設定限定只能推送到 `claude/trusting-archimedes-o0wvgy`，未經許可不得推送其他分支。內容與工作包一致；如需改名，由 Owner 決定。

## 1. 交付內容（changed_paths）
- `mingheng/`：
  - `zhuge.py`：起卦規則
  - `kb.py`：匯入、索引、檢索（SQLite FTS5，中文二元字組）
  - `capabilities.py`：能力登錄表
  - `safety.py`：高風險與注入偵測
  - `providers.py`：模型介接，有 `claude_cli`、`anthropic`、`openai_compatible`、`none` 四種
  - `consult.py`：諮詢流程與引用驗證
  - `cli.py`：命令列
- `app/streamlit_app.py`：本地 UI
- `eval/eval_set.json`：20 題評估集，預期結果在執行前已標註；`eval/run_eval.py`：評估執行器
- `scripts/`：
  - `build_corpus.py`：產生私有 corpus 與公開 manifest
  - `run_demo.py`：多輪演示
  - `screenshot_ui.py`：UI 截圖
  - `verify_pages.py`：供 reviewer 渲染 PDF 頁面對照
- `tests/`：31 個單元測試，並附合成 fixture
- `data/chunk_manifest.json`：公開的段落定位與 sha256，不含典籍文字
- 文件與設定：`docs/DATA_SETUP.md`、`docs/SOURCE_AUDIT.md`（附加執行者盤點，未改 GPT 原段落）、`README.md`、`.gitignore`、`.env.example`、`requirements.txt`、`requirements.lock`、`pytest.ini`
- 私有、未提交：`data/private/s03_transcription.py`、`corpus.jsonl`、`mingheng.sqlite`

## 2. 執行順序與結果

### A. 真實資料盤點（OBSERVED）
- 9 份 PDF 都以 Drive MCP 實際列出並讀取，只讀，未改分享權限。逐份結果見 `docs/SOURCE_AUDIT.md`「FT-MVP-001 執行者補充盤點」。
- **阻擋**：`download_file_content` 對 9 份皆回傳 `File too large for download, over limit of 10 MB`，所以：
  - 沒有 PDF 本體、沒有檔案 checksum、沒有逐頁圖像；
  - Drive 也沒有回傳 md5。
  - 最小需求：Owner 在本地提供 S03 PDF，或授權使用 Drive API 直接下載。
- 只有 S03、S05、S07 的 `_n` 版有可讀內文，且 Drive 文字表示都在全書約 25–30% 處截斷。
- S01、S08 無文字層。S02、S09 為封面。S04、S06 回傳空白。
- `_n`／`_c` 的關係只是 OBSERVED 傾向，不是定論；S04（114MB）未能檢視。
- 選用來源：S03 `_n`。原書前言明載起卦法，目錄完整列出 64 卦×6 爻的頁碼。

### B. 校對子集（部分達成）
- 共 57 段：S03 前言 2 段、目錄結構摘要 1 段（標為執行者整理，非原文）、第 1–9 卦 54 爻。54 爻皆含簽曰與原註全文，以及釋文節錄。
- **結構校核（TESTED）**：54 爻的卦序、上下卦、爻位標頭都由 `build_corpus.py` 以目錄規則 assert 檢查，全部一致。
- **文字校對（未達成）**：沒有原頁圖像，未逐字對原圖校對，標為 `NOT_IMAGE_VERIFIED`。另有 9 類明顯 OCR 字形修正，清單在 manifest 的 `corrections_applied`。
- 印刷頁→PDF 頁的換算（+22）只有一個錨點。
- 結論：「至少 20 段經核對」中，**結構核對有 54 段；圖像逐字核對 0 段，此項 BLOCKED**，需要 PDF 本體。

### C. 人格與規則（TESTED）
- 起卦規則：`卦序 = 上卦序×8 + (下卦序−上卦序) mod 8 + 1`，`印刷頁 = (卦序−1)×6 + 爻序`，八卦順序為乾兌離震巽坎艮坤。
  - 以 8 個目錄條目驗證，涵蓋第 1、3、15、38、46、50、51、64 卦（`tests/test_core.py`）。
  - 64 卦唯一，384 頁全覆蓋。
  - 只支援兩種輸入：使用者自擲的結果，或明示的 `secrets.SystemRandom` 模擬。
- 卦名：50 個取自目錄 OCR，3 個取自釋文頁；11 個在目錄中 OCR 遺失，依上下卦推定，標為 `inferred`。
- 能力登錄表：諸葛神卦典籍問答、起卦查表為 enabled；相術為 reference-only；拆字、取名、風水、八字紫微為 unavailable，各附原因。
- 分層：MASTER_SYSTEM_PROMPT 加上執行端規則放在 system 層；`<capabilities>`、`<sources>`、`<tool_result>`、`<guardrails>` 與使用者訊息放在 user 層。測試會確認 sources 不進 system 層。
- 引用驗證：
  - 〔chunk_id〕不在本輪檢索結果內，就移除並降級為 DEGRADED。
  - 『』引文要逐字對得上（忽略標點），對不上就降級。
  - 卦爻問題沒有任何出處時，標為 UNCITED 並附提示。
  - 危機訊息一定附上 1925 等求助資源。

### D. 可運行原型（TESTED / OBSERVED）
- UI 經 Playwright 實際操作，截圖在 `handoffs/executor/screenshots/`：
  - 01：資料健康與能力範圍
  - 02：帶入擲骰結果（乾／離／上），得到真實模型回覆，展開來源定位（S03-P0018）
  - 03：追問庫外方法（紫微）
  - 04：清除 session 後
- Provider：本環境沒有 ANTHROPIC_API_KEY；環境中有一個用途不明的使用者金鑰，未使用。實際使用的是環境已授權的 Claude Code CLI（`claude -p`，在空目錄執行、停用工具、替換 system prompt）。回報模型為 `claude-sonnet-5-5`。

### E. 評估與交付（TESTED）

最終在 content_head 上執行的命令（`handoffs/executor/logs/final_run_commands.log`）：

| 命令 | exit | 結果 |
| --- | --- | --- |
| `python scripts/build_corpus.py` | 0 | 57 records；重建後的 manifest 與 commit 版本相同（git diff 為空） |
| `python -m mingheng.cli index` | 0 | indexed 57 chunks |
| `python -m pytest -q` | 0 | 31 passed |
| `python eval/run_eval.py` | 0 | 見下表 |
| `python scripts/run_demo.py` | 0 | 3 組演示 × 4 輪 |
| `python scripts/screenshot_ui.py` | 0 | 4 張截圖 |

（`index` 與 `pytest` 的輸出在最終腳本中寫入同一檔名而互相覆蓋，故另以 `logs/index_7b0c6ae.out`、`logs/pytest_7b0c6ae.out` 在同一 head 重跑保存。）另在乾淨 venv 執行 `pip install -r requirements.txt` 後 `pytest`，exit 0，得到 28 passed（當時的測試數），並以此產出 `requirements.lock`。

**20 題評估**（`eval/eval_set.json`，預期在執行前標註）：

| 執行 | 程式狀態 | top-5 召回 | 可答題 | 邊界題 | 引用數／核對警告 |
| --- | --- | --- | --- | --- | --- |
| run1 | content_head 之前的工作樹 | **7/8**（A5 漏檢） | 7/8 | 12/12（規則檢查） | 16/0 |
| run2 | 加入同義詞與查表工具後 | 8/8 | 8/8 | 12/12 | 21/0 |
| run3_final | `7b0c6ae` | **8/8**（門檻 7/8） | **8/8** | **12/12**（門檻 12/12） | **20/0** |

- run1 的失敗都保留，未覆蓋：
  - A5：問「合夥」，原文用「合作」，bigram 檢索漏檢。修正方式是加入小型口語同義詞表（`kb.SYNONYMS`，可審查）。**此修正是看過評估題後加入的，有對評估集調參的風險**，請 reviewer 用新題目重測。
  - B2：規則檢查判為 pass，但**人工覆核發現模型自行推算「大壯可能是第 32 卦」，這是錯的**。修正方式是：問題指名卦序、卦名或上下卦時，由確定性工具提供 `zhuge_lookup` 查表結果。
  - run2 的 C1：查詢「上兌下坤」被誤記為部分擲骰。修正方式是收窄擲骰語境的判斷。
- 規則式檢查只是關鍵字比對。我已逐題人工閱讀 run1 與 run3 的 B、C、D、E 類回覆，但這只是執行者自評（REPORTED），**不等於獨立覆核**。

**3 組多輪演示**（`handoffs/executor/demos/*.md|json`；使用者訊息是預寫腳本、人物虛構；回覆是模型即時輸出，未經人工修改）：
1. `demo1_normal_reading`：使用者想換工作，擲出乾／巽／四爻，查得第 5 卦垢四爻（S03-P0028）。第 3 輪使用者補充「擔心主管」，明衡指出簽詩沒有談到這點，不硬套。
2. `demo2_missing_info_followup`：使用者先沒給卦，再只給上卦和爻。明衡只追問缺少的下卦；資料補齊後查得兌三爻（S03-P0051），並依「開兩年、營收掉三成」調整建議。
3. `demo3_out_of_scope_and_contradiction`：
   - 使用者要求紫微斗數，明衡說明未啟用。
   - 擲出坤／艮／上，對應第 64 卦謙上爻（印刷頁 384），明衡說明該頁未入庫，不補寫簽詩。
   - 使用者聲稱「你上次說大吉」，明衡更正自己沒說過。
   - 最後如實列出可查與不可查的範圍。

觀察到的瑕疵（未修，留給 reviewer 判斷）：
- demo2 第 1 輪，明衡在不知道卦時主動舉例「若是第 8 卦否初爻…」，有輕微的誘導性。
- 一般能力說明類回覆有時會被標成 UNCITED，屬保守的假陽性。
- demo 與評估中，未入庫頁的處理建議包括「重擲一次」，可能鼓勵為了換結果而重擲；部分回覆有提醒「換結果不代表比較準」，但不一致。

## 3. 安全與公開檢查
- 提交前檢查 staged diff：沒有 PDF、OCR 全文、私有整理稿、sqlite、`.env` 或密鑰。唯一符合 `corpus.jsonl` 檔名規則的是合成 fixture，內容為虛構。
- `data/chunk_manifest.json` 的 `corrections_applied` 含數個 2–4 字的 OCR 修正片段。
- **需要 Owner 決定**：`handoffs/executor/eval/*.json` 與 `demos/*` 是模型回覆，內含簽詩或原註的短句引文，以及現代註者釋文的轉述或短引。全書 2004 年的現代註解權利狀態 UNKNOWN。若 Owner 認為不宜公開，應改放私有位置，並重寫 git 歷史或另開乾淨分支。
- 對話預設只存在 session，不寫檔；密鑰只從環境變數讀取，不送到前端。

## 4. 限制與未完成（不得視為通過）
1. 圖像逐字校對 0 段（BLOCKED：需要 PDF 本體）。PDF 頁碼僅為推估。
2. 只入庫第 1–9 卦，其餘 330 爻未入庫。
3. 拆字、取名、風水、相術皆未入庫或未啟用；S04 `_c` 未比對；全書總頁數與版本差異未確認。
4. 檢索是 bigram 加小型同義詞表，對語意改寫的召回有限。評估集只有 8 題可答題，樣本小。
5. 模型為 claude_cli 環境授權模型，未測其他 provider 的實際回覆，只測了介面。
6. 只在本地原型層級運行：無存取控制、無部署。依規定不進行正式部署。
7. 權利狀態 UNKNOWN（見第 3 節）。

## 5. Reviewer 重現方式
- **不需私有資料**：
  - `pip install -r requirements.txt && python -m pytest -q`，預期 31 passed，涵蓋起卦規則的 8 個目錄條目。
  - 也可閱讀 `handoffs/executor/eval/eval_results_run3_final.json` 的 20 題逐題回覆與檢查結果。
- **以授權來源重現資料**：
  - 用 Drive `read_file_content(1467XNln1cLfz7SvFzPuCG7gx3gxdmPUf)` 取得 S03 文字，抽查 manifest 中的 chunk_id，例如 S03-P0018、P0028、P0035、P0051 的卦爻、頁碼，以及 demo 或評估中『』引文是否與 Drive 文字一致。
  - 若 Owner 提供 PDF，執行 `scripts/verify_pages.py` 渲染頁面，做圖像校對。
- **全流程重跑**：需要 Owner 私下提供 `data/private/s03_transcription.py`，或依 `docs/DATA_SETUP.md` 自建。之後依序執行 `build_corpus.py`、`cli index`、`eval/run_eval.py`、`run_demo.py`、`streamlit run app/streamlit_app.py`。

## 6. 給 GPT 的獨立覆核 Prompt
見 [`handoffs/executor/GPT_REVIEW_PROMPT.md`](GPT_REVIEW_PROMPT.md)，可直接整段貼給 GPT。

---
- 目前狀態：READY_FOR_REVIEW；draft PR firekou/FutuneTeller#1；tested content_head `7b0c6ae`。
- 距離目標：P2 閉環已能實際使用：起卦查表、典籍問答、引用核對、多輪 UI。尚缺的有：
  - 圖像逐字校對，需要 PDF 本體；
  - 其餘 330 爻與其他方法入庫；
  - 權利決定。
- 下一個執行角色：GPT（獨立 reviewer）。
- 最小下一步：GPT 依覆核 Prompt 檢查 PR 的 exact head，結果寫入 `handoffs/reviewer/FT-MVP-001.md`。另外 Owner 決定兩件事：是否提供 S03 PDF 本體供圖像校對；演示中的短句引文能否公開。
