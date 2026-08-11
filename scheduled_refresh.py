"""
Automatic weekly dataset refresh scheduler.

Runs inside the always-on (VM) deployment: a daemon thread wakes up
periodically and, when the last successful refresh is more than
REFRESH_INTERVAL_DAYS old, runs `python refresh_dataset.py` as a
subprocess. Results (success or failure, with output tail) are written to
data/refresh_status.json and logged to stderr so failures show up in the
deployment logs instead of disappearing silently.

Enabled automatically in production (REPLIT_DEPLOYMENT is set). For local
testing set AUTO_REFRESH_ENABLED=1.
"""
import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("scheduled_refresh")
if not logger.handlers:
    _h = logging.StreamHandler(sys.stderr)
    _h.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

STATUS_PATH = Path("data/refresh_status.json")
REFRESH_INTERVAL_DAYS = float(os.getenv("REFRESH_INTERVAL_DAYS", "7"))
CHECK_INTERVAL_SECONDS = 60 * 60  # re-check hourly
REFRESH_TIMEOUT_SECONDS = 60 * 60  # hard cap on one refresh run
MAX_GAMES_PER_RUN = os.getenv("REFRESH_MAX_GAMES", "25")

_started = False
_start_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_status() -> dict:
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_status(update: dict):
    status = read_status()
    status.update(update)
    try:
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATUS_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(status, indent=2), encoding="utf-8")
        os.replace(tmp, STATUS_PATH)
    except Exception as e:
        logger.error(f"Could not write refresh status file: {e}")


def _seconds_since_last_success() -> float:
    status = read_status()
    ts = status.get("last_success")
    if not ts:
        return float("inf")
    try:
        last = datetime.fromisoformat(ts)
        return (datetime.now(timezone.utc) - last).total_seconds()
    except Exception:
        return float("inf")


def run_refresh_once() -> bool:
    """Run refresh_dataset.py as a subprocess and record the outcome."""
    logger.info("Starting scheduled dataset refresh...")
    _write_status({"last_attempt": _now_iso(), "state": "running"})
    try:
        proc = subprocess.run(
            [sys.executable, "refresh_dataset.py", "--seasons", "2",
             "--limit", str(MAX_GAMES_PER_RUN)],
            capture_output=True,
            text=True,
            timeout=REFRESH_TIMEOUT_SECONDS,
            cwd=str(Path(__file__).resolve().parent),
        )
        output_tail = (proc.stdout + "\n" + proc.stderr)[-4000:]
        if proc.returncode == 0:
            logger.info("Scheduled dataset refresh succeeded.")
            _write_status({
                "state": "ok",
                "last_success": _now_iso(),
                "last_error": None,
                "last_output": output_tail,
            })
            return True
        logger.error(
            f"Scheduled dataset refresh FAILED (exit {proc.returncode}). "
            f"Output tail:\n{output_tail}"
        )
        _write_status({
            "state": "failed",
            "last_error": f"refresh_dataset.py exited with code {proc.returncode}",
            "last_output": output_tail,
        })
        return False
    except subprocess.TimeoutExpired:
        logger.error("Scheduled dataset refresh FAILED: timed out.")
        _write_status({"state": "failed", "last_error": "refresh timed out"})
        return False
    except Exception as e:
        logger.error(f"Scheduled dataset refresh FAILED: {e}")
        _write_status({"state": "failed", "last_error": str(e)})
        return False


def _scheduler_loop():
    # Small startup delay so app boot isn't competing with a refresh.
    time.sleep(120)
    while True:
        try:
            due = _seconds_since_last_success() >= REFRESH_INTERVAL_DAYS * 86400
            if due:
                run_refresh_once()
        except Exception as e:
            logger.error(f"Refresh scheduler loop error: {e}")
        time.sleep(CHECK_INTERVAL_SECONDS)


def _enabled() -> bool:
    if os.getenv("AUTO_REFRESH_ENABLED", "").lower() in ("1", "true", "yes"):
        return True
    if os.getenv("AUTO_REFRESH_ENABLED", "").lower() in ("0", "false", "no"):
        return False
    # Default: on in the published deployment, off in the dev workspace.
    return bool(os.getenv("REPLIT_DEPLOYMENT"))


def start_scheduler():
    """Start the weekly refresh scheduler once per process (no-op if disabled)."""
    global _started
    with _start_lock:
        if _started:
            return
        if not _enabled():
            logger.info("Auto-refresh scheduler disabled (not in deployment; "
                        "set AUTO_REFRESH_ENABLED=1 to force).")
            _started = True
            return
        _started = True
    t = threading.Thread(target=_scheduler_loop, daemon=True, name="dataset-refresh-scheduler")
    t.start()
    logger.info(f"Auto-refresh scheduler started (every {REFRESH_INTERVAL_DAYS:g} days).")
