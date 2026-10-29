"""
Job link -> job description text. No AI.

1. Many job pages hide structured data (schema.org "JobPosting") with the title, company and
   full description. If it is there, we read it directly.
2. Otherwise we take the visible text of the page, and check that it looks like a job posting.

The page is downloaded into memory, read, and dropped. Nothing is saved.

Safety: the server opens a link a user typed, so we must not let it reach the server's own network.
Only public http(s) addresses are allowed, every redirect is checked again, and the download has a
size limit and a time limit.
"""

import html
import ipaddress
import json
import re
import socket
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

MAX_BYTES = 2_000_000  # a job page is ~100 KB to 2 MB
MAX_CHARS = 20_000  # same limit as a pasted job description
MAX_REDIRECTS = 4
TIMEOUT = 10.0  # seconds per network step
DEADLINE = 15.0  # seconds for the whole download (stops a server that sends one byte at a time)
MIN_PAGE_CHARS = 300

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ResumeTailor/1.0)",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
    "Accept-Language": "en-US,en;q=0.8",
}

# Words a real job posting almost always has. A page needs at least 3 different ones.
_JOB_HINTS = (
    "responsibilit",
    "qualification",
    "requirements",
    "experience",
    "skills",
    "you will",
    "we are looking",
    "apply",
    "salary",
    "benefits",
    "full-time",
    "years of",
)

_INVALID = "That doesn't look like a valid link. It should start with https://"
_UNREACHABLE = "Couldn't open that link. Check it, or paste the job text instead."
_BLOCKED = "That site doesn't let us read the page. Please paste the job text instead."
_NOT_A_JOB = "This page doesn't look like a job posting. Check the link, or paste the job text instead."


class JobPageError(ValueError):
    """The message is safe to show to the user."""


@dataclass
class JobPosting:
    text: str  # the job description, ready for the tailor
    title: str = ""
    company: str = ""
    job_number: str = ""  # the job's own ID, like REQ21135


# ------------------------------------------------------------------ 1. is this link safe to open?


def _resolve(host: str, port: int) -> list[str]:
    """Host name -> IP addresses. A separate function so tests can replace it."""
    try:
        return sorted({info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
    except (socket.gaierror, UnicodeError):
        raise JobPageError(_UNREACHABLE) from None


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%")[0])
    if ip.version == 6 and ip.ipv4_mapped:  # ::ffff:127.0.0.1 is really 127.0.0.1
        ip = ip.ipv4_mapped
    return ip.is_global  # False for localhost, 10.x, 192.168.x, 169.254.x (cloud metadata), ...


def check_url(url: str) -> str:
    """Return the cleaned link, or raise JobPageError if it is not a normal public web link."""
    url = url.strip()
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise JobPageError(_INVALID) from None
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise JobPageError(_INVALID)
    if port not in (None, 80, 443):  # no port scanning
        raise JobPageError(_INVALID)
    addresses = _resolve(parts.hostname, port or (443 if parts.scheme == "https" else 80))
    if not addresses or not all(_is_public(a) for a in addresses):
        raise JobPageError(_INVALID)
    return url


# ------------------------------------------------------------------ 2. download


def _check_status(code: int) -> None:
    if code == 404 or code == 410:
        raise JobPageError("That page wasn't found (404). The job may be closed. Check the link.")
    if code in (401, 403, 429, 999):  # 999 is LinkedIn's "no bots"
        raise JobPageError(_BLOCKED)
    if code >= 400:
        raise JobPageError(_UNREACHABLE)


def _download(url: str, client: httpx.Client) -> str:
    """The page as text. Follows redirects by hand, so every hop is checked."""
    start = time.monotonic()
    for _ in range(MAX_REDIRECTS + 1):
        check_url(url)
        with client.stream("GET", url, headers=HEADERS, timeout=TIMEOUT) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            _check_status(response.status_code)
            kind = response.headers.get("content-type", "").lower()
            if kind and "html" not in kind and "text/plain" not in kind:
                raise JobPageError("That link isn't a web page. Paste the job text instead.")
            body = bytearray()
            for chunk in response.iter_bytes():
                body += chunk
                if len(body) > MAX_BYTES:
                    raise JobPageError("That page is too big to read. Paste the job text instead.")
                if time.monotonic() - start > DEADLINE:
                    raise JobPageError(_UNREACHABLE)
            return body.decode(response.encoding or "utf-8", errors="replace")
    raise JobPageError(_UNREACHABLE)  # too many redirects


# ------------------------------------------------------------------ 3. read the page

_BLOCK_TAGS = {
    "p",
    "br",
    "div",
    "ul",
    "ol",
    "li",
    "tr",
    "section",
    "article",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
}
_SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}


class _PageReader(HTMLParser):
    """Collects the visible text and any JSON-LD blocks of an HTML page."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.json_ld: list[str] = []
        self._skip = 0
        self._ld: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and "ld+json" in (dict(attrs).get("type") or "").lower():
            self._ld = []
        elif tag in _SKIP_TAGS:
            self._skip += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n- " if tag == "li" else "\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._ld is not None:
            self.json_ld.append("".join(self._ld))
            self._ld = None
        elif tag in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ld is not None:
            self._ld.append(data)
        elif not self._skip:
            self.parts.append(data)


def _tidy(text: str) -> str:
    lines = [re.sub(r"[ \t\r\f\v\xa0]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def html_to_text(page: str) -> str:
    reader = _PageReader()
    reader.feed(page)
    reader.close()
    return _tidy("".join(reader.parts))


def _find_job_posting(node: object) -> dict | None:
    """Search JSON-LD (it can be a list, or nested in @graph) for the JobPosting."""
    if isinstance(node, list):
        for item in node:
            if found := _find_job_posting(item):
                return found
    elif isinstance(node, dict):
        kind = node.get("@type")
        if "JobPosting" in (kind if isinstance(kind, list) else [kind]):
            return node
        for value in node.values():
            if isinstance(value, dict | list) and (found := _find_job_posting(value)):
                return found
    return None


def _from_structured_data(blocks: list[str]) -> JobPosting | None:
    for block in blocks:
        try:
            posting = _find_job_posting(json.loads(block, strict=False))
        except ValueError:
            continue
        if not posting:
            continue
        description = str(posting.get("description") or "")
        if "&lt;" in description:  # some sites escape the HTML twice
            description = html.unescape(description)
        description = html_to_text(description)
        if len(description) < 100:
            continue
        org = posting.get("hiringOrganization")
        company = org.get("name") if isinstance(org, dict) else org
        title = str(posting.get("title") or "").strip()
        company = str(company or "").strip()
        ident = posting.get("identifier")
        job_id = str(
            (ident.get("value") or ident.get("name") or "") if isinstance(ident, dict) else ident or ""
        ).strip()
        fields = {"Job title": title, "Company": company}
        header = "\n".join(f"{name}: {value}" for name, value in fields.items() if value)
        return JobPosting(
            text=f"{header}\n\n{description}".strip(),
            title=title,
            company=company,
            job_number="" if is_internal_id(job_id) else job_id,
        )
    return None


# ------------------------------------------------------------------ the job's own ID (e.g. REQ21135)

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
_LONG_HEX = re.compile(r"[0-9a-f]{20,}", re.IGNORECASE)
# "Job ID: R-1234", "Requisition Number 5521", "Req ID: REQ21135". The ID must contain a digit.
_LABELLED_ID = re.compile(
    r"\b(?:job|requisition|req|reference|posting)\s*(?:id|number|no\.?|#|code)\s*[:#-]?\s*"
    r"((?=[A-Za-z0-9_-]*\d)[A-Za-z0-9][A-Za-z0-9_-]{2,30})",
    re.IGNORECASE,
)
# Many sites keep the real ID only in the data inside the page: "reqId":"REQ21135". Best keys first.
_ID_KEYS = ("customJobReqId", "reqId", "requisitionId", "requisitionNumber", "jobReqId", "jobNumber")
_ID_IN_DATA = re.compile(
    r'"(' + "|".join(_ID_KEYS) + r')"\s*:\s*"([A-Za-z0-9][A-Za-z0-9_.-]{2,30})"', re.IGNORECASE
)


def is_internal_id(value: str) -> bool:
    """A database ID like 662176bd-c1d9-4ea3-b22a-9b602ceba771 is not the number people see on the job."""
    value = value.strip()
    return bool(_UUID.fullmatch(value) or _LONG_HEX.fullmatch(value))


def find_job_number(page: str, visible_text: str) -> str:
    """The job's own ID: from the visible text first, then from the data inside the page. Or empty."""
    if (match := _LABELLED_ID.search(visible_text)) and not is_internal_id(match.group(1)):
        return match.group(1)
    found = {k.lower(): v for k, v in reversed(_ID_IN_DATA.findall(page)) if not is_internal_id(v)}
    return next((found[k.lower()] for k in _ID_KEYS if k.lower() in found), "")


def _looks_like_job(text: str) -> bool:
    low = text.lower()
    return len(text) >= MIN_PAGE_CHARS and sum(hint in low for hint in _JOB_HINTS) >= 3


def parse_job_page(page: str) -> JobPosting:
    reader = _PageReader()
    reader.feed(page)
    reader.close()

    visible = _tidy("".join(reader.parts))
    posting = _from_structured_data(reader.json_ld)
    if posting is None:
        if not _looks_like_job(visible):
            raise JobPageError(_NOT_A_JOB)
        posting = JobPosting(text=visible)

    posting.job_number = posting.job_number or find_job_number(page, visible)
    if posting.job_number and posting.job_number not in posting.text:
        posting.text = f"Job ID: {posting.job_number}\n{posting.text}"  # so the tailor can see it
    posting.text = posting.text[:MAX_CHARS]
    return posting


# ------------------------------------------------------------------ the one function to call


def fetch_job_posting(url: str, client: httpx.Client | None = None) -> JobPosting:
    """
    Job link -> JobPosting. Raises JobPageError with a message the user can act on.
    `client` is only passed by tests.
    """
    url = check_url(url)
    own_client = client is None
    client = client or httpx.Client(follow_redirects=False)
    try:
        page = _download(url, client)
    except httpx.HTTPError:
        raise JobPageError(_UNREACHABLE) from None
    finally:
        if own_client:
            client.close()
    return parse_job_page(page)
