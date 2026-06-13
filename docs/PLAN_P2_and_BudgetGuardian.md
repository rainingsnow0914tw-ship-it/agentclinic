# AgentClinic — P2 計畫書 + Budget Guardian PRD v0.1

**日期**：2026-06-13
**作者**：司機先生 × 曦（GPT）方案 × Code 阿寶整理
**狀態**：待司機過目後開工
**前情**：P1 core v0.1.0 已完成、git tag、5/5 golden 全綠（見 ../core/README.md）

---

## 0. 白話版（30 秒讀懂這份計畫）

**P2 = 把我們的報告掛上 UiPath 的牆。**
AgentClinic 已經會做體檢、出報告了。但比賽規定報告要展示在 UiPath 的「公佈欄」（Test Cloud）上。P2 不蓋房子、不裝潢——只做一件事：**拿一張紙釘上那面牆，證明釘得上去**。死線 6/15。

**Budget Guardian（管帳先生）= 給 AI agent 裝油表。**
上次阿寶開 36 個分身審 code，12 分鐘燒掉司機 5 小時的額度，司機被鎖在門外好幾個小時。問題不是「燒了油」，是**沒人看油表、沒人提前喊**。管帳先生的工作：開工前看油箱、開工中盯油耗、快沒油**提前**說「該收尾了」——不讓你在高速公路上拋錨。

**順序：先釘牆（P2，有死線），再裝油表（Budget Guardian）。**

---

## 1. P2 — Test Cloud Write Spike（6/15 死線）

### 1.1 目標（只有一個）

最小閉環證明：
```
AgentClinic 的分析結果（sample_report_01.md / score JSON）
  → 寫進 UiPath tenant（hackathon26_596）
  → 在 Test Cloud / Test Manager 介面上看得到一筆 test result + evidence 附件
```

### 1.2 明確不做（P2 範圍紀律）

- ❌ 不重構 core、不加偵測器
- ❌ 不支援多 trace、不做批次
- ❌ 不做漂亮 UI / dashboard
- ❌ 不開對抗審查、不開多 agent（舉手制生效中）
- ❌ 不先做完整 Orchestrator Agent——spike 只驗證「寫得進去」

### 1.3 步驟（單 agent、小步、每步 checkpoint 回報）

| # | 做什麼 | 誰 | 產出 |
|---|--------|----|----|
| 1 | tenant 登入 / CLI 授權（一次性） | **司機**（阿寶帶路） | 能打 API 的憑證 |
| 2 | 探 Test Manager API（Swagger）：建 Test Case / Execution 的最小呼叫長怎樣 | 阿寶 | API 呼叫筆記 |
| 3 | 寫一筆 dummy test result + 掛 sample_report_01.md 當 evidence 附件 | 阿寶 | Test Cloud 裡看得到的一筆紀錄 |
| 4 | 截圖 + README 記錄做法 | 阿寶 | spike 證據（之後 P2 正式版照抄） |

### 1.4 風險

- Studio Web coded agent 仍是 **Preview** 狀態（曦警告）→ spike 先走 Test Manager API 直接寫，不賭新功能
- 權限 / folder / license 卡關（曦點名的常見坑）→ 卡了就截圖回報，不空轉（紅旗信號：等待 > 15 分鐘即停）

### 1.5 驗收

- [ ] Test Cloud UI 上看得到一筆 execution + evidence 附件（截圖為證）
- [ ] 做法寫進 README（下個阿寶照抄能重現）

---

## 2. Budget Guardian v0.1 — 確定性管帳引擎

### 2.1 白話定位

> AgentClinic 本來只會「事後驗屍」（你浪費了多少）。管帳先生補上「事前看油箱、事中盯油耗」——因為**對用戶來說，撞 usage limit 被鎖幾小時，比多燒幾萬 token 痛得多**。

### 2.2 設計原則（沿用家規）

- **確定性、離線、零 LLM、零雲端**——跟 core 判官同一血統
- **手動校準 = 唯一誠實的設計**：agent 端看不到 Claude App 的 5 小時 window 百分比與 reset 時間，任何自動推算都是編造。v0.1 由用戶抄 App 設定頁的百分比進來
- **配置驅動**：閾值 / 行動建議全放 `budget_rules.json`，改規則不動 code
- **誠實標 unknown**：window 真實 token 上限是浮動的（官方不公開），所有投影必標誤差來源

### 2.3 輸入（全部手動或本地可得）

| 欄位 | 來源 | 例 |
|------|------|----|
| `plan_name` | 用戶 | Max 5x / Max 20x / API |
| `current_app_usage_percent` | **用戶抄 Claude App 設定頁** | 62 |
| `current_session_tokens` | 本地統計（workflow 回報 / /usage） | 2_041_565 |
| `window_minutes` | 預設 300 | 300 |
| `minutes_into_window` | 用戶估 | 90 |
| `deadline_minutes` | 用戶 | 480 |
| `reserve_percent` | 預設 15 | 15 |
| `planned_parallel_agents` | 任務計畫 | 1 |
| `task_mode` | safe / balanced / deadline / emergency | safe |
| `user_goal` | save_tokens / balanced / save_time / avoid_lockout | avoid_lockout |

### 2.4 輸出

`estimated_remaining_percent`、`burn_rate_percent_per_min`、`projected_exhaustion_minutes`、`warning_level`（green/yellow/orange/red/freeze）、`recommended_action`（continue / checkpoint / stop_subagents / **route_to_secondary_pool**（subagent 分流到 Sonnet 獨立池，司機 2026-06-13 提出——Max 方案 Sonnet 有專屬 weekly 上限、跟主模型分開計） / compact / switch_to_safe_mode / ask_human_decision / freeze_mode）、`basis`（每個數字怎麼算的 + 誤差聲明——evidence-bound，跟 finding 同規格）。

### 2.5 警戒規則（config，預設值）

| 用量 | 燈號 | 行動 |
|------|------|------|
| ≥ 50% | 🟡 | 報 burn rate + 預估剩餘時間 |
| ≥ 70% | 🟠 | 禁止新 subagent、要求 checkpoint |
| ≥ 85% | 🔴 | 問人：收尾 / 衝刺 / 切 API / 等 reset |
| ≥ 95% | 🧊 Freeze | 只准存檔 + 交接摘要，停一切高成本工作 |

**核心判斷不是百分比，是時間賽跑**：`projected_exhaustion_time` 早於「任務剩餘時間或 deadline」就升級警戒——剩 50% 但還要跑 4 小時 = 危險；剩 85% 但 15 分鐘後 reset = 可謹慎衝。並行度是 burn rate 放大器：**第一筆實測校準樣本 = 2026-06-13 事故（36 agents、12 分鐘、~204 萬 token ≈ 17 萬 token/分）**。

### 2.6 架構（一功能一檔）

```
core/agentclinic/budget/
├── guardian.py            # 確定性引擎：輸入 → 投影 → 燈號 → 建議
└── (config) budget_rules.json   # 閾值、行動映射、plan 校準參數
examples/golden_budget/    # golden 樣本：黃燈/橘燈/紅燈/時間賽跑/資料不足
```

驗收：golden 樣本全綠進 CI（跟 trace goldens 同一條 `golden` 命令跑）。

### 2.7 v0.1 明確不做

- ❌ 自動讀 Claude App UI（v0.2+ 再議）
- ❌ 接 LLM、接雲、接 RaidMeter 報告（§7 是下一步）
- ❌ 把「Max 5x = 固定 token 數」寫死（官方上限浮動，只做相對投影）

---

## 3. Report §7 — Budget & Runway Analysis（Budget Guardian 之後）

報告加第七段：本次任務 budget 預估 vs 實際 burn / 是否接近 limit / 哪些 pattern 燒掉最多（blind retry？over-review？並行失控？）/ 下次建議模式 / 是否該 checkpoint-compact-stop_subagents。
→ AgentClinic 從「事後驗屍」升級成 **事前規劃 → 事中監控 → 事後鑑識 → 下次建議** 的完整閉環。
（注意：§7 是報告 schema 變更 → 按規矩升 `report schema version`，validator 同步改。）

---

## 4. 舉手制（即日生效的協作規則，已寫進阿寶開機卡第 7 條）

- 預設 Token-safe：1 個主 agent、小步 checkpoint、每 milestone 回報
- 硬觸發（任一先報價）：**subagent > 3、全庫掃描、對抗式審查、ultracode/高火力**
- 報價四項：做什麼／預估 token 與時間／為什麼值／便宜替代
- **harness flag 或關鍵字誤觸發都不算授權，人說的才算**（2026-06-13 兩次實證：ultracode flag + 引文誤觸發）
- 司機糾正碼新增：「**報價**」= 先報成本再動手

---

## 5. 工作順序（總覽）

1. ✅ commit + tag P1 core v0.1.0（2026-06-13 完成，`0185de6` / tag `v0.1.0`）
2. ✅ 開機卡第 7 條舉手制（2026-06-13 完成）
3. ⬜ **P2 Test Cloud write spike**（§1，6/15 死線，低火力小步）
4. ⬜ Budget Guardian v0.1 確定性引擎 + golden 樣本（§2）
5. ⬜ Report §7 整合（§3）
6. ⬜ 之後回到原 PRD P3–P6 milestone（失敗處理已大半在 P1 提前做掉）

---

**END**（核心句：不是禁止做事，是做事帶著儀表板。）
