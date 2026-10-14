"""E2E tests for mycurl - run the real CLI against a local test server."""

import base64
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _read_body(self) -> str:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return ""
        return self.rfile.read(length).decode("utf-8", "replace")

    def _reply(self, code: int, content: str, content_type: str = "text/plain") -> None:
        data = content.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)

    def _handle(self) -> None:
        body = self._read_body()
        if self.path == "/status/404":
            self._reply(404, "not found")
            return
        if self.path == "/redirect/302":
            self.send_response(302)
            self.send_header("Location", "/final")
            self.send_header("Connection", "close")
            self.end_headers()
            return
        if self.path == "/final":
            self._reply(200, "final destination")
            return
        if self.path == "/echo":
            payload = {
                "method": self.command,
                "headers": {k: v for k, v in self.headers.items()},
                "body": body,
            }
            self._reply(200, json.dumps(payload), "application/json")
            return
        self._reply(200, "hello world")

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_PUT(self):
        self._handle()

    def do_DELETE(self):
        self._handle()

    def do_PATCH(self):
        self._handle()

    def do_HEAD(self):
        self._handle()

    def log_message(self, *args):
        pass


def run_mycurl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "mycurl", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


class TestE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_get_request(self):
        result = run_mycurl(f"{self.base}/")
        self.assertEqual(result.returncode, 0)
        self.assertIn("hello world", result.stdout)

    def test_status_404_exits_1(self):
        result = run_mycurl(f"{self.base}/status/404")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not found", result.stdout)

    def test_post_data_and_custom_header(self):
        result = run_mycurl(
            "-X", "POST",
            "-d", "name=test&value=123",
            "-H", "X-Custom: hello",
            f"{self.base}/echo",
        )
        self.assertEqual(result.returncode, 0)
        echo = json.loads(result.stdout)
        self.assertEqual(echo["method"], "POST")
        self.assertEqual(echo["body"], "name=test&value=123")
        self.assertEqual(echo["headers"].get("X-Custom"), "hello")

    def test_json_request(self):
        result = run_mycurl(
            "--json", '{"key":"value","num":42}',
            "-X", "POST",
            f"{self.base}/echo",
        )
        self.assertEqual(result.returncode, 0)
        echo = json.loads(result.stdout)
        self.assertTrue(echo["headers"].get("Content-Type", "").startswith("application/json"))
        self.assertEqual(json.loads(echo["body"]), {"key": "value", "num": 42})

    def test_include_headers(self):
        result = run_mycurl("-i", f"{self.base}/")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Content-Type", result.stdout)
        self.assertIn("hello world", result.stdout)

    def test_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "out.txt")
            result = run_mycurl("-o", out, f"{self.base}/")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(Path(out).read_text(encoding="utf-8"), "hello world")

    def test_verbose(self):
        result = run_mycurl("-v", f"{self.base}/")
        self.assertEqual(result.returncode, 0)
        self.assertIn("* Trying", result.stdout)
        self.assertIn(f"> GET {self.base}/ HTTP/1.1", result.stdout)

    def test_follow_redirect(self):
        result = run_mycurl("-L", f"{self.base}/redirect/302")
        self.assertEqual(result.returncode, 0)
        self.assertIn("final destination", result.stdout)

    def test_no_follow_redirect_by_default(self):
        result = run_mycurl(f"{self.base}/redirect/302")
        self.assertEqual(result.returncode, 0)

    def test_write_out_format(self):
        result = run_mycurl("-w", "code=%{http_code}", f"{self.base}/")
        self.assertEqual(result.returncode, 0)
        self.assertIn("code=200", result.stdout)

    def test_cookie(self):
        result = run_mycurl("-b", "session=abc123", f"{self.base}/echo")
        self.assertEqual(result.returncode, 0)
        echo = json.loads(result.stdout)
        self.assertEqual(echo["headers"].get("Cookie"), "session=abc123")

    def test_basic_auth(self):
        result = run_mycurl("-u", "user:pass", f"{self.base}/echo")
        self.assertEqual(result.returncode, 0)
        echo = json.loads(result.stdout)
        expected = "Basic " + base64.b64encode(b"user:pass").decode("ascii")
        self.assertEqual(echo["headers"].get("Authorization"), expected)

    def test_delete_method(self):
        result = run_mycurl("-X", "DELETE", f"{self.base}/echo")
        self.assertEqual(result.returncode, 0)
        echo = json.loads(result.stdout)
        self.assertEqual(echo["method"], "DELETE")

    def test_user_agent(self):
        result = run_mycurl("-A", "MyAgent/1.0", f"{self.base}/echo")
        self.assertEqual(result.returncode, 0)
        echo = json.loads(result.stdout)
        self.assertEqual(echo["headers"].get("User-Agent"), "MyAgent/1.0")

    def test_custom_user_agent_header_beats_default(self):
        result = run_mycurl(f"{self.base}/echo")
        self.assertEqual(result.returncode, 0)
        echo = json.loads(result.stdout)
        self.assertTrue(echo["headers"].get("User-Agent", "") != "")


if __name__ == "__main__":
    unittest.main()