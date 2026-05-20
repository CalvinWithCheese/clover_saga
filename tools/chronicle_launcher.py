from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / "workflow" / "runtime"
STATE_FILE = RUNTIME_DIR / "chronicle_server_state.json"
LOG_FILE = RUNTIME_DIR / "chronicle_server.log"

DEFAULT_PORT = 8000
TARGET_PAGE = "The Saga of Clover Stonefield.html"
STARTUP_TIMEOUT_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 0.25


class LauncherError(RuntimeError):
    pass


def build_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/{quote(TARGET_PAGE)}"


def page_is_available(url: str) -> bool:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=1.0) as response:
            return 200 <= response.status < 400
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def wait_for_page(url: str, process: subprocess.Popen[bytes] | None = None) -> bool:
    deadline = time.time() + STARTUP_TIMEOUT_SECONDS
    while time.time() < deadline:
        if page_is_available(url):
            return True
        if process is not None and process.poll() is not None:
            return False
        time.sleep(POLL_INTERVAL_SECONDS)
    return False


def save_state(pid: int, port: int, url: str) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(
            {
                "pid": pid,
                "port": port,
                "url": url,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def load_state() -> dict[str, object] | None:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def remove_state() -> None:
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def start_server(port: int) -> subprocess.Popen[bytes]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = LOG_FILE.open("ab")
    creationflags = 0
    creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port)],
            cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            close_fds=True,
        )
    finally:
        log_handle.close()

    return process


def open_in_browser(url: str) -> None:
    webbrowser.open(url)


def open_chronicle(port: int, no_browser: bool) -> int:
    url = build_url(port)

    if page_is_available(url):
        if not no_browser:
            open_in_browser(url)
        print(f"Chronicle is already available at {url}")
        return 0

    process = start_server(port)
    if not wait_for_page(url, process):
        remove_state()
        raise LauncherError(
            "The local server did not become ready. "
            f"Check {LOG_FILE} for details."
        )

    save_state(process.pid, port, url)

    if not no_browser:
        open_in_browser(url)

    print(f"Chronicle server started at {url}")
    return 0


def stop_chronicle() -> int:
    state = load_state()
    if not state:
        print("No tracked chronicle server is currently running.")
        return 0

    pid = state.get("pid")
    if not isinstance(pid, int):
        remove_state()
        raise LauncherError("The saved server state is invalid.")

    url = state.get("url")
    if not isinstance(url, str) or not url:
        url = build_url(DEFAULT_PORT)

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        if not page_is_available(url):
            remove_state()
            print(f"Tracked chronicle server process {pid} is already gone.")
            return 0
        completed = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip()
            raise LauncherError(
                "Could not stop the tracked chronicle server. "
                f"taskkill said: {stderr}"
            )

    for _ in range(int(STARTUP_TIMEOUT_SECONDS / POLL_INTERVAL_SECONDS)):
        if not page_is_available(url):
            remove_state()
            print(f"Stopped chronicle server process {pid}.")
            return 0
        time.sleep(POLL_INTERVAL_SECONDS)

    raise LauncherError(f"Chronicle server process {pid} did not stop in time.")


def status_chronicle(port: int) -> int:
    url = build_url(port)
    state = load_state()
    if page_is_available(url):
        tracked = ""
        if state and isinstance(state.get("pid"), int):
            tracked = f" (tracked PID {state['pid']})"
        print(f"Chronicle is available at {url}{tracked}")
        return 0

    if state:
        remove_state()
    print(f"Chronicle is not currently reachable at {url}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Start, stop, or check the local Clover Chronicle viewer."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Local port for the HTTP server. Defaults to {DEFAULT_PORT}.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    open_parser = subparsers.add_parser("open", help="Start the server if needed and open the chronicle page.")
    open_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the server without opening a browser window.",
    )

    subparsers.add_parser("stop", help="Stop the tracked local chronicle server.")
    subparsers.add_parser("status", help="Check whether the chronicle page is currently reachable.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "open":
            return open_chronicle(args.port, args.no_browser)
        if args.command == "stop":
            return stop_chronicle()
        if args.command == "status":
            return status_chronicle(args.port)
    except LauncherError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    raise AssertionError("Unhandled command")


if __name__ == "__main__":
    raise SystemExit(main())
