# P2 Spike — Test Cloud Write 驗證結果

**日期**：2026-06-13（死線 6/15 前 2 天完成）
**狀態**：✅ 全綠
**驗收**：UiPath Test Manager UI 看得到 evidence 附件（截圖 `p2_spike_evidence.png`）

---

## 0. 30 秒讀懂

最小閉環證明：**AgentClinic 報告寫得進 UiPath Test Cloud**。

```
External App OAuth (client_credentials)
  → POST /projects               → AgentClinic Spike (prefix ACS)
  → POST /testcases              → AC-Spike-001 Blind Retry Chain (ACS:1)
  → POST /attachments/testCase/{id}/upload
                                 → sample_report_01.md (2053 bytes, mime md)
```

UI 驗證：Test Manager → Projects → ACS → Test Cases → ACS:1 → **Documents** tab → 看到 `sample_report_01.md`、Added by "External"。

---

## 1. 環境

| 項 | 值 |
|---|---|
| tenant | `hackathon26_596` / `DefaultTenant` |
| base URL | `https://staging.uipath.com/hackathon26_596/DefaultTenant/testmanager_/` |
| 認證 | External Application (Confidential) + Client Credentials grant |
| App ID | 存於 `.uipath/app.json`（不入 git） |
| OpenAPI spec | `.uipath/swagger.json`（1MB，spike 開始時 fetch、不入 git） |

---

## 2. 認證踩坑紀錄（最大時間殺手）

**結論：staging hackathon 環境的 Personal Access Token (PAT) 走不通，必須改 External Application + client_credentials**。

### 排查路徑（5 條證據）

1. 兩把不同 PAT（舊 + 新）打 `testmanager_/api/v2/projects` 全 401
2. 同 PAT 打 `orchestrator_/odata/Folders` 也 401（不只 Test Manager service 問題）
3. PAT scope 從 0 個到 TM 全勾、結果不變
4. 401 response header `WWW-Authenticate: Bearer realm="identity_", error="invalid_token"` → identity service 拒絕
5. 試 OAuth `refresh_token` grant 用 `nonInteractiveClient` 換 access token → `invalid_client`

→ 改走 External Application 後 200 OK。

### External Application setup（司機操作步驟）

1. UiPath Admin → 左 nav **External Applications** → **+ Add Application**
2. Type = **Confidential application**
3. Name = `agentclinic-spike`（隨意）
4. **Resources → Add resource → TestManager**
5. **必須**：切到 **Application scope(s)** 分頁、Select all 全勾（不是 User scope；client_credentials 用 Application scope）
6. Save → 拿 **App ID** + **App Secret**（Secret 只顯示一次）

### Token Exchange

```powershell
POST https://staging.uipath.com/identity_/connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id={APP_ID}
&client_secret={URL-encoded APP_SECRET}
&scope=TM.Projects TM.Projects.Read TM.Projects.Write TM.TestCases TM.TestCases.Read TM.TestCases.Write TM.TestSets TM.TestSets.Read TM.TestSets.Write TM.TestExecutions TM.TestExecutions.Read TM.TestExecutions.Write TM.Attachments TM.Attachments.Read TM.Attachments.Write
```

回 `{access_token, token_type:Bearer, expires_in:3600, scope:...}`。1 小時過期、過了重新 exchange。

---

## 3. 物件依賴鏈

| 物件 | endpoint | 必要欄位 |
|---|---|---|
| Project | `POST /api/v2/projects` | `name`, `projectPrefix`, `isActive` |
| TestCase | `POST /api/v2/{projectId}/testcases` | `name`, `projectId`, **`containerId`** ← 用 `projectId` 即可（root container default） |
| Attachment | `POST /api/v2/{projectId}/attachments/{objectType}/{id}/upload` (multipart) | `objectType` (enum: project/testCase/testSet/testExecution/testCaseLog/defect/...)、`file` (binary) |

**重要**：`containerId = projectId` 可用 root container、不必另建 folder。

**未走完的 chain**（spike 範圍外，P2 正式版再做）：
- TestSet（schema 同 TestCase、需 containerId）
- TestExecution（綁 testSetId、source enum: TestManager / Orchestrator / **ThirdParty** / Studio — 用 ThirdParty 標 AgentClinic 是外部 testing tool）
- TestCaseLog（綁 testCaseId + testExecutionId、result 寫進去）

**踩坑**：直接 POST TestExecution + testCaseIds（不掛 TestSet）回 500 internal — UiPath 可能不允許 free-standing TestCaseIds-only execution。P2 正式版要先建 TestSet 才能 execute。

---

## 4. 完整 reproducible 指令（PowerShell）

前置：`.uipath/app.json` 含 `app_id` / `app_secret` / `token_endpoint` / `scope`。

```powershell
# Step 1: exchange access_token
$app = Get-Content .uipath/app.json -Raw | ConvertFrom-Json
Add-Type -AssemblyName System.Web
$body = "grant_type=client_credentials" `
  + "&client_id=" + [System.Web.HttpUtility]::UrlEncode($app.app_id) `
  + "&client_secret=" + [System.Web.HttpUtility]::UrlEncode($app.app_secret) `
  + "&scope=" + [System.Web.HttpUtility]::UrlEncode($app.scope)
$tokR = Invoke-RestMethod $app.token_endpoint -Method POST -Body $body `
  -ContentType "application/x-www-form-urlencoded"
$tok = $tokR.access_token

# Step 2: create project
$base = "https://staging.uipath.com/hackathon26_596/DefaultTenant/testmanager_"
$H = @{ Authorization = "Bearer $tok"; Accept = "application/json"; "Content-Type" = "application/json" }
$proj = Invoke-RestMethod "$base/api/v2/projects" -Method POST -Headers $H `
  -Body (@{ name = "AgentClinic Spike"; projectPrefix = "ACS"; isActive = $true } | ConvertTo-Json)

# Step 3: create testcase
$tc = Invoke-RestMethod "$base/api/v2/$($proj.id)/testcases" -Method POST -Headers $H `
  -Body (@{ name = "AC-Spike-001"; projectId = $proj.id; containerId = $proj.id; version = "1.0" } | ConvertTo-Json)

# Step 4: upload attachment
$uploadH = @{ Authorization = "Bearer $tok"; Accept = "application/json" }
$r = Invoke-WebRequest "$base/api/v2/$($proj.id)/attachments/testCase/$($tc.id)/upload" `
  -Method POST -Headers $uploadH `
  -Form @{ objectType = "testCase"; file = Get-Item ../examples/sample_report_01.md }
```

---

## 5. 安全紀錄

- spike 期間共暴露 **2 把 PAT**（在對話 transcript 內、雖未公開但仍 leak） + **1 把 App Secret**。
- spike 完成後立即動作：
  - [ ] Revoke 兩把 PAT（UiPath Admin → Personal Access Tokens）
  - [ ] App Secret 已存 `.uipath/app.json`（在 `.gitignore` 內）；若不再用、Revoke App Secret 並重生
- `.gitignore` 已含 `.pat.txt` / `.uipath/`。

---

## 6. P2 正式版下一步（從 spike → production）

| # | 動作 | 阻塞點 |
|---|---|---|
| 1 | 把 spike 4 步包成 Python script、寫進 core | core 目前是 Python、PowerShell 換成 `requests` |
| 2 | 走完整 chain：TestSet → TestExecution → TestCaseLog | TestExecution 直接 POST 500，要先 TestSet |
| 3 | TestCaseLog 寫 result（pass/fail）+ attachment 掛 TestCaseLog（不是 TestCase）| TestCaseLog schema 要 testExecutionId + testCaseId |
| 4 | Studio Web 建 Orchestrator Agent 串 core | Studio Web Coded Agent 仍 Preview、別賭 |
| 5 | 整合進 AI Trust Layer LLM connection（P4） | 6/22 後再做 |

---

## 7. 驗收證據

- 截圖：`p2_spike_evidence.png`（同目錄）
  - Test Manager → ACS → Test Cases → ACS:1 → Documents tab → `sample_report_01.md`
- API response cache：`.uipath/project.json`（project DTO）
- access_token cache：`.uipath/token.json`（1 小時過期）

---

**spike 完成 = 風險①（薄殼/核心在外不合規）解了一半**：證明 AgentClinic 報告能 native 寫進 Test Cloud、不是「外部 agent + UiPath webhook」薄殼。P2 正式版把 chain 走完、加 Studio Web Orchestrator Agent 當主體就剩風險②（Test Cloud 深整合 framing）。
