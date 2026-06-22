# 🎬 AgentClinic — Demo 影片懶人包

> 照這份做,不用動腦。≤3 分鐘｜全螢幕錄影｜AI 英文旁白 + 英文字幕｜上 YouTube
> 純錄屏路線,不用 Veo / 不用 AI 痛點動畫。

---

## ⚡ 三步驟總流程(先看這個)

1. **錄螢幕**(7 段,每段獨立 take,失敗那段重來就好)
2. **生 AI 旁白**(把最後的純英文整段稿一次貼進 ElevenLabs / OpenAI TTS)
3. **剪接合成 → 上字幕(SRT) → 上 YouTube → Devpost 貼連結**

錄影前先 `uipath auth` warm tokens 一次,免得錄到一半 token 過期跳重 auth 視窗。

---

## 📋 七段結構表

| 段 | 內容 | 長度 | 鏡頭 |
|---|---|---|---|
| 1 | 痛點開場 + 證據鏈 hook | 18s | Test Manager 列表 → Override Result dialog hold |
| 2 | 七大偵測器 + Evidence Contract | 25s | VS Code: detect.py + golden trace JSON |
| 3 | 本機跑通 CLI | 22s | 終端機 publish 指令 → JSON output |
| 4 | Cloud runtime 觸發 ⭐ 合規關鍵 | 30s | Orchestrator → Process → Start now → Test Cloud 新 execution |
| 5 | 四角色架構 | 20s | 靜態卡(可用 README 截圖) |
| 6 | 25 commits ledger | 18s | GitHub repo / git log |
| 7 | 收尾 + pitch | 12s | End frame 靜態 |

總長 **2 分 25 秒**,安全在 3 分鐘內、留 buffer。

---

## 🖥️ Pre-flight checklist(錄影前 5 分鐘做完)

- [ ] 瀏覽器:三個 tab 都登入好
  - Test Manager UI:`staging.uipath.com/hackathon26_596/DefaultTenant/testmanager_/ACR2/testexecutions`
  - Orchestrator Process detail:`agentclinic-coded-agent` v0.1.1
  - GitHub repo:`https://github.com/rainingsnow0914tw-ship-it/agentclinic`
- [ ] VS Code 開三個分頁:`main.py` / `core/agentclinic/detect.py` / `examples/golden_traces/01_hard_hat_loop.golden.json`
- [ ] 終端機 cwd 在 `RaidMeter-UiPath`,publish 指令**預打好但不要按 Enter**:
  ```
  PYTHONPATH=core python -m agentclinic publish examples/golden_traces/01_hard_hat_loop.golden.json --project-name "AgentClinic Reports v2" --project-prefix ACR2 --coach uipath
  ```
- [ ] 桌面背景乾淨(沒個人照片 / 無關 app)
- [ ] 瀏覽器書籤列隱藏(`Ctrl+Shift+B`)
- [ ] Windows 通知關閉(Focus Assist 設「Alarms only」)
- [ ] Slack / Discord / 信箱通通關
- [ ] 螢幕解析度 1920×1080(16:9)
- [ ] Test Manager 瀏覽器 zoom 110-125%(評審看 reason 不用瞇眼)
- [ ] 工作列 tray icons 隱藏非必要

---

# 📺 七段詳細腳本

## 第 1 段(18s)痛點開場 + 證據鏈 hook

**畫面:**
- 0-5s:Test Manager → ACR2 → Executions 列表,5 條 execution 紅綠 Results bar 視覺
- 5-13s:點最新一條 `exec:trace_gold_001/run_deploy_4x` → 進 detail → 點 `⋮` → **Override Result**
- 13-18s:Dialog 跳出,**hold 5 秒**讓 multi-line reason 整段顯示在畫面上(評審讀)

**旁白:**
- 🇬🇧 *"AI agents ship to production faster than any prior software category — but the testing discipline traditional software earned over decades hasn't caught up. This is AgentClinic. Every finding bound to evidence in the trace, published natively into UiPath Test Cloud."*
- 🇹🇼 AI agent 上線速度是過去任何軟體都比不上的,但傳統軟體幾十年累積的測試紀律還沒跟上。這就是 AgentClinic — 每個 finding 都釘在 trace 證據上,直接寫進 UiPath Test Cloud。

---

## 第 2 段(25s)七大偵測器 + Evidence Contract

**畫面:**
- 0-10s:VS Code 切到 `core/agentclinic/detect.py`,捲過七個 detector 函數(各掃 1 秒)
- 10-20s:切到 `examples/golden_traces/01_hard_hat_loop.golden.json`,捲到 `events[]`,**hover** 在 `state_hash: "S0"` 停 2 秒,讓觀眾看到四次 retry 同個 hash
- 20-25s:切到產出的 `report.md` Section 2,**圈起** `evidence_spans: [evt_0002, evt_0003, evt_0004]`

**旁白:**
- 🇬🇧 *"Seven deterministic detectors, source-controlled. Every finding must point at specific trace events as evidence — a finding without an evidence span is a contract violation, rejected at the schema layer. The score is reproducible: same trace, same rules, same number, every time."*
- 🇹🇼 七個確定性偵測器,版本管理。每個 finding 必須指向 trace 上特定事件當證據 — 沒證據的 finding 違反 contract、直接被 schema 退回。分數可重現:同樣的 trace、同樣的規則、永遠同樣的數字。

---

## 第 3 段(22s)本機跑通 CLI

**畫面:**
- 0-3s:切終端機,publish 指令已預打,**按下 Enter**
- 3-15s:**不要 cut** — 讓真實 CLI 跑 10-12 秒(這是 credibility 最強的鏡頭,真實執行)
- 15-22s:輸出 JSON 出現,捲到 `test_cloud.execution.id` 跟 `test_cloud.logs[0].result: "Failed"`、`result_override_error: null`、`publish_error: null`

**旁白:**
- 🇬🇧 *"Run it locally first. The CLI normalizes the trace, detects seven waste patterns, scores L0 to L3, then publishes natively into Test Cloud. No mocks. The execution ID, test set, and case log are all real. Live."*
- 🇹🇼 先在本機跑一次。CLI 把 trace 正規化、偵測七種浪費 pattern、評分 L0 到 L3、然後直接寫進 Test Cloud。沒有任何造假。execution ID、test set、log 全部都是真的、即時的。

---

## 第 4 段(30s)Cloud runtime 觸發 ⭐ 合規關鍵

**畫面:**
- 0-5s:切 Orchestrator → Processes → `agentclinic-coded-agent` 0.1.1 detail → 點 **Start now**
- 5-10s:Job 提交 dialog,Trace 已預貼,確認送出
- 10-18s:Jobs 列表,新 job **Running → Successful**(實際 30 秒,**剪成 8 秒**但保留 "Running" 狀態 3 秒讓觀眾看到真在跑)
- 18-25s:切 Test Manager → ACR2 → Executions,F5 重整,新 row 跑出來,點進去
- 25-30s:點 Failed 那條 → Override Result → **hold 5 秒**展示 multi-line evidence-bound reason

**旁白:**
- 🇬🇧 *"Same agent, this time triggered from Automation Cloud. Same pipeline as the local runtime — but now writing directly into Test Manager. One Test Case per pattern, reusable across runs. The evidence-bound reason is visible right in the dialog reviewers already use. Quality is no longer a late-stage checkpoint."*
- 🇹🇼 同一個 agent,這次從 Automation Cloud 觸發。和本機跑的是同一條 pipeline — 但結果直接寫進 Test Manager。每個 pattern 一個可重用的 Test Case。Evidence-bound 的 reason 直接顯示在評審本來就在用的對話框裡。Quality 不再是 release 末期才檢查的關卡。

**💡 這段是整支影片的 climax。錄壞重來。**

---

## 第 5 段(20s)四角色架構

**畫面:**
靜態卡(用 README 截圖或自製簡單黑底文字):

```
👨‍⚖️ JUDGE        deterministic rule engine — runs without an LLM
🏃  COACH        LLM, bounded — translate findings, forbidden to judge
📋 RECORDER      UiPath Test Cloud — execution + log + attachment
🎼 ORCHESTRATOR  UiPath — Process + AI Trust Layer audit
```

每個角色淡入,各 ~5 秒。

**旁白:**
- 🇬🇧 *"Four roles, no overlap. Judge is deterministic — the LLM cannot revise the verdict. Coach rides UiPath's AgentHub LLM Gateway, every call inside the AI Trust Layer. No direct LLM provider API key. Test Cloud is the system of record. UiPath ties it all together."*
- 🇹🇼 四個角色,責任不重疊。Judge 是確定性的 — LLM 不准翻案。Coach 走 UiPath 的 AgentHub LLM Gateway,每次呼叫都在 AI Trust Layer 裡。沒有直接接 LLM 廠商的 API key。Test Cloud 是紀錄系統。UiPath 把所有東西串起來。

---

## 第 6 段(18s)25 commits ledger ⭐ Coding Agents +2

**畫面:**
- 0-8s:切 GitHub repo 頁,CI badge 綠勾,README 第一段(badge bar + tagline)停 3 秒
- 8-18s:開終端機跑 `git log --oneline | head -25`,讓 commits 跑過

**旁白:**
- 🇬🇧 *"Every line of source, every commit message, every documentation file in this repository was written by Claude Code over eleven days. Twenty-plus commits, every one visible in the log. The human role was driver — framing, vetting, correcting, performing the GUI actions Claude can't."*
- 🇹🇼 這個 repo 的每一行 source code、每一個 commit message、每一份文件,都是 Claude Code 在 11 天內寫的。20 幾個 commit、log 上一個都不少。人類的角色是駕駛 — 設定方向、審查、糾正、執行 Claude 不能做的 GUI 操作。

---

## 第 7 段(12s)收尾 + pitch

**畫面:**
End frame 靜態卡:

```
github.com/rainingsnow0914tw-ship-it/agentclinic

AgentClinic
Forensic analysis for AI agents · Native to UiPath Test Cloud

UiPath AgentHack 2026 · Track 3 · Agentic Testing
```

停 8 秒 → fade to black 2 秒。

**旁白:**
- 🇬🇧 *"Repository public, MIT licensed, CI green, error matrix documented. Drop a trace in, get an audit trail. AgentClinic — coach, not surveillance. Thank you."*
- 🇹🇼 Repo 公開、MIT 授權、CI 綠、錯誤矩陣有文件。丟一條 trace 進來,拿到一條完整的審計軌跡。AgentClinic — 是教練,不是監控。謝謝。

---

# 🔊 AI 旁白純英文整段稿(貼進 ElevenLabs / TTS)

直接整段複製,一次生成,後製剪接時對段切。

```
AI agents ship to production faster than any prior software category — but the testing discipline traditional software earned over decades hasn't caught up. This is AgentClinic. Every finding bound to evidence in the trace, published natively into UiPath Test Cloud.

Seven deterministic detectors, source-controlled. Every finding must point at specific trace events as evidence — a finding without an evidence span is a contract violation, rejected at the schema layer. The score is reproducible: same trace, same rules, same number, every time.

Run it locally first. The CLI normalizes the trace, detects seven waste patterns, scores L0 to L3, then publishes natively into Test Cloud. No mocks. The execution ID, test set, and case log are all real. Live.

Same agent, this time triggered from Automation Cloud. Same pipeline as the local runtime — but now writing directly into Test Manager. One Test Case per pattern, reusable across runs. The evidence-bound reason is visible right in the dialog reviewers already use. Quality is no longer a late-stage checkpoint.

Four roles, no overlap. Judge is deterministic — the LLM cannot revise the verdict. Coach rides UiPath's AgentHub LLM Gateway, every call inside the AI Trust Layer. No direct LLM provider API key. Test Cloud is the system of record. UiPath ties it all together.

Every line of source, every commit message, every documentation file in this repository was written by Claude Code over eleven days. Twenty-plus commits, every one visible in the log. The human role was driver — framing, vetting, correcting, performing the GUI actions Claude can't.

Repository public, MIT licensed, CI green, error matrix documented. Drop a trace in, get an audit trail. AgentClinic — coach, not surveillance. Thank you.
```

**TTS 設定建議:**
- 聲音:choose a confident, slightly tech-flavored male or female voice(ElevenLabs 推薦 `Adam` / `Rachel` / `Bella`)
- 語速:1.0× ~ 1.05×(自然偏微快,符合 hackathon demo tempo)
- 不加配樂、不加 reverb
- 段落間留 0.5 秒呼吸(剪接時對段就是切這個 gap)

---

# 📝 英文字幕檔(`docs/demo.srt`)

獨立檔在 repo 同資料夾,剪接軟體 import 或 YouTube Studio upload。完整 SRT 看 `docs/demo.srt`。

---

# ✅ 提交前最終確認清單

- [ ] 影片 ≤ 3 分鐘(目標 2:25,給自己 buffer)
- [ ] 英文字幕掛上(SRT 燒錄 or YouTube CC)
- [ ] 第 4 段 Cloud runtime 那段拍清楚(合規鐵證)
- [ ] 第 1、4 段 Override Result dialog 各 hold 5 秒(讓評審讀 evidence-bound reason)
- [ ] 沒露個人資料(Slack 通知 / 信箱預覽 / 桌面檔案 / 工作列 tray)
- [ ] 上傳 YouTube **Public** 或 **Unlisted**(規則要求 publicly visible)
- [ ] 縮圖選第 4 段那張 evidence-bound reason dialog 的截圖
- [ ] 用無痕視窗測 YouTube 連結能打開(防止意外設成 Private)
- [ ] **Devpost Hosted URL 填**:`https://github.com/rainingsnow0914tw-ship-it/agentclinic`
- [ ] **Devpost Video Demo Link 填**:YouTube 上傳完的網址
- [ ] `docs/SUBMISSION.md` 內 7 個 Field blockquote 分別 paste 進 Devpost 對應欄位
- [ ] Devpost 表單送出 ✅

# 🧹 提交後善後

- [ ] hackathon staging tenant 不用清(主辦方會自己清),但**檢查 `.uipath/app.json` secret 沒進 git** — `git ls-files | grep -E '\.uipath/|\.env'` 該回空
- [ ] 如果 demo 影片內任何畫面露出 External App secret / token 殘跡 → rotate 那個 secret(staging tenant → External Applications → 找 `cad1015e-...` → Regenerate secret)
- [ ] GitHub repo Settings → Social preview 換一張(可選,polish)

---

# 💡 如果只有時間錄一次重來

**重錄第 4 段**(Cloud runtime → Test Cloud)。那是 climax,其他段稍微 rough 評審還會繼續看,第 4 段不順那整支影片就垮。
