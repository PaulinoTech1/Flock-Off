"""Tests for scripts/fetch_client.py content decoding.

Regression test: the stdlib urllib fallback advertised
"Accept-Encoding: gzip, deflate, br" but never decoded the response body,
so a gzipping server produced binary garbage that was fingerprinted as
page text (false drift, e.g. the 2026-10-09 Tompkins County push block).
The client must return decoded text for gzip/deflate responses.
"""
import gzip
import os
import sys
import threading
import unittest
import zlib
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fetch_client as fc

BODY = "<html><head><title>Test page</title></head><body>Hello, Flock-Off.</body></html>"


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/gzip":
            payload = gzip.compress(BODY.encode("utf-8"))
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Encoding", "gzip")
        elif self.path == "/deflate":
            payload = zlib.compress(BODY.encode("utf-8"))
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Encoding", "deflate")
        elif self.path == "/plain":
            payload = BODY.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/html")
            payload = b"not found"
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class TestContentDecoding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def _url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def test_decompress_body_gzip(self):
        raw = gzip.compress(b"hello")
        self.assertEqual(fc._decompress_body(raw, "gzip"), b"hello")

    def test_decompress_body_deflate(self):
        raw = zlib.compress(b"hello")
        self.assertEqual(fc._decompress_body(raw, "deflate"), b"hello")

    def test_decompress_body_identity_passthrough(self):
        self.assertEqual(fc._decompress_body(b"hello", None), b"hello")
        self.assertEqual(fc._decompress_body(b"hello", "identity"), b"hello")

    def test_decompress_body_corrupt_falls_back_to_raw(self):
        # Never fail the fetch on undecodable bytes; return them as-is.
        self.assertEqual(fc._decompress_body(b"not-gzip", "gzip"), b"not-gzip")

    def test_urllib_backend_decodes_gzip(self):
        client = fc.FetchClient()
        # NB: do not assert client.backend here. The test calls _fetch_urllib
        # directly, which exercises the stdlib fallback regardless of which
        # backend is default. CI installs curl_cffi via requirements.txt, so
        # asserting backend == "urllib" fails there (2026-10-09 incident).
        status, url, html = client._fetch_urllib(self._url("/gzip"))
        self.assertEqual(status, "ok")
        self.assertIn("Hello, Flock-Off.", html)
        self.assertNotIn("\ufffd", html[:20])  # no binary garbage

    def test_urllib_backend_decodes_deflate(self):
        client = fc.FetchClient()
        status, url, html = client._fetch_urllib(self._url("/deflate"))
        self.assertEqual(status, "ok")
        self.assertIn("Hello, Flock-Off.", html)

    def test_urllib_backend_plain_still_works(self):
        client = fc.FetchClient()
        status, url, html = client._fetch_urllib(self._url("/plain"))
        self.assertEqual(status, "ok")
        self.assertIn("Hello, Flock-Off.", html)

    def test_urllib_backend_does_not_offer_brotli(self):
        # The fallback cannot decode brotli (no stdlib support), so it must
        # not advertise it: a server must never answer with undecodable br.
        seen = {}

        orig_urlopen = fc.urllib.request.urlopen

        class _Resp:
            status = 200
            headers = {"Content-Type": "text/html", "Content-Encoding": None}

            def geturl(self):
                return "http://x/"

            def read(self, n):
                return b"<html></html>"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=None):
            seen["accept_encoding"] = req.get_header("Accept-encoding")
            return _Resp()

        fc.urllib.request.urlopen = fake_urlopen
        try:
            fc.FetchClient()._fetch_urllib("http://127.0.0.1:1/")
        finally:
            fc.urllib.request.urlopen = orig_urlopen
        self.assertNotIn("br", (seen.get("accept_encoding") or "").split(","))


if __name__ == "__main__":
    unittest.main()
