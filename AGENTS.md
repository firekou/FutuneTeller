# FutuneTeller 工作規則
1. 最新 Owner 指示優先。先讀 README、docs/PROJECT_PLAN.md、docs/SOURCE_AUDIT.md、governance/state.json 與本檔。
2. GPT 本輪為規劃文件作者；Claude 為 FT-MVP-001 執行者。作者不能獨立核准自己的內容。
3. repo 是公開的。禁止提交原始典籍、完整 OCR、密鑰、帶簽名 URL、個案個資。使用私有本地資料目錄並 gitignore。
4. 一次只做一個工作包。FT-MVP-001 在 claude/ft-mvp-001 分支交付，建立 draft PR，停止於 READY_FOR_REVIEW；未通過獨立覆核不自行合併。
5. 執行結果放 handoffs/executor/；獨立覆核放 handoffs/reviewer/，不得覆寫對方證據。
6. 每次紀錄 work_id、role、base_sha、content_head、changed_paths、實際命令與退出碼、結果、限制、next_checkpoint。文件描述與 commit 狀態不符時以 live 狀態為準。
7. 覆核 vocabulary：APPROVED、APPROVED_WITH_CONDITIONS、NEEDS_INFORMATION、BLOCKED。來源與測試缺失不預設通過。
8. 證據等級：REPORTED 自述、OBSERVED 看見、TESTED 有測試、VERIFIED 獨立查核、REPRODUCED 獨立重現。README 或截圖不等同真實完整運行。
9. 改動實作或證據後舊覆核失效。reviewed_head 和後加覆核文件的 commit 分開記。
10. 現階段只授權規劃與有界本地原型。新付費服務、正式公開部署、資料分享權限更動另需 Owner 決定；不能因此停止無依賴的本地工作。
11. 未驗證的 Claude 喚醒／排程狀態為 NOT_ENABLED；寫入 GitHub 不代表 Claude 已接單。
12. 所有回報結尾寫：目前狀態、距離目標、下一個執行角色、最小下一步。
