#!/usr/bin/env python3
"""Render the Larder case study mockups from the Larder app itself.

Serves Larder's production build (dist/) on a local port. Each screen is
opened at /__shot, which is the app's own index.html with its settings stored
first (demo banner dismissed, light or dark theme), and screenshotted on its own
with headless Chrome. The sample kitchen is the store's starting state, so it
loads alongside those settings. The screenshots are then placed in browser and
phone frames and each composition is screenshotted into assets/media/larder/.

Usage:
    npm run build                      # in the Larder folder, if dist/ is stale
    python3 tools/larder_mockups.py <path to the Larder folder>
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
PORT = 8770
BACKDROP = "#1d2a1f"                              # deep green, Larder's accent family
DOMAIN = "gxxthxm.github.io/larder-app/"         # shown in the mock address bar
DESKTOP = (1440, 900)
TALL = (1440, 1900)                               # long page, shown from an offset (scrolling is unreliable)
PHONE = (500, 1082)                               # Chrome's narrowest window, at a phone's aspect

# name: (route, theme, window size)
SCREENS = {
    "home": ("/", "light", DESKTOP),
    "recipes": ("/recipes", "light", DESKTOP),
    "impact-dark": ("/impact", "dark", DESKTOP),
    "m-home": ("/", "light", PHONE),
    "m-recipes": ("/recipes", "light", PHONE),
    "m-recipe": ("/recipes/palak-paneer", "light", PHONE),
    "m-add": ("/add", "light", PHONE),
    "m-inventory": ("/inventory", "light", PHONE),
    "m-impact": ("/impact", "light", PHONE),
    "m-home-dark": ("/", "dark", PHONE),
}

CSS = f"""
html,body{{margin:0;width:1600px;height:1000px;overflow:hidden;background:{BACKDROP};font-family:system-ui}}
.browser{{position:absolute;border-radius:14px;overflow:hidden;background:#f6f1e7;
  box-shadow:0 0 0 1px #34483a,0 50px 100px -30px rgba(0,0,0,.8)}}
.bar{{height:34px;display:flex;align-items:center;gap:8px;padding:0 14px;background:#e9e6df;border-bottom:1px solid #d8d4cb}}
.bar i{{width:10px;height:10px;border-radius:50%;background:#bdb8ad;display:block}}
.bar span{{margin-left:14px;flex:1;max-width:460px;height:20px;border-radius:6px;background:#fbfaf7;color:#6f6a60;font-size:11px;line-height:20px;padding-left:10px}}
.browser img,.phone img{{display:block}}
.phone{{position:absolute;padding:10px;border-radius:50px;background:#0c0d10;
  box-shadow:0 0 0 2px #34483a,0 50px 100px -30px rgba(0,0,0,.85)}}
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
    "cover": lambda s: browser(s, "home", "/", 80, 110, 1100) + phone(s, "m-home", 1150, 170, 290),
    "cook": row(["m-home", "m-recipes", "m-recipe"]),
    "recipes": lambda s: browser(s, "recipes", "/recipes", 100, 60, 1400),
    "kitchen": row(["m-add", "m-inventory", "m-impact"]),
    "dark": lambda s: browser(s, "impact-dark", "/impact", 80, 110, 1100) + phone(s, "m-home-dark", 1150, 170, 290),
}

# Prepended to the app's page: store the settings before the app boots (saved
# state is merged over the store's starting state, so the sample kitchen stays),
# and show Framer Motion's entrance animations at their end state. Framer
# animates through inline styles, which some screens leave mid-fade in a headless
# capture; the app's own opacity comes from classes, so this touches only motion.
BOOT = """<style>[style*="opacity"]{opacity:1!important;transform:none!important}</style><script>
const theme = new URLSearchParams(location.search).get('theme');
const settings = { currency: '\u20b9', theme, bannerDismissed: true, celebrated: false };
localStorage.setItem('larder.v1', JSON.stringify({ state: { settings }, version: 1 }));
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


def screenshot(url, png, size, tmp, tries=4):
    """Screenshot `url` at `size` (CSS px, 2x) into `png`, retrying blank captures.

    Now and then Chrome takes the screenshot before the app has painted, which
    leaves a near-empty PNG.
    """
    for _ in range(tries):
        if os.path.exists(png):
            os.remove(png)
        capture(url, png, size, tmp)
        if os.path.getsize(png) > 40000:
            return
    raise SystemExit(f"Chrome kept producing a blank {png}")


def capture(url, png, size, tmp):
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
    out_dir = os.path.join(ROOT, "assets", "media", "larder")
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
