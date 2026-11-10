import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        healthy = os.getenv("FAULTY_RELEASE", "false") != "true"
        status = 200 if healthy else 503
        payload = {
            "status": "healthy" if healthy else "unhealthy",
            "version": os.getenv("APP_VERSION", "dev"),
        }
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
