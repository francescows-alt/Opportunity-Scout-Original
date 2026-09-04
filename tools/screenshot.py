"""Screenshot a page of the local app so an assistant can actually look at it.

Claude and Codex cannot see a browser. This script closes that gap: it starts a
throwaway Django server on its own port, loads a path in headless Chromium, and
saves a PNG the assistant can open with its file reader.

    .venv/bin/python tools/screenshot.py /inbox/
    .venv/bin/python tools/screenshot.py /applications/ --width 480 --out /tmp/mobile.png

Notes
-----
* It runs against the real local database, read-only, exactly like a browser tab.
  It never posts a form, so it cannot spend AI credit or change data.
* It uses its own port, so Francesco's `runserver` can stay running.
* Screenshots land in `.screenshots/`, which is git-ignored.
"""

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".screenshots"


def _free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _wait_until_serving(base_url, process, timeout=40):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SystemExit(f"The test server exited early:\n{process.communicate()[1]}")
        try:
            urlopen(base_url, timeout=1)
            return
        except URLError:
            time.sleep(0.25)
        except Exception:
            # Any HTTP answer at all, including a 404 or 500, means it is listening.
            return
    raise SystemExit(f"The test server did not answer on {base_url} within {timeout}s.")


def capture(path, out_file, width, height, full_page, wait_ms):
    from playwright.sync_api import sync_playwright

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    # DEBUG is on locally, so Django already trusts 127.0.0.1 with an empty ALLOWED_HOSTS.
    environment = {**os.environ, "PYTHONUNBUFFERED": "1"}
    server = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"],
        cwd=PROJECT_ROOT, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        _wait_until_serving(base_url, server)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            response = page.goto(f"{base_url}{path}", wait_until="networkidle")
            if wait_ms:
                page.wait_for_timeout(wait_ms)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out_file), full_page=full_page)
            title = page.title()
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    status = response.status if response else "no response"
    print(f"{path} -> {out_file}")
    print(f"HTTP {status} · {width}x{height}{' · full page' if full_page else ''} · title: {title!r}")
    if status != 200:
        print(f"WARNING: {path} returned HTTP {status}. The screenshot shows the error page.")
    for error in errors:
        print(f"JS ERROR: {error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", default="/applications/", help="Path to open, e.g. /inbox/")
    parser.add_argument("--out", type=Path, help="Where to save the PNG")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--viewport-only", action="store_true", help="Only the visible area, not the whole page")
    parser.add_argument("--wait-ms", type=int, default=0, help="Extra pause before the shot, for animations")
    args = parser.parse_args()

    path = args.path if args.path.startswith("/") else f"/{args.path}"
    name = path.strip("/").replace("/", "-") or "home"
    out_file = args.out or DEFAULT_OUTPUT_DIR / f"{name}.png"
    capture(path, out_file, args.width, args.height, not args.viewport_only, args.wait_ms)


if __name__ == "__main__":
    main()
