import os
import re
import asyncio
from typing import List, Optional, Tuple, Dict

import httpx
from bs4 import BeautifulSoup  # make sure beautifulsoup4 is in requirements.api.txt

# --- Lazy Playwright import (so API doesn't crash if not installed) ---
PLAYWRIGHT_ENABLED = os.getenv("PLAYWRIGHT_ENABLED", "false").lower() == "true"
SEO_BROWSER_URL = os.getenv("SEO_BROWSER_URL", "").strip()

try:
    if PLAYWRIGHT_ENABLED:
        from playwright.async_api import async_playwright  # type: ignore
    else:
        async_playwright = None  # type: ignore
except Exception:
    async_playwright = None  # type: ignore


# ------------------------
# Helpers
# ------------------------
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

async def _fetch_text(client: httpx.AsyncClient, url: str, timeout: int = 20) -> str:
    r = await client.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    return r.text

async def _playwright_html(url: str) -> str:
    """
    Render a page with Playwright (if available).
    """
    if async_playwright is None:
        raise RuntimeError("Playwright is not available in the API container. "
                           "Set PLAYWRIGHT_ENABLED=true and install it here, or route via SEO_BROWSER_URL.")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(user_agent=USER_AGENT)
            await page.goto(url, wait_until="networkidle", timeout=30000)
            html = await page.content()
            return html
        finally:
            await browser.close()

async def _remote_browser_html(url: str) -> str:
    """
    Call a separate SEO browser microservice to render HTML (if configured).
    Expected endpoint: POST {SEO_BROWSER_URL}/render { json: { url } } -> { html }
    """
    if not SEO_BROWSER_URL:
        raise RuntimeError("SEO browser service not configured. Set SEO_BROWSER_URL or enable Playwright in API.")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{SEO_BROWSER_URL.rstrip('/')}/render", json={"url": url})
        resp.raise_for_status()
        data = resp.json()
        return data.get("html", "")

async def get_html(url: str, prefer_render: bool = False) -> str:
    """
    Unified HTML getter:
      - If prefer_render: use Playwright or remote browser
      - Else: try simple GET first; fallback to rendered if needed
    """
    async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        if not prefer_render:
            try:
                return await _fetch_text(client, url)
            except Exception:
                # fallback to render
                pass

    # Rendered path
    if PLAYWRIGHT_ENABLED and async_playwright is not None:
        return await _playwright_html(url)
    if SEO_BROWSER_URL:
        return await _remote_browser_html(url)
    raise RuntimeError("No rendering path available. Enable Playwright or set SEO_BROWSER_URL.")


# ------------------------
# Public API used by main.py
# ------------------------
async def find_sitemap(url: str, client: httpx.AsyncClient) -> Optional[str]:
    """
    Try common sitemap locations and robots.txt.
    Signature expected by main.py: find_sitemap(url, client) -> Optional[str]
    """
    base = url.rstrip("/")

    # 1) robots.txt → look for Sitemap: lines
    try:
        robots = await _fetch_text(client, f"{base}/robots.txt")
        for line in robots.splitlines():
            if line.lower().startswith("sitemap:"):
                sm = line.split(":", 1)[1].strip()
                if sm:
                    return sm
    except Exception:
        pass

    # 2) common locations
    candidates = [
        f"{base}/sitemap.xml",
        f"{base}/sitemap_index.xml",
        f"{base}/sitemap_index.xml.gz",
        f"{base}/sitemap.gz",
    ]
    for sm in candidates:
        try:
            r = await client.get(sm, timeout=12)
            if r.status_code == 200 and ("<urlset" in r.text or "<sitemapindex" in r.text):
                return sm
        except Exception:
            continue

    return None


def generate_prompts_for_url(
    url: str,
    competitors: List[str] | str,
    project_id: str,
    location: str
) -> Dict:
    """
    Synchronous function returning categorized prompts for SEO/content tasks.
    Signature expected by main.py.
    Keep this lightweight and deterministic (no heavy browser here).
    """
    if isinstance(competitors, str):
        competitors = [c.strip() for c in competitors.split(",") if c.strip()]

    # Very basic prompt scaffolding (you can expand later)
    prompts = {
        "crawl": [f"Crawl and extract titles, H1s, and meta descriptions for: {url}"],
        "keywords": [
            f"Generate primary and long-tail keywords for: {url}",
            *[f"Extract competitor keywords from: {c}" for c in competitors],
        ],
        "content": [
            f"Draft 5 blog post ideas aligned to {url}'s core topics.",
            f"Create 3 product page meta descriptions (<=155 chars) for {url}.",
        ],
        "tech": [
            "List top technical SEO issues: broken links, slow pages, missing canonicals, large CLS.",
            "Create JSON-LD schema recommendations for key templates.",
        ]
    }
    return prompts


async def run_full_seo_analysis(
    websocket,  # fastapi.WebSocket
    project_id: str,
    location: str,
    your_site: str,
    competitors: List[str],
    prompts: Dict
) -> Dict:
    """
    Async pipeline that streams status via WebSocket and returns final report.
    This example keeps it lightweight; plug in your real logic as needed.
    Signature expected by main.py.
    """
    report: Dict = {"site": your_site, "sections": []}

    async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": USER_AGENT}, timeout=20) as client:
        await websocket.send_json({"status": "info", "message": "Finding sitemap..."})
        sitemap_url = await find_sitemap(your_site, client)
        report["sitemap"] = sitemap_url or "not found"

        await websocket.send_json({"status": "info", "message": "Fetching homepage..."})
        try:
            html = await get_html(your_site, prefer_render=False)
            soup = BeautifulSoup(html, "lxml")
            title = (soup.title.string.strip() if soup.title else "") or ""
            h1 = (soup.find("h1").get_text(strip=True) if soup.find("h1") else "")
            report["overview"] = {"title": title, "h1": h1, "url": your_site}
        except Exception as e:
            report["overview_error"] = str(e)

    # Add prompts summary (you can expand to actually fulfill each)
    report["requested_prompts"] = prompts

    await websocket.send_json({"status": "info", "message": "SEO analysis finished."})
    return report
