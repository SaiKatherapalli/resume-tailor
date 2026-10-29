"""Job link reader. A fake web (httpx.MockTransport) is used, so no test touches the internet."""

import json

import httpx
import pytest

from core import job_page
from core.job_page import JobPageError, fetch_job_posting

PUBLIC_IP = "93.184.216.34"

DESCRIPTION = (
    "<p>We are looking for a backend engineer. You will build REST APIs with Python and AWS.</p>"
    "<ul><li>Responsibilities: design services</li><li>Requirements: 3 years of experience</li></ul>"
)
JSON_LD_PAGE = f"""<html><head><title>x</title>
<script type="application/ld+json">{
    json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Backend Engineer",
            "identifier": {"@type": "PropertyValue", "name": "Acme", "value": "REQ-4471"},
            "hiringOrganization": {"@type": "Organization", "name": "Acme Corp"},
            "description": DESCRIPTION,
        }
    )
}</script></head><body>Hello</body></html>"""

PLAIN_PAGE = (
    """<html><head><title>Job</title><style>.a{color:red}</style></head><body>
<nav>Home</nav><h1>Backend Engineer</h1>
<p>Responsibilities: build and run APIs. Requirements: strong Python skills and 3 years of experience.
You will work with a small team. Benefits include health cover. Apply today and join us. """
    + "More details. " * 20
    + """</p>
<script>var x = "ignore me";</script></body></html>"""
)


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    """Every host name points to a public address, unless a test says otherwise."""
    monkeypatch.setattr(job_page, "_resolve", lambda host, port: [PUBLIC_IP])


def web(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def page(body: str, status: int = 200, content_type: str = "text/html; charset=utf-8"):
    return lambda request: httpx.Response(status, text=body, headers={"content-type": content_type})


# ------------------------------------------------------------------ reading a page


def test_reads_title_company_and_description_from_structured_data():
    posting = fetch_job_posting("https://jobs.example.com/1", web(page(JSON_LD_PAGE)))
    assert posting.title == "Backend Engineer"
    assert posting.company == "Acme Corp"
    assert posting.job_number == "REQ-4471"
    assert posting.text.startswith("Job ID: REQ-4471\nJob title: Backend Engineer\nCompany: Acme Corp")
    assert "REST APIs with Python and AWS" in posting.text
    assert "<p>" not in posting.text


def test_structured_data_inside_graph_and_with_escaped_html():
    data = {
        "@graph": [
            {"@type": "WebSite"},
            {
                "@type": ["JobPosting"],
                "title": "SRE",
                "hiringOrganization": "Globex",
                "description": DESCRIPTION.replace("<", "&lt;").replace(">", "&gt;"),
            },
        ]
    }
    html_page = f'<script type="application/ld+json">{json.dumps(data)}</script>'
    posting = fetch_job_posting("https://jobs.example.com/2", web(page(html_page)))
    assert (posting.title, posting.company) == ("SRE", "Globex")
    assert "&lt;" not in posting.text and "Responsibilities" in posting.text


def test_falls_back_to_visible_text():
    posting = fetch_job_posting("https://jobs.example.com/3", web(page(PLAIN_PAGE)))
    assert "Backend Engineer" in posting.text and "Requirements" in posting.text
    assert "ignore me" not in posting.text and "color:red" not in posting.text
    assert posting.title == "" and posting.company == ""


def test_text_is_limited_to_the_job_description_size():
    big = PLAIN_PAGE.replace("More details. ", "More details about the role. " * 5)
    big = big.replace("</p>", "<p>" + "x " * 30_000 + "</p>")
    assert len(fetch_job_posting("https://jobs.example.com/4", web(page(big))).text) <= job_page.MAX_CHARS


# ------------------------------------------------------------------ "check the link" answers


def test_page_that_is_not_a_job_is_rejected():
    shop = "<html><body><h1>Shoes</h1><p>Buy shoes. " + "Great price. " * 50 + "</p></body></html>"
    with pytest.raises(JobPageError, match="doesn't look like a job posting"):
        fetch_job_posting("https://shop.example.com", web(page(shop)))


def test_login_wall_is_rejected():
    with pytest.raises(JobPageError, match="doesn't look like a job posting"):
        fetch_job_posting("https://x.example.com", web(page("<body>Sign in to view this job</body>")))


@pytest.mark.parametrize(
    "link", ["hello", "ftp://example.com/job", "https://", "http://user:pw@example.com", ""]
)
def test_not_a_web_link_is_rejected(link):
    with pytest.raises(JobPageError, match="valid link"):
        fetch_job_posting(link, web(page(PLAIN_PAGE)))


@pytest.mark.parametrize(
    "status,words", [(404, "wasn't found"), (403, "paste the job text"), (999, "paste the job text")]
)
def test_site_errors_have_clear_messages(status, words):
    with pytest.raises(JobPageError, match=words):
        fetch_job_posting("https://jobs.example.com/5", web(page("nope", status)))


def test_pdf_or_image_link_is_rejected():
    with pytest.raises(JobPageError, match="isn't a web page"):
        fetch_job_posting("https://example.com/a.pdf", web(page("%PDF", content_type="application/pdf")))


def test_network_failure_is_a_clear_message():
    def boom(request):
        raise httpx.ConnectError("down")

    with pytest.raises(JobPageError, match="Couldn't open"):
        fetch_job_posting("https://jobs.example.com/6", web(boom))


def test_huge_page_is_rejected(monkeypatch):
    monkeypatch.setattr(job_page, "MAX_BYTES", 1000)
    with pytest.raises(JobPageError, match="too big"):
        fetch_job_posting("https://jobs.example.com/7", web(page("a" * 5000)))


# ------------------------------------------------------------------ the server's own network is off limits


@pytest.mark.parametrize(
    "link",
    [
        "http://localhost/admin",
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://10.0.0.5/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "https://example.com:8080/",  # odd port
    ],
)
def test_private_addresses_and_odd_ports_are_blocked(link, monkeypatch):
    monkeypatch.undo()  # use the real resolver: these are IP literals / localhost, no internet needed
    with pytest.raises(JobPageError, match="valid link"):
        fetch_job_posting(link, web(page(PLAIN_PAGE)))


def test_host_name_that_points_to_a_private_address_is_blocked(monkeypatch):
    monkeypatch.setattr(job_page, "_resolve", lambda host, port: ["192.168.1.10"])
    with pytest.raises(JobPageError, match="valid link"):
        fetch_job_posting("https://innocent.example.com/", web(page(PLAIN_PAGE)))


def test_redirect_to_a_private_address_is_blocked(monkeypatch):
    monkeypatch.setattr(
        job_page, "_resolve", lambda host, port: ["10.0.0.1"] if host == "internal" else [PUBLIC_IP]
    )

    def handler(request):
        if request.url.host == "jobs.example.com":
            return httpx.Response(302, headers={"location": "http://internal/secret"})
        return httpx.Response(200, text=PLAIN_PAGE, headers={"content-type": "text/html"})

    with pytest.raises(JobPageError, match="valid link"):
        fetch_job_posting("https://jobs.example.com/8", web(handler))


def test_normal_redirect_is_followed_and_loops_are_stopped():
    def redirect_once(request):
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "/new"})
        return httpx.Response(200, text=PLAIN_PAGE, headers={"content-type": "text/html"})

    assert "Requirements" in fetch_job_posting("https://jobs.example.com/old", web(redirect_once)).text

    def forever(request):
        return httpx.Response(302, headers={"location": "/again"})

    with pytest.raises(JobPageError, match="Couldn't open"):
        fetch_job_posting("https://jobs.example.com/loop", web(forever))


# ------------------------------------------------------------------ the job's own ID


def snowflake_like_page(identifier: str, data: str = "") -> str:
    """The structured data holds an internal database ID; the real ID is only in the page data."""
    posting = {
        "@type": "JobPosting",
        "title": "Software Engineer",
        "identifier": {"@type": "PropertyValue", "name": "Snowflake", "value": identifier},
        "hiringOrganization": {"name": "Snowflake"},
        "description": DESCRIPTION,
    }
    return (
        f'<script type="application/ld+json">{json.dumps(posting)}</script>'
        f"<script>window.__DATA__ = {data}</script><body>Software Engineer</body>"
    )


def test_internal_database_id_is_not_used_as_the_job_id():
    page_data = '{"reqId":"REQ21135","other":{"reqId":"REQ99999"}}'  # the first one is this job's
    html_page = snowflake_like_page("662176bd-c1d9-4ea3-b22a-9b602ceba771", page_data)
    posting = fetch_job_posting("https://careers.example.com/1", web(page(html_page)))
    assert posting.job_number == "REQ21135"
    assert "662176bd" not in posting.text
    assert posting.text.startswith("Job ID: REQ21135\n")


def test_no_job_id_when_only_an_internal_id_exists():
    html_page = snowflake_like_page("662176bd-c1d9-4ea3-b22a-9b602ceba771")
    posting = fetch_job_posting("https://careers.example.com/2", web(page(html_page)))
    assert posting.job_number == "" and "Job ID" not in posting.text


def test_job_id_from_the_visible_text():
    labelled = PLAIN_PAGE.replace("<h1>", "<h1>Job ID: 10583340 ")
    assert fetch_job_posting("https://jobs.example.com/9", web(page(labelled))).job_number == "10583340"
    # no ID on the page: nothing is made up
    assert fetch_job_posting("https://jobs.example.com/10", web(page(PLAIN_PAGE))).job_number == ""
