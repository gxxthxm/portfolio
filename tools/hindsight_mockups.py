#!/usr/bin/env python3
"""Render the Hindsight case study mockups from the Hindsight app itself.

Serves Hindsight's production build (dist/) on a local port. Each screen is
opened at /__shot, which is the app's own index.html with its UI settings
stored first (demo banner dismissed, light or dark theme), and screenshotted
on its own with headless Chrome. The app seeds its sample decisions on first
load. The screenshots are then placed in browser and phone frames and each
composition is screenshotted into assets/media/hindsight/.

Usage:
    npm run build                      # in the Hindsight folder, if dist/ is stale
    python3 tools/hindsight_mockups.py <path to the Hindsight folder>
"""
import functools
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 8769
BACKDROP = "#0f2a2c"                              # deep teal, Hindsight's accent family
DOMAIN = "gxxthxm.github.io/hindsightApp/"        # shown in the mock address bar
DESKTOP = (1440, 900)
TALL = (1440, 1900)                               # long page, shown from an offset (scrolling is unreliable)
PHONE = (500, 1082)                               # Chrome's narrowest window, at a phone's aspect

# name: (route, theme, window size)
SCREENS = {
    "dash": ("/", "light", DESKTOP),
    "insights": ("/insights", "light", DESKTOP),
    "charts": ("/insights", "light", TALL),
    "list-dark": ("/decisions", "dark", DESKTOP),
    "m-dash": ("/", "light", PHONE),
    "m-new": ("/new", "light", PHONE),
    "m-review": ("/decisions/seed-15/review", "light", PHONE),
    "m-detail": ("/decisions/seed-03", "light", PHONE),
    "m-insights-dark": ("/insights", "dark", PHONE),
}

CSS = f"""
html,body{{margin:0;width:1600px;height:1000px;overflow:hidden;background:{BACKDROP};font-family:system-ui}}
.browser{{position:absolute;border-radius:14px;overflow:hidden;background:#f7f5f0;
  box-shadow:0 0 0 1px #2c4a4c,0 50px 100px -30px rgba(0,0,0,.8)}}
.bar{{height:34px;display:flex;align-items:center;gap:8px;padding:0 14px;background:#e9e6df;border-bottom:1px solid #d8d4cb}}
.bar i{{width:10px;height:10px;border-radius:50%;background:#bdb8ad;display:block}}
.bar span{{margin-left:14px;flex:1;max-width:460px;height:20px;border-radius:6px;background:#fbfaf7;color:#6f6a60;font-size:11px;line-height:20px;padding-left:10px}}
.browser img,.phone img{{display:block}}
.phone{{position:absolute;padding:10px;border-radius:50px;background:#0c0d10;
  box-shadow:0 0 0 2px #2c4a4c,0 50px 100px -30px rgba(0,0,0,.85)}}
.phone img{{border-radius:40px}}
"""


def browser(shots, name, route, x, y, w, size=DESKTOP, top=0):
    """A browser window showing a desktop-sized slice of screenshot `name`, from `top` CSS px down."""
    k = w / size[0]
    return (f'<div class="browser" style="left:{x}px;top:{y}px;width:{w}px">'
            f'<div class="bar"><i></i><i></i><i></i><span>{DOMAIN}#{route}</span></div>'
            f'<div style="height:{round(DESKTOP[1] * k)}px;overflow:hidden">'
            f'<img src="file://{shots}/{name}.png" width="{w}" height="{round(size[1] * k)}" '
            f'style="margin-top:{-round(top * k)}px"></div></div>')


def phone(shots, name, x, y, w=300):
    return (f'<div class="phone" style="left:{x}px;top:{y}px">'
            f'<img src="file://{shots}/{name}.png" width="{w}" height="{round(w * PHONE[1] / PHONE[0])}"></div>')


def row(names, y=130, w=300, gap=90):
    """Phones centred in a row."""
    def build(shots):
        x = (1600 - len(names) * (w + 20) - (len(names) - 1) * gap) // 2
        return "".join(phone(shots, n, x + i * (w + 20 + gap), y, w) for i, n in enumerate(names))
    return build


LAYOUTS = {
    "cover": lambda s: browser(s, "dash", "/", 80, 110, 1100) + phone(s, "m-dash", 1150, 170, 290),
    "insights": lambda s: browser(s, "insights", "/insights", 100, 60, 1400),
    "charts": lambda s: browser(s, "charts", "/insights", 100, 60, 1400, TALL, 625),
    "flow": row(["m-new", "m-review", "m-detail"]),
    "dark": lambda s: browser(s, "list-dark", "/decisions", 80, 110, 1100) + phone(s, "m-insights-dark", 1150, 170, 290),
}

# Prepended to the app's page: store the UI settings before the app boots.
BOOT = """<script>
const theme = new URLSearchParams(location.search).get('theme');
localStorage.setItem('hindsight.v1.ui', JSON.stringify({ state: { theme, bannerDismissed: true }, version: 1 }));
</script>"""


def serve(dist):
    with open(os.path.join(dist, "index.html"), encoding="utf-8") as f:
        shot = f.read().replace("<head>", "<head>" + BOOT, 1).encode()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if urllib.parse.urlparse(self.path).path != "/__shot":
                return super().do_GET()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(shot)

        def log_message(self, *args):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Handler, directory=dist))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def screenshot(url, png, size, tmp):
    """Screenshot `url` at `size` (CSS px, 2x) into `png` with headless Chrome."""
    # Headless Chrome writes the screenshot but does not always exit, so wait
    # for the file to appear and settle, then stop the process ourselves.
    proc = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        f"--user-data-dir={os.path.join(tmp, 'profile-' + os.path.basename(png))}",
        f"--window-size={size[0]},{size[1]}", "--force-device-scale-factor=2",
        "--virtual-time-budget=8000", "--allow-file-access-from-files",
        # the app's own reduced-motion mode shows count-ups and charts finished
        "--force-prefers-reduced-motion",
        f"--screenshot={png}", url,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline, last = time.time() + 90, -1
    while time.time() < deadline and proc.poll() is None:
        size_now = os.path.getsize(png) if os.path.exists(png) else 0
        if size_now and size_now == last:
            break
        last = size_now
        time.sleep(2)
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    if not os.path.exists(png):
        raise SystemExit(f"Chrome did not produce {png}")


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    httpd = serve(os.path.join(os.path.abspath(sys.argv[1]), "dist"))
    out_dir = os.path.join(ROOT, "assets", "media", "hindsight")
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        shots = os.path.join(tmp, "shots")
        os.makedirs(shots)
        for name, (route, theme, size) in SCREENS.items():
            screenshot(f"http://127.0.0.1:{PORT}/__shot?theme={theme}#{route}",
                       os.path.join(shots, f"{name}.png"), size, tmp)
            print("captured", name)
        httpd.shutdown()

        for name, build in LAYOUTS.items():
            html = os.path.join(tmp, f"{name}.html")
            png = os.path.join(tmp, f"{name}.png")
            with open(html, "w", encoding="utf-8") as f:
                f.write(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{build(shots)}</body></html>")
            screenshot(f"file://{html}", png, (1600, 1000), tmp)
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "84", "--resampleWidth", "2400",
                            png, "--out", os.path.join(out_dir, f"{name}.jpg")],
                           stdout=subprocess.DEVNULL, check=True)
            print("rendered", name)


if __name__ == "__main__":
    main()
