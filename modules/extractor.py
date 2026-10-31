import requests
import pymupdf

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from ddgs import DDGS
from urllib.parse import urlparse, unquote


MAX_CONTENT_LENGTH = 20000
MAX_SEARCH_RESULTS = 5
REQUEST_TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/pdf,"
        "application/json;q=0.9,*/*;q=0.8"
    )
}

BLOCKED_PAGE_PHRASES = [
    "client challenge",
    "checking your browser",
    "verify you are human",
    "access denied",
    "request blocked",
    "enable javascript and cookies",
    "captcha",
    "robot verification",
    "security verification",
    "temporarily unavailable",
    "403 forbidden",
    "404 not found",
    "502 bad gateway",
    "503 service unavailable"
]

REMOVE_SELECTORS = [
    "script", "style", "nav", "footer", "header",
    "aside", "noscript", "form", "svg", "iframe",
    "button", "input", "select", "textarea"
]

CONTENT_SELECTORS = [
    "article",
    "main",
    '[role="main"]',
    ".article-content",
    ".article-body",
    ".entry-content",
    ".post-content",
    ".content-body",
    ".story-body",
    ".research-content",
    "#article-content",
    "#main-content"
]


def extract_pdf_bytes(pdf_bytes, url=None, title=None):
    try:
        document = pymupdf.open(
            stream=pdf_bytes,
            filetype="pdf"
        )

        pages = []

        for page in document:
            text = page.get_text("text")
            if text:
                pages.append(text)

        content = "\n\n".join(pages).strip()
        document.close()

        if len(content) < 200:
            raise ValueError(
                "PDF contains too little readable text."
            )

        return {
            "title": title or (
                urlparse(url).netloc if url else "PDF Document"
            ),
            "source_type": "pdf",
            "url": url,
            "source_url": url,
            "published_date": None,
            "content": content[:MAX_CONTENT_LENGTH]
        }

    except Exception as error:
        raise ValueError(
            f"PDF extraction failed: {error}"
        ) from error


def is_pdf_response(url, response):
    content_type = response.headers.get(
        "Content-Type", ""
    ).lower()

    path = unquote(
        urlparse(url).path
    ).lower()

    return (
        "application/pdf" in content_type
        or path.endswith(".pdf")
        or response.content[:5] == b"%PDF-"
    )


def check_page_quality(content, title=""):
    combined = f"{title} {content}".lower()

    for phrase in BLOCKED_PAGE_PHRASES:
        if phrase in combined:
            raise ValueError(
                "The website returned a blocked, challenge, "
                "or error page instead of research content."
            )

    if len(content.strip()) < 200:
        raise ValueError(
            "Not enough readable content on this page."
        )

    if len(content.split()) < 35:
        raise ValueError(
            "The page contains too little meaningful text."
        )

    return True


def get_published_date(soup):
    date_meta_tags = [
        {"property": "article:published_time"},
        {"property": "og:article:published_time"},
        {"name": "date"},
        {"name": "pubdate"},
        {"itemprop": "datePublished"},
        {"name": "DC.date"},
        {"name": "citation_publication_date"},
        {"name": "citation_date"},
        {"name": "publication_date"}
    ]

    for attrs in date_meta_tags:
        tag = soup.find("meta", attrs=attrs)

        if tag and tag.get("content"):
            return tag["content"].strip()

    time_tag = soup.find("time")

    if time_tag:
        date_value = (
            time_tag.get("datetime")
            or time_tag.get_text(strip=True)
        )

        if date_value:
            return date_value

    return None


def clean_content_container(container):
    container = BeautifulSoup(
        str(container),
        "html.parser"
    )

    for element in container(REMOVE_SELECTORS):
        element.decompose()

    unwanted_phrases = [
        "related articles",
        "recommended articles",
        "read more",
        "share this article",
        "subscribe to our newsletter",
        "advertisement",
        "cookie preferences"
    ]

    for element in container.find_all(
        ["div", "section", "aside"]
    ):
        text = element.get_text(" ", strip=True).lower()

        if (
            text
            and len(text) < 500
            and any(
                phrase in text
                for phrase in unwanted_phrases
            )
        ):
            element.decompose()

    parts = []

    for element in container.find_all(
        ["h1", "h2", "h3", "h4", "p", "li", "blockquote"]
    ):
        text = " ".join(
            element.get_text(" ", strip=True).split()
        )

        if len(text) >= 35:
            parts.append(text)

    return "\n\n".join(parts).strip()


def extract_article_content(soup):
    candidates = []

    for selector in CONTENT_SELECTORS:
        for element in soup.select(selector):
            content = clean_content_container(element)

            if len(content) > 300:
                candidates.append(content)

    if candidates:
        return max(candidates, key=len)

    paragraphs = []

    for element in soup.find_all(
        ["h1", "h2", "h3", "h4", "p", "blockquote"]
    ):
        text = " ".join(
            element.get_text(" ", strip=True).split()
        )

        if len(text) >= 35:
            paragraphs.append(text)

    return "\n\n".join(paragraphs).strip()


def extract_url(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        response.raise_for_status()

        if is_pdf_response(url, response):
            return extract_pdf_bytes(
                response.content,
                url=response.url,
                title=urlparse(response.url).netloc
            )

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        if (
            content_type
            and "html" not in content_type
            and "xhtml" not in content_type
            and "text/plain" not in content_type
        ):
            raise ValueError(
                f"Unsupported webpage content type: {content_type}"
            )

        soup = BeautifulSoup(
            response.content,
            "html.parser"
        )

        title = (
            soup.title.get_text(strip=True)
            if soup.title
            else urlparse(response.url).netloc
        )

        published_date = get_published_date(soup)
        content = extract_article_content(soup)

        if not content:
            content = soup.get_text(
                separator=" ",
                strip=True
            )

        content = "\n\n".join(
            line.strip()
            for line in content.splitlines()
            if line.strip()
        )

        check_page_quality(content, title)

        return {
            "title": title,
            "source_type": "webpage",
            "url": response.url,
            "source_url": response.url,
            "published_date": published_date,
            "content": content[:MAX_CONTENT_LENGTH]
        }

    except Exception as error:
        return {
            "title": urlparse(url).netloc or url,
            "source_type": "webpage",
            "url": url,
            "source_url": url,
            "published_date": None,
            "content": "",
            "error": str(error)
        }


def discover_sources(topic, max_results=MAX_SEARCH_RESULTS):
    sources = []
    limited_sources = []
    errors = []

    try:
        search_results = DDGS().text(
            topic,
            max_results=max_results
        )

        results = list(search_results)

    except Exception as error:
        return [], [], [
            f"Web search failed: {error}"
        ]

    unique_results = []
    seen_urls = set()

    for result in results:
        url = result.get("href") or result.get("url")

        if not url or url in seen_urls:
            continue

        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            continue

        seen_urls.add(url)

        unique_results.append({
            "url": url,
            "title": result.get("title", ""),
            "snippet": result.get("body", "")
        })

    if not unique_results:
        return [], [], [
            "No valid web search results were found."
        ]

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {
            executor.submit(
                extract_url,
                item["url"]
            ): item
            for item in unique_results
        }

        for future in as_completed(future_map):
            item = future_map[future]

            try:
                source = future.result()

                if source.get("content"):
                    source["search_snippet"] = item["snippet"]
                    source["discovery_method"] = (
                        "automatic_web_search"
                    )
                    sources.append(source)

                elif item["snippet"].strip():
                    limited_sources.append({
                        "title": (
                            item["title"]
                            or urlparse(item["url"]).netloc
                        ),
                        "url": item["url"],
                        "source_url": item["url"],
                        "search_snippet": item["snippet"],
                        "source_type": "search_snippet",
                        "discovery_method": "search_snippet_fallback",
                        "extraction_error": source.get(
                            "error",
                            "Full webpage extraction failed."
                        )
                    })

                    errors.append(
                        f"{item['title'] or item['url']}: "
                        "Full page unavailable; search snippet retained "
                        "as limited evidence."
                    )

                else:
                    errors.append(
                        f"{item['title'] or item['url']}: "
                        f"{source.get('error', 'Extraction failed')}"
                    )

            except Exception as error:
                errors.append(
                    f"{item['url']}: {error}"
                )

    return sources, limited_sources, errors


def extract_pdf(uploaded_file):
    try:
        pdf_bytes = uploaded_file.read()

        if not pdf_bytes.startswith(b"%PDF-"):
            raise ValueError(
                "The uploaded file is not a valid PDF."
            )

        return extract_pdf_bytes(
            pdf_bytes,
            title=uploaded_file.name
        )

    except Exception as error:
        raise ValueError(
            f"Could not read PDF {uploaded_file.name}: {error}"
        ) from error


def extract_pasted_text(text):
    if not text or not text.strip():
        return None

    content = "\n\n".join(
        line.strip()
        for line in text.splitlines()
        if line.strip()
    )

    if len(content) < 100:
        raise ValueError(
            "Pasted research text is too short."
        )

    return {
        "title": "Pasted Research Text",
        "source_type": "pasted_text",
        "url": None,
        "source_url": None,
        "published_date": None,
        "content": content[:MAX_CONTENT_LENGTH]
    }


def extract_sources(
    urls=None,
    uploaded_files=None,
    pasted_text=None
):
    sources = []
    errors = []

    if urls:
        valid_urls = [
            url.strip()
            for url in urls
            if url and url.strip()
        ]

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(
                    extract_url,
                    url
                ): url
                for url in valid_urls
            }

            for future in as_completed(futures):
                try:
                    source = future.result()

                    if source.get("content"):
                        sources.append(source)
                    else:
                        errors.append(
                            f"{futures[future]}: "
                            f"{source.get('error', 'Extraction failed')}"
                        )

                except Exception as error:
                    errors.append(str(error))

    if uploaded_files:
        for uploaded_file in uploaded_files:
            try:
                source = extract_pdf(uploaded_file)
                sources.append(source)

            except Exception as error:
                errors.append(str(error))

    if pasted_text:
        try:
            source = extract_pasted_text(pasted_text)

            if source:
                sources.append(source)

        except Exception as error:
            errors.append(str(error))

    return sources, errors