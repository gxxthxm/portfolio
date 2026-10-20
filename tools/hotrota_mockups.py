#!/usr/bin/env python3
"""Render the Hot Rota case study mockups from the Hot Rota site itself.

Loads pages of the locally served Hot Rota site (with reduced motion, so they
render still) inside browser and phone frames, then screenshots each
composition with headless Chrome into assets/media/hotrota/.

Usage:
    python3 -m http.server 8766        # in the Hot Rota folder, in another terminal
    python3 tools/hotrota_mockups.py
"""
import os
import subprocess
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL = "http://localhost:8766/"
DOMAIN = "hotrota.com/"                           # shown in the mock address bar
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BACKDROP = "#2a2826"                              # warm charcoal, close to Hot Rota's ink

CSS = f"""
html,body{{margin:0;width:1600px;height:1000px;overflow:hidden;background:{BACKDROP};font-family:system-ui}}
.browser{{position:absolute;border-radius:14px;overflow:hidden;background:#f6f2ec;
  box-shadow:0 0 0 1px #45423e,0 50px 100px -30px rgba(0,0,0,.8)}}
.bar{{height:34px;display:flex;align-items:center;gap:8px;padding:0 14px;background:#e3ded6;border-bottom:1px solid #cfcac2}}
.bar i{{width:10px;height:10px;border-radius:50%;background:#b4b0aa;display:block}}
.bar span{{margin-left:14px;flex:1;max-width:460px;height:20px;border-radius:6px;background:#f6f2ec;color:#72716d;font-size:11px;line-height:20px;padding-left:10px;white-space:nowrap;overflow:hidden}}
.view{{position:relative;overflow:hidden}}
.view iframe{{border:0;transform-origin:0 0;display:block}}
.phone{{position:absolute;padding:12px;border-radius:46px;background:#0c0d10;
  box-shadow:0 0 0 2px #45423e,0 50px 100px -30px rgba(0,0,0,.85)}}
.phone .view{{border-radius:34px;background:#f6f2ec}}
.notch{{position:absolute;left:50%;top:22px;width:96px;height:26px;margin-left:-48px;border-radius:14px;background:#000;z-index:2}}
"""


def browser(x, y, w, path, scale=0.62, vh=900, off=0):
    """A browser window showing `path` at desktop width, scaled down to `w` px; `off` scrolls the page down."""
    iw, vhh = int(w / scale), int(vh * scale)
    shown = DOMAIN + (path.split("#")[0] if path != "index.html" else "")
    return (f'<div class="browser" style="left:{x}px;top:{y}px;width:{w}px">'
            f'<div class="bar"><i></i><i></i><i></i><span>{shown}</span></div>'
            f'<div class="view" style="width:{w}px;height:{vhh}px">'
            f'<iframe src="{LOCAL}{path}" width="{iw}" height="{vh + off}" '
            f'style="transform:scale({scale});margin-top:{-int(off * scale)}px"></iframe></div></div>')


def phone(x, y, path, scale=0.8, off=0):
    """A phone showing `path` at 390px wide; `off` scrolls the page down by that many pixels."""
    w, h = 390, 844
    return (f'<div class="phone" style="left:{x}px;top:{y}px"><span class="notch"></span>'
            f'<div class="view" style="width:{int(w * scale)}px;height:{int(h * scale)}px">'
            f'<iframe src="{LOCAL}{path}" width="{w}" height="{h + off}" '
            f'style="transform:scale({scale});margin-top:{-int(off * scale)}px"></iframe></div></div>')


LAYOUTS = {
    "cover": browser(90, 110, 1080, "index.html", scale=0.75, vh=980) + phone(1130, 170, "index.html"),
    "help": browser(90, 70, 1420, "index.html", scale=0.95, vh=920, off=1380),
    "films": browser(80, 90, 960, "films.html", scale=0.66, vh=1180)
             + phone(1090, 110, "film.html?id=the-picnic-affair"),
    "info": phone(250, 150, "info.html") + phone(700, 150, "info.html", off=2350)
            + phone(1150, 150, "post.html?id=film-night-for-two"),
}


def main():
    out_dir = os.path.join(ROOT, "assets", "media", "hotrota")
    os.makedirs(out_dir, exist_ok=True)
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
                "--force-prefers-reduced-motion",  # skip the curtain intro and entrance animations
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
                raise SystemExit(f"Chrome did not produce {name}.png — is the Hot Rota server running on :8766?")
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "84", "--resampleWidth", "2400",
                            png, "--out", os.path.join(out_dir, f"{name}.jpg")],
                           stdout=subprocess.DEVNULL, check=True)
            print("rendered", name)


if __name__ == "__main__":
    main()
