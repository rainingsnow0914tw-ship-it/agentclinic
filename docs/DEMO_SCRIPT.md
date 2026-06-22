# 🎬 AgentClinic — Demo 影片懶人包

> 照這份做,不用動腦。**目標 4:00-4:30**(Devpost 5:00 cap 留 30s buffer)
> 全螢幕錄影 · AI 英文旁白 · 英文字幕 · CapCut 剪接 · 上 YouTube
> 不用 Veo / 不用 AI 痛點動畫。

---

## ⚡ 三步驟總流程

1. **錄螢幕**(8 段,每段獨立 take,失敗那段重來)
2. **生 AI 旁白**(把純英文整段稿一次貼 ElevenLabs / OpenAI TTS)
3. **CapCut 合成 → 對 SRT 字幕 → 上 YouTube → Devpost 貼連結**

錄影前先 `uipath auth` warm 一次 token,免得錄到一半跳重 auth。

---

## 📋 八段結構表

| 段 | 內容 | 長度 | 鏡頭 |
|---|---|---|---|
| 1 | 痛點 + Test Cloud 五條 execution 全景 | 30s | Test Manager 列表 |
| 2 | 證據鏈 hook · Override Result dialog | 30s | 點進去 · multi-line reason hold |
| 3 | Why deterministic? Why bounded coach? | 30s | VS Code: `coach/validator.py` boundary |
| 4 | 七大偵測器 + Evidence Contract | 35s | VS Code: `detect.py` + golden + report §5 |
| 5 | 本機 CLI 全鏈跑通 | 35s | 終端機 publish 指令 + JSON output |
| 6 | Cloud runtime 觸發 → Test Cloud ⭐ climax | 50s | Orchestrator Start now → 新 execution → reason hold |
| 7 | 四角色 + UiPath 五元件 | 30s | 靜態卡 |
| 8 | GitHub repo + CI + 25 commits + 收尾 | 30s | GitHub repo + git log + End frame |

總長 **約 4 分 30 秒**,離 Devpost 5:00 cap 留 30 秒安全 buffer。

---

## 🖥️ Pre-flight checklist(錄影前 5 分鐘做完)

- [ ] **瀏覽器三個 tab** 都已登入
  - Test Manager → **直接導航到 demo execution**(避免從列表找錯條):
    `https://staging.uipath.com/hackathon26_596/DefaultTenant/testmanager_/ACR2/testexecutions/16ae3abb-f0ee-0b00-5d97-0b49cca9bee1`
    這是 ACR2:86 / `exec:trace_gold_001/run_deploy_4x`,reason 已經 hotfix 寫真實 evidence-bound 文字。**錄影第 1 + 4 段都用這條**。
  - Orchestrator:Process detail page,`agentclinic-coded-agent 0.1.1`
  - GitHub:`https://github.com/rainingsnow0914tw-ship-it/agentclinic`
- [ ] **VS Code 五個分頁**(切換用):
  - `main.py`
  - `core/agentclinic/detect.py`
  - `core/agentclinic/coach/validator.py`
  - `examples/golden_traces/01_hard_hat_loop.golden.json`
  - 上次跑 publish 留下的 `report.md`(或自己 `--report out.md` 跑一份)
- [ ] **終端機** cwd 在 `RaidMeter-UiPath`,publish 指令**預打好不要按 Enter**(PowerShell 語法):
  ```powershell
  $env:PYTHONPATH = "core"
  $env:PYTHONUTF8 = "1"
  python -m agentclinic publish examples\golden_traces\01_hard_hat_loop.golden.json --project-name "AgentClinic Reports v2" --project-prefix ACR2 --coach uipath
  ```
  (若用 Git Bash 改 `PYTHONPATH=core PYTHONUTF8=1 python -m agentclinic publish examples/golden_traces/...` 一行)
- [ ] **桌面背景乾淨**(沒個人照 / 無關 app 開著)
- [ ] **瀏覽器書籤列隱藏**(`Ctrl+Shift+B`)
- [ ] **Windows Focus Assist**「Alarms only」
- [ ] **Slack / Discord / 信箱** 全關
- [ ] **螢幕解析度** 1920×1080(16:9)
- [ ] **Test Manager 瀏覽器 zoom** 110-125%(評審讀 reason 不瞇眼)
- [ ] **工作列 tray icons** 隱藏非必要

---

# 📺 八段詳細腳本

## 第 1 段(30s)痛點 + Test Cloud 五條 execution 全景

**畫面:**
- 0-8s:Test Manager 開啟,ACR2 → Executions 列表載入。鏡頭停在列表頂部
- 8-18s:**慢速捲動** 五條 execution 一條條看過(每條停 ~2 秒),特別讓觀眾看到 Results 欄的紅綠 bar(L0 綠 / L1 橘 / L2 / L3 紅)
- 18-30s:回到列表頂部,**hover** 在最新一條 `exec:trace_gold_001/run_deploy_4x`,游標停 3 秒,讓觀眾預期這就是接下來要點的

**旁白:**
- 🇬🇧 *"AI agents are shipping to production faster than any prior software category. Every team I've worked with ships them the same way — hope it works, pray it scales, debug post-incident. What's missing is the testing discipline traditional software earned over decades. This is AgentClinic. Here are five golden traces, each published natively into UiPath Test Cloud. Failed, Passed, varying score levels from L0 to L3 — every result an actual audit record, not a report PDF."*
- 🇹🇼 AI agent 上線速度是任何過去軟體都比不上的。我合作過的每個團隊都用同樣方式 ship — 祈禱它能跑、希望它能 scale、出事再回頭 debug。缺的是傳統軟體幾十年累積的測試紀律。這就是 AgentClinic。畫面上五條 golden trace,每條都直接寫進 UiPath Test Cloud。Failed、Passed、L0 到 L3 不同 score 等級 — 每個結果都是真實的審計紀錄,不是 PDF 報告。

---

## 第 2 段(30s)證據鏈 hook · Override Result dialog

**畫面:**
- 0-8s:點 `exec:trace_gold_001/run_deploy_4x` 進 detail。Execution 詳情頁顯示
- 8-15s:點 testcase log 那行的 `⋮` menu → 選 **Override Result**
- 15-30s:Dialog 開,**完全不動滑鼠 hold 12 秒**,讓 multi-line evidence-bound reason 整段顯示:
  ```
  AgentClinic detected pattern `hard_hat_loop` -- 1 finding(s):
    RM-F-trace_gold_001-001 | severity=critical confidence=0.9 | events: evt_0002, evt_0003, evt_0004
  Evidence-bound by finding_schema_v1; see attached report.
  ```

**旁白:**
- 🇬🇧 *"Click into the failed log. Look at the reason. This is the difference. Not 'agent looks bad' — but the exact finding ID, the severity, the confidence, and the specific trace event IDs that drove the verdict. A reviewer can jump from this dialog straight to events evt_0002 through evt_0004 in the source trace. The chain is unbroken. Every claim points at evidence."*
- 🇹🇼 點進 Failed 那條 log。看 reason 區。差別在這裡。不是「agent 好像有問題」這種模糊話 — 而是明確的 finding ID、嚴重度、信心值、加上推導出這個判決的特定 trace event ID。評審可以從這個對話框直接跳到原始 trace 的 evt_0002 到 evt_0004 三個事件。鏈條沒斷。每個 claim 都指向證據。

---

## 第 3 段(30s)Why deterministic? Why bounded coach?

**畫面:**
- 0-10s:切 VS Code,開 `core/agentclinic/coach/validator.py`,捲到 `JUDGE_RESERVED_WORDS` 或 `IMMUTABLE_FIELDS` 那個 list,**hover** 在那個 list 停 3 秒
- 10-20s:捲到 `BoundaryViolation` 的 raise 那行,圈起來
- 20-30s:切到 `core/agentclinic/detect.py` 頂部 docstring 或前幾行,讓觀眾看到「pure rule engine, no LLM」的脈絡

**旁白:**
- 🇬🇧 *"Why does this work? Because the judge and the coach are different things. The judge is a deterministic Python rule engine — no LLM involved, no probabilistic reasoning, just source-controlled rules that produce the same verdict on the same trace every time. The coach uses an LLM, but is bounded by a validator that blocks judge-reserved phrases like 'might be a false positive' or 'I'd downgrade this.' If the coach tries to revise the verdict, the call is rejected. The coach translates findings into remediation. It never judges. Coach, not surveillance."*
- 🇹🇼 為什麼這套行得通?因為 judge 跟 coach 是兩件不同的事。Judge 是確定性的 Python 規則引擎 — 不用 LLM、不靠機率推理,版控管理的規則對同一條 trace 永遠產生同一個判決。Coach 才用 LLM,但被一個 validator 約束住 — 像「可能誤判」「我會降級」這種 judge 專屬的詞,coach 一寫出來就被拒。Coach 想翻案,直接被擋下。Coach 把 finding 翻譯成可執行的建議。它從來不下判決。Coach, not surveillance。

---

## 第 4 段(35s)七大偵測器 + Evidence Contract

**畫面:**
- 0-12s:VS Code 切到 `core/agentclinic/detect.py`,**快速捲過七個 detector 函數**,每個停 ~1.5 秒(`hard_hat_loop` / `state_unchanged_retry` / `lucky_guess` / `agent_piling_on` / `full_file_read_before_grep` / `redundant_tool_call` / `completion_claim_without_verification`)
- 12-22s:切到 `examples/golden_traces/01_hard_hat_loop.golden.json`,捲到 `events[]`,**hover** 在 `state_hash: "S0"` 第一個 event,然後 scroll 看到四次 retry 都同樣 `S0`,停 3 秒
- 22-35s:切到 `report.md` 或 publish output 的 Section 2 + Section 5,圈起 `evidence_spans: [evt_0002, evt_0003, evt_0004]`,然後捲到 Section 5「Information Gaps」**hold 5 秒**讓觀眾看 `no_stated_goal` 條目

**旁白:**
- 🇬🇧 *"Seven detectors. All deterministic, all source-controlled. Hard hat loop catches blind retries with the state hash unchanged. Lucky guess catches a claim of success with no verification step. Each one fires only when its rule signature matches. Every finding produced must include an evidence span — specific trace event IDs as the contract requires. And section five — information gaps. When data is missing, the report admits exactly what it cannot judge. No guessing. No hallucination. That iron rule is what makes a clinic different from a courtroom."*
- 🇹🇼 七個偵測器。全部確定性、全部版控管理。Hard hat loop 抓 state hash 沒變還盲目重試。Lucky guess 抓宣稱成功但沒驗證的情況。每個 detector 只在規則 signature 對上時才觸發。產出的每個 finding 都必須附 evidence span — contract 要求的明確 trace event ID。再來看 Section 5 — Information Gaps。資料缺失的時候,報告會明白寫出「我看不到 X,所以無法判斷 Y」。不猜、不幻覺。這條鐵律就是診所跟法庭的差別。

---

## 第 5 段(35s)本機 CLI 全鏈跑通

**畫面:**
- 0-3s:切終端機,publish 指令已預打,**按下 Enter**
cd "C:\Users\soulf\OneDrive\Desktop\code寶創作天地\AI情報員\RaidMeter-UiPath"; $env:PYTHONPATH="core"; $env:PYTHONUTF8="1"; python -m agentclinic publish examples\golden_traces\01_hard_hat_loop.golden.json --project-name "AgentClinic Reports v2" --project-prefix ACR2 --coach uipath
- 3-18s:**不要 cut** — 讓真實 CLI 跑 12-15 秒。Token exchange、project ensure、testcase ensure、testset、execution、log、override、attachment upload 一連串輸出在終端機跑出來
- 18-25s:JSON output 完整顯示,**滑鼠捲到** `test_cloud.execution.id`、`test_cloud.logs[0].result: "Failed"`、`test_cloud.logs[0].result_override_error: null`、`publish_error: null`,每條停 ~1 秒
- 25-35s:捲到最底 `ui_url` 顯示 — 那個就是 Test Cloud Web UI 連結。然後**靜止** 5 秒讓觀眾看完整 JSON

**旁白:**
- 🇬🇧 *"Run it locally first. The CLI normalizes the trace against the schema, runs the seven detectors, scores L0 to L3, then drives the full Test Manager API chain — project, test case, test set, execution, case log, override result, and a markdown report uploaded as attachment. Every step real, every ID a live resource. publish_error is null, result_override_error is null. End-to-end, deterministic, reproducible."*
- 🇹🇼 先本機跑。CLI 用 schema 把 trace 正規化、跑七個 detector、評分 L0 到 L3、然後驅動完整的 Test Manager API 鏈條 — project、test case、test set、execution、case log、override result、最後把 markdown 報告當 attachment 上傳。每一步都是真的,每個 ID 都是 live resource。publish_error 是 null,result_override_error 也是 null。端到端、確定性、可重現。

---

## 第 6 段(50s)Cloud runtime 觸發 → Test Cloud ⭐ climax

**畫面:**
- 0-8s:切 Orchestrator → Processes 列表,點 `agentclinic-coded-agent 0.1.1` 進 detail
- 8-15s:點右上 **Start now**。Job submission dialog 跳出,Trace 欄位已預貼 golden,確認 Start
- 15-30s:Jobs 列表,新 job 顯示 **Running**(實際 30 秒,**剪成 15 秒**但保留 Running 狀態 5 秒讓觀眾看到真在跑)→ **Successful**
- 30-40s:切 Test Manager → ACR2 → Executions,**F5 重整**,新一條 execution 出現在列表頂部(Results 紅 bar),點進去
- 40-50s:點 testcase log 的 `⋮` → Override Result → Dialog 跳出,**hold 8 秒**讓 multi-line evidence-bound reason 整段顯示。最後 2 秒**滑鼠移到** `evidence_spans: [...]` 那行下面畫線

**旁白:**
- 🇬🇧 *"Same agent, this time triggered from Automation Cloud. The Orchestrator process invokes the Coded Agent, which runs the exact same pipeline as the local CLI — only this time, every credential comes from environment variables set on the process itself, not from a local config file. The job completes, and back in Test Manager, a new execution appears. Open the failed log, open the override dialog — and there it is. The same multi-line evidence-bound reason. Same finding ID. Same trace event IDs. Cloud runtime writes the same audit record as local runtime, every time."*
- 🇹🇼 同一個 agent,這次從 Automation Cloud 觸發。Orchestrator process 呼叫 Coded Agent,它跑的是跟本機 CLI 同樣那條 pipeline — 只是這次每個憑證都從 process 上設的環境變數來,不是本機設定檔。Job 跑完,回到 Test Manager,一條新的 execution 出現。點進 Failed log、打開 override dialog — 一模一樣的 multi-line evidence-bound reason。同樣的 finding ID、同樣的 trace event ID。Cloud runtime 跟本機 runtime 寫進來的審計紀錄,永遠是同一個格式、同一個品質。

**💡 這段是整支影片的 climax。錄壞重來,沒關係。第 40-50s 那 10 秒的 hold 是評審看完整支影片唯一會記住的鏡頭。**

---

## 第 7 段(30s)四角色 + UiPath 五元件

**畫面:**
靜態卡(用 README 截圖或自製簡單黑底文字):

```
👨‍⚖️ JUDGE         deterministic rule engine — runs without an LLM
🏃  COACH         LLM, bounded — translate findings, forbidden to judge
📋 RECORDER       UiPath Test Cloud — execution + log + attachment
🎼 ORCHESTRATOR   UiPath — Process + AI Trust Layer audit

UiPath components used:
  Test Cloud (Test Manager)  ·  Coded Agent (Function)
  Orchestrator Process       ·  AgentHub LLM Gateway
  AI Trust Layer             ·  External Application
```

每個角色淡入,然後元件清單一起淡入。

**旁白:**
- 🇬🇧 *"Four roles, no overlap. Judge is deterministic — the LLM cannot revise the verdict. Coach rides UiPath's AgentHub LLM Gateway, every call inside the AI Trust Layer for audit and PII redaction. No direct LLM provider API key. Test Cloud is the system of record. Orchestrator ties everything together. Six native UiPath components used end to end. Track 3 framing: quality as a continuous, governed capability across the enterprise."*
- 🇹🇼 四個角色,責任不重疊。Judge 確定性 — LLM 不准翻案。Coach 走 UiPath 的 AgentHub LLM Gateway,每次呼叫都在 AI Trust Layer 裡,有 audit + PII redaction。沒有直接接 LLM 廠商的 API key。Test Cloud 是紀錄系統。Orchestrator 把所有東西串起來。六個原生 UiPath 元件,端到端都在用。Track 3 的 framing:把 quality 變成跨企業、可治理、持續性的能力。

---

## 第 8 段(30s)GitHub repo + CI + 25 commits + 收尾

**畫面:**
- 0-12s:切 GitHub repo 頁。**慢速** 從上往下捲:badge 列(CI 綠勾、MIT、Python、UiPath、Track 3)→ tagline → Why AgentClinic 列表 → Why-not 對比表
- 12-22s:切到開終端機,跑 `git log --oneline | head -25`,讓 commits 跑過顯示 23+ 條
- 22-28s:End frame 靜態卡:
  ```
  github.com/rainingsnow0914tw-ship-it/agentclinic

  AgentClinic
  Forensic analysis for AI agents · Native to UiPath Test Cloud

  UiPath AgentHack 2026 · Track 3 · Agentic Testing
  ```
- 28-30s:Fade to black 2 秒

**旁白:**
- 🇬🇧 *"Repository public, MIT licensed. CI green across trace goldens, budget goldens, and the Coded Agent build. Every line of source, every commit message, every documentation file was written by Claude Code over eleven days — twenty-plus commits, every one visible in the log. The human role was driver: framing, vetting, correcting, performing the GUI actions Claude can't. Drop a trace in, get an audit trail. AgentClinic — coach, not surveillance. Thank you."*
- 🇹🇼 Repo 公開、MIT 授權。CI 在 trace goldens、budget goldens、Coded Agent build 三條 job 全綠。每一行 source code、每一個 commit message、每一份文件,都是 Claude Code 在 11 天裡寫的 — 20 幾個 commit,log 上一個都不少。人類的角色是駕駛:設定方向、審查、糾正、執行 Claude 做不了的 GUI 操作。丟一條 trace 進來,拿到一條完整審計軌跡。AgentClinic — 教練,不是監控。謝謝。

---

# 🔊 AI 旁白純英文整段稿(貼進 ElevenLabs / TTS 一次生成)

整段複製,一次生成,後製剪接時對段切。八段之間留約 0.5 秒呼吸(剪接時對段就是切這個 gap)。

```
AI agents are shipping to production faster than any prior software category. Every team I've worked with ships them the same way — hope it works, pray it scales, debug post-incident. What's missing is the testing discipline traditional software earned over decades. This is AgentClinic. Here are five golden traces, each published natively into UiPath Test Cloud. Failed, Passed, varying score levels from L0 to L3 — every result an actual audit record, not a report PDF.

Click into the failed log. Look at the reason. This is the difference. Not "agent looks bad" — but the exact finding ID, the severity, the confidence, and the specific trace event IDs that drove the verdict. A reviewer can jump from this dialog straight to events evt_0002 through evt_0004 in the source trace. The chain is unbroken. Every claim points at evidence.

Why does this work? Because the judge and the coach are different things. The judge is a deterministic Python rule engine — no LLM involved, no probabilistic reasoning, just source-controlled rules that produce the same verdict on the same trace every time. The coach uses an LLM, but is bounded by a validator that blocks judge-reserved phrases like "might be a false positive" or "I'd downgrade this." If the coach tries to revise the verdict, the call is rejected. The coach translates findings into remediation. It never judges. Coach, not surveillance.

Seven detectors. All deterministic, all source-controlled. Hard hat loop catches blind retries with the state hash unchanged. Lucky guess catches a claim of success with no verification step. Each one fires only when its rule signature matches. Every finding produced must include an evidence span — specific trace event IDs as the contract requires. And section five — information gaps. When data is missing, the report admits exactly what it cannot judge. No guessing. No hallucination. That iron rule is what makes a clinic different from a courtroom.

Run it locally first. The CLI normalizes the trace against the schema, runs the seven detectors, scores L0 to L3, then drives the full Test Manager API chain — project, test case, test set, execution, case log, override result, and a markdown report uploaded as attachment. Every step real, every ID a live resource. publish_error is null, result_override_error is null. End-to-end, deterministic, reproducible.

Same agent, this time triggered from Automation Cloud. The Orchestrator process invokes the Coded Agent, which runs the exact same pipeline as the local CLI — only this time, every credential comes from environment variables set on the process itself, not from a local config file. The job completes, and back in Test Manager, a new execution appears. Open the failed log, open the override dialog — and there it is. The same multi-line evidence-bound reason. Same finding ID. Same trace event IDs. Cloud runtime writes the same audit record as local runtime, every time.

Four roles, no overlap. Judge is deterministic — the LLM cannot revise the verdict. Coach rides UiPath's AgentHub LLM Gateway, every call inside the AI Trust Layer for audit and PII redaction. No direct LLM provider API key. Test Cloud is the system of record. Orchestrator ties everything together. Six native UiPath components used end to end. Track 3 framing: quality as a continuous, governed capability across the enterprise.

Repository public, MIT licensed. CI green across trace goldens, budget goldens, and the Coded Agent build. Every line of source, every commit message, every documentation file was written by Claude Code over eleven days — twenty-plus commits, every one visible in the log. The human role was driver: framing, vetting, correcting, performing the GUI actions Claude can't. Drop a trace in, get an audit trail. AgentClinic — coach, not surveillance. Thank you.
```

**TTS 設定建議:**
- 聲音:confident, tech-flavored(ElevenLabs 推薦 `Adam` / `Rachel` / `Bella`,或 `Daniel` 偏 BBC 腔)
- 語速:**1.0× 自然**(不要加速 — 4:30 已經夠長,加速反而讓評審聽不清)
- 不加配樂、不加 reverb
- 段落間留 0.5 秒呼吸(CapCut import 時對段就是這個 gap)
- 整段約 5,300 字元 — ElevenLabs 一次生成 OK,輸出約 4:00-4:30 mp3

---

# 📝 英文字幕檔(`docs/demo.srt`)

獨立檔在同 `docs/` 資料夾,**CapCut 直接 import**:右側面板「Captions」→「Import」→ 選 `demo.srt`。對 timing 後燒進影片。

完整 SRT 看 `docs/demo.srt`,32 cues 對應 4:30 時間軸。

---

# ✅ 提交前最終確認清單

- [ ] 影片總長 **4:00-4:50 之間**(Devpost 5:00 是 hard cap)
- [ ] 英文字幕已掛上(CapCut burn 或 YouTube CC)
- [ ] **第 6 段 Cloud runtime → Test Cloud** 那段拍清楚(climax)
- [ ] 第 2、6 段 Override Result dialog 各 hold 8-12 秒(讓評審讀 reason)
- [ ] 沒露個人資料(Slack 通知 / 信箱預覽 / 桌面檔案 / 工作列 tray)
- [ ] 終端機沒露出 `.uipath/app.json` 內的 secret(publish 指令本身 OK,但別誤捲到 cat app.json 那種)
- [ ] 上傳 YouTube **Public** 或 **Unlisted**(規則要求 publicly visible)
- [ ] 縮圖選第 6 段那張 evidence-bound reason dialog 截圖
- [ ] 用無痕視窗測 YouTube 連結能打開(防意外設成 Private)
- [ ] **Devpost Hosted URL 填**:`https://github.com/rainingsnow0914tw-ship-it/agentclinic`
- [ ] **Devpost Video Demo Link 填**:YouTube 網址
- [ ] `docs/SUBMISSION.md` 八個 Field blockquote 分別 paste 進 Devpost 對應欄位
- [ ] Devpost 表單送出 ✅

# 🧹 提交後善後

- [ ] **檢查影片有沒有任何畫面露出 secret**(雖然 publish 指令本身不秀 secret,還是看一次 frame-by-frame)
- [ ] 露了就 rotate:Automation Cloud → Admin → External Applications → 找 `cad1015e-...` → Regenerate secret → 更新本機 `.uipath/app.json`
- [ ] `git ls-files | grep -E '\.uipath/|\.env'` 該回空(secret 沒進 git)
- [ ] GitHub repo Settings → Social preview 換一張(可選,polish)

---

# 💡 如果只有時間錄一段重來

**第 6 段**(Cloud runtime → Test Cloud)。那是 climax,其他段稍微 rough 評審還會繼續看,第 6 段不順整支影片就垮。

**第二優先**第 2 段(Override Result dialog hold)。

# 💡 CapCut 剪接的注意點

- ElevenLabs 生出整段 mp3 後,直接拖進 CapCut timeline 當音軌
- 每段對應的螢幕錄影 mp4 拖到 video track,**對齊** 對應旁白的開始時間
- 八段中間留 0.5 秒 gap(就是 TTS 自然的 pause)— 不要硬切
- `demo.srt` import 後 CapCut 會自動把 cue 對到 timeline 時間軸,自己微調 timing
- Export 1080p / H.264 / 30fps / `.mp4`,大小通常 < 200 MB,YouTube 上傳順
