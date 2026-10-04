# 給 GPT 的 FT-MVP-001 獨立覆核 Prompt（可整段貼上）

你是 firekou/FutuneTeller 的**獨立 reviewer**，覆核 Claude 交付的 FT-MVP-001。Claude 是 executor，不能核准自己的成果；你也不得修改 executor 的證據檔。

## 覆核對象
- Repository：https://github.com/firekou/FutuneTeller（public）
- PR：https://github.com/firekou/FutuneTeller/pull/1（draft；head 分支 `claude/trusting-archimedes-o0wvgy`，base `main`）
- base_sha：`071fe074fcf9e240613ab634c1343c18c79457d5`
- **tested content_head**：`7b0c6ae4cb04cc5b79ebd9157f415d47aa509c82`。所有程式、測試與評估以此 commit 為準。
- 其後的 commit 只應新增 `handoffs/executor/**` 與更新 `governance/state.json`、`README.md`。請以 live `git log` 與 `git diff 7b0c6ae..<PR head> -- mingheng app tests eval scripts data` 確認後續 commit 沒有改程式。若有改動，舊證據對新程式無效。
- 私有資料來源：Owner 的 Google Drive 資料夾（Owner 會另外提供存取）。S03 fileId 為 `1467XNln1cLfz7SvFzPuCG7gx3gxdmPUf`。不得更改分享權限，不得把原書或 OCR 全文貼進公開 repo 或 PR。

## 先讀
`AGENTS.md`、`docs/PROJECT_PLAN.md`（第 6 節是驗收標準）、`prompts/CLAUDE_EXECUTION_PROMPT.md`、`docs/SOURCE_AUDIT.md`（含執行者補充）、`docs/DATA_SETUP.md`、`handoffs/executor/FT-MVP-001.md`、`governance/state.json`。

## 驗收項目（逐項判定，證據等級使用 REPORTED / OBSERVED / TESTED / VERIFIED / REPRODUCED）
1. **來源盤點**：9 份 PDF 是否都有實際存取結果，未知項是否明確標記。請判斷「Drive MCP 10MB 下載上限，因而沒有 checksum 與圖像」這個阻擋是否屬實、是否記錄充分。
2. **起卦規則**：
   - 用 Drive 文字表示或原書目錄獨立抽查至少 5 個卦序與頁碼，建議包含第 2、12、30、45、59 卦，以及 executor 未測的卦。
   - 確認 `mingheng/zhuge.py` 的公式與前言「紅字上卦、黑字下卦、一粒爻數」一致。
   - 確認沒有由 LLM 選卦的路徑。
3. **校對子集**：
   - 抽查 `data/chunk_manifest.json` 中至少 8 個 chunk，建議包含 S03-P0004、P0012、P0016、P0018、P0028、P0035、P0051、P0054。
   - 比對 demo 與評估中『』引文和 Drive 文字是否一致，卦爻標頭是否正確。
   - 「圖像逐字校對 0 段」的狀態必須判為未達成，不得預設通過。
4. **人格與分層**：
   - system 層是否只有人格與規則，sources 與使用者訊息是否在 user 層；
   - 能力登錄表是否與實際資料一致；
   - 是否有冒充真人資歷、保證應驗等內容。
5. **引用驗證**：檢查 `consult.validate` 的邏輯。請以新的對抗性案例嘗試：捏造 chunk_id、改字的『』引文、無出處的卦爻解讀，確認都會被降級或標示。
6. **評估**：
   - 檢查 `eval/eval_set.json` 的預期是否事先標註，以及 `handoffs/executor/eval/eval_results_run3_final.json` 的 20 題逐題回覆。
   - 不要只看規則式 pass，請**人工判讀** 12 題邊界題。
   - 注意 executor 自承的過度擬合風險：同義詞表是看過 A5 後加入的。請用**你自己新寫的至少 5 題**可答題與 3 題邊界題重測，前提是你能取得私有資料並執行。
7. **多輪演示**：檢查 `handoffs/executor/demos/` 三組演示：
   - 是否為真實模型輸出（看 model 與延遲欄位、JSON 結構）；
   - 是否達成「正常解讀／資訊缺失追問／庫外或矛盾誠實回應」；
   - 是否有誘導重擲、過度延伸等瑕疵。
8. **可運行性**：
   - `pip install -r requirements.txt && python -m pytest -q`，預期 31 passed。
   - 能取得私有資料時，依 `docs/DATA_SETUP.md` 重建，執行 `streamlit run app/streamlit_app.py`，確認 UI 有資料健康、能力、起卦、來源定位、清除 session 等功能。
   - 對照 `handoffs/executor/screenshots/`。
9. **公開與私有分層**：
   - 檢查 PR 全部 diff，確認沒有原書 PDF、OCR 全文、私有整理稿、密鑰或帶簽名 URL。
   - 評估與演示中的短句引文與現代釋文轉述，是否符合 AGENTS.md 第 3 條。請提出建議，最終由 Owner 決定。
10. **流程**：
    - 確認分支名偏離 AGENTS.md（`claude/ft-mvp-001`）的原因已揭露；
    - PR 維持 draft，未自行合併；
    - `governance/state.json` 與 live 狀態一致。

## 輸出
寫入 `handoffs/reviewer/FT-MVP-001.md`，不得修改 `handoffs/executor/`。內容包含：
- reviewed_head：你實際檢查的 exact SHA；
- 你新增覆核文件的 commit 要分開記錄；
- 每一項的判定、證據等級、實際命令與 exit code；
- 發現的問題，分為 blocking 與 non-blocking；
- 最終決定只能是 `APPROVED`、`APPROVED_WITH_CONDITIONS`、`NEEDS_INFORMATION`、`BLOCKED` 之一。

來源或測試缺失時，不預設通過。結尾寫明：目前狀態、距離目標、下一個執行角色、最小下一步。
