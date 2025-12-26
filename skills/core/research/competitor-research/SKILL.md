---
name: competitor-research
description: Competitive analysis and market research
version: 1.0.0
category: research
technologies: [python, web-scraping, apis]
triggers:
  - competitor research
  - market research
  - competitive analysis
  - competitor analysis
---

# Competitor Research

Competitive analysis and market intelligence gathering.

## Research Framework

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class Competitor:
    name: str
    website: str
    description: str = ""
    founded: Optional[int] = None
    funding: Optional[str] = None
    employee_count: Optional[str] = None
    features: List[str] = field(default_factory=list)
    pricing: Dict = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    social_links: Dict = field(default_factory=dict)

@dataclass
class CompetitiveAnalysis:
    market: str
    date: datetime
    competitors: List[Competitor]
    market_trends: List[str]
    opportunities: List[str]
    threats: List[str]
```

## Data Collection

```python
import httpx
from bs4 import BeautifulSoup
from typing import Dict

class CompetitorScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible; ResearchBot)"},
            follow_redirects=True
        )

    async def analyze_website(self, url: str) -> Dict:
        """Extract basic information from competitor website."""
        html = await self._fetch(url)
        soup = BeautifulSoup(html, 'html.parser')

        return {
            "title": self._get_title(soup),
            "description": self._get_meta_description(soup),
            "features": self._extract_features(soup),
            "pricing_page": self._find_pricing_link(soup, url),
            "social_links": self._find_social_links(soup),
            "tech_stack": await self._detect_tech_stack(url)
        }

    def _get_title(self, soup) -> str:
        title = soup.find('title')
        return title.text.strip() if title else ""

    def _get_meta_description(self, soup) -> str:
        meta = soup.find('meta', {'name': 'description'})
        return meta['content'] if meta else ""

    def _extract_features(self, soup) -> List[str]:
        """Look for feature lists on the page."""
        features = []

        # Common feature section patterns
        feature_sections = soup.find_all(['section', 'div'],
            class_=lambda x: x and any(word in str(x).lower()
                for word in ['feature', 'benefit', 'capability']))

        for section in feature_sections:
            for item in section.find_all(['li', 'h3', 'h4']):
                text = item.get_text(strip=True)
                if 10 < len(text) < 200:
                    features.append(text)

        return features[:20]  # Limit results

    def _find_social_links(self, soup) -> Dict[str, str]:
        social_platforms = {
            'twitter': ['twitter.com', 'x.com'],
            'linkedin': ['linkedin.com'],
            'github': ['github.com'],
            'facebook': ['facebook.com'],
            'youtube': ['youtube.com']
        }

        links = {}
        for a in soup.find_all('a', href=True):
            href = a['href']
            for platform, domains in social_platforms.items():
                if any(domain in href for domain in domains):
                    links[platform] = href
                    break

        return links

    async def _detect_tech_stack(self, url: str) -> List[str]:
        """Detect technologies used by the website."""
        # Use builtwith or wappalyzer APIs for production
        # This is a simplified version
        html = await self._fetch(url)

        tech = []
        if 'react' in html.lower():
            tech.append('React')
        if 'vue' in html.lower():
            tech.append('Vue.js')
        if 'angular' in html.lower():
            tech.append('Angular')
        if 'next' in html.lower():
            tech.append('Next.js')

        return tech
```

## Pricing Analysis

```python
@dataclass
class PricingTier:
    name: str
    price: Optional[float]
    billing: str  # monthly, yearly, one-time
    features: List[str]
    limits: Dict[str, str]

class PricingAnalyzer:
    async def analyze_pricing_page(self, url: str) -> List[PricingTier]:
        """Extract pricing information from pricing page."""
        html = await self._fetch(url)
        soup = BeautifulSoup(html, 'html.parser')

        tiers = []

        # Look for pricing cards/tables
        pricing_elements = soup.find_all(['div', 'article'],
            class_=lambda x: x and 'pricing' in str(x).lower())

        for element in pricing_elements:
            tier = self._extract_tier(element)
            if tier:
                tiers.append(tier)

        return tiers

    def _extract_tier(self, element) -> Optional[PricingTier]:
        """Extract pricing tier from HTML element."""
        name = self._find_tier_name(element)
        price = self._find_price(element)
        features = self._find_features(element)

        if name:
            return PricingTier(
                name=name,
                price=price,
                billing="monthly",  # Default, would need more parsing
                features=features,
                limits={}
            )
        return None

    def _find_price(self, element) -> Optional[float]:
        """Extract price from element."""
        import re
        text = element.get_text()

        # Match common price patterns
        patterns = [
            r'\$(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?)\s*(?:USD|EUR)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))

        return None
```

## Market Analysis

```python
class MarketAnalyzer:
    def __init__(self, search_client):
        self.search = search_client

    async def analyze_market(self, market: str) -> Dict:
        """Analyze market trends and landscape."""
        queries = [
            f"{market} market size",
            f"{market} market trends 2024",
            f"{market} industry analysis",
            f"top {market} companies"
        ]

        results = {}
        for query in queries:
            results[query] = await self.search.search(query, num=5)

        return {
            "market": market,
            "search_results": results,
            "analysis_date": datetime.now().isoformat()
        }

    def generate_swot(self, competitor: Competitor, our_product: Dict) -> Dict:
        """Generate SWOT analysis vs competitor."""
        return {
            "strengths": self._identify_strengths(our_product, competitor),
            "weaknesses": self._identify_weaknesses(our_product, competitor),
            "opportunities": self._identify_opportunities(competitor),
            "threats": self._identify_threats(competitor)
        }
```

## Report Generation

```python
def generate_competitive_report(analysis: CompetitiveAnalysis) -> str:
    report = f"""
# Competitive Analysis Report
**Market:** {analysis.market}
**Date:** {analysis.date.strftime('%Y-%m-%d')}

## Competitors Overview

"""

    for comp in analysis.competitors:
        report += f"""
### {comp.name}
- **Website:** {comp.website}
- **Description:** {comp.description}
- **Employees:** {comp.employee_count or 'Unknown'}
- **Funding:** {comp.funding or 'Unknown'}

**Key Features:**
"""
        for feature in comp.features[:5]:
            report += f"- {feature}\n"

        report += f"""
**Strengths:**
"""
        for strength in comp.strengths:
            report += f"- {strength}\n"

        report += f"""
**Weaknesses:**
"""
        for weakness in comp.weaknesses:
            report += f"- {weakness}\n"

    report += f"""
## Market Trends
"""
    for trend in analysis.market_trends:
        report += f"- {trend}\n"

    report += f"""
## Opportunities
"""
    for opp in analysis.opportunities:
        report += f"- {opp}\n"

    return report
```

## Best Practices

1. Verify information from multiple sources
2. Update research regularly
3. Focus on actionable insights
4. Respect competitors' terms of service
5. Use official APIs when available
6. Document methodology
7. Present findings objectively
8. Include recommendations
