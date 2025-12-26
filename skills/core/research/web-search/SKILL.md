---
name: web-search
description: Web search and information gathering
version: 1.0.0
category: research
technologies: [python, selenium, beautifulsoup, apis]
triggers:
  - web search
  - research
  - find information
  - search online
---

# Web Search & Research

Automated web search and information gathering.

## Search APIs

```python
# Google Custom Search API
import httpx
from typing import List, Dict

class GoogleSearch:
    def __init__(self, api_key: str, cx: str):
        self.api_key = api_key
        self.cx = cx  # Custom search engine ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    async def search(self, query: str, num: int = 10) -> List[Dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={
                    "key": self.api_key,
                    "cx": self.cx,
                    "q": query,
                    "num": num
                }
            )
            data = response.json()
            return data.get("items", [])

# DuckDuckGo (no API key needed)
from duckduckgo_search import DDGS

def search_duckduckgo(query: str, max_results: int = 10):
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
        return results
```

## Web Scraping

```python
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class WebScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"
            },
            follow_redirects=True,
            timeout=30.0
        )

    async def fetch_page(self, url: str) -> str:
        response = await self.client.get(url)
        response.raise_for_status()
        return response.text

    async def extract_content(self, url: str) -> Dict:
        html = await self.fetch_page(url)
        soup = BeautifulSoup(html, 'html.parser')

        # Remove scripts and styles
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        return {
            "title": soup.title.string if soup.title else None,
            "text": soup.get_text(separator=' ', strip=True),
            "links": [
                urljoin(url, a['href'])
                for a in soup.find_all('a', href=True)
            ],
            "meta_description": self._get_meta(soup, 'description'),
        }

    def _get_meta(self, soup, name: str) -> str:
        meta = soup.find('meta', attrs={'name': name})
        return meta['content'] if meta else None
```

## Content Extraction

```python
from readability import Document
import trafilatura

class ContentExtractor:
    @staticmethod
    def extract_article(html: str) -> Dict:
        """Extract main article content from HTML."""
        # Using readability
        doc = Document(html)

        return {
            "title": doc.title(),
            "content": doc.summary(),
            "short_title": doc.short_title()
        }

    @staticmethod
    def extract_text(url: str) -> str:
        """Extract clean text from URL using trafilatura."""
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded)
        return None
```

## Research Workflow

```python
from dataclasses import dataclass
from typing import List
import asyncio

@dataclass
class ResearchResult:
    query: str
    sources: List[Dict]
    summary: str
    key_findings: List[str]

class Researcher:
    def __init__(self, search_client, scraper, llm_client):
        self.search = search_client
        self.scraper = scraper
        self.llm = llm_client

    async def research(self, topic: str, depth: int = 5) -> ResearchResult:
        # Step 1: Search for relevant pages
        search_results = await self.search.search(topic, num=depth)

        # Step 2: Fetch and extract content
        contents = []
        for result in search_results:
            try:
                content = await self.scraper.extract_content(result['link'])
                contents.append({
                    "url": result['link'],
                    "title": result['title'],
                    "content": content['text'][:5000]  # Limit content
                })
            except Exception as e:
                print(f"Failed to fetch {result['link']}: {e}")

        # Step 3: Synthesize findings
        summary = await self._synthesize(topic, contents)

        return ResearchResult(
            query=topic,
            sources=contents,
            summary=summary['summary'],
            key_findings=summary['key_findings']
        )

    async def _synthesize(self, topic: str, contents: List[Dict]) -> Dict:
        prompt = f"""
        Research topic: {topic}

        Sources:
        {self._format_sources(contents)}

        Provide:
        1. A comprehensive summary
        2. Key findings (bullet points)
        3. Areas needing more research
        """

        response = await self.llm.complete(prompt)
        return self._parse_synthesis(response)
```

## Rate Limiting

```python
import asyncio
from collections import deque
from datetime import datetime

class RateLimitedClient:
    def __init__(self, requests_per_minute: int = 30):
        self.rpm = requests_per_minute
        self.timestamps = deque()

    async def throttle(self):
        now = datetime.now().timestamp()

        # Remove timestamps older than 1 minute
        while self.timestamps and self.timestamps[0] < now - 60:
            self.timestamps.popleft()

        if len(self.timestamps) >= self.rpm:
            sleep_time = 60 - (now - self.timestamps[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        self.timestamps.append(now)
```

## Caching

```python
import hashlib
import json
from pathlib import Path

class SearchCache:
    def __init__(self, cache_dir: str = ".cache/search"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, query: str) -> str:
        return hashlib.md5(query.encode()).hexdigest()

    def get(self, query: str) -> Dict | None:
        cache_file = self.cache_dir / f"{self._get_cache_key(query)}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())
        return None

    def set(self, query: str, results: Dict):
        cache_file = self.cache_dir / f"{self._get_cache_key(query)}.json"
        cache_file.write_text(json.dumps(results))
```

## Best Practices

1. Respect robots.txt
2. Implement rate limiting
3. Cache results appropriately
4. Use appropriate user agents
5. Handle errors gracefully
6. Verify source credibility
7. Cross-reference multiple sources
8. Cite sources properly
