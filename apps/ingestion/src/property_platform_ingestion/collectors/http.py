"""HTTPS acquisition with explicit URLs, byte budgets and real collector timestamps."""

import base64
import hashlib
import ipaddress
import ssl
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
from property_platform.modules.evidence.source_withdrawals import is_withdrawn

MAX_SESSION_BYTES = 64 * 1024 * 1024
MAX_SESSION_RESPONSES = 600


class AcquisitionError(ValueError):
    """A collection failed; no old receipt is substituted for the failed request."""


def checked_url(url: str) -> str:
    """Check reviewed configuration, not an arbitrary URL submitted by a visitor."""
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or parsed.fragment
            or "." not in parsed.hostname
            or parsed.hostname.endswith((".local", ".localhost", ".internal"))
            or any(ord(char) < 33 for char in url)
        ):
            raise AcquisitionError("Source URL must be an explicit public HTTPS URL")
        try:
            ipaddress.ip_address(parsed.hostname)
        except ValueError:
            return url
    except (AttributeError, TypeError, ValueError) as exc:
        if isinstance(exc, AcquisitionError):
            raise
        raise AcquisitionError("Malformed source URL") from exc
    raise AcquisitionError("Literal IP addresses are not accepted as sources")


@dataclass(frozen=True)
class Acquisition:
    url: str
    payload: bytes
    fetched_started_at: datetime
    fetched_at: datetime
    http_status: int
    etag: str = ""
    last_modified_raw: str = ""

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()

    def capture_receipt(self) -> dict:
        """Fields consumed by evidence.Capture, retaining unsuccessful HTTP responses."""
        return {
            "url": self.url,
            "fetched_started_at": self.fetched_started_at,
            "fetched_at": self.fetched_at,
            "http_status": self.http_status,
            "etag": self.etag,
            "last_modified_raw": self.last_modified_raw,
            "acquisition_method": "scheduled_https_collect",
            "timestamp_basis": "collector_clock",
        }

    def property_receipt(self) -> dict:
        """Exact receipt format accepted by the existing property review importer."""
        if self.http_status != 200 or not self.payload:
            raise AcquisitionError("Property acquisition requires a non-empty HTTP 200 response")
        return {
            "url": self.url,
            "fetched_started_at": self.fetched_started_at.isoformat(),
            "fetched_at": self.fetched_at.isoformat(),
            "http_status": self.http_status,
            "sha256": self.sha256,
            "payload": base64.b64encode(self.payload).decode("ascii"),
        }


class SourceHTTP:
    """One acquisition session, no redirects or hidden retries, bounded source bytes.

    Approved URLs come exclusively from reviewed repository source registries. The
    transport parameter enables network-free tests; production keeps certificate
    verification enabled with the operating system certificate store.
    """

    def __init__(
        self,
        allowed_urls: Iterable[str],
        *,
        transport: httpx.BaseTransport | None = None,
        min_interval_seconds: float = 0.5,
        total_timeout_seconds: float = 120,
        max_session_bytes: int = MAX_SESSION_BYTES,
        max_session_responses: int = MAX_SESSION_RESPONSES,
    ):
        self._allowed_urls = frozenset(checked_url(url) for url in allowed_urls)
        if not self._allowed_urls:
            raise AcquisitionError("At least one reviewed source URL is required")
        if not 0 <= min_interval_seconds <= 60 or not 1 <= total_timeout_seconds <= 300:
            raise AcquisitionError("Invalid acquisition pacing or timeout")
        if type(max_session_bytes) is not int or not 1 <= max_session_bytes <= MAX_SESSION_BYTES:
            raise AcquisitionError("Invalid acquisition session byte budget")
        if (
            type(max_session_responses) is not int
            or not 1 <= max_session_responses <= MAX_SESSION_RESPONSES
        ):
            raise AcquisitionError("Invalid acquisition session response budget")
        self._interval = min_interval_seconds
        self._total_timeout = total_timeout_seconds
        self._max_session_bytes = max_session_bytes
        self._received_bytes = 0
        self._max_session_responses = max_session_responses
        self._request_count = 0
        self._acquisitions: list[Acquisition] = []
        self._last_requests: dict[str, float] = {}
        self._client = httpx.Client(
            transport=transport,
            verify=ssl.create_default_context(),
            follow_redirects=False,
            trust_env=False,
            timeout=httpx.Timeout(connect=15, read=30, write=15, pool=15),
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=4),
            headers={
                "User-Agent": "PropertyPlatform/0.1 (scheduled source acquisition)",
                "Accept-Encoding": "identity",
            },
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._client.close()

    @property
    def acquisitions(self) -> tuple[Acquisition, ...]:
        """Completed real responses survive rejection by a source parser.

        The tuple and its frozen items cannot be edited by the caller. Partial
        streams, missing responses and exhausted budgets never invent a capture.
        """
        return tuple(self._acquisitions)

    def fetch(
        self,
        url: str,
        *,
        max_bytes: int,
        allowed_base: str | None = None,
        read_timeout_seconds: float = 30,
    ) -> Acquisition:
        """Allow query parameters only when a connector verified a registered base."""
        checked_url(url)
        # Last guard for every connector, including manual runs of a skipped source.
        if is_withdrawn(url):
            raise AcquisitionError("Source site is withdrawn by owner decision")
        if allowed_base is None:
            approved = url in self._allowed_urls
        else:
            parsed = urlsplit(url)
            base = urlsplit(allowed_base)
            approved = (
                allowed_base in self._allowed_urls
                and not base.query
                and (parsed.scheme, parsed.netloc, parsed.path)
                == (base.scheme, base.netloc, base.path)
            )
        if not approved:
            raise AcquisitionError("Source URL is not registered for this connector")
        if type(max_bytes) is not int or not 1 <= max_bytes <= 16 * 1024 * 1024:
            raise AcquisitionError("Invalid response byte budget")
        if type(read_timeout_seconds) not in (float, int) or not 1 <= read_timeout_seconds <= 120:
            raise AcquisitionError("Invalid source read timeout")
        if self._received_bytes >= self._max_session_bytes:
            raise AcquisitionError("Acquisition exceeds the session byte budget")
        if self._request_count >= self._max_session_responses:
            raise AcquisitionError("Acquisition exceeds the session response budget")
        host = urlsplit(url).hostname
        pause = self._interval - (time.monotonic() - self._last_requests.get(host, 0))
        if pause > 0:
            time.sleep(pause)
        started, clock = datetime.now(UTC), time.monotonic()
        self._last_requests[host] = clock
        self._request_count += 1
        try:
            timeout = httpx.Timeout(connect=15, read=read_timeout_seconds, write=15, pool=15)
            with self._client.stream("GET", url, timeout=timeout) as response:
                if 300 <= response.status_code < 400:
                    raise AcquisitionError("Source redirects require an explicit registry review")
                if response.headers.get("Content-Encoding", "").strip().lower() not in (
                    "",
                    "identity",
                ):
                    raise AcquisitionError("Source did not honor the identity encoding request")
                length = response.headers.get("Content-Length")
                if length is not None:
                    try:
                        if int(length) < 0 or int(length) > max_bytes:
                            raise AcquisitionError("Source response exceeds its byte budget")
                        if self._received_bytes + int(length) > self._max_session_bytes:
                            raise AcquisitionError("Acquisition exceeds the session byte budget")
                    except ValueError as exc:
                        if isinstance(exc, AcquisitionError):
                            raise
                        raise AcquisitionError("Source has an invalid Content-Length") from exc
                payload, size = [], 0
                # Raw network chunks avoid buffering/decompressing arbitrary data before
                # checking size and elapsed time. The source must honor Accept-Encoding.
                for chunk in response.iter_raw():
                    if time.monotonic() - clock > self._total_timeout:
                        raise AcquisitionError("Source exceeded its total acquisition timeout")
                    size += len(chunk)
                    self._received_bytes += len(chunk)
                    if size > max_bytes:
                        raise AcquisitionError("Source response exceeds its byte budget")
                    if self._received_bytes > self._max_session_bytes:
                        raise AcquisitionError("Acquisition exceeds the session byte budget")
                    payload.append(chunk)
                if time.monotonic() - clock > self._total_timeout:
                    raise AcquisitionError("Source exceeded its total acquisition timeout")
                acquisition = Acquisition(
                    url=url,
                    payload=b"".join(payload),
                    fetched_started_at=started,
                    fetched_at=datetime.now(UTC),
                    http_status=response.status_code,
                    etag=response.headers.get("ETag", "")[:500],
                    last_modified_raw=response.headers.get("Last-Modified", "")[:160],
                )
                self._acquisitions.append(acquisition)
                return acquisition
        except httpx.HTTPError as exc:
            # Do not include response bytes, cookies or potentially sensitive query values.
            raise AcquisitionError(f"Source transport failed: {type(exc).__name__}") from exc
