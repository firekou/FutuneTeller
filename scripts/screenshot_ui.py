"""啟動 Streamlit 並以 Playwright 實際操作 UI、截圖（真實模型回覆）。

python scripts/screenshot_ui.py [--out handoffs/executor/screenshots] [--port 8599]
環境已預裝 Chromium 時以 PLAYWRIGHT_CHROMIUM 或 /opt/pw-browsers 下的執行檔啟動。
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def chromium_path() -> str | None:
    if os.getenv("PLAYWRIGHT_CHROMIUM"):
        return os.getenv("PLAYWRIGHT_CHROMIUM")
    c = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return c[-1] if c else None


def wait_http(url: str, timeout: int = 60) -> None:
    t = time.time()
    while time.time() - t < timeout:
        try:
            urllib.request.urlopen(url, timeout=3)
            return
        except Exception:
            time.sleep(1)
    raise TimeoutError(url)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "handoffs" / "executor" / "screenshots"))
    ap.add_argument("--port", type=int, default=8599)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"),
                             "--server.headless", "true", "--server.port", str(a.port),
                             "--browser.gatherUsageStats", "false"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, cwd=ROOT)
    try:
        url = f"http://localhost:{a.port}"
        wait_http(url + "/_stcore/health")
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium_path())
            pg = b.new_page(viewport={"width": 1400, "height": 1000})
            pg.goto(url)
            pg.get_by_text("明衡老師").first.wait_for(timeout=60000)
            time.sleep(2)
            pg.get_by_text("能力範圍").click()
            time.sleep(1)
            pg.screenshot(path=str(out / "01_home_health_capabilities.png"), full_page=True)

            # 側欄選擇擲骰結果：乾／離／上
            for label, value in [("紅（上卦）", "乾"), ("黑（下卦）", "離"), ("爻", "上")]:
                pg.locator(f"div[data-testid='stSelectbox']:has-text('{label}') input").click()
                pg.keyboard.type(value)
                pg.keyboard.press("Enter")
                time.sleep(0.8)
            pg.get_by_role("button", name="帶入我的擲骰結果").click()
            time.sleep(2)
            box = pg.get_by_placeholder("說說你想釐清的事…")
            box.fill("我擲出來的這一爻在說什麼？我在猶豫要不要結束一段拖了很久的關係。")
            box.press("Enter")
            pg.get_by_text("來源定位").first.wait_for(timeout=240000)
            time.sleep(1)
            pg.get_by_text("來源定位").first.click()
            time.sleep(1)
            pg.screenshot(path=str(out / "02_cast_consult_with_sources.png"), full_page=True)

            box.fill("那我可以幫我用紫微斗數看看嗎？")
            box.press("Enter")
            pg.wait_for_function("document.querySelectorAll('[data-testid=\"stChatMessage\"]').length >= 5",
                                 timeout=240000)
            time.sleep(2)
            pg.screenshot(path=str(out / "03_followup_out_of_scope.png"), full_page=True)

            pg.get_by_role("button", name="🧹 清除本次對話（session）").click()
            time.sleep(3)
            pg.screenshot(path=str(out / "04_after_clear_session.png"), full_page=True)
            b.close()
        print("screenshots ->", out)
        return 0
    finally:
        proc.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
