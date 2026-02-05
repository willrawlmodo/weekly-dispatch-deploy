"""
Modo Energy Terminal Article Scraper

Fetches research articles from the Modo Energy API.
Filters by region and date (adjustable lookback period).
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import re


class ModoArticleScraper:
    """Scraper for Modo Energy research articles via the JSON API."""

    # Article page base URL (for building article links)
    ARTICLE_BASE_URL = "https://modoenergy.com/research/en"

    # JSON API endpoint
    API_BASE_URL = "https://admin.modo.energy/v1/content-service/news/insights/"

    # Maps region keys to comma-separated API region codes
    API_REGIONS = {
        "gb_europe": "gb,de,fr,it,ib",
        "us": "ercot,caiso,miso,pjm,nyiso,isone,spp",
        "australia": "australia,nem,wem",
        "non_europe": "ercot,caiso,miso,pjm,nyiso,isone,spp,nem,wem",
        "all": None,
    }

    # Weighted keywords for region detection
    # Higher weight = stronger signal for that region
    # Format: (keyword, weight)

    EUROPE_KEYWORDS = [
        # Countries/regions - weight 3
        ('great britain', 3), ('united kingdom', 3), ('britain', 3), ('british', 3),
        ('england', 3), ('scotland', 3), ('wales', 3), ('northern ireland', 3),
        ('germany', 3), ('german', 3), ('deutschland', 3),
        ('spain', 3), ('spanish', 3), ('iberia', 3), ('iberian', 3),
        ('italy', 3), ('italian', 3),
        ('france', 3), ('french', 3),
        ('netherlands', 3), ('dutch', 3), ('belgium', 3), ('belgian', 3),
        ('poland', 3), ('polish', 3), ('nordic', 3), ('scandinavia', 3),
        ('europe', 2), ('european', 2),
        # General terms - weight 1-2
        ('uk', 2), ('gb ', 2),
        # Grid/market operators - weight 4 (very specific)
        ('national grid eso', 4), ('national grid', 3), ('ofgem', 4),
        ('epex spot', 4), ('nord pool', 4), ('energinet', 4),
        ('entsoe', 4), ('entso-e', 4), ('bundesnetzagentur', 4),
    ]

    US_KEYWORDS = [
        # ISOs/RTOs - weight 5 (very specific market indicators)
        ('ercot', 5), ('caiso', 5), ('miso', 5), ('pjm', 5),
        ('nyiso', 5), ('iso-ne', 5), ('iso ne', 5), ('spp', 4),
        ('southwest power pool', 5), ('midcontinent iso', 5),
        # Regulatory bodies - weight 4
        ('ferc', 4), ('nerc', 4), ('doe ', 3), ('department of energy', 3),
        # States - weight 3
        ('california', 3), ('texas', 3), ('florida', 3), ('new york', 3),
        ('arizona', 3), ('nevada', 3), ('colorado', 3), ('illinois', 3),
        ('ohio', 3), ('pennsylvania', 3), ('new jersey', 3), ('massachusetts', 3),
        ('michigan', 3), ('georgia', 3), ('north carolina', 3), ('virginia', 3),
        # Country terms - weight 2
        ('united states', 3), ('usa', 2), ('american', 2), ('u.s.', 2),
        # US-specific energy terms - weight 3
        ('lcr', 3), ('resource adequacy', 3), ('wholesale market', 2),
    ]

    AUSTRALIA_KEYWORDS = [
        # Grid/market operators - weight 5 (very specific)
        ('nem', 5), ('national electricity market', 5),
        ('wem', 5), ('wholesale electricity market', 5),
        ('aemo', 5), ('australian energy market operator', 5),
        ('aemc', 4), ('aer', 3),
        # States/territories - weight 3
        ('queensland', 3), ('new south wales', 3), ('nsw', 3),
        ('victoria', 3), ('south australia', 3), ('tasmania', 3),
        ('western australia', 3), ('northern territory', 3),
        # Country terms - weight 2-3
        ('australia', 3), ('australian', 3),
        # Australia-specific energy terms - weight 3
        ('snowy hydro', 4), ('origin energy', 3), ('agl', 3),
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

    def get_articles(
        self,
        region: str = "gb_europe",
        days: int = 7,
        limit: int = 20
    ) -> List[Dict]:
        """
        Fetch articles from the Modo Energy API.

        Args:
            region: "gb_europe", "us", "australia", "non_europe", or "all"
            days: Number of days to look back (filters by publishedAt date)
            limit: Maximum number of articles to return

        Returns:
            List of article dictionaries with title, description, url, date, slug, etc.
        """
        region_code = self.API_REGIONS.get(region, self.API_REGIONS["gb_europe"])

        params = {
            "source": "R,S,MV",
            "language": "en",
            "limit": min(limit, 50),
            "offset": 0,
        }
        if region_code:
            params["region"] = region_code

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        articles = []
        seen_slugs = set()

        try:
            # Paginate through results until we have enough or run out
            while len(articles) < limit:
                response = self.session.get(
                    self.API_BASE_URL, params=params, timeout=30
                )
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                if not results:
                    break

                for item in results:
                    if len(articles) >= limit:
                        break

                    slug = item.get("slug", "")
                    if not slug or slug in seen_slugs:
                        continue
                    seen_slugs.add(slug)

                    # Filter by date (API uses snake_case: published_at)
                    published_at = item.get("published_at", "") or ""
                    if published_at:
                        try:
                            pub_date = datetime.strptime(
                                published_at, "%Y-%m-%dT%H:%M:%S%z"
                            )
                            if pub_date < cutoff:
                                # Articles are sorted newest-first; once we hit
                                # one older than the cutoff, all remaining are older too
                                return articles
                        except ValueError:
                            pass  # Include articles with unparseable dates

                    title = item.get("title", slug.replace("-", " ").title())
                    description = item.get("short_description", "")
                    thumbnail = (
                        item.get("share_image_url")
                        or item.get("main_image_url")
                        or ""
                    )

                    article = {
                        "title": title,
                        "description": description,
                        "url": f"{self.ARTICLE_BASE_URL}/{slug}",
                        "slug": slug,
                        "date": published_at,
                        "thumbnail_url": thumbnail,
                        "og_image": thumbnail,
                        "detected_region": self._detect_article_region(
                            title, description, slug
                        ),
                        "source_type": item.get("source", ""),
                        "categories": [
                            c.get("name", "") for c in item.get("categories", [])
                        ],
                        "reading_time": item.get("reading_time_minutes"),
                    }
                    articles.append(article)

                # Check if there's a next page
                next_url = data.get("next")
                if not next_url or len(articles) >= limit:
                    break

                # Update offset for next page
                params["offset"] = params["offset"] + params["limit"]

        except requests.RequestException as e:
            print(f"Error fetching articles from API: {e}")

        return articles

    # ------------------------------------------------------------------
    # Region detection (unchanged)
    # ------------------------------------------------------------------

    def _calculate_region_score(self, text: str, keywords: list) -> tuple:
        """
        Calculate weighted score for a region based on keyword matches.

        Args:
            text: Combined text to search (lowercase)
            keywords: List of (keyword, weight) tuples

        Returns:
            Tuple of (total_score, list of matched keywords)
        """
        total_score = 0
        matches = []

        for keyword, weight in keywords:
            if keyword in text:
                total_score += weight
                matches.append((keyword, weight))

        return total_score, matches

    def _detect_article_region(self, title: str, description: str, slug: str) -> str:
        """
        Detect the region of an article based on weighted keyword scoring.

        Uses a weighted scoring system where market-specific terms (ISOs, RTOs)
        have higher weight than general geographic terms.

        Returns: 'europe', 'us', 'australia', or 'global'
        """
        text = (title + ' ' + description + ' ' + slug).lower()

        # Calculate weighted scores for each region
        europe_score, europe_matches = self._calculate_region_score(text, self.EUROPE_KEYWORDS)
        us_score, us_matches = self._calculate_region_score(text, self.US_KEYWORDS)
        australia_score, australia_matches = self._calculate_region_score(text, self.AUSTRALIA_KEYWORDS)

        # Determine region based on highest score
        # Require minimum score of 2 to avoid false positives
        min_score = 2

        # If both Europe and non-Europe have scores, use the higher one
        # But give slight preference to non-Europe for "world articles" feature
        non_europe_score = max(us_score, australia_score)

        if non_europe_score > europe_score and non_europe_score >= min_score:
            # Non-Europe wins
            if us_score >= australia_score:
                return 'us'
            else:
                return 'australia'
        elif europe_score >= min_score and europe_score > non_europe_score:
            return 'europe'
        elif non_europe_score >= min_score:
            # Equal scores but non-Europe has minimum - favor non-Europe
            if us_score >= australia_score:
                return 'us'
            else:
                return 'australia'
        elif europe_score >= min_score:
            return 'europe'
        else:
            return 'global'

    def get_region_scores(self, article: Dict) -> Dict:
        """
        Get detailed region scores for an article (useful for debugging).

        Args:
            article: Article dict with title, description, slug

        Returns:
            Dictionary with scores and matched keywords for each region
        """
        text = (
            article.get('title', '') + ' ' +
            article.get('description', '') + ' ' +
            article.get('slug', '')
        ).lower()

        europe_score, europe_matches = self._calculate_region_score(text, self.EUROPE_KEYWORDS)
        us_score, us_matches = self._calculate_region_score(text, self.US_KEYWORDS)
        australia_score, australia_matches = self._calculate_region_score(text, self.AUSTRALIA_KEYWORDS)

        return {
            'europe': {'score': europe_score, 'matches': europe_matches},
            'us': {'score': us_score, 'matches': us_matches},
            'australia': {'score': australia_score, 'matches': australia_matches},
            'detected_region': self._detect_article_region(
                article.get('title', ''),
                article.get('description', ''),
                article.get('slug', '')
            )
        }

    def is_non_europe_article(self, article: Dict) -> bool:
        """
        Check if an article is from outside Europe (US, Australia, etc).

        Uses weighted scoring to determine if article is primarily about
        non-European markets.

        Args:
            article: Article dict with title, description, slug

        Returns:
            True if article is non-European
        """
        region = self._detect_article_region(
            article.get('title', ''),
            article.get('description', ''),
            article.get('slug', '')
        )
        return region in ['us', 'australia']

    # ------------------------------------------------------------------
    # Article detail fetching (kept for chart image extraction)
    # ------------------------------------------------------------------

    def get_article_details(self, url: str) -> Dict:
        """
        Fetch detailed information about a specific article.
        Extracts og:image, og:description, and any charts/images.
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching article details: {e}")
            return {}

        soup = BeautifulSoup(response.text, 'lxml')

        # Extract Open Graph metadata
        og_image = soup.find('meta', property='og:image')
        og_description = soup.find('meta', property='og:description')
        og_title = soup.find('meta', property='og:title')

        # Find images that might be charts
        chart_images = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            # Look for images that are likely charts
            if any(word in src.lower() or word in alt.lower()
                   for word in ['chart', 'graph', 'plot', 'scenario', 'forecast']):
                chart_images.append({
                    "src": src,
                    "alt": alt
                })

        return {
            "og_image": og_image.get('content') if og_image else None,
            "og_description": og_description.get('content') if og_description else None,
            "og_title": og_title.get('content') if og_title else None,
            "chart_images": chart_images
        }

    # ------------------------------------------------------------------
    # Aggregate fetchers
    # ------------------------------------------------------------------

    def get_all_articles(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """
        Fetch ALL recent articles by combining both region feeds.

        The Modo API requires a region filter, so we fetch from both
        gb_europe and non_europe feeds and combine the results.

        Args:
            days: Number of days to look back
            limit: Maximum number of articles to return

        Returns:
            List of all article dictionaries with detected_region field
        """
        all_articles = []
        seen_slugs = set()

        # Fetch from GB/Europe feed
        europe_articles = self.get_articles(region="gb_europe", days=days, limit=limit)
        for article in europe_articles:
            if article['slug'] not in seen_slugs:
                seen_slugs.add(article['slug'])
                all_articles.append(article)

        # Fetch from US/Australia feed
        non_europe_articles = self.get_articles(region="non_europe", days=days, limit=limit)
        for article in non_europe_articles:
            if article['slug'] not in seen_slugs:
                seen_slugs.add(article['slug'])
                all_articles.append(article)

        return all_articles[:limit]

    def get_non_europe_articles(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """
        Fetch articles that are specifically about non-European markets (US, Australia).

        Fetches from both region feeds and uses weighted scoring to find
        articles about US/Australia markets.

        Args:
            days: Number of days to look back
            limit: Maximum number of articles to return

        Returns:
            List of article dictionaries for US/Australia markets
        """
        # Fetch all articles from both feeds
        all_articles = self.get_all_articles(days=days, limit=limit * 3)

        # Filter to only include articles detected as US or Australia
        non_europe_articles = []
        for article in all_articles:
            region = article.get('detected_region', 'global')
            if region in ['us', 'australia']:
                non_europe_articles.append(article)

        return non_europe_articles[:limit]


def _format_date(iso_date: str) -> str:
    """Format an ISO date string for display."""
    if not iso_date:
        return "Unknown date"
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S%z")
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return iso_date


def main():
    """Test the scraper with the JSON API."""
    scraper = ModoArticleScraper()

    print("=" * 60)
    print("ALL AVAILABLE ARTICLES (last 7 days)")
    print("=" * 60)
    all_articles = scraper.get_all_articles(days=7, limit=20)

    if not all_articles:
        print("\nNo articles found. Check network connection.")
        return

    print(f"\nFound {len(all_articles)} articles:\n")

    # Group by detected region
    europe_articles = []
    non_europe_articles = []
    global_articles = []

    for article in all_articles:
        region = article.get('detected_region', 'global')
        if region == 'europe':
            europe_articles.append(article)
        elif region in ['us', 'australia']:
            non_europe_articles.append(article)
        else:
            global_articles.append(article)

    # Show Europe articles
    print(f"EUROPE ({len(europe_articles)} articles):")
    for i, article in enumerate(europe_articles, 1):
        date_str = _format_date(article.get('date', ''))
        print(f"  {i}. {article['title']}")
        print(f"     {date_str} | {article['url']}")

    # Show Non-Europe articles
    print(f"\nUS/AUSTRALIA ({len(non_europe_articles)} articles):")
    if non_europe_articles:
        for i, article in enumerate(non_europe_articles, 1):
            scores = scraper.get_region_scores(article)
            date_str = _format_date(article.get('date', ''))
            print(f"  {i}. [{scores['detected_region'].upper()}] {article['title']}")
            print(f"     {date_str} | {article['url']}")
            if scores['us']['matches']:
                print(f"     US keywords: {[m[0] for m in scores['us']['matches']]}")
            if scores['australia']['matches']:
                print(f"     AU keywords: {[m[0] for m in scores['australia']['matches']]}")
    else:
        print("  (None found - Modo may not have published US/AU content recently)")

    # Show Global/unclassified articles
    if global_articles:
        print(f"\nGLOBAL/OTHER ({len(global_articles)} articles):")
        for i, article in enumerate(global_articles, 1):
            date_str = _format_date(article.get('date', ''))
            print(f"  {i}. {article['title']}")
            print(f"     {date_str}")


if __name__ == "__main__":
    main()
