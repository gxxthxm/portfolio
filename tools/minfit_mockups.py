#!/usr/bin/env python3
"""Render the MinFit case study mockups from iOS Simulator screenshots.

Places full-resolution simulator screenshots (1320x2868, iPhone Pro Max) inside
phone frames, then screenshots each composition with headless Chrome into
assets/media/minfit/.

Usage:
    python3 tools/minfit_mockups.py <folder of screenshots>

The folder needs: 01-onboarding.png 02-home.png 03-profile.png 04-social.png
05-workouts.png 06-active.png
"""
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BACKDROP = "#0a1a1e"                              # matches --surface-strong

CSS = f"""
html,body{{margin:0;width:1600px;height:1000px;overflow:hidden;background:{BACKDROP}}}
.phone{{position:absolute;padding:10px;border-radius:52px;background:#0c0d10;
  box-shadow:0 0 0 2px #2c2e35,0 50px 100px -30px rgba(0,0,0,.85)}}
.phone img{{display:block;border-radius:42px}}
"""


def phone(src, x, y, w=300):
    """A phone frame `w` px wide showing screenshot `src`, top-left at (x, y)."""
    return (f'<div class="phone" style="left:{x}px;top:{y}px">'
            f'<img src="file://{src}" width="{w}" height="{round(w * 2868 / 1320)}"></div>')


def row(shots, y, w=300, gap=60, lift=None):
    """Phones centred in a row; `lift` raises the phone at that index for rhythm."""
    total = len(shots) * (w + 20) + (len(shots) - 1) * gap
    x = (1600 - total) // 2
    out = ""
    for i, s in enumerate(shots):
        out += phone(s, x, y - (40 if i == lift else 0), w)
        x += w + 20 + gap
    return out


def layouts(d):
    s = lambda name: os.path.join(d, name + ".png")
    return {
        "cover": row([s("04-social"), s("02-home"), s("06-active")], 150, w=330, gap=70, lift=1),
        "tabs": row([s("02-home"), s("05-workouts"), s("04-social"), s("03-profile")], 150, w=300, gap=50),
        "logging": row([s("05-workouts"), s("06-active")], 130, w=340, gap=120),
        "social": row([s("04-social"), s("03-profile")], 130, w=340, gap=120),
        "onboarding": row([s("01-onboarding")], 130, w=340),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    shots = os.path.abspath(sys.argv[1])
    out_dir = os.path.join(ROOT, "assets", "media", "minfit")
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, body in layouts(shots).items():
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
                "--allow-file-access-from-files",
                f"--screenshot={png}", f"file://{html}",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline, last = time.time() + 60, -1
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
                raise SystemExit(f"Chrome did not produce {name}.png")
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "84", "--resampleWidth", "2400",
                            png, "--out", os.path.join(out_dir, f"{name}.jpg")],
                           stdout=subprocess.DEVNULL, check=True)
            print("rendered", name)


if __name__ == "__main__":
    main()
