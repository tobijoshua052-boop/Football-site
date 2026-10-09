import json, os, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LEAGUES = {"eng.1", "esp.1", "ita.1", "ger.1", "fra.1", "uefa.champions"}
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
STAND = "https://site.api.espn.com/apis/v2/sports/soccer/%s/standings"
cache = {}

def upstream(kind, code):
    if kind == "scores":
        t = datetime.now(timezone.utc).date()
        return f"{SITE}/{code}/scoreboard?dates={t - timedelta(days=2):%Y%m%d}-{t + timedelta(days=3):%Y%m%d}"
    return STAND % code if kind == "table" else f"{SITE}/{code}/news"

def get(kind, code):
    hit = cache.get((kind, code))
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    try:
        req = urllib.request.Request(upstream(kind, code), headers={"User-Agent": "football-digest-site"})
        body = urllib.request.urlopen(req, timeout=15).read()
        cache[(kind, code)] = (time.time(), body)
        return body
    except Exception:
        return hit[1] if hit else None

class H(BaseHTTPRequestHandler):
    def reply(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api":
            qs = urllib.parse.parse_qs(u.query)
            kind, code = qs.get("kind", [""])[0], qs.get("league", [""])[0]
            if kind not in ("scores", "table", "news") or code not in LEAGUES:
                return self.reply(400, b'{"error":"bad request"}', "application/json")
            body = get(kind, code)
            return self.reply(200, body, "application/json") if body else self.reply(502, b'{"error":"upstream"}', "application/json")
        if u.path in ("/", "/index.html"):
            return self.reply(200, (Path(__file__).parent / "index.html").read_bytes(), "text/html; charset=utf-8")
        self.reply(404, b"Not found", "text/plain")

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", "8000"))), H).serve_forever()
