# Demo Video — Recording Script

Hard cap **4:45** on the YouTube timeline (Devpost rule is 5:00, leave
15s buffer; judges aren't obligated to watch past 5:00 anyway).

Five segments. Each block below has:

- **⏱ Timecode** — start/end of the segment on the final cut
- **🖥 Screen** — what the viewer sees, step by step
- **🎙 Voiceover** — verbatim English narration to read
- **💬 On-screen text** — optional overlay (only if you have time in
  post; not required to win)
- **💡 Tip** — recording technique for that segment

---

## Pre-flight checklist

Do all of these before hitting Record.

- [ ] **Browser** open to `staging.uipath.com/hackathon26_596/DefaultTenant/testmanager_/ACR2/testexecutions` — already logged in, the five execution rows visible
- [ ] **Second tab** open to `https://github.com/rainingsnow0914tw-ship-it/agentclinic` (for the close shot)
- [ ] **Third tab** open to Orchestrator Process detail for `agentclinic-coded-agent` (for live trigger)
- [ ] **VS Code / your editor** open to `main.py` AND `core/agentclinic/detect.py` AND `examples/golden_traces/01_hard_hat_loop.golden.json` in three tabs
- [ ] **Terminal** open in `RaidMeter-UiPath` directory with the Test Cloud publish command pre-typed (don't run yet):
      ```
      PYTHONPATH=core python -m agentclinic publish examples/golden_traces/01_hard_hat_loop.golden.json --project-name "AgentClinic Reports v2" --project-prefix ACR2 --coach uipath
      ```
- [ ] **Desktop background** — no personal photos, screenshots, or unrelated app windows
- [ ] **Browser bookmarks bar** — hide (Ctrl+Shift+B) or clear of personal entries
- [ ] **Notifications** — Windows Focus Assist on "Alarms only"; close Slack/Discord/email
- [ ] **Microphone** — test 30s sample first, headset preferred over laptop mic
- [ ] **Screen resolution** — 1920×1080 minimum (1080p), 16:9 aspect
- [ ] **Tray icons** — hide non-essential ones (right-click taskbar → Taskbar settings)
- [ ] **Browser zoom** — 110-125% on Test Manager so judges can read the multi-line reason without squinting

## Tools

- **Recording**: OBS Studio (free, professional) OR Windows Game Bar (Win+G, basic) OR Loom (browser, easy upload)
- **Trimming**: YouTube Studio's built-in trim is enough — no need to install Premiere/DaVinci
- **Captions**: YouTube auto-generates from your audio; manually correct any errors in YouTube Studio's caption editor

---

# Segment 1 · The hook · 0:00 – 0:30 (30s)

### ⏱ 0:00 – 0:30

### 🖥 Screen

1. **0:00–0:08** — Open on Test Manager UI, ACR2 project, **Executions list**. Five rows visible, the top one (`exec:trace_gold_001/run_deploy_4x`) has a red Results bar.
2. **0:08–0:15** — Click into the top row's execution detail. Show the testcase log table.
3. **0:15–0:23** — Click the `⋮` menu on the Failed log → click **Override Result**. The dialog opens showing the multi-line evidence-bound reason.
4. **0:23–0:30** — **Hold on the dialog** so viewers can read the reason text. Don't move the mouse.

### 🎙 Voiceover

> "AI agents are shipping to production faster than any prior software category — but the testing discipline traditional software earned over decades hasn't caught up.
>
> This is AgentClinic. Every finding bound to evidence in the trace, every result published natively into UiPath Test Cloud as the system of record. Coach, not surveillance.
>
> Five minutes. Here's how it works."

### 💬 On-screen text (optional)

- 0:08: lower-third caption — `Test Cloud · ACR2 · Five published goldens`
- 0:23: red box highlight around the multi-line reason text in the dialog

### 💡 Tip

This 30s sets the entire impression. **Voiceover and screen should sync exactly** — line 1 of voiceover plays over screen step 1, etc. Re-record the audio if it drifts.

---

# Segment 2 · The problem · 0:30 – 1:15 (45s)

### ⏱ 0:30 – 1:15

### 🖥 Screen

1. **0:30–0:50** — Cut to VS Code, open `examples/golden_traces/01_hard_hat_loop.golden.json`. Scroll slowly through `events[]` showing four `retry` entries with the same `state_hash`. Hover (don't click) on one `state_hash` field — let it sit on screen for 2 seconds.
2. **0:50–1:05** — Cut to a slide or a quick screenshot: "**ChatGPT review of the same trace**" with placeholder confident-but-unsourced output (one paragraph of generic LLM prose).
3. **1:05–1:15** — Cut back to AgentClinic's `report.md` Section 2 — show `evidence_spans: [evt_0002, evt_0003, evt_0004]` clearly.

### 🎙 Voiceover

> "This agent retried the same broken deploy four times. State hash unchanged, no error log read in between. Seven thousand four hundred tokens, wasted.
>
> A general-purpose LLM can describe this trace, but it can't tell you *which event* drove the verdict, or verify its own claim.
>
> What we need is an audit trail — and it needs to live in the release-gate system the team already uses."

### 💬 On-screen text

- 0:50: `Generic LLM review · ⚠️ no evidence anchor` over the placeholder
- 1:05: green highlight around the `evidence_spans` line

### 💡 Tip

This is the only slide/cutaway shot in the whole video. If recording slides is painful, **just compare two screens side-by-side** (your trace JSON vs. a screenshot of ChatGPT output) — same effect.

---

# Segment 3 · The forensic pipeline · 1:15 – 2:30 (75s)

### ⏱ 1:15 – 2:30

### 🖥 Screen

1. **1:15–1:30** — Cut to terminal. The publish command is already typed. Hit Enter. The CLI runs (cmd runs ~10-15s in real time, **don't cut yet** — let viewers see live execution).
2. **1:30–1:45** — While it runs, cut to `core/agentclinic/detect.py` in editor. Scroll past the seven detector functions briefly (one second each).
3. **1:45–2:00** — Terminal output appears: `== published: execution ... ==` Show the JSON output, scroll to `test_cloud.execution.id` and `test_cloud.logs[0].result: Failed`.
4. **2:00–2:30** — Open the published `report.md` file (`out.md` or via the Test Cloud attachment). Scroll through:
   - Section 2: finding `RM-F-trace_gold_001-001`, expand `evidence_spans` showing three trace_event_ids
   - Section 5: "Information Gaps" — `no_stated_goal` entry
   - **Hold on Section 5** for 3 seconds.

### 🎙 Voiceover

> "Seven deterministic detectors, source-controlled. Every finding must point at specific trace events as evidence — a finding without an evidence span is a contract violation, rejected at the schema layer.
>
> The score is reproducible: same trace, same rules, same number, every time.
>
> Section five is the iron rule that matters most. When data is missing, we say so. No guessing. No hallucination. The report admits exactly what it cannot judge — that's how a clinic differs from a courtroom."

### 💬 On-screen text

- 1:15: terminal-style overlay — `$ uipath agentclinic publish --coach uipath`
- 2:00: green checkmark animation if your tool supports it, otherwise nothing

### 💡 Tip

**Don't speed up the terminal output**. The 10-15 second live run is the most credibility-building part — it shows the system actually works, in real time, not edited. If you must trim, only cut between "publish command runs" and "report.md opens" — never inside the live run.

---

# Segment 4 · UiPath Test Cloud integration · 2:30 – 3:30 (60s)

### ⏱ 2:30 – 3:30

### 🖥 Screen

1. **2:30–2:40** — Cut to Orchestrator → Processes → `agentclinic-coded-agent` 0.1.1 detail page. Click **Start now**.
2. **2:40–2:50** — The job submission dialog. Show the input JSON in the Trace field (pre-pasted; if first time, narrate while typing). Click Confirm/Start.
3. **2:50–3:05** — Jobs list, the new job appears Running → Successful (~30s real time; **trim to 15 seconds** with a single cut, but keep "Running" visible for 3s before the cut so viewers know it's real).
4. **3:05–3:15** — Cut to Test Manager → ACR2 → Executions. F5 refresh. The new execution row appears at the top. Click it.
5. **3:15–3:25** — Click the failed Test Case Log → Override Result. The dialog opens.
6. **3:25–3:30** — **Hold on the multi-line evidence-bound reason** for 5 seconds. Let it breathe.

### 🎙 Voiceover

> "Same agent, this time triggered from Automation Cloud. Same pipeline as the local runtime, but now writing the result straight into Test Manager.
>
> One Test Case per pattern, reusable across runs. One Test Set, one Execution per publish. A per-pattern log with the evidence-bound reason visible right in the dialog the reviewer already uses. The full markdown report attached.
>
> Quality is no longer a late-stage checkpoint. It's a continuous, governed capability — exactly the shape Track 3 is asking for."

### 💬 On-screen text

- 3:25: red box highlight around the multi-line reason

### 💡 Tip

**This is the climax segment.** The 5-second hold at 3:25 is the single most important shot in the whole video — that's the moment a judge sees "evidence chain → UI dialog → release gate" in one frame. **Don't rush past it**. If anywhere in the video you go over budget, cut from segment 2 (the problem), never from this hold.

---

# Segment 5 · Four roles + Close · 3:30 – 4:45 (75s)

### ⏱ 3:30 – 4:15 · Four roles (45s)

### 🖥 Screen

Slide with the four roles diagram (use a simple text slide or screenshot from the README):

```
👨‍⚖️ JUDGE        deterministic rule engine — runs without an LLM
🏃 COACH        LLM, bounded — translate findings, forbidden to judge
📋 RECORDER     UiPath Test Cloud — execution + log + attachment
🎼 ORCHESTRATOR  UiPath — Process + AI Trust Layer audit
```

Each role pops in one at a time, one per ~10 seconds. If you can't animate, just leave the slide static and use voiceover.

### 🎙 Voiceover

> "Four roles, no overlap.
>
> Judge is deterministic — the LLM cannot revise the verdict.
>
> Coach rides UiPath's AgentHub LLM Gateway, so every LLM call stays inside the AI Trust Layer for audit and PII redaction. No direct LLM provider API key.
>
> Test Cloud is the system of record.
>
> UiPath is the orchestration and governance layer that ties everything together. That's the Track 3 framing — quality as a continuous, intelligent, governed capability across the enterprise."

### 💡 Tip

This is the slowest segment for voice — speak deliberately, one role at a time. **Do not crowd words**.

---

### ⏱ 4:15 – 4:45 · Close (30s)

### 🖥 Screen

1. **4:15–4:25** — Cut to GitHub repo page (`https://github.com/rainingsnow0914tw-ship-it/agentclinic`). Pan slowly: badge bar (CI green), README first paragraph, scroll to `docs/ERROR_MATRIX.md` link.
2. **4:25–4:35** — Open a terminal, run `git log --oneline | head -25`. Show 23+ commits scrolling.
3. **4:35–4:43** — End frame: GitHub URL + `Track 3 · AgentHack 2026` text overlay. Static, no motion.
4. **4:43–4:45** — Fade to black (2 frames is enough).

### 🎙 Voiceover

> "The whole codebase was written by Claude Code over eleven days. Every commit visible in the git log.
>
> Repository public, MIT licensed, CI green, error matrix documented.
>
> Drop a trace in, get an audit trail.
>
> Thank you."

### 💬 On-screen text

- 4:35: `github.com/rainingsnow0914tw-ship-it/agentclinic`
- 4:35: `UiPath AgentHack 2026 · Track 3 · Agentic Testing`

### 💡 Tip

End on a static frame, not on motion. Judges sometimes pause the last frame to note the GitHub URL. **Make the URL easy to read.**

---

# Post-production checklist

- [ ] **Trim to ≤ 4:50** on the final cut (gives 10s buffer below Devpost cap)
- [ ] **Audio-normalize** — no clipping, no whisper-quiet sections
- [ ] **Upload to YouTube** as **Public** or **Unlisted** (rules require "publicly visible")
- [ ] **Set thumbnail** — a clear shot from segment 4's evidence-bound reason dialog works best
- [ ] **Generate captions** — see "Captions" section below
- [ ] **Test the YouTube link in a private/incognito browser** before pasting into Devpost (catches accidentally-private uploads)
- [ ] **Paste the YouTube URL into Devpost project's `Video Demo Link` field**

# Captions / Subtitles · 3 paths

Pick one. All three satisfy Devpost's accessibility ask; the rules
don't require captions but they show polish.

### Path A · YouTube auto-caption + manual fix (recommended, easiest)

1. After upload, wait ~5-10 minutes for YouTube to auto-generate captions from your audio.
2. YouTube Studio → Subtitles → click the auto-generated track → **Edit**.
3. Read through, fix:
   - Technical terms YouTube mis-hears: "UiPath" (it often hears "you path"), "Test Cloud", "AgentHub", "Orchestrator"
   - Brand names: "Claude Code"
   - Run line-by-line, takes ~10-15 minutes for a 5-minute video.
4. **Publish** the corrected track.

### Path B · Hand-write SRT and upload (most control)

Use the SRT starter file at `docs/demo.srt` — timecodes are estimated
from the script above, you'll need to nudge them to match your final
cut. YouTube Studio → Subtitles → Upload file → select `.srt`.

### Path C · Burn-in (only if you want them visually on every viewer)

Open in your video editor, add captions as text overlay layer.
Overkill for hackathon submission — most judges have YouTube CC
enabled already. **Don't spend time on this unless YouTube CC fails.**

---

# Common pitfalls (read before recording)

- **Don't live-debug on camera.** If something breaks mid-record, stop, fix off-camera, re-record the segment. Editing out a 30s "wait, why isn't this working" is worse than re-recording cleanly.
- **Don't show personal info.** Cover Slack notifications, email previews, browser tabs with personal names. Check the taskbar and tray icons.
- **Don't go over 5:00.** Devpost truncates; judges stop watching. The script above lands at 4:45 — record each segment with a timer.
- **Don't speed up audio.** Sped-up voiceover sounds like marketing-bot. Speak at natural pace, trim *gaps* between segments instead.
- **Don't add music with copyright.** Either silence or a CC0 ambient loop (YouTube Audio Library has free ones). Most hackathon demos are music-free and that's fine.
- **Don't open the dialog and immediately close it.** Hold on key shots (segment 1's reason dialog at 0:23, segment 4's hold at 3:25). 5 seconds feels like forever when you're recording but reads as confident-and-deliberate to a viewer.

---

# If you only have time for one re-take

Re-record **Segment 4** (Test Cloud integration). That's the climax,
and it's the one shot that, if smooth, sells the whole Track 3
framing. Segments 1-3 you can tolerate small rough edges on; segment
4 needs to land clean.
