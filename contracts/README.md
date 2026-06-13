# RaidMeter — Evidence Contract v1（產品脊椎）

> 曦哥審查定調：「凍結一份 versioned Evidence Contract」是整個 production-grade RaidMeter 的脊椎。
> **守住它 = 有機會打 Track 3；守不住 = 變成「AI 幫我寫測試評論」的廉價作品。**

## 一條鏈

```
Trace Evidence Contract → Deterministic Score → Evidence-backed Finding → Test Cloud Execution Record
```

## 四個角色（不混）

| 角色 | 誰 | 紀律 |
|------|----|------|
| 判官 | Rule engine（確定性） | 不靠 LLM 也能出基本報告 |
| 教練 | LLM | 只把 deterministic findings 翻成 remediation；**不准重判、不准新增無證據的 finding** |
| 紀錄 | Test Cloud | execution / case log / evidence attachment |
| 編排＋治理 | UiPath | Orchestrator + AI Trust Layer |

## 三份合約

1. **`trace_schema_v1.json`** — 輸入合約。任何 agent（Claude Code / Codex / Gemini CLI / UiPath Agent…）的原始 trace，先用 adapter 正規化成這份，才進 RaidMeter Core。多一種來源 = 加一個 adapter，不動 core。
2. **`finding_schema_v1.json`** — 發現合約（心臟）。每個 finding **必須綁至少一條 trace evidence span**；無證據 = 非法 finding。`confidence` 在資料不足時降，不硬判。
3. **`examples/golden_traces/*.golden.json`** — 黃金樣本。input trace + expected findings 成對；CI 迴歸跑這些，保證 RaidMeter 改版不會越改越爛。

## Test Cloud 映射（Track 3 對題）

| RaidMeter 概念 | UiPath Test Cloud |
|----------------|-------------------|
| 一批被測 traces | Test Set |
| 一種 waste pattern | Test Case |
| 一次 agent run 鑑識 | Test Execution |
| 每個 finding | Test Case Log + evidence attachment |

## 7 個 waste pattern（沿用 RaidMeter 既有詞彙表）

`hard_hat_loop` · `state_unchanged_retry` · `lucky_guess` · `agent_piling_on` · `full_file_read_before_grep` · `redundant_tool_call` · `completion_claim_without_verification`

## 版本紀律

- schema 帶 `schema_version`，向後相容。
- detector 帶 `detector_version`，finding 紀錄 detector 版本 → 舊報告永遠可解釋、可重跑。
