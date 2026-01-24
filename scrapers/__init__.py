"""Scrapers for the Newsletter Agent."""

from .modo_articles import ModoArticleScraper
from .youtube_podcast import YouTubePodcastScraper
from .news_sources import NewsSourcesScraper

__all__ = [
    'ModoArticleScraper',
    'YouTubePodcastScraper',
    'NewsSourcesScraper'
]
