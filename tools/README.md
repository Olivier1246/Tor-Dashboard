# Screenshot tooling

Scripts used to generate the README screenshots in `docs/screenshots/`. They
are **not** required to run the dashboard.

They spin up a demo instance with realistic **mock** data (no real Tor needed)
and capture each page with a headless browser.

## Requirements

```bash
pip install playwright pillow
python -m playwright install chromium
```

## Usage

```bash
# Terminal 1 — demo server with mock data on port 8096
python tools/demo_server.py

# Terminal 2 — capture all pages into docs/screenshots/
python tools/capture.py
```

Generated demo state (`demo_users.json`, `demo_history.db`) is git-ignored.
