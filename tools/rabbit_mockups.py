#!/usr/bin/env python3
"""Render the Rabbit case study mockups from the Rabbit prototype itself.

Serves the Rabbit folder on a local port. Each screen is opened at /__shot,
which is Rabbit's own index.html with a demo state (onboarded buyer, saved
condos, a tour, a countered offer and a chat) stored first, and screenshotted
on its own with headless Chrome. Chrome windows can't be narrower than 500px,
so phone screens (?phone) are laid out 390px wide in the middle of the window
and cropped to it. The
screenshots are then placed in phone and browser frames and each composition is
screenshotted into assets/media/rabbit/.

Usage:
    python3 tools/rabbit_mockups.py <path to the Rabbit folder>
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
PORT = 8768
BACKDROP = "#1f1b29"                              # deep plum, close to Rabbit's brand tile
DESKTOP = (1640, 1010)                            # desktop window for the prototype page

DAY = 86400000
NOW = int(time.time() * 1000)
STATE = {
    "onboarded": True,
    "user": {"name": "Sam"},
    "prefs": {"budget": 240000, "beds": "1", "hoods": ["riverside", "oldtown"], "musts": ["In-unit laundry", "Near transit"]},
    "saved": ["juniper-1204", "maple-4b", "alder-808"],
    "tours": [{"id": "T-1", "listingId": "juniper-1204", "date": time.strftime("%Y-%m-%d", time.localtime(time.time() + 3 * 86400)),
               "slot": 1, "type": "person", "note": "", "created": NOW}],
    "offers": [{"id": "RB-4821", "listingId": "alder-808", "amount": 205000, "downPct": 10, "years": 30, "moveIn": "45",
                "insp": True, "fin": True, "appr": False, "pay": "wallet", "status": "countered", "counter": 210000,
                "created": NOW - DAY, "history": [{"status": "submitted", "at": NOW - DAY}, {"status": "countered", "at": NOW}]}],
    "drafts": {},
    "chats": {"juniper-1204": [
        {"from": "agent", "text": "Hi Sam, I’m Maya, the Rabbit agent for The Juniper. What would you like to know about Unit 1204?", "at": NOW - 3600000},
        {"from": "me", "text": "Is the storage locker included?", "at": NOW - 3500000},
        {"from": "agent", "text": "Yes, Unit 1204 comes with its own storage locker on P1, next to the garage spot.", "at": NOW - 3400000},
    ]},
    "recent": ["loft", "riverside"], "notifications": True,
}

# name: (route, pixels to scroll the app's view)
SCREENS = {
    "welcome": ("/welcome", 0), "home": ("/home", 0), "browse": ("/browse", 0), "search": ("/search", 0),
    "listing": ("/listing/juniper-1204", 0), "inspection": ("/listing/juniper-1204", 1180), "tour": ("/tour/juniper-1204", 0),
    "offer": ("/offer/alder-808", 0), "checkout": ("/checkout/juniper-1204", 0), "tracker": ("/offers/RB-4821", 0),
    "saved": ("/saved", 0), "chat": ("/chat/juniper-1204", 0), "account": ("/account", 0),
}

CSS = f"""
html,body{{margin:0;width:1600px;height:1000px;overflow:hidden;background:{BACKDROP};font-family:system-ui}}
.browser{{position:absolute;border-radius:14px;overflow:hidden;background:#f3f3f7;
  box-shadow:0 0 0 1px #3a3450,0 50px 100px -30px rgba(0,0,0,.8)}}
.bar{{height:34px;display:flex;align-items:center;gap:8px;padding:0 14px;background:#e6e5ee;border-bottom:1px solid #d3d1de}}
.bar i{{width:10px;height:10px;border-radius:50%;background:#b9b6c8;display:block}}
.bar span{{margin-left:14px;flex:1;max-width:460px;height:20px;border-radius:6px;background:#fdfdfe;color:#6b6880;font-size:11px;line-height:20px;padding-left:10px}}
.browser img,.phone img{{display:block}}
.phone{{position:absolute;padding:12px;border-radius:52px;background:#0c0d10;
  box-shadow:0 0 0 2px #3a3450,0 50px 100px -30px rgba(0,0,0,.85)}}
.phone img{{border-radius:40px}}
"""


def phone(shots, name, x, y, w):
    return (f'<div class="phone" style="left:{x}px;top:{y}px">'
            f'<img src="file://{shots}/{name}.png" width="{w}" height="{round(w * 844 / 390)}"></div>')


def row(names, y=110, w=320, gap=90):
    """Phones centred in a row."""
    def build(shots):
        x = (1600 - len(names) * (w + 24) - (len(names) - 1) * gap) // 2
        return "".join(phone(shots, n, x + i * (w + 24 + gap), y, w) for i, n in enumerate(names))
    return build


def desktop(shots, x=100, y=70, w=1400):
    h = round(w * DESKTOP[1] / DESKTOP[0])
    return (f'<div class="browser" style="left:{x}px;top:{y}px;width:{w}px">'
            f'<div class="bar"><i></i><i></i><i></i><span>gxxthxm.github.io/rabbit-app/#/home</span></div>'
            f'<img src="file://{shots}/desktop.png" width="{w}" height="{h}"></div>')


LAYOUTS = {
    "cover": row(["welcome", "home", "listing"]),
    "discover": row(["home", "browse", "search"]),
    "listing": row(["listing", "inspection", "tour"]),
    "offer": row(["offer", "checkout", "tracker"]),
    "account": row(["saved", "chat", "account"]),
    "desktop": desktop,
}

# Prepended to Rabbit's page: store the demo state before the app boots, keep
# the page hidden until fonts and the first screen are in, scroll the app's view
# (?s=), wait for the photos on screen, then reveal it. A capture taken too early is then blank
# rather than half-loaded, and screenshot() retries it.
BOOT = """<style>html:not(.shot-ready) body{visibility:hidden}</style><script>
localStorage.setItem('rabbit:v1', %s);
const params = new URLSearchParams(location.search);
if (params.has('phone')) document.head.insertAdjacentHTML('beforeend', '<style>.stage{width:390px;margin:0 auto}</style>');
// load and decode every photo straight away: lazy loading and async decoding
// both leave photos blank in a headless capture
new MutationObserver(() => document.querySelectorAll('img[loading], img[decoding]').forEach((i) => {
  i.removeAttribute('loading');
  i.removeAttribute('decoding');
}))
  .observe(document.documentElement, { childList: true, subtree: true });
addEventListener('load', async () => {
  await document.fonts.ready;
  const view = document.getElementById('view');
  while (!view.children.length) await new Promise((r) => setTimeout(r, 100));
  await new Promise((r) => setTimeout(r, 800)); // let the 0.34s screen transition finish
  const s = +params.get('s');
  if (s) view.scrollTop = s;
  // wait for every photo's own load event: timers would run out Chrome's
  // virtual clock before the downloads finish
  await Promise.all([...document.images].map((i) => i.complete ? 0 : new Promise((r) => { i.onload = i.onerror = r; })));
  await new Promise((r) => setTimeout(r, 200));
  document.documentElement.classList.add('shot-ready');
});
</script>"""


def serve(rabbit):
    with open(os.path.join(rabbit, "index.html"), encoding="utf-8") as f:
        shot = f.read().replace("<head>", "<head>" + BOOT % json.dumps(json.dumps(STATE)), 1).encode()

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

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Handler, directory=rabbit))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def screenshot(url, png, size, tmp, tries=4):
    """Screenshot `url` at `size` (CSS px, 2x) into `png`, retrying blank captures.

    Now and then Chrome takes the screenshot before the page has loaded. Shot
    pages stay hidden until they are ready (see BOOT), so that leaves a
    near-empty PNG.
    """
    for _ in range(tries):
        if os.path.exists(png):
            os.remove(png)
        capture(url, png, size, tmp)
        if os.path.getsize(png) > 20000:
            return
    raise SystemExit(f"Chrome kept producing a blank {png}")


def capture(url, png, size, tmp):
    # Headless Chrome writes the screenshot but does not always exit, so wait
    # for the file to appear and settle, then stop the process ourselves.
    proc = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        f"--user-data-dir={os.path.join(tmp, 'profile-' + os.path.basename(png))}",
        f"--window-size={size[0]},{size[1]}", "--force-device-scale-factor=2",
        # no --force-prefers-reduced-motion: with it, Chrome never paints the revealed page
        "--virtual-time-budget=6000", "--allow-file-access-from-files",
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
    httpd = serve(os.path.abspath(sys.argv[1]))
    base = f"http://127.0.0.1:{PORT}/__shot"
    out_dir = os.path.join(ROOT, "assets", "media", "rabbit")
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        shots = os.path.join(tmp, "shots")
        os.makedirs(shots)
        for name, (route, scroll) in SCREENS.items():
            png = os.path.join(shots, f"{name}.png")
            screenshot(f"{base}?phone&s={scroll}#{route}", png, (500, 844), tmp)
            # the screen is centred in the window, and sips crops from the centre
            subprocess.run(["sips", "-c", "1688", "780", png],
                           stdout=subprocess.DEVNULL, check=True)
            print("captured", name)
        screenshot(f"{base}?s=0#/home", os.path.join(shots, "desktop.png"), DESKTOP, tmp)
        print("captured desktop")
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
