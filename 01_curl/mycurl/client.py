"""HTTP Client - Core functionality for mycurl."""

import json
import ssl
import sys
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urlparse

import requests
from requests.adapters import HTTPAdapter


class _CustomSSLAdapter(HTTPAdapter):
    """HTTP adapter that always uses a user-provided SSL context."""

    def __init__(self, ssl_context: ssl.SSLContext, **kwargs: Any):
        self._custom_ssl_context = ssl_context
        super().__init__(**kwargs)

    def build_connection_pool_key_attributes(self, request, verify, cert=None):
        host_params, pool_kwargs = super().build_connection_pool_key_attributes(
            request, verify, cert
        )
        pool_kwargs["ssl_context"] = self._custom_ssl_context
        return host_params, pool_kwargs


@dataclass
class RequestConfig:
    """Configuration for an HTTP request."""

    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    data: str | None = None
    json_data: Any = None
    cookies: dict[str, str] = field(default_factory=dict)
    cookie_file: str | None = None
    proxy: str | None = None
    timeout: int = 30
    verify_ssl: bool = True
    follow_redirects: bool = True
    max_redirects: int = 10
    upload_file: str | None = None
    upload_field: str = "file"
    verbose: bool = False
    include_headers: bool = False
    user_agent: str | None = None
    auth: str | None = None
    insecure: bool = False
    legacy: bool = False


@dataclass
class ResponseInfo:
    """Information about an HTTP response."""

    status_code: int
    headers: dict[str, str]
    body: str
    elapsed_ms: float
    url: str
    redirected: bool = False


class MyCurlClient:
    """A curl-like HTTP client."""

    def __init__(self, config: RequestConfig):
        self.config = config
        self.session = requests.Session()

    def execute(self) -> ResponseInfo:
        """Execute the HTTP request and return response info."""
        self._setup_session()

        method = self.config.method.upper()
        kwargs = self._build_request_kwargs()

        if self.config.verbose:
            self._print_request(method)

        response = self.session.request(method, self.config.url, **kwargs)

        self._fix_response_encoding(response)

        return ResponseInfo(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.text,
            elapsed_ms=response.elapsed.total_seconds() * 1000,
            url=response.url,
            redirected=response.history is not None and len(response.history) > 0,
        )

    def _setup_session(self) -> None:
        """Setup session with cookies, proxies, and SSL settings."""
        if self.config.proxy:
            self.session.proxies = {"http": self.config.proxy, "https": self.config.proxy}

        self.session.verify = not self.config.insecure

        if self.config.legacy or self.config.insecure:
            self._mount_custom_ssl_adapter()

        if self.config.follow_redirects:
            self.session.max_redirects = self.config.max_redirects

        if self.config.auth:
            username, password = self.config.auth.split(":", 1)
            self.session.auth = (username, password)

        if self.config.cookie_file:
            self._load_cookies_from_file(self.config.cookie_file)

        self.session.cookies.update(self.config.cookies)

    def _mount_custom_ssl_adapter(self) -> None:
        """Mount an HTTPS adapter with a custom SSL context."""
        adapter = _CustomSSLAdapter(self._build_ssl_context())
        self.session.mount("https://", adapter)

    def _build_ssl_context(self) -> ssl.SSLContext:
        """Build an SSL context honoring insecure and legacy options."""
        ctx = ssl.create_default_context()
        if self.config.insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        if self.config.legacy:
            legacy_flag = getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0)
            ctx.options |= legacy_flag
        return ctx

    def _build_request_kwargs(self) -> dict[str, Any]:
        """Build keyword arguments for the request."""
        kwargs: dict[str, Any] = {
            "headers": dict(self.config.headers),
            "timeout": self.config.timeout,
            "allow_redirects": self.config.follow_redirects,
        }

        if self.config.user_agent:
            kwargs["headers"]["User-Agent"] = self.config.user_agent

        if self.config.data:
            kwargs["data"] = self.config.data.encode("utf-8")
            if "Content-Type" not in kwargs["headers"]:
                kwargs["headers"]["Content-Type"] = "application/x-www-form-urlencoded"

        if self.config.json_data:
            kwargs["json"] = self.config.json_data
            kwargs["headers"]["Content-Type"] = "application/json"

        if self.config.upload_file:
            files = {self.config.upload_field: open(self.config.upload_file, "rb")}
            kwargs["files"] = files
            if "Content-Type" in kwargs["headers"]:
                del kwargs["headers"]["Content-Type"]

        return kwargs

    def _load_cookies_from_file(self, cookie_file: str) -> None:
        """Load cookies from a Netscape cookie file."""
        try:
            with open(cookie_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 7:
                        self.session.cookies.set(parts[5], parts[6], domain=parts[0])
        except FileNotFoundError:
            print(f"Warning: Cookie file '{cookie_file}' not found.", file=sys.stderr)

    def _fix_response_encoding(self, response: requests.Response) -> None:
        """Improve response decoding when charset is missing or misdetected."""
        if response.encoding and response.encoding.lower() not in (
            "iso-8859-1",
            "latin-1",
        ):
            return

        content = response.content[:2048].lower()
        if content.startswith(b"\xef\xbb\xbf") or b"charset=utf-8" in content:
            response.encoding = "utf-8"
        elif response.apparent_encoding:
            response.encoding = response.apparent_encoding
        else:
            response.encoding = "utf-8"

    def _print_request(self, method: str) -> None:
        """Print verbose request information."""
        print(f"* Trying {urlparse(self.config.url).netloc}...")
        print(f"* Connected to {urlparse(self.config.url).netloc}")
        print(f"> {method} {self.config.url} HTTP/1.1")
        for key, value in self.config.headers.items():
            print(f"> {key}: {value}")
        print(">")
