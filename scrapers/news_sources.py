"""
News Sources Scraper

Fetches energy storage news from multiple sources for the "This Week's News" section.
"""

import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
import json
from pathlib import Path


class NewsSourcesScraper:
    """Scraper for energy industry news sources."""

    def __init__(self, config_path: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

        # Load sources from config
        if config_path:
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.sources = config.get('news_sources', [])
        else:
            self.sources = self._get_default_sources()

    def _get_default_sources(self) -> List[Dict]:
        """Return default news sources organized by region."""
        return {
            "europe": [
                {
                    "name": "Energy Storage News",
                    "rss": "https://www.energy-storage.news/feed/",
                    "category": "industry",
                    "region": "europe"
                },
                {
                    "name": "PV Magazine",
                    "rss": "https://www.pv-magazine.com/feed/",
                    "category": "industry",
                    "region": "europe"
                },
                {
                    "name": "Current±",
                    "rss": "https://www.current-news.co.uk/feed/",
                    "category": "industry",
                    "region": "europe"
                },
                {
                    "name": "Recharge News",
                    "rss": "https://www.rechargenews.com/rss",
                    "category": "industry",
                    "region": "europe"
                }
            ],
            "global": [
                {
                    "name": "Canary Media",
                    "rss": "https://www.canarymedia.com/feed",
                    "category": "industry",
                    "region": "global"
                },
                {
                    "name": "Electrek",
                    "rss": "https://electrek.co/feed/",
                    "category": "industry",
                    "region": "global"
                },
                {
                    "name": "CleanTechnica",
                    "rss": "https://cleantechnica.com/feed/",
                    "category": "industry",
                    "region": "global"
                }
            ],
            "us": [
                {
                    "name": "Utility Dive",
                    "rss": "https://www.utilitydive.com/feeds/news/",
                    "category": "industry",
                    "region": "us"
                }
            ],
            "australia": [
                {
                    "name": "RenewEconomy",
                    "rss": "https://reneweconomy.com.au/feed/",
                    "category": "industry",
                    "region": "australia"
                }
            ]
        }

    def get_news(self, days: int = 7, limit: int = 30, region: str = "europe") -> List[Dict]:
        """
        Fetch news from configured sources filtered by region.

        Args:
            days: Number of days to look back
            limit: Maximum total articles to return
            region: Region to filter sources ("europe", "global", "us", "australia", or "all")

        Returns:
            List of news articles sorted by date
        """
        all_news = []
        cutoff_date = datetime.now() - timedelta(days=days)

        # Get sources for the specified region
        if isinstance(self.sources, dict):
            # New region-based structure
            if region == "all":
                sources_to_use = []
                for region_sources in self.sources.values():
                    sources_to_use.extend(region_sources)
            else:
                sources_to_use = self.sources.get(region, [])
                # Always include europe sources for the European newsletter
                if region != "europe" and region != "all":
                    sources_to_use = self.sources.get("europe", []) + sources_to_use
        else:
            # Legacy flat list structure
            sources_to_use = self.sources

        for source in sources_to_use:
            if source.get('rss'):
                articles = self._fetch_rss(source, cutoff_date)
                all_news.extend(articles)

        # Sort by date (newest first)
        all_news.sort(key=lambda x: x.get('date', ''), reverse=True)

        # Filter for energy storage relevance and apply regional filtering
        filtered_news = self._filter_relevant(all_news, target_region=region)

        return filtered_news[:limit]

    def _fetch_rss(self, source: Dict, cutoff_date: datetime) -> List[Dict]:
        """Fetch articles from an RSS feed."""
        articles = []

        try:
            feed = feedparser.parse(source['rss'])

            for entry in feed.entries[:20]:  # Limit per source
                # Parse date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])

                # Skip old articles
                if pub_date and pub_date < cutoff_date:
                    continue

                article = {
                    "title": entry.get('title', ''),
                    "url": entry.get('link', ''),
                    "description": self._clean_html(entry.get('summary', '')),
                    "date": pub_date.isoformat() if pub_date else '',
                    "source": source['name'],
                    "category": source.get('category', 'general'),
                    "region": source.get('region', 'global')
                }

                articles.append(article)

        except Exception as e:
            print(f"Error fetching RSS from {source['name']}: {e}")

        return articles

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags and clean text."""
        soup = BeautifulSoup(html, 'lxml')
        text = soup.get_text(separator=' ', strip=True)
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        return text[:300]

    def _filter_relevant(self, articles: List[Dict], target_region: str = None) -> List[Dict]:
        """Filter articles for battery/energy storage relevance with scoring and regional filtering."""
        # High-priority keywords (battery/storage focused)
        priority_keywords = [
            'battery', 'bess', 'energy storage', 'battery storage',
            'lithium', 'li-ion', 'grid-scale storage', 'utility-scale storage',
            'battery project', 'storage project', 'battery asset',
            'ancillary services', 'frequency response', 'balancing market',
            'wholesale market', 'merchant battery', 'storage developer',
            'battery operator', 'flexitricity', 'grid services'
        ]

        # Secondary keywords (related energy topics)
        secondary_keywords = [
            'solar', 'pv', 'photovoltaic', 'wind', 'renewable',
            'grid', 'flexibility', 'capacity market',
            'interconnector', 'transmission', 'distribution',
            'megawatt', 'mw', 'gwh', 'mwh', 'energy transition',
            'net zero', 'decarbonisation'
        ]

        # Negative keywords (less relevant)
        negative_keywords = [
            'electric vehicle', 'ev battery', 'ev charging', 'tesla car',
            'phone battery', 'laptop battery', 'consumer electronics',
            'hydrogen', 'fuel cell', 'nuclear'
        ]

        # Regional keywords for content-based filtering
        europe_keywords = [
            'uk', 'britain', 'british', 'england', 'scotland', 'wales',
            'germany', 'german', 'deutschland',
            'spain', 'spanish', 'iberia', 'iberian',
            'italy', 'italian',
            'france', 'french',
            'netherlands', 'dutch',
            'belgium', 'belgian',
            'poland', 'polish',
            'nordic', 'sweden', 'norway', 'denmark', 'finland',
            'ireland', 'irish',
            'portugal', 'portuguese',
            'austria', 'austrian',
            'greece', 'greek',
            'europe', 'european', 'eu '
        ]

        us_keywords = [
            'us ', 'usa', 'united states', 'american',
            'california', 'texas', 'florida', 'new york', 'arizona',
            'ercot', 'caiso', 'miso', 'pjm', 'nyiso', 'spp', 'iso-ne',
            'ferc', 'doe ', 'department of energy'
        ]

        australia_keywords = [
            'australia', 'australian',
            'nem', 'wem', 'aemo',
            'queensland', 'new south wales', 'victoria', 'south australia'
        ]

        scored_articles = []
        for article in articles:
            text = (article['title'] + ' ' + article['description']).lower()

            # Check for negative keywords first
            if any(neg in text for neg in negative_keywords):
                continue

            # Calculate relevance score
            score = 0
            for kw in priority_keywords:
                if kw in text:
                    score += 3

            for kw in secondary_keywords:
                if kw in text:
                    score += 1

            # Apply regional filtering if a target region is specified
            if target_region and target_region != 'all' and target_region != 'global':
                # Detect article's actual region from content
                is_europe = any(kw in text for kw in europe_keywords)
                is_us = any(kw in text for kw in us_keywords)
                is_australia = any(kw in text for kw in australia_keywords)

                # Update article's detected region
                if is_us and not is_europe:
                    article['_detected_region'] = 'us'
                elif is_australia and not is_europe:
                    article['_detected_region'] = 'australia'
                elif is_europe:
                    article['_detected_region'] = 'europe'
                else:
                    article['_detected_region'] = 'global'

                # Filter based on target region
                if target_region == 'europe':
                    # For Europe, exclude articles that are clearly US or Australia
                    if is_us and not is_europe:
                        continue
                    if is_australia and not is_europe:
                        continue
                elif target_region == 'us':
                    # For US, only include articles with US keywords
                    if not is_us:
                        continue
                elif target_region == 'australia':
                    # For Australia, only include articles with Australia keywords
                    if not is_australia:
                        continue

            # Only include articles with a minimum score
            if score >= 2:
                article['_relevance_score'] = score
                scored_articles.append(article)

        # Sort by relevance score (highest first), then by date
        scored_articles.sort(key=lambda x: (-x.get('_relevance_score', 0), x.get('date', '')), reverse=False)
        scored_articles.sort(key=lambda x: x.get('_relevance_score', 0), reverse=True)

        return scored_articles

    def fetch_custom_url(self, url: str) -> Optional[Dict]:
        """
        Fetch and extract content from a custom news URL.

        Args:
            url: The URL to fetch

        Returns:
            Dict with title, description, url, source, or None if fetch failed
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')

            # Extract title
            title = ""
            if soup.title:
                title = soup.title.get_text(strip=True)
            # Try og:title
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title['content']

            # Extract description
            description = ""
            og_desc = soup.find('meta', property='og:description')
            if og_desc and og_desc.get('content'):
                description = og_desc['content']
            else:
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    description = meta_desc['content']

            # Extract source from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            source = parsed.netloc.replace('www.', '')

            # Try to detect region from URL/content
            region = "global"
            region_keywords = {
                'europe': ['energy-storage.news', 'pv-magazine.com', 'current-news.co.uk', 'rechargenews.com'],
                'us': ['utilitydive.com', 'greentechmedia.com'],
                'australia': ['reneweconomy.com.au']
            }
            for reg, domains in region_keywords.items():
                if any(d in url.lower() for d in domains):
                    region = reg
                    break

            return {
                "title": title,
                "description": description[:300] if description else "",
                "url": url,
                "source": source,
                "date": datetime.now().isoformat(),
                "category": "custom",
                "region": region
            }

        except Exception as e:
            print(f"Error fetching custom URL: {e}")
            return None

    def format_for_newsletter(self, articles: List[Dict], max_items: int = 4) -> List[Dict]:
        """
        Format selected articles for the newsletter "This Week's News" section.

        Each item should have:
        - headline: Bold lead text
        - body: Rest of the sentence

        Example format:
        "Gresham House has completed its merger with SUSI Partners, creating a £2.7
         billion energy transition investment platform."
        """
        formatted = []

        for article in articles[:max_items]:
            title = article['title']
            description = article['description']

            # Try to create a headline + body format
            # Use the title as the headline, description as body
            formatted.append({
                "headline": title,
                "body": f", {description}" if description else ".",
                "url": article['url'],
                "source": article['source']
            })

        return formatted


def main():
    """Test the scraper."""
    scraper = NewsSourcesScraper()

    print("Fetching news from sources...")
    news = scraper.get_news(days=7, limit=20)

    print(f"\nFound {len(news)} relevant articles:\n")
    for i, article in enumerate(news[:10], 1):
        print(f"{i}. [{article['source']}] {article['title']}")
        print(f"   {article['date']}")
        print()


if __name__ == "__main__":
    main()
