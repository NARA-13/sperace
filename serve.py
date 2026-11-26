#!/usr/bin/env python3
"""Small local server for the SPERACE web build (browsers block wasm over file://)."""
import http.server, socketserver, os, sys, webbrowser

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".wasm": "application/wasm",
        ".pck": "application/octet-stream",
        ".js": "text/javascript",
    }

    def end_headers(self):
        # PWA + audio worklets behave best with these
        self.send_header("Cache-Control", "no-store")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()

    def log_message(self, *args):
        pass


with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), Handler) as httpd:
    url = f"http://localhost:{PORT}/Web_Build/index.html"
    print(f"SPERACE is running at {url}  (Ctrl+C to stop)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    httpd.serve_forever()
