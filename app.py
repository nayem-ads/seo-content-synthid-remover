from __future__ import annotations
import json
import os
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Callable, Iterable
from wsgiref.simple_server import WSGIServer, make_server

from seo_antigravity_cleaner import (
    extract_auto_keywords,
    preserve_and_scrub_seo_detailed,
)

BASE_DIR = Path(__file__).resolve().parent
INDEX_HTML_PATH = BASE_DIR / "templates" / "index.html"


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def _json_response(
    start_response: Callable, payload: dict, status: str = "200 OK"
) -> Iterable[bytes]:
    body = json.dumps(payload).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
    ]
    start_response(status, headers)
    return [body]


def _read_json_body(environ: dict) -> dict:
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    if length <= 0:
        return {}
    raw = environ["wsgi.input"].read(length).decode("utf-8")
    return json.loads(raw) if raw else {}


def app(environ: dict, start_response: Callable) -> Iterable[bytes]:
    """
    Production WSGI application compatible with both `gunicorn app:app` on Railway
    and `python3 app.py` locally with zero third-party web framework overhead.
    """
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    if path == "/health" and method == "GET":
        return _json_response(start_response, {"status": "ok"})

    if path == "/" and method == "GET":
        html_bytes = INDEX_HTML_PATH.read_bytes()
        headers = [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(html_bytes))),
        ]
        start_response("200 OK", headers)
        return [html_bytes]

    if path == "/api/clean" and method == "POST":
        try:
            data = _read_json_body(environ)
            text = str(data.get("text") or "")
            keywords = data.get("keywords") or []
            mode = str(data.get("mode") or "deep")
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",") if k.strip()]

            result = preserve_and_scrub_seo_detailed(
                text=text, protected_keywords=keywords, mode=mode
            )
            return _json_response(start_response, result)
        except Exception as e:
            return _json_response(
                start_response,
                {"error": str(e)},
                status="500 Internal Server Error",
            )

    if path == "/api/auto-keywords" and method == "POST":
        try:
            data = _read_json_body(environ)
            text = str(data.get("text") or "")
            kws = extract_auto_keywords(text)
            return _json_response(start_response, {"keywords": kws})
        except Exception as e:
            return _json_response(
                start_response,
                {"error": str(e)},
                status="500 Internal Server Error",
            )

    return _json_response(
        start_response, {"error": "Not found"}, status="404 Not Found"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    host = "0.0.0.0"
    print(f"[*] Antigravity SEO Purifier Studio running at http://localhost:{port}")
    with make_server(host, port, app, server_class=ThreadingWSGIServer) as httpd:
        httpd.serve_forever()
