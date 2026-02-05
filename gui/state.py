"""
Session State Manager

Manages the newsletter content state across GUI interactions.
Equivalent to the CLI's self.content dict + self.completed_steps.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


# Region configuration — mirrored from main.py NewsletterAgent.REGION_CONFIG
REGION_CONFIG = {
    "us": {
        "name": "US",
        "header_url": "https://25093280.fs1.hubspotusercontent-eu1.net/hubfs/25093280/Screenshot%202026-01-23%20at%2021.48.06.png",
        "header_alt": "MODOENERGY Weekly Dispatch US Edition",
        "article_region": "us",
        "news_region": "us",
        "from_name": "Brandt Vermillion",
        "from_email": "brandt@modoenergy.com",
        "image_folder": "US Weekly Dispatch",
        "covered_isos": ["ERCOT", "MISO", "CAISO", "PJM", "NYISO", "ISO-NE", "SPP"],
    },
    "europe": {
        "name": "Europe & GB",
        "header_url": "https://25093280.fs1.hubspotusercontent-eu1.net/hubfs/25093280/European%20Weekly%20Dispatch/Weekly%20Dispatch%20Header_EU.png",
        "header_alt": "MODOENERGY Weekly Dispatch Europe & GB Edition",
        "article_region": "gb_europe",
        "news_region": "europe",
        "from_name": "Shaniyaa Holness-Mckenzie",
        "from_email": "shaniyaa@modoenergy.com",
        "image_folder": "European Weekly Dispatch",
    },
    "australia": {
        "name": "Australia",
        "header_url": "https://25093280.fs1.hubspotusercontent-eu1.net/hubfs/25093280/Screenshot%202026-01-23%20at%2021.50.29.png",
        "header_alt": "MODOENERGY Weekly Dispatch Australia Edition",
        "article_region": "australia",
        "news_region": "australia",
        "from_name": "Wendel from Modo Energy",
        "from_email": "wendel@modoenergy.com",
        "image_folder": "Aus Weekly Dispatch",
    },
}


CHECKPOINT_FILE = Path(__file__).parent.parent / '.gui_checkpoint.json'


class SessionState:
    """
    Holds all newsletter content and tracks step completion.
    
    This is the GUI equivalent of the CLI's self.content dict.
    A single instance lives on the server for the duration of a session.
    """

    def __init__(self):
        self.region: str = "us"
        self.content: Dict[str, Any] = {}
        self.completed_steps: List[str] = []
        self.created_at: str = datetime.now().isoformat()

        # Scraped data cache (so we don't re-scrape on every request)
        self._article_cache: List[Dict] = []
        self._news_cache: List[Dict] = []
        self._podcast_cache: List[Dict] = []
        self._world_article_cache: List[Dict] = []

    # ── Region ──────────────────────────────────────────────

    def set_region(self, region: str) -> Dict:
        """Set the newsletter region and populate header defaults."""
        if region not in REGION_CONFIG:
            raise ValueError(f"Invalid region: {region}. Must be one of {list(REGION_CONFIG.keys())}")

        self.region = region
        config = REGION_CONFIG[region]

        self.content["region"] = region
        self.content["region_name"] = config["name"]
        self.content["header_url"] = config["header_url"]
        self.content["header_alt"] = config["header_alt"]

        self._mark_complete("region")
        return {"region": region, "config": config}

    # ── Step tracking ───────────────────────────────────────

    def _mark_complete(self, step: str):
        if step not in self.completed_steps:
            self.completed_steps.append(step)

    def is_complete(self, step: str) -> bool:
        return step in self.completed_steps

    def get_progress(self) -> Dict:
        """Return current progress summary."""
        all_steps = [
            "region", "featured_articles", "subject_line",
            "intro_text", "news_section", "chart",
            "banner", "podcast", "world_articles", "assemble"
        ]
        return {
            "completed": self.completed_steps,
            "all_steps": all_steps,
            "current_step": next(
                (s for s in all_steps if s not in self.completed_steps),
                "done"
            ),
            "region": self.region,
            "region_name": REGION_CONFIG.get(self.region, {}).get("name", ""),
        }

    # ── Content setters (called by API endpoints) ──────────

    def set_featured_articles(self, articles: List[Dict]):
        self.content["featured_articles"] = articles
        self._mark_complete("featured_articles")

    def set_subject(self, subject: str):
        self.content["subject"] = subject
        self._mark_complete("subject_line")

    def set_intro_text(self, text: str):
        self.content["intro_text"] = text
        self._mark_complete("intro_text")

    def set_news_items(self, items: List[Dict]):
        self.content["news_items"] = items
        self._mark_complete("news_section")

    def set_chart(self, chart: Dict):
        self.content["chart"] = chart
        self._mark_complete("chart")

    def skip_chart(self):
        self._mark_complete("chart")

    def set_promotional_banner(self, banner: Optional[Dict]):
        if banner:
            self.content["promotional_banner"] = banner
        self._mark_complete("banner")

    def set_podcast(self, podcast: Dict):
        self.content["podcast"] = podcast
        self._mark_complete("podcast")

    def set_world_articles(self, articles: List[Dict]):
        self.content["world_articles"] = articles
        self._mark_complete("world_articles")

    # ── Checkpoint save/load ────────────────────────────────

    def save_checkpoint(self) -> str:
        """Save state to disk. Returns the file path."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "region": self.region,
            "completed_steps": self.completed_steps,
            "content": self.content,
        }
        CHECKPOINT_FILE.write_text(json.dumps(data, indent=2, default=str))
        return str(CHECKPOINT_FILE)

    def load_checkpoint(self) -> bool:
        """Load state from disk. Returns True if loaded."""
        if not CHECKPOINT_FILE.exists():
            return False
        try:
            data = json.loads(CHECKPOINT_FILE.read_text())
            self.region = data.get("region", "us")
            self.completed_steps = data.get("completed_steps", [])
            self.content = data.get("content", {})
            return True
        except (json.JSONDecodeError, KeyError):
            return False

    def clear_checkpoint(self):
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()

    def reset(self):
        """Reset all state for a fresh session."""
        self.__init__()
        self.clear_checkpoint()

    # ── Serialization ───────────────────────────────────────

    def to_dict(self) -> Dict:
        """Full state dump for frontend."""
        return {
            "region": self.region,
            "region_config": REGION_CONFIG.get(self.region, {}),
            "content": self.content,
            "progress": self.get_progress(),
        }
