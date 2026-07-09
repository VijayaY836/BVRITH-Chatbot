"""
BVRIT Hyderabad website scraper.

Crawls a curated list of pages, extracts clean text, and saves to:
  - scraped_pages/          raw per-page text files
  - scraped_knowledge.md    merged markdown knowledge base ready for RAG
  - scraped_chunks.json     chunked version with section metadata

Usage:
    python scraper.py
    python scraper.py --pages 20          # limit crawl depth
    python scraper.py --delay 1.5         # seconds between requests
"""

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "scraped_pages"
OUT_DIR.mkdir(exist_ok=True)

BASE_URL = "https://bvrithyderabad.edu.in"
DEFAULT_DELAY = 1.0  # seconds between requests — be polite

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; BVRITHKnowledgeBot/1.0; "
        "educational-chatbot research project)"
    )
}

# ── Curated seed pages (high-value, confirmed to exist) ──────────────────────
SEED_PAGES = [
    # Core
    "/",
    "/about",
    "/management",
    "/contact-us",
    # Academics
    "/cse",
    "/ece",
    "/eee",
    "/it",
    "/csm",
    "/mtech-data-sciences",
    "/mtech-vlsi",
    "/mtech-cse",
    "/bsc",
    # Admissions
    "/admissions",
    "/fee-structure",
    "/scholarships",
    "/hostel",
    # Placements
    "/placements",
    "/placement-statistics",
    "/recruiters",
    # Campus life
    "/campus-facilities",
    "/library",
    "/sports",
    "/student-clubs",
    "/nss",
    # Research
    "/research",
    "/research-development",
    "/centres-of-excellence",
    # Accreditations
    "/naac-aqar",
    "/nba",
    "/approvals",
    # Leadership / governance
    "/principal-message",
    "/chairman-message",
    "/governing-body",
    "/iqac",
    # Misc
    "/anti-ragging",
    "/grievance",
    "/alumni",
    "/news-events",
    "/achievements",
    "/differentiators",
]

# Patterns to skip — PDFs, images, admin, etc.
SKIP_PATTERNS = re.compile(
    r"\.(pdf|jpg|jpeg|png|gif|svg|doc|docx|xls|xlsx|zip|rar|mp4|mp3)$"
    r"|/wp-admin|/wp-login|/feed|/tag/|/page/\d+|\?",
    re.IGNORECASE,
)

# Tags that never contain useful content
NOISE_TAGS = [
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "form", "button", "iframe", "meta", "link",
    "figure",  # keep img alt text separately if needed
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch(url: str, session: requests.Session) -> BeautifulSoup | None:
    """GET a page and return a BeautifulSoup object, or None on failure."""
    try:
        resp = session.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return None
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"    ⚠  Fetch error {url}: {e}")
        return None


def extract_text(soup: BeautifulSoup) -> str:
    """Remove noise tags and return clean readable text."""
    for tag in soup(NOISE_TAGS):
        tag.decompose()

    # Prefer main content areas
    for selector in ["main", "article", "#content", ".entry-content",
                     ".page-content", "#primary", ".site-content"]:
        container = soup.select_one(selector)
        if container:
            soup = container
            break

    lines = []
    for elem in soup.descendants:
        if elem.name in ("h1", "h2", "h3"):
            text = elem.get_text(strip=True)
            if text:
                prefix = "#" * int(elem.name[1])
                lines.append(f"\n{prefix} {text}\n")
        elif elem.name in ("p", "li", "td", "th", "dd", "dt"):
            text = elem.get_text(" ", strip=True)
            if text and len(text) > 20:
                lines.append(text)

    raw = "\n".join(lines)
    # Collapse excessive blank lines
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()


def extract_links(soup: BeautifulSoup, base: str) -> list[str]:
    """Extract internal links from a page."""
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(base, href)
        parsed = urlparse(full)
        # Internal only, no fragments, no skipped patterns
        if (
            parsed.netloc in ("bvrithyderabad.edu.in", "www.bvrithyderabad.edu.in")
            and not parsed.fragment
            and not SKIP_PATTERNS.search(parsed.path)
            and parsed.path != "/"
        ):
            clean = f"https://bvrithyderabad.edu.in{parsed.path.rstrip('/')}"
            links.append(clean)
    return list(dict.fromkeys(links))  # deduplicate, preserve order


def slug(url: str) -> str:
    """Turn a URL into a safe filename."""
    path = urlparse(url).path.strip("/").replace("/", "_") or "home"
    return re.sub(r"[^\w\-]", "_", path)


def page_title(soup: BeautifulSoup, url: str) -> str:
    """Best-effort page title."""
    if soup.title:
        t = soup.title.string or ""
        t = t.split("–")[0].split("|")[0].strip()
        if t:
            return t
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return urlparse(url).path.strip("/").replace("-", " ").replace("/", " › ").title()


# ── Main crawl ────────────────────────────────────────────────────────────────

def crawl(max_pages: int = 60, delay: float = DEFAULT_DELAY) -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)

    # Start with seed pages, then discover more from links
    queue = [urljoin(BASE_URL, p) for p in SEED_PAGES]
    visited: set[str] = set()
    pages: list[dict] = []

    print(f"🌐 Starting crawl of {BASE_URL}")
    print(f"   Seed pages : {len(queue)}")
    print(f"   Max pages  : {max_pages}")
    print(f"   Delay      : {delay}s\n")

    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        print(f"[{len(pages)+1}/{max_pages}] {url}")
        soup = fetch(url, session)

        if soup is None:
            print("    ✗ skipped (fetch failed or 404)")
            time.sleep(delay)
            continue

        text = extract_text(soup)
        if len(text) < 80:
            print(f"    ✗ skipped (too little content: {len(text)} chars)")
            time.sleep(delay)
            continue

        title = page_title(soup, url)
        page = {"url": url, "title": title, "text": text}
        pages.append(page)

        # Save raw text
        fname = OUT_DIR / f"{slug(url)}.txt"
        fname.write_text(f"# {title}\nSource: {url}\n\n{text}", encoding="utf-8")
        print(f"    ✓ {len(text):,} chars — {title}")

        # Discover new links and append to queue
        new_links = extract_links(soup, url)
        for lnk in new_links:
            if lnk not in visited and lnk not in queue:
                queue.append(lnk)

        time.sleep(delay)

    print(f"\n✅ Crawled {len(pages)} pages.")
    return pages


# ── Output builders ───────────────────────────────────────────────────────────

def build_markdown(pages: list[dict]) -> str:
    """Merge all pages into a single markdown knowledge base."""
    lines = [
        "# BVRIT HYDERABAD College of Engineering for Women",
        "## Scraped Knowledge Base",
        f"*Source: {BASE_URL} — {len(pages)} pages*\n",
        "---\n",
    ]
    for p in pages:
        lines.append(f"## {p['title']}")
        lines.append(f"*Source: {p['url']}*\n")
        lines.append(p["text"])
        lines.append("\n---\n")
    return "\n".join(lines)


def build_chunks(pages: list[dict], chunk_size: int = 500, overlap: int = 80) -> list[dict]:
    """Split pages into overlapping chunks with metadata."""
    chunks = []
    chunk_id = 0
    for p in pages:
        words = p["text"].split()
        step = chunk_size - overlap
        for i in range(0, max(1, len(words) - overlap), step):
            chunk_words = words[i: i + chunk_size]
            if len(chunk_words) < 30:
                continue
            chunks.append({
                "id": chunk_id,
                "url": p["url"],
                "section_heading": p["title"],
                "text": " ".join(chunk_words),
            })
            chunk_id += 1
    return chunks


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BVRIT website scraper")
    parser.add_argument("--pages", type=int, default=60, help="Max pages to crawl")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay between requests (s)")
    args = parser.parse_args()

    pages = crawl(max_pages=args.pages, delay=args.delay)

    if not pages:
        print("❌ No pages scraped. Check connectivity.")
        return

    # Write merged markdown
    md_path = ROOT / "scraped_knowledge.md"
    md_content = build_markdown(pages)
    md_path.write_text(md_content, encoding="utf-8")
    print(f"📄 Merged markdown  → {md_path}  ({len(md_content):,} chars)")

    # Write chunks JSON
    chunks = build_chunks(pages)
    chunks_path = ROOT / "scraped_chunks.json"
    chunks_path.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"🧩 Chunks JSON      → {chunks_path}  ({len(chunks)} chunks)")

    print("\nDone. Next step: feed scraped_knowledge.md into your knowledge base.")


if __name__ == "__main__":
    main()
