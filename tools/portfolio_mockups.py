#!/usr/bin/env python3
"""Re-render the "This Portfolio" case study mockups from the live pages.

Loads pages of the locally served site (with ?shot, which renders them still)
inside browser and phone frames, then screenshots each composition with
headless Chrome into assets/media/portfolio/.

Usage:
    python3 -m http.server 8765        # in the repo root, in another terminal
    python3 tools/portfolio_mockups.py
"""
import json
import os
import subprocess
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = json.load(open(os.path.join(ROOT, "content", "site.json"), encoding="utf-8"))
LOCAL = "http://localhost:8765/"
DOMAIN = SITE["url"].split("://", 1)[1]          # shown in the mock address bar
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BACKDROP = "#0a1a1e"                              # matches --surface-strong

CSS = f"""
html,body{{margin:0;width:1600px;height:1000px;overflow:hidden;background:{BACKDROP};font-family:system-ui}}
.browser{{position:absolute;border-radius:14px;overflow:hidden;background:#0b0b0d;
  box-shadow:0 0 0 1px #2a2c33,0 50px 100px -30px rgba(0,0,0,.8)}}
.bar{{height:34px;display:flex;align-items:center;gap:8px;padding:0 14px;background:#1c1d23;border-bottom:1px solid #2a2c33}}
.bar i{{width:10px;height:10px;border-radius:50%;background:#3a3c44;display:block}}
.bar span{{margin-left:14px;flex:1;max-width:460px;height:20px;border-radius:6px;background:#26272e;color:#8a8d9a;font-size:11px;line-height:20px;padding-left:10px;white-space:nowrap;overflow:hidden}}
.view{{position:relative;overflow:hidden}}
.view iframe{{border:0;transform-origin:0 0;display:block}}
.phone{{position:absolute;padding:12px;border-radius:46px;background:#0c0d10;
  box-shadow:0 0 0 2px #2c2e35,0 50px 100px -30px rgba(0,0,0,.85)}}
.phone .view{{border-radius:34px}}
.notch{{position:absolute;left:50%;top:22px;width:96px;height:26px;margin-left:-48px;border-radius:14px;background:#000;z-index:2}}
"""


def browser(x, y, w, path, scale=0.62, vh=900):
    """A browser window showing `path` at desktop width, scaled down to `w` px."""
    iw, vhh = int(w / scale), int(vh * scale)
    shown = DOMAIN + path.split("?")[0]
    return (f'<div class="browser" style="left:{x}px;top:{y}px;width:{w}px">'
            f'<div class="bar"><i></i><i></i><i></i><span>{shown}</span></div>'
            f'<div class="view" style="width:{w}px;height:{vhh}px">'
            f'<iframe src="{LOCAL}{path}" width="{iw}" height="{vh}" style="transform:scale({scale})"></iframe></div></div>')


def phone(x, y, path, scale=0.8, off=0):
    """A phone showing `path` at 390px wide; `off` scrolls the page down by that many pixels."""
    w, h = 390, 844
    return (f'<div class="phone" style="left:{x}px;top:{y}px"><span class="notch"></span>'
            f'<div class="view" style="width:{int(w * scale)}px;height:{int(h * scale)}px">'
            f'<iframe src="{LOCAL}{path}" width="{w}" height="{h + off}" '
            f'style="transform:scale({scale});margin-top:{-int(off * scale)}px"></iframe></div></div>')


LAYOUTS = {
    "cover": browser(90, 110, 1080, "?shot", scale=0.75, vh=980) + phone(1130, 170, "?shot"),
    "work": browser(90, 70, 1420, "?shot#work", scale=0.95, vh=920),
    "case": browser(80, 90, 960, "professional_works/hp-appen-2-0/?shot", scale=0.66, vh=1180)
            + phone(1090, 110, "professional_works/hp-appen-2-0/?shot", off=2600),
    "about": phone(250, 150, "about/?shot") + phone(700, 150, "service/?shot") + phone(1150, 150, "contact/?shot"),
}


def main():
    out_dir = os.path.join(ROOT, "assets", "media", "portfolio")
    with tempfile.TemporaryDirectory() as tmp:
        for name, body in LAYOUTS.items():
            html = os.path.join(tmp, f"{name}.html")
            png = os.path.join(tmp, f"{name}.png")
            with open(html, "w", encoding="utf-8") as f:
                f.write(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>")
            # Headless Chrome writes the screenshot but does not always exit, so wait
            # for the file to appear and settle, then stop the process ourselves.
            proc = subprocess.Popen([
                CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                f"--user-data-dir={os.path.join(tmp, 'profile-' + name)}",
                "--window-size=1600,1000", "--force-device-scale-factor=2",
                "--virtual-time-budget=9000", "--allow-file-access-from-files",
                f"--screenshot={png}", f"file://{html}",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline, last = time.time() + 90, -1
            while time.time() < deadline and proc.poll() is None:
                size = os.path.getsize(png) if os.path.exists(png) else 0
                if size and size == last:
                    break
                last = size
                time.sleep(2)
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
            if not os.path.exists(png):
                raise SystemExit(f"Chrome did not produce {name}.png — is the local server running on :8765?")
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "84", "--resampleWidth", "2400",
                            png, "--out", os.path.join(out_dir, f"{name}.jpg")],
                           stdout=subprocess.DEVNULL, check=True)
            print("rendered", name)


if __name__ == "__main__":
    main()
