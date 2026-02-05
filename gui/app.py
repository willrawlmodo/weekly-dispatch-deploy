"""
Weekly Dispatch GUI — FastAPI Backend

Exposes the newsletter pipeline as REST API endpoints.
Each step from the CLI is mapped to GET (fetch options) and POST (save selection) routes.

Run: python -m gui.app
"""

import sys
import os
import json
import webbrowser
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# Add project root to path so we can import scrapers/generators/etc.
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.modo_articles import ModoArticleScraper
from scrapers.youtube_podcast import YouTubePodcastScraper
from scrapers.news_sources import NewsSourcesScraper
from generators.content_generator import ContentGenerator
from assembler import NewsletterAssembler

# Optional HubSpot
try:
    from integrations.hubspot import HubSpotIntegration
    HUBSPOT_AVAILABLE = True
except ImportError:
    HUBSPOT_AVAILABLE = False

from gui.state import SessionState, REGION_CONFIG

# ── App setup ───────────────────────────────────────────────

app = FastAPI(title="Weekly Dispatch GUI", version="1.0.0")

# Serve static files (HTML/CSS/JS frontend)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Shared instances ────────────────────────────────────────

state = SessionState()
modo_scraper = ModoArticleScraper()
youtube_scraper = YouTubePodcastScraper()
news_scraper = NewsSourcesScraper()
content_generator = ContentGenerator()
assembler = NewsletterAssembler()

# ── Pydantic request models ────────────────────────────────

class RegionSelect(BaseModel):
    region: str  # "us" | "europe" | "australia"

class ArticleSelect(BaseModel):
    indices: List[int]          # 0-based indices into scraped articles
    num_layout: int = 2         # 1, 2, or 3 article layout

class SubjectSelect(BaseModel):
    subject: str

class IntroSelect(BaseModel):
    intro_text: str

class NewsSelect(BaseModel):
    indices: List[int]          # 0-based indices into scraped news
    custom_urls: List[str] = [] # Additional URLs to fetch

class ChartSubmit(BaseModel):
    source_article_index: int   # Which featured article the chart is from
    image_url: str              # URL or local path
    intro_text: str = ""
    outro_text: str = ""
    skip: bool = False

class BannerSubmit(BaseModel):
    image_url: str = ""
    link: str = ""
    alt_text: str = ""
    skip: bool = False

class PodcastSelect(BaseModel):
    episode_index: int = 0
    guest_name: str = ""
    guest_role: str = ""
    company: str = ""
    guest_linkedin: str = ""
    company_linkedin: str = ""
    moderator: str = "Ed"
    thumbnail: str = ""

class WorldSelect(BaseModel):
    indices: List[int]  # 0-based indices

class HubSpotPublish(BaseModel):
    upload_images: bool = True


# ═══════════════════════════════════════════════════════════
#  ROOT + STATE ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main GUI page."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/state")
async def get_state():
    """Return full session state for frontend hydration."""
    return state.to_dict()


@app.post("/api/reset")
async def reset_state():
    """Reset all state and start fresh."""
    state.reset()
    return {"status": "reset"}


@app.post("/api/checkpoint/save")
async def save_checkpoint():
    path = state.save_checkpoint()
    return {"status": "saved", "path": path}


@app.post("/api/checkpoint/load")
async def load_checkpoint():
    loaded = state.load_checkpoint()
    if loaded:
        content_generator.set_region(state.region)
        return {"status": "loaded", "state": state.to_dict()}
    raise HTTPException(404, "No checkpoint found")


# ═══════════════════════════════════════════════════════════
#  STEP 0: REGION SELECTION
# ═══════════════════════════════════════════════════════════

@app.get("/api/regions")
async def get_regions():
    """Return available regions and their config."""
    return {
        "regions": {
            k: {"name": v["name"], "article_region": v["article_region"]}
            for k, v in REGION_CONFIG.items()
        }
    }


@app.post("/api/step/region")
async def select_region(body: RegionSelect):
    """Set the newsletter region."""
    try:
        result = state.set_region(body.region)
        content_generator.set_region(body.region)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


# ═══════════════════════════════════════════════════════════
#  STEP 1: FEATURED ARTICLES
# ═══════════════════════════════════════════════════════════

@app.get("/api/step/articles/fetch")
async def fetch_articles(days: int = 7):
    """Scrape Modo Terminal for recent articles in the selected region."""
    config = REGION_CONFIG.get(state.region, {})
    region = config.get("article_region", "us")

    articles = modo_scraper.get_articles(region=region, days=days)
    state._article_cache = articles

    return {
        "articles": [
            {
                "index": i,
                "title": a.get("title", ""),
                "date": a.get("date", ""),
                "url": a.get("url", ""),
                "description": a.get("description", ""),
                "thumbnail_url": a.get("thumbnail_url", ""),
            }
            for i, a in enumerate(articles)
        ],
        "count": len(articles),
    }


@app.post("/api/step/articles/select")
async def select_articles(body: ArticleSelect):
    """Save user's featured article selections."""
    selected = []
    for idx in body.indices:
        if 0 <= idx < len(state._article_cache):
            selected.append(state._article_cache[idx])

    if not selected:
        raise HTTPException(400, "No valid articles selected")

    state.set_featured_articles(selected)
    return {"selected": len(selected), "articles": selected}


# ═══════════════════════════════════════════════════════════
#  STEP 2: SUBJECT LINE
# ═══════════════════════════════════════════════════════════

@app.get("/api/step/subject/generate")
async def generate_subjects():
    """Generate AI subject line suggestions from featured articles."""
    articles = state.content.get("featured_articles", [])
    if not articles:
        raise HTTPException(400, "No featured articles set. Complete Step 1 first.")

    suggestions = content_generator.generate_subject_line(articles)
    return {"suggestions": suggestions}


@app.post("/api/step/subject/select")
async def select_subject(body: SubjectSelect):
    """Save the chosen subject line."""
    state.set_subject(body.subject)
    return {"subject": body.subject}


# ═══════════════════════════════════════════════════════════
#  STEP 3: INTRO TEXT
# ═══════════════════════════════════════════════════════════

@app.get("/api/step/intro/generate")
async def generate_intro():
    """Generate AI intro paragraph from featured articles."""
    articles = state.content.get("featured_articles", [])
    if not articles:
        raise HTTPException(400, "No featured articles set. Complete Step 1 first.")

    preview = content_generator.generate_preview_text(articles)
    return {"intro_text": preview}


@app.post("/api/step/intro/select")
async def select_intro(body: IntroSelect):
    """Save the intro text (may be edited by user)."""
    state.set_intro_text(body.intro_text)
    return {"intro_text": body.intro_text}


# ═══════════════════════════════════════════════════════════
#  STEP 4: NEWS SECTION
# ═══════════════════════════════════════════════════════════

@app.get("/api/step/news/fetch")
async def fetch_news(region: Optional[str] = None):
    """Fetch battery/energy storage news via RSS."""
    news_region = region or REGION_CONFIG.get(state.region, {}).get("news_region", "us")
    news = news_scraper.get_news(days=8, limit=20, region=news_region)
    state._news_cache = news

    return {
        "news": [
            {
                "index": i,
                "title": n.get("title", ""),
                "source": n.get("source", ""),
                "date": n.get("date", ""),
                "url": n.get("url", ""),
                "description": n.get("description", ""),
                "region": n.get("region", ""),
            }
            for i, n in enumerate(news)
        ],
        "count": len(news),
    }


@app.post("/api/step/news/select")
async def select_news(body: NewsSelect):
    """Save selected news items. Formats them with AI."""
    selected = []
    for idx in body.indices:
        if 0 <= idx < len(state._news_cache):
            selected.append(state._news_cache[idx])

    # Fetch and append any custom URLs
    for url in body.custom_urls:
        article = news_scraper.fetch_custom_url(url)
        if article:
            selected.append(article)

    # Format with AI (same logic as CLI's _format_news_with_ai)
    formatted = []
    for article in selected[:4]:
        try:
            item = content_generator.format_news_item(
                title=article.get("title", ""),
                description=article.get("description", ""),
                url=article.get("url", ""),
                source=article.get("source", ""),
                region_prefix=""  # GUI user can edit freely
            )
            formatted.append(item)
        except Exception:
            formatted.append({
                "headline": article.get("title", ""),
                "body": f", {article.get('description', '')}",
                "url": article.get("url", ""),
                "source": article.get("source", ""),
            })

    state.set_news_items(formatted)
    return {"news_items": formatted, "count": len(formatted)}


# ═══════════════════════════════════════════════════════════
#  STEP 5: CHART OF THE WEEK
# ═══════════════════════════════════════════════════════════

@app.post("/api/step/chart/generate-text")
async def generate_chart_text(body: ChartSubmit):
    """Generate AI intro/outro text for the chart."""
    if body.skip:
        state.skip_chart()
        return {"status": "skipped"}

    articles = state.content.get("featured_articles", [])
    if not articles or body.source_article_index >= len(articles):
        raise HTTPException(400, "Invalid source article index")

    source = articles[body.source_article_index]
    text = content_generator.generate_chart_text(
        "Chart of the week",
        source.get("description", "")
    )

    return {"intro": text["intro"], "outro": text["outro"]}


@app.post("/api/step/chart/select")
async def select_chart(body: ChartSubmit):
    """Save chart of the week configuration."""
    if body.skip:
        state.skip_chart()
        return {"status": "skipped"}

    articles = state.content.get("featured_articles", [])
    source_url = ""
    if articles and body.source_article_index < len(articles):
        source_url = articles[body.source_article_index].get("url", "")

    state.set_chart({
        "title": "Chart of the week",
        "intro_text": body.intro_text,
        "outro_text": body.outro_text,
        "image_url": body.image_url,
        "article_url": source_url,
    })
    return {"status": "saved"}


# ═══════════════════════════════════════════════════════════
#  STEP 5b: MORE ARTICLES (additional articles after chart)
# ═══════════════════════════════════════════════════════════

class MoreArticlesSelect(BaseModel):
    indices: List[int]
    skip: bool = False


@app.get("/api/step/more-articles/fetch")
async def fetch_more_articles(days: int = 14):
    """Fetch articles for the 'More from Modo Energy' section, excluding featured."""
    config = REGION_CONFIG.get(state.region, {})
    region = config.get("article_region", "us")

    articles = modo_scraper.get_articles(region=region, days=days, limit=30)

    # Exclude already-selected featured articles
    featured_slugs = {a.get('slug') for a in state.content.get('featured_articles', [])}
    articles = [a for a in articles if a.get('slug') not in featured_slugs]

    state._more_article_cache = articles

    return {
        "articles": [
            {
                "index": i,
                "title": a.get("title", ""),
                "date": a.get("date", ""),
                "url": a.get("url", ""),
                "description": a.get("description", ""),
                "thumbnail_url": a.get("thumbnail_url", ""),
            }
            for i, a in enumerate(articles)
        ],
        "count": len(articles),
    }


@app.post("/api/step/more-articles/select")
async def select_more_articles(body: MoreArticlesSelect):
    """Save additional article selections (or skip)."""
    if body.skip:
        state.skip_more_articles()
        return {"status": "skipped"}

    selected = []
    cache = getattr(state, '_more_article_cache', [])
    for idx in body.indices:
        if 0 <= idx < len(cache):
            selected.append(cache[idx])

    state.set_more_articles(selected[:10])
    return {"status": "saved", "count": len(selected[:10])}


# ═══════════════════════════════════════════════════════════
#  STEP 6: PROMOTIONAL BANNER
# ═══════════════════════════════════════════════════════════

@app.post("/api/step/banner/select")
async def select_banner(body: BannerSubmit):
    """Save or skip the promotional banner."""
    if body.skip:
        state.set_promotional_banner(None)
        return {"status": "skipped"}

    state.set_promotional_banner({
        "image_url": body.image_url,
        "link": body.link,
        "alt_text": body.alt_text,
    })
    return {"status": "saved"}


# ═══════════════════════════════════════════════════════════
#  STEP 7: PODCAST
# ═══════════════════════════════════════════════════════════

@app.get("/api/step/podcast/fetch")
async def fetch_podcasts():
    """Fetch recent Transmission podcast episodes from YouTube."""
    episodes = youtube_scraper.get_recent_episodes(limit=4)
    state._podcast_cache = episodes

    results = []
    for i, ep in enumerate(episodes):
        guest_info = youtube_scraper.parse_guest_info(ep.get("title", ""))
        results.append({
            "index": i,
            "title": ep.get("title", ""),
            "url": ep.get("url", ""),
            "thumbnail": ep.get("thumbnail", ""),
            "video_id": ep.get("video_id", ""),
            "guest_name": guest_info.get("guest_name", ""),
            "guest_role": guest_info.get("guest_role", ""),
            "company": guest_info.get("company", ""),
            "topic": guest_info.get("topic", ""),
        })

    return {"episodes": results, "count": len(results)}


@app.post("/api/step/podcast/select")
async def select_podcast(body: PodcastSelect):
    """Save podcast section configuration."""
    # Get episode from cache
    episode = {}
    if 0 <= body.episode_index < len(state._podcast_cache):
        episode = state._podcast_cache[body.episode_index]

    # Generate description with AI
    description = content_generator.generate_podcast_description(
        guest_name=body.guest_name,
        guest_role=body.guest_role,
        company=body.company,
        topic=episode.get("title", ""),
        moderator=body.moderator,
    )

    # Insert LinkedIn links if provided
    if body.guest_linkedin and body.guest_name:
        description = description.replace(
            f"<strong>{body.guest_name}</strong>",
            f'<a href="{body.guest_linkedin}" style="color:#000000; text-decoration:none; font-weight:bold;">{body.guest_name}</a>'
        )
    if body.company_linkedin and body.company:
        description = description.replace(
            f"<strong>{body.company}</strong>",
            f'<a href="{body.company_linkedin}" style="color:#000000; text-decoration:none; font-weight:bold;">{body.company}</a>'
        )

    thumbnail = body.thumbnail or episode.get("thumbnail", "")

    state.set_podcast({
        "title": episode.get("title", body.guest_name),
        "url": episode.get("url", ""),
        "thumbnail": thumbnail,
        "description": description,
    })
    return {"status": "saved", "description": description}


# ═══════════════════════════════════════════════════════════
#  STEP 8: WORLD ARTICLES
# ═══════════════════════════════════════════════════════════

@app.get("/api/step/world/fetch")
async def fetch_world_articles(days: int = 14):
    """Fetch articles from other regions (cross-promotion)."""
    if state.region == "us":
        articles = modo_scraper.get_articles(region="gb_europe", days=days, limit=10)
        aus = modo_scraper.get_articles(region="australia", days=days, limit=5)
        articles.extend(aus)
    elif state.region == "europe":
        articles = modo_scraper.get_articles(region="us", days=days, limit=10)
        aus = modo_scraper.get_articles(region="australia", days=days, limit=5)
        articles.extend(aus)
    else:  # australia
        articles = modo_scraper.get_articles(region="gb_europe", days=days, limit=10)

    state._world_article_cache = articles

    return {
        "articles": [
            {
                "index": i,
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "thumbnail_url": a.get("thumbnail_url", ""),
                "detected_region": a.get("detected_region", "unknown"),
            }
            for i, a in enumerate(articles)
        ],
        "count": len(articles),
    }


@app.post("/api/step/world/select")
async def select_world_articles(body: WorldSelect):
    """Save world article selections."""
    selected = []
    for idx in body.indices:
        if 0 <= idx < len(state._world_article_cache):
            selected.append(state._world_article_cache[idx])

    state.set_world_articles(selected[:3])
    return {"selected": len(selected), "articles": selected[:3]}


# ═══════════════════════════════════════════════════════════
#  STEP 9: ASSEMBLE + PREVIEW + PUBLISH
# ═══════════════════════════════════════════════════════════

@app.get("/api/preview")
async def preview_newsletter():
    """Assemble current content into HTML and return it for preview."""
    try:
        html = assembler.assemble(state.content)
        return {"html": html, "subject": state.content.get("subject", "")}
    except Exception as e:
        raise HTTPException(500, f"Assembly error: {e}")


@app.post("/api/assemble")
async def assemble_newsletter():
    """Final assembly: save HTML to output/ and return metadata."""
    try:
        html = assembler.assemble(state.content)
        metadata = assembler.get_email_metadata(state.content)

        # Save to output/
        output_dir = PROJECT_ROOT / "output"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"newsletter_{timestamp}.html"
        output_file.write_text(html)

        meta_file = output_dir / f"newsletter_{timestamp}_meta.txt"
        meta_file.write_text(
            f"Subject: {metadata['subject']}\n\nPreview Text: {metadata['preview_text']}"
        )

        state._mark_complete("assemble")

        return {
            "status": "assembled",
            "output_file": str(output_file),
            "meta_file": str(meta_file),
            "subject": metadata["subject"],
            "preview_text": metadata["preview_text"],
            "html_length": len(html),
        }
    except Exception as e:
        raise HTTPException(500, f"Assembly error: {e}")


@app.post("/api/publish/hubspot")
async def publish_hubspot(body: HubSpotPublish):
    """Publish to HubSpot as a draft email."""
    if not HUBSPOT_AVAILABLE:
        raise HTTPException(501, "HubSpot integration not available. Install the hubspot package.")

    try:
        html = assembler.assemble(state.content)
        metadata = assembler.get_email_metadata(state.content)
        hubspot = HubSpotIntegration()

        # Apply region-specific HubSpot settings
        config = REGION_CONFIG.get(state.region, {})
        hubspot.settings["from_name"] = config.get("from_name", hubspot.settings["from_name"])
        hubspot.settings["from_email"] = config.get("from_email", hubspot.settings["from_email"])
        hubspot.settings["image_folder"] = config.get("image_folder", hubspot.settings["image_folder"])

        result = hubspot.publish_newsletter(
            html=html,
            content=state.content,
            subject=metadata["subject"],
            preview_text=metadata["preview_text"],
            upload_images=body.upload_images,
        )

        if result:
            return {
                "status": "published",
                "email_id": result.get("id"),
                "message": "Draft created in HubSpot",
            }
        raise HTTPException(500, "HubSpot publish returned no result")

    except FileNotFoundError as e:
        raise HTTPException(401, f"HubSpot credential not found: {e}")
    except Exception as e:
        raise HTTPException(500, f"HubSpot error: {e}")


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════

def open_browser():
    """Open the GUI in the default browser after a short delay."""
    import time
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    print("\n  ╔══════════════════════════════════════════╗")
    print("  ║   MODO ENERGY WEEKLY DISPATCH — GUI      ║")
    print("  ╠══════════════════════════════════════════╣")
    print("  ║   http://localhost:8000                  ║")
    print("  ╚══════════════════════════════════════════╝\n")

    # Open browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
