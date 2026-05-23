---
id: PLAN-0001
title: Living Progress — Streaming Visual Feedback for resume-resume
status: draft
created: '2026-04-01'
milestone: MS-0001
tags:
  - ux
  - streaming
  - progress
  - native-ui
verification:
  - 'Tier 0: Claude Code shows gray progress lines under tool spinner during boot_up/search
  execution'
  - 'Tier 1: Floating HUD appears within 500ms of tool call, shows live updates, auto-dismisses'
  - 'Tier 2: Streaming cards with CSS animation render in floating window, match Perplexity
  visual quality'
  - No tier regresses tool response time by more than 200ms
  - HUD does not steal keyboard focus from terminal/IDE
---
## Why

resume-resume does parallel work (BM25 search, git scanning, L2 lookups, bookmark reads) but returns one blob at the end. The user stares at a spinner with no sense of progress. This violates the Living Memory thesis — living memory should feel alive.

Perplexity solved this: show the thinking happening in real time. Not because users read every line, but because streaming results provide proof of life, progressive value, and perceived speed.

## Architecture

Three tiers, each building on the last. Ship each tier independently — each one is valuable alone.

### Tier 0: Context.info() Progress Logging (1 hour)

MCP protocol already supports `Context.info()` logging that Claude Code renders as gray lines under the tool spinner. resume-resume uses none of it.

**What changes:**
- Convert heavy tools from sync → async: `boot_up`, `search_sessions`, `project_orient`
- Add `ctx: Context` parameter to each
- Emit `await ctx.info("...")` at key milestones during execution
- Emit `await ctx.report_progress(n, total)` for countable operations

**Example for boot_up:**
```python
@mcp.tool()
async def boot_up(hours: int = 24, ctx: Context = None) -> dict:
    if ctx: await ctx.info(f"Scanning sessions from last {hours}h...")
    sessions = find_recent_sessions(hours)
    if ctx: await ctx.info(f"Found {len(sessions)} sessions, checking {len(repos)} repos...")
    # parallel git scanning
    if ctx: await ctx.info(f"Git: {len(dirty)} dirty repos, loading bookmarks...")
    # bookmark loading
    if ctx: await ctx.info(f"Scoring {len(candidates)} sessions by urgency...")
```

**Example for search_sessions:**
```python
if ctx: await ctx.info(f"BM25 searching '{query}' across {len(all_sessions)} sessions...")
# after ThreadPoolExecutor completes
if ctx: await ctx.info(f"{len(matches)} matches, scoring top {limit}...")
```

**Example for project_orient:**
```python
if ctx: await ctx.info(f"Loading L2 summaries for {project_name}...")
if ctx: await ctx.info(f"Found {len(topics)} topics, checking git state...")
if ctx: await ctx.info(f"Reading latest bookmark...")
```

**Files touched:**
- `resume_resume/mcp_server.py` — boot_up, search_sessions (sync → async + ctx)
- `resume_resume/l2_tools.py` — project_orient, project_summary (add ctx)

**Verification:**
- Start Claude Code, call any resume-resume tool, see gray progress lines under spinner
- Confirm lines appear incrementally (not all at once at end)

**Risk:** Claude Code may not render `info()` lines for MCP tools. If not, skip to Tier 1.

---

### Tier 1: PyObjC Floating HUD (half day)

A native macOS floating panel that shows live status lines — checkmarks, spinners, results streaming in. Spawned as a subprocess, receives JSON-lines on stdin.

**Architecture:**
```
MCP tool starts heavy operation
  → subprocess.Popen("python -m resume_resume.progress_hud")
  → writes JSON-lines to stdin: {"event": "status", "line": "BM25: 42 matches", "icon": "search"}
  → HUD renders each line with animation
  → tool writes {"event": "done"} → HUD fades out and exits
```

**HUD spec:**
- NSPanel with NSWindowStyleMaskHUDWindow (translucent dark overlay)
- Non-activating (doesn't steal focus from terminal)
- Always on top, positioned bottom-right of screen
- 360px wide, height adjusts to content
- 5-8 NSTextField lines, each with SF Symbol icon + text
- Lines animate in (fade + slide from right)
- Checkmark replaces spinner when step completes
- Auto-dismisses 1.5s after "done" event

**Files to create:**
- `resume_resume/progress_hud.py` — the PyObjC NSPanel subprocess (~100 LOC)
- `resume_resume/progress.py` — thin wrapper: `start_hud()` returns a `ProgressHUD` object with `.update(text, icon)` and `.done()` methods (~30 LOC)

**Integration in mcp_server.py:**
```python
@mcp.tool()
async def boot_up(hours: int = 24, ctx: Context = None) -> dict:
    hud = start_hud()  # spawns subprocess
    hud.update("Scanning sessions...", icon="magnifyingglass")
    sessions = find_recent_sessions(hours)
    hud.update(f"Found {len(sessions)} sessions", icon="checkmark")
    hud.update(f"Git scanning {len(repos)} repos...", icon="arrow.triangle.2.circlepath")
    # ...
    hud.done()  # fade out + exit
```

**Verification:**
- Call boot_up from Claude Code
- See floating HUD appear bottom-right with live status updates
- HUD auto-dismisses after results return
- Confirm HUD doesn't steal keyboard focus

---

### Tier 2: WKWebView Streaming Cards (1 day)

Replace NSTextField in the HUD with a WKWebView rendering HTML/CSS. This enables full Perplexity-grade visual streaming: animated cards, typewriter text, progress bars, source chips.

**Architecture change from Tier 1:**
- Same subprocess pattern, same JSON-lines stdin protocol
- NSPanel now contains a WKWebView instead of NSTextFields
- WKWebView loads inline HTML string with CSS transitions
- JavaScript receives events via `window.webkit.messageHandlers` or polling stdin-injected script
- CSS handles all animation (slide-in cards, fade transitions, pulsing skeletons)

**HTML/CSS spec:**
```html
<div class="results">
  <!-- Each result streams in as a card -->
  <div class="card entering">
    <span class="icon">🔍</span>
    <span class="text typewriter">BM25: searching 1,247 sessions...</span>
  </div>
</div>
```

**CSS animations:**
- `.entering` → slide up + fade in (200ms ease-out)
- `.typewriter` → text appears character by character (50ms/char)
- `.complete .icon` → crossfade from spinner to checkmark
- `.card` → subtle background pulse while in-progress

**Files to create/modify:**
- `resume_resume/progress_hud.py` — replace NSTextField with WKWebView (~150 LOC)
- `resume_resume/progress_template.html` — inline HTML/CSS/JS for the streaming UI (~80 LOC)

**Verification:**
- Same as Tier 1 but visually richer
- Cards slide in with animation
- Text appears progressively
- Matches Perplexity's streaming feel

---

## Execution Order

1. **Tier 0 first** — takes 1 hour, immediately tells us if Claude Code renders progress. If it does, this alone may be "good enough" and we ship it.
2. **Tier 1 if Tier 0 isn't enough** — the native HUD is the minimum visual that feels like "living memory." Half day to build.
3. **Tier 2 only if we want the wow** — full Perplexity clone. Only pursue if the project needs a demo-quality experience.

## Dependencies

- PyObjC 11.1 (already installed) for Tier 1/2
- FastMCP Context API (already in mcp SDK) for Tier 0
- No new pip dependencies for any tier

## Risks

1. Claude Code may not render `Context.info()` for MCP tools — test first before building Tier 0
2. PyObjC NSPanel may require `NSApplication.sharedApplication()` initialization which conflicts with headless subprocess — test in isolation first
3. WKWebView in subprocess may need entitlements on newer macOS — test on current OS version
