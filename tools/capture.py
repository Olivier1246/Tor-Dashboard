"""Capture dashboard screenshots into docs/screenshots/ via Playwright.

Run the demo server first (tools/demo_server.py on port 8096), then:
    .venv/Scripts/python.exe tools/capture.py
"""
import asyncio
import os

import pyotp
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8096"
OUT = "docs/screenshots"
TOTP = "XKGR62XMKXIKGAGHUM6RMRZOIWUGJP3J"


async def main():
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900}, device_scale_factor=2
        )
        pg = await ctx.new_page()

        # Login page (before authenticating)
        await pg.goto(BASE + "/login", wait_until="networkidle")
        await pg.wait_for_timeout(600)
        await pg.screenshot(path=f"{OUT}/login.png")
        print("captured login")

        # Authenticate
        await pg.fill("input[name=username]", "admin")
        await pg.fill("input[name=password]", "Demo1234567")
        await pg.fill("input[name=totp]", pyotp.TOTP(TOTP).now())
        await pg.click("button[type=submit]")
        await pg.wait_for_url(BASE + "/")

        # Dashboard: let the sparklines fill from a few polls
        await pg.wait_for_timeout(32000)
        await pg.screenshot(path=f"{OUT}/dashboard.png", full_page=True)
        print("captured dashboard")

        for name, wait in [("history", 2800), ("connections", 2200),
                           ("config", 1200), ("control", 1200)]:
            await pg.goto(BASE + f"/{name}", wait_until="networkidle")
            await pg.wait_for_timeout(wait)
            await pg.screenshot(path=f"{OUT}/{name}.png", full_page=True)
            print("captured", name)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
