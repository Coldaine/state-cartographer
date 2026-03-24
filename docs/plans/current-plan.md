# Execution Plan: Observation-First Automation Runtime

> Historical note: moved from `docs/plans/plan.md`. It preserves an older observation-first runtime phase and legacy `OBS/NAV/EXE/AUT` terminology.


> This document replaces `plans/phase-reset.md`, `plans/automation-runtime-consolidation.md`, 
> and `plans/alas-observation-launch-plan.md`. It reflects the actual working code in the repo.

## Phase 0: Foundation Reality Check

### What Actually Works

| Component | Status | Evidence |
|-----------|--------|----------|
| `pilot_bridge.py` | **REAL** | DroidCast screenshots + ADB tap/swipe. The only working live backend. |
| `alas_observe_runner.py` | **REAL** | Monkeypatch instrumentation captures screenshots + ALAS page labels. |
| `vlm_detector.py` | **REAL** | Qwen3.5-9B-AWQ page detection. Replaces pixel anchors entirely. |
| `label_raw_stream.py` | **REAL** | Labels corpus frames from ALAS log timestamps. |
| `executor.py` | **PARTIAL** | Action dispatch works. `read_resource` is stub. `conditional` is broken. |
| `scheduler.py` | **PLACEHOLDER** | `pick_next()` exists. Not wired to executor. Not imported anywhere. |
| `locate.py` | **OBSOLETE** | Pixel-anchor classifier. Returns "unknown" for all real frames. |
| `calibrate.py` | **OBSOLETE** | Pixel RGB sampling. Superseded by VLM detection. |
| `graph.json` | **REFERENCE ONLY** | ALAS-derived coordinates. Untested against live game. |

### What Went Wrong

The original plan assumed pixel-color anchors would work. They don't. The RGB values in 
`graph.json` are from ALAS source code (`Button.color` tuples), not sampled from real pixels.
Result: 0% classification rate on real screenshots.

**The pivot:** Use VLM (Vision Language Model) for state detection instead of pixel matching.
- Qwen3.5-9B-AWQ runs locally (~18GB VRAM)
- Or use Claude/GPT-4V API for classification
- Either way, no pixel calibration needed

### Phase 0 Exit Criteria

- [ ] VLM classifies screenshots correctly against held-out test set (>80% accuracy)
- [ ] ALAS monkeypatch produces labeled corpus: `(screenshot, page_label, task_label)`
- [ ] PilotBridge backend verified: screenshot → tap → screenshot cycle works

---

## Phase 1: Corpus Collection

### 1.1 ALAS Instrumentation (Existing)

`scripts/alas_observe_runner.py` monkeypatches ALAS methods to emit events:
- `module/device/screenshot.py` → captures every screenshot
- `module/ui/ui.py` → logs page transitions  
- `module/device/control.py` → logs tap/swipe actions

**Run:**
```bash
uv run python scripts/alas_observe_runner.py \
  --config PatrickCustom \
  --duration 3600 \
  --output data/corpus/run-20260320
```

**Output:**
```
data/corpus/run-20260320/
  index.jsonl          # {"ts": "...", "path": "000001.png", "alas_page": "page_main", "task": "Commission"}
  000001.png
  000002.png
  ...
```

### 1.2 Log-Based Labeling (Existing)

If ALAS already ran, label existing `raw_stream` frames:

```bash
uv run python scripts/label_raw_stream.py \
  --log vendor/AzurLaneAutoScript/log/2026-03-20_PatrickCustom.txt \
  --raw-stream data/raw_stream \
  --output data/corpus/labeled/index.jsonl
```

### 1.3 Deduplication

Remove near-duplicate frames to keep corpus lean:

```bash
uv run python scripts/screenshot_dedupe.py \
  --input data/corpus/run-20260320 \
  --output data/corpus/run-20260320/dedup_report.json
```

### Phase 1 Exit Criteria

- [ ] >=500 labeled screenshots covering >=10 unique pages
- [ ] Deduplicated to <=100 representative frames per page
- [ ] Index.jsonl validates against schema

---

## Phase 2: VLM Validation

### 2.1 Validated Model: Qwen3.5-9B-AWQ

**Hardware:** RTX 5090 (or equivalent ~18GB VRAM)
**Serving:** vLLM with AWQ quantization for 4-bit inference

**Setup:**
```bash
pip install vllm

# Option A: Full precision (requires ~18GB VRAM)
vllm serve QuantTrio/Qwen3.5-9B-AWQ \
  --quantization awq \
  --limit-mm-per-prompt image=1 \
  --max-model-len 8192 \
  --port 18900
```

**Test against corpus:**
```bash
# Evaluates accuracy against labeled corpus
uv run python scripts/vlm_detector.py \
  --eval-corpus \
  --corpus data/corpus/run-20260320 \
  --endpoint http://localhost:18900/v1 \
  --model QuantTrio/Qwen3.5-9B-AWQ
```

### 2.2 VLM Detection Interface

```python
# scripts/vlm_detector.py
from pathlib import Path

class VLMDetector:
    def __init__(self, base_url: str = "http://localhost:18900/v1", model: str = "QuantTrio/Qwen3.5-9B-AWQ"):
        self.client = openai.OpenAI(base_url=base_url, api_key="dummy")
        self.model = model
        self.pages = self._load_pages_from_graph()
    
    def detect_page(self, image_path: Path) -> tuple[str, str]:
        """Returns (page_id, raw_response)."""
        # Implements _PAGE_DETECT_TMPL prompt
        ...
    
    def locate_element(self, image_path: Path, description: str) -> tuple[int, int] | None:
        """Returns (x, y) coordinates for element description."""
        # Implements _LOCATE_TMPL prompt
        ...
```

### 2.3 Hybrid Detection Strategy

For runtime efficiency, layer detection:

1. **Black frame filter:** Skip classification if `dark_fraction > 0.9`
2. **Session cache:** If last state was `page_main` and screenshot hash matches, return cached
3. **VLM classification:** Full vision model for unknown/new states

```python
def locate(screenshot: Path, session: Session) -> dict:
    # 1. Black frame check
    if is_black_frame(screenshot):
        return {"state": "unknown", "confidence": 0.0, "reason": "transition"}
    
    # 2. Session history constraint
    if session.last_state and screenshot_hash_matches(session.last_screenshot, screenshot):
        return {"state": session.last_state, "confidence": 0.95, "source": "cache"}
    
    # 3. VLM classification
    page_id, raw = vlm.detect_page(screenshot)
    return {"state": page_id, "confidence": 0.85, "source": "vlm", "raw": raw}
```

### Phase 2 Exit Criteria

- [ ] Qwen3.5-9B-AWQ achieves >80% top-1 accuracy on held-out corpus
- [ ] Per-page precision/recall reported (identify which pages need more training data)
- [ ] Classification latency <2s per frame at 1280x720
- [ ] VLM service stays stable under load (100 consecutive classifications)

---
## Phase 3: Executor Hardening

The executor exists but has bugs. Fix the real backend before building the daemon loop.

### 3.1 Backend Integration

**Current:** `executor.py` has `default_backend()` with broken imports (see Gap 9 from old consolidation doc).
**Fix:** Replace with `PilotBridgeBackend` class.

```python
# scripts/executor.py
class PilotBridgeBackend:
    """Production backend using pilot_bridge for screenshot + control."""
    
    def __init__(self, serial: str = "127.0.0.1:21513"):
        self.bridge = PilotBridge(serial=serial)
        self.vlm = VLMDetector()  # From Phase 2
    
    def screenshot(self) -> Path:
        return self.bridge.capture()
    
    def tap(self, x: int, y: int) -> None:
        self.bridge.tap(x, y)
    
    def locate(self) -> dict:
        """VLM-based state detection."""
        screenshot = self.screenshot()
        page_id, _ = self.vlm.detect_page(screenshot)
        return {
            "state": page_id,
            "confidence": 0.85 if page_id != "page_unknown" else 0.0,
            "screenshot": str(screenshot)
        }
    
    def navigate(self, target_state: str, graph: dict) -> dict:
        """Pathfind → tap sequence → verify arrival."""
        current = self.locate()["state"]
        if current == target_state:
            return {"success": True, "state": target_state}
        
        route = pathfind(graph, current, target_state)
        for transition in route["transitions"]:
            self.execute_transition(transition)
            # Verify arrival
            arrived = self._wait_for_state(transition["to"], timeout=10)
            if not arrived:
                return {"success": False, "error": f"Failed to arrive at {transition['to']}"}
        
        return {"success": True, "state": target_state}
```

### 3.2 Action Type Implementation

Complete the stub actions in executor:

| Action | Status | Implementation |
|--------|--------|----------------|
| `navigate` | Works | Pathfind + tap sequence |
| `tap` | Works | ADB tap at coordinates |
| `wait` | Works | `time.sleep(seconds)` |
| `assert_state` | Partial | VLM verify, retry if mismatch |
| `read_resource` | **STUB** | VLM OCR or pixel read |
| `conditional` | **BROKEN** | Implement condition evaluation |

**Fix `read_resource`:**
```python
def _read_resource_real(self, resource: str, region: dict | None = None) -> dict:
    """Read resource value from screenshot.
    
    Options:
    1. VLM: "What is the Oil value shown in top right?"
    2. OCR: pytesseract on cropped region
    3. Pixel: Color sample for progress bars
    """
    screenshot = self.screenshot()
    
    if region:
        # Crop and OCR
        crop = crop_screenshot(screenshot, region)
        value = ocr_digits(crop)
    else:
        # VLM query
        value = self.vlm.query(screenshot, f"What is the current {resource} value?")
    
    return {"success": True, "resource": resource, "value": value}
```

### 3.3 Arrival Verification

Every navigation must verify arrival, not assume:

```python
def _wait_for_state(self, target: str, timeout: int = 10) -> bool:
    """Poll VLM until target state detected or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        current = self.locate()["state"]
        if current == target:
            return True
        time.sleep(1)  # Account for VLM latency
    return False
```

### 3.4 Event Logging

Wire `execution_event_log.py` into executor:

```python
def execute_task(self, task: dict) -> dict:
    log = ExecutionEventLog()
    task_id = task["id"]
    
    log.append({
        "ts": datetime.utcnow().isoformat(),
        "event_type": "task_start",
        "task_id": task_id,
        "state_before": self.locate()["state"]
    })
    
    try:
        for action in task["actions"]:
            result = self.execute_action(action)
            log.append({
                "ts": datetime.utcnow().isoformat(),
                "event_type": "action_complete",
                "action": action,
                "result": result
            })
            if not result["success"]:
                raise ActionFailed(action, result)
        
        log.append({
            "ts": datetime.utcnow().isoformat(),
            "event_type": "task_complete",
            "task_id": task_id,
            "state_after": self.locate()["state"]
        })
        return {"success": True}
        
    except ActionFailed as e:
        log.append({
            "ts": datetime.utcnow().isoformat(),
            "event_type": "task_failed",
            "task_id": task_id,
            "error": str(e)
        })
        return {"success": False, "error": str(e)}
```

### Phase 3 Exit Criteria

- [ ] `executor.py --backend pilot --task commission` runs end-to-end
- [ ] Every navigation verifies arrival via VLM
- [ ] Event log captures all actions with before/after state
- [ ] `read_resource` returns actual values (not stub)
- [ ] Error strategies work: retry, restart, skip, escalate

---

## Phase 4: Scheduler + Daemon Loop

### 4.1 Wiring Scheduler to Executor

Currently `scheduler.py` is standalone. Import and use it:

```python
# scripts/daemon.py (new file)
from scheduler import Scheduler, TaskManifest
from executor import Executor, PilotBridgeBackend
from resource_model import ResourceStore

class AutomationDaemon:
    def __init__(self, tasks_path: Path, graph_path: Path, config: dict):
        self.scheduler = Scheduler(TaskManifest.load(tasks_path))
        self.executor = Executor(PilotBridgeBackend(), graph_path)
        self.resources = ResourceStore()
        self.running = False
    
    def run_once(self) -> dict:
        """Single iteration: pick task, execute, schedule next."""
        # 1. Pick next task
        task = self.scheduler.pick_next(
            now=datetime.now(),
            resources=self.resources
        )
        if not task:
            return {"status": "idle", "next_wakeup": self.scheduler.next_wakeup()}
        
        # 2. Execute
        result = self.executor.execute_task(task)
        
        # 3. Update resources if task reported changes
        if result.get("resource_deltas"):
            self.resources.apply_deltas(result["resource_deltas"])
        
        # 4. Schedule next run
        self.scheduler.schedule_next(task, success=result["success"])
        
        return {"status": "executed", "task": task["id"], "result": result}
    
    def run_loop(self) -> None:
        """Main daemon loop with circuit breaker."""
        self.running = True
        failure_counts = {}
        
        while self.running:
            iteration = self.run_once()
            
            if iteration["status"] == "executed":
                task_id = iteration["task"]
                if iteration["result"]["success"]:
                    failure_counts[task_id] = 0
                else:
                    failure_counts[task_id] = failure_counts.get(task_id, 0) + 1
                    
                    # Circuit breaker: 3 consecutive failures
                    if failure_counts[task_id] >= 3:
                        self._disable_task(task_id)
                        self._escalate(f"Task {task_id} failed 3 times consecutively")
            
            # Sleep until next wakeup or 5 min max
            sleep_duration = min(
                self.scheduler.seconds_until_next_task(),
                300
            )
            time.sleep(sleep_duration)
```

### 4.2 Error Strategy Enforcement

Task definitions specify `error_strategy`. Daemon must implement:

```python
def _handle_task_failure(self, task: dict, result: dict) -> None:
    strategy = task.get("error_strategy", "escalate")
    
    if strategy == "retry":
        # Already counted by circuit breaker, will retry next cycle
        pass
    
    elif strategy == "restart":
        # Inject restart task at head of queue
        restart_task = self._build_restart_task()
        self.scheduler.inject_priority(restart_task)
    
    elif strategy == "skip":
        # Log and move on
        self.scheduler.schedule_next(task, success=True)  # Mark as "done" to skip
    
    elif strategy == "escalate":
        self._escalate(f"Task {task['id']} failed with strategy=escalate")
```

### 4.3 Agent Escalation

When escalation triggers:

```python
def _escalate(self, reason: str) -> None:
    """Pause daemon, emit escalation payload for agent review."""
    self.running = False
    
    payload = {
        "ts": datetime.utcnow().isoformat(),
        "type": "escalation",
        "reason": reason,
        "screenshot": str(self.executor.backend.screenshot()),
        "current_state": self.executor.locate(),
        "recent_events": self.executor.event_log.tail(10),
        "resources": self.resources.to_dict(),
        "proposed_recovery": [
            "Check current state manually",
            "Restart emulator if needed",
            "Resume daemon with: daemon.resume()"
        ]
    }
    
    # Write to file for agent to find
    Path("data/escalation.json").write_text(json.dumps(payload, indent=2))
    print(f"ESCALATION: {reason}")
    print("Daemon paused. Review data/escalation.json and call daemon.resume()")
```

### Phase 4 Exit Criteria

- [ ] `daemon.py --tasks examples/azur-lane/tasks.json` runs for 1 hour autonomously
- [ ] Circuit breaker triggers after 3 consecutive failures
- [ ] Escalation writes payload and pauses cleanly
- [ ] On resume, daemon re-orients via VLM and continues
- [ ] Event log shows complete task lifecycle

---

## Phase 5: Emulator Lifecycle

### 5.1 System-Level Emulator Monitor

Use Win32 API (not ADB) to check emulator health:

```python
# scripts/emulator_monitor.py
import ctypes
from mss import mss

def check_emulator_window() -> dict:
    """Check MEmu window state via Win32."""
    # Find window by class/title
    hwnd = ctypes.windll.user32.FindWindowW(b"MEmu", None)
    if not hwnd:
        return {"status": "not_found"}
    
    # Check if responding
    if ctypes.windll.user32.IsHungAppWindow(hwnd):
        return {"status": "not_responding", "hwnd": hwnd}
    
    # Capture screenshot via MSS (Windows desktop)
    with mss() as sct:
        monitor = sct.monitors[1]  # Primary
        screenshot = sct.grab(monitor)
        # Crop to emulator window region...
    
    return {"status": "running", "hwnd": hwnd}

def classify_frame_brightness(screenshot) -> str:
    """Classify emulator state from brightness."""
    dark_fraction = compute_dark_fraction(screenshot)
    if dark_fraction > 0.95:
        return "black_screen"
    elif dark_fraction > 0.7:
        return "loading"
    else:
        return "game_visible"
```

### 5.2 Startup Sequence

```python
def ensure_game_ready(emulator="memu", serial="127.0.0.1:21513", timeout=180) -> dict:
    """Full startup from cold emulator to page_main."""
    start = time.time()
    
    while time.time() - start < timeout:
        # 1. Check emulator window
        emu = check_emulator_window()
        if emu["status"] == "not_found":
            start_emulator()
            time.sleep(20)
            continue
        
        if emu["status"] == "not_responding":
            kill_emulator()
            continue
        
        # 2. Check ADB connection
        if not adb_connected(serial):
            adb_connect(serial)
            time.sleep(2)
            continue
        
        # 3. Check ATX agent
        if not atx_alive(serial):
            init_atx(serial)
            time.sleep(5)
            continue
        
        # 4. Check game state via VLM
        screenshot = capture_screenshot()
        state = vlm.detect_page(screenshot)
        
        if state == "page_main":
            return {"success": True, "state": "page_main", "duration": time.time() - start}
        elif state == "page_title":
            tap(640, 360)  # "PRESS TO START"
            time.sleep(10)
        elif state == "page_announcement":
            tap(1203, 91)  # Close announcement
            time.sleep(2)
        else:
            # Unknown state, try to recover to main
            goto_main()
    
    return {"success": False, "error": "timeout", "last_state": state}
```

### Phase 5 Exit Criteria

- [ ] `ensure_game_ready()` works from cold start to page_main in <2 minutes
- [ ] Detects and recovers from: emulator crash, ADB disconnect, ATX down, game not running
- [ ] All transitions logged with screenshots

---

## Phase 6: Full Integration

### 6.1 Agent Control Surface

Provide the three-tier API from AGENTS.md:

```python
# scripts/runtime_api.py

def where_am_i(backend: PilotBridgeBackend) -> dict:
    """Tier 2: Supervisory query."""
    return backend.locate()

def navigate_to(target: str, backend: PilotBridgeBackend, graph: dict) -> dict:
    """Tier 1: High-level runtime call."""
    return backend.navigate(target, graph)

def execute_task_by_id(task_id: str, daemon: AutomationDaemon) -> dict:
    """Tier 1: High-level runtime call."""
    task = daemon.scheduler.get_task(task_id)
    return daemon.executor.execute_task(task)

def ensure_game_ready(config: dict) -> dict:
    """Tier 1: High-level runtime call."""
    return emulator_lifecycle.ensure_game_ready(**config)
```

### 6.2 Success Metrics

| Metric | Target |
|--------|--------|
| Navigation success rate | >90% (A→B via pathfind) |
| Task completion rate | >80% (end-to-end task execution) |
| Mean time between escalation | >30 minutes |
| Startup time (cold→main) | <120 seconds |
| VLM classification accuracy | >85% |
| Autonomous runtime | 4+ hours |

### Phase 6 Exit Criteria

- [ ] Full task loop: Commission, Research, Dorm, Reward run autonomously
- [ ] Recover from emulator crash without human intervention
- [ ] 4-hour continuous runtime with <5 escalations
- [ ] All success metrics met

---

## Appendix: Deleted/Archived Documents

| Old Document | Disposition | Reason |
|--------------|-------------|--------|
| `plans/phase-reset.md` | **Delete** | Prescribed pixel calibration, superseded by VLM |
| `plans/automation-runtime-consolidation.md` | **Delete** | Pre-VLM gap analysis, 14 gaps mostly moot |
| `plans/alas-observation-launch-plan.md` | **Delete** | Sidecar spec unnecessary, monkeypatch exists |
| `synthesis.md` | Archive | Historical founding doc |
| `novel-capabilities.md` | Archive | Pitch document, capabilities now in code |
| `alas-state-machine-build-plan.md` | Archive | 5-layer plan superseded by execution plan |

