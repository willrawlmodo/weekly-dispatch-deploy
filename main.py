#!/usr/bin/env python3
"""
Weekly Dispatch Newsletter Agent

Interactive CLI tool to generate the Modo Energy Weekly Dispatch newsletter.

Usage:
    python3 main.py              # Normal interactive mode
    python3 main.py --preview    # Dry run with cached/dummy content
    python3 main.py --resume     # Resume from last checkpoint
"""

import os
import re
import sys
import json
import argparse
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from difflib import SequenceMatcher

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.modo_articles import ModoArticleScraper
from scrapers.youtube_podcast import YouTubePodcastScraper
from scrapers.news_sources import NewsSourcesScraper
from generators.content_generator import ContentGenerator
from assembler import NewsletterAssembler

# Optional HubSpot integration
try:
    from integrations.hubspot import HubSpotIntegration
    HUBSPOT_AVAILABLE = True
except ImportError:
    HUBSPOT_AVAILABLE = False

# Optional Slack integration
try:
    import requests as slack_requests
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False


class NewsletterAgent:
    """Interactive agent for generating the Weekly Dispatch newsletter."""

    # Region configuration with header banners
    REGION_CONFIG = {
        "europe": {
            "name": "Europe & GB",
            "header_url": "https://25093280.fs1.hubspotusercontent-eu1.net/hubfs/25093280/European%20Weekly%20Dispatch/Weekly%20Dispatch%20Header_EU.png",
            "header_alt": "MODOENERGY Weekly Dispatch Europe & GB Edition",
            "article_region": "gb_europe",
            "news_region": "europe",
            "from_name": "Shaniyaa Holness-Mckenzie",
            "from_email": "shaniyaa@modoenergy.com",
            "image_folder": "European Weekly Dispatch",
            "include_lists": [
                "July GB/Europe livestream registrants",
                "EU contacts [ALL] (Neil's Dispatch list)",
                "Germany livestream signups - October 2025",
                "Spain livestream signups - October 2025",
                "GB livestream signup - October 2025",
                "Madrid Workshops Guest List - Tuesday.csv",
                "Madrid Workshops Guest List - Wednesday Session 1.csv",
                "Madrid Workshops Guest List - Wednesday Session 2.csv",
                "Party Attendees - Sheet1.csv",
                "Weekly Newsletter - Great Britain",
                "Contacts from Company with LIVE GB & Europe Research Deals"
            ],
            "exclude_lists": [
                "Opted out of weekly newsletter",
                "GB Weekly Roundup Did Not Sends",
                "Marketing suppression list (unsubscribed from ALL email or Sales want excluded)"
            ],
            "exclude_emails": [
                "tim+03@modoenergy.com",
                "tim+1@modoenergy.com",
                "admin@modo.energy",
                "tim+2@modo.energy",
                "tim+3@modoenergy.com",
                "tim+1@modo.energy"
            ]
        },
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
            "include_lists": [
                # ERCOT lists
                "Weekly Newsletter - ERCOT",
                "ERCOT livestream (July 2025) signups",
                "Webinar follow-up ERCOT BESS 7/29",
                "ERCOT Livestream Q3 2025 non-attendees",
                "ERCOT Market Summit 2024 - Leads",
                # General US lists
                "US Growth US Outreach",
                "Feb 26 2025 US BESS briefing list",
                "US Research Sequence [Sept 25]",
                "USA livestream registrants - October 2025",
                "ESS USA 2025 attendees - Registrant List.csv",
                "US BESS Operators and Optimizers viewers",
                "US Research Outbound",
                "US Customer Contacts - no GB overlap",
                "US Customer Contacts - multi-region under Matt",
                "Paying customers in North America (Neil's bodgejob list)"
            ],
            "exclude_lists": [
                "Opted out of weekly newsletter",
                "Marketing suppression list (unsubscribed from ALL email or Sales want excluded)"
            ],
            "exclude_emails": [
                "tim+03@modoenergy.com",
                "tim+1@modoenergy.com",
                "admin@modo.energy",
                "tim+2@modo.energy",
                "tim+3@modoenergy.com",
                "tim+1@modo.energy"
            ]
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
            "include_lists": [
                "Contact region = APAC",
                "Australia livestream signups - October 2025",
                "ESS AUS 2025",
                "Weekly Newsletter - Australia",
                "General Registration - Aus Livestream Aug 2025",
                "Sequence follow up aus livestream",
                "WORKSHOP_ The Outlook for BESS in the NEM - Guests - 2025-09-30-13-50-44 - WORKSHOP_ The Outlook for BESS in the NEM - Guests"
            ],
            "exclude_lists": [
                "Opted out of weekly newsletter",
                "Marketing suppression list (unsubscribed from ALL email or Sales want excluded)"
            ],
            "exclude_emails": [
                "tim+03@modoenergy.com",
                "tim+1@modoenergy.com",
                "admin@modo.energy",
                "tim+2@modo.energy",
                "tim+3@modoenergy.com",
                "tim+1@modo.energy"
            ]
        }
    }

    # Checkpoint file for save/resume
    CHECKPOINT_FILE = Path(__file__).parent / '.workflow_checkpoint.json'
    
    # Slack webhook URL (set via environment variable or config)
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
    SLACK_CHANNEL = os.getenv('SLACK_CHANNEL', '#weekly-dispatch')

    def __init__(self, dry_run: bool = False, resume: bool = False):
        self.dry_run = dry_run
        self.resume = resume
        
        self.modo_scraper = ModoArticleScraper()
        self.youtube_scraper = YouTubePodcastScraper()
        self.news_scraper = NewsSourcesScraper()
        self.content_generator = ContentGenerator()
        self.assembler = NewsletterAssembler()

        # Collected content
        self.content = {}
        
        # Track completed steps for checkpointing
        self.completed_steps = []

        # Selected region (set during workflow) - default to US for this fork
        self.selected_region = "us"
        
        # Load checkpoint if resuming
        if resume and self.CHECKPOINT_FILE.exists():
            self._load_checkpoint()

    def _validate_image_url(self, url: str) -> str:
        """
        Validate and clean an image URL or file path.
        Returns cleaned URL/path or empty string if invalid.
        """
        if not url:
            return ''

        # Strip whitespace and surrounding quotes
        url = url.strip().strip("'\"")

        # Check if it's a valid URL
        if url.startswith('http://') or url.startswith('https://'):
            return url

        # Check if it's a local file path
        if url.startswith('/') or url.startswith('~') or url.startswith('./'):
            # Expand ~ to home directory
            expanded = os.path.expanduser(url)
            if os.path.exists(expanded):
                return expanded
            else:
                print(f"    ⚠ Warning: Local file not found: {expanded}")
                return ''

        # Check for Windows-style paths
        if len(url) > 2 and url[1] == ':':
            if os.path.exists(url):
                return url
            else:
                print(f"    ⚠ Warning: Local file not found: {url}")
                return ''

        # Invalid - not a URL or valid file path
        # Could be user accidentally entering a number like "1"
        if url.isdigit() or len(url) < 5:
            print(f"    ⚠ Warning: '{url}' is not a valid image URL or path")
            return ''

        return ''

    # ==================== CHECKPOINT METHODS ====================
    
    def _save_checkpoint(self, step_name: str):
        """Save current progress to checkpoint file."""
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'selected_region': self.selected_region,
            'completed_steps': self.completed_steps,
            'content': self.content
        }
        try:
            with open(self.CHECKPOINT_FILE, 'w') as f:
                json.dump(checkpoint, f, indent=2, default=str)
            print(f"    💾 Progress saved (step: {step_name})")
        except Exception as e:
            print(f"    ⚠ Could not save checkpoint: {e}")
    
    def _load_checkpoint(self):
        """Load progress from checkpoint file."""
        try:
            with open(self.CHECKPOINT_FILE, 'r') as f:
                checkpoint = json.load(f)
            
            self.selected_region = checkpoint.get('selected_region', 'us')
            self.completed_steps = checkpoint.get('completed_steps', [])
            self.content = checkpoint.get('content', {})
            
            timestamp = checkpoint.get('timestamp', 'unknown')
            print(f"\n✓ Loaded checkpoint from {timestamp}")
            print(f"  Completed steps: {', '.join(self.completed_steps) if self.completed_steps else 'None'}")
            print(f"  Region: {self.selected_region}")
            
            # Set region on content generator
            self.content_generator.set_region(self.selected_region)
            
        except Exception as e:
            print(f"\n⚠ Could not load checkpoint: {e}")
            print("  Starting fresh...")
            self.completed_steps = []
            self.content = {}
    
    def _clear_checkpoint(self):
        """Remove checkpoint file after successful completion."""
        try:
            if self.CHECKPOINT_FILE.exists():
                self.CHECKPOINT_FILE.unlink()
                print("    🗑 Checkpoint cleared")
        except Exception as e:
            print(f"    ⚠ Could not clear checkpoint: {e}")
    
    def _should_skip_step(self, step_name: str) -> bool:
        """Check if step was already completed (for resume mode)."""
        if self.resume and step_name in self.completed_steps:
            print(f"\n[SKIPPING] {step_name} (already completed)")
            return True
        return False
    
    def _mark_step_complete(self, step_name: str):
        """Mark a step as complete and save checkpoint."""
        if step_name not in self.completed_steps:
            self.completed_steps.append(step_name)
        self._save_checkpoint(step_name)

    # ==================== ISO DETECTION ====================
    
    ISO_KEYWORDS = {
        'ERCOT': ['ercot', 'texas grid', 'texas power', 'oncor', 'centerpoint texas'],
        'MISO': ['miso', 'midcontinent', 'midcon'],
        'CAISO': ['caiso', 'california iso', 'california grid', 'cpuc'],
        'PJM': ['pjm', 'mid-atlantic'],
        'NYISO': ['nyiso', 'new york iso', 'new york grid', 'con edison', 'nyserda'],
        'ISO-NE': ['iso-ne', 'iso ne', 'new england iso', 'new england grid'],
        'SPP': ['spp', 'southwest power pool'],
    }
    
    def _detect_isos(self, text: str) -> List[str]:
        """Detect which ISOs are mentioned in text."""
        text_lower = text.lower()
        detected = []
        for iso, keywords in self.ISO_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                detected.append(iso)
        return detected
    
    def _add_iso_tags_to_articles(self, articles: List[Dict]) -> List[Dict]:
        """Add ISO tags to news articles based on content."""
        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            isos = self._detect_isos(text)
            article['_detected_isos'] = isos
        return articles

    # ==================== DUPLICATE DETECTION ====================
    
    def _similarity_score(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings (0-1 scale)."""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
    
    def _find_duplicates(self, articles: List[Dict], threshold: float = 0.65) -> List[tuple]:
        """
        Find potential duplicate articles based on headline similarity.
        
        Returns list of tuples: (index1, index2, similarity_score)
        """
        duplicates = []
        for i, art1 in enumerate(articles):
            for j, art2 in enumerate(articles[i+1:], start=i+1):
                title1 = art1.get('title', '')
                title2 = art2.get('title', '')
                score = self._similarity_score(title1, title2)
                if score >= threshold:
                    duplicates.append((i, j, score))
        return duplicates
    
    def _display_with_duplicate_warnings(self, articles: List[Dict], label: str = "articles", show_isos: bool = False):
        """
        Display articles with duplicate warnings and optional ISO tags.
        """
        duplicates = self._find_duplicates(articles)
        duplicate_indices = set()
        for i, j, _ in duplicates:
            duplicate_indices.add(i)
            duplicate_indices.add(j)
        
        # Add ISO tags if requested and for US region
        if show_isos:
            articles = self._add_iso_tags_to_articles(articles)
        
        print(f"\nFound {len(articles)} {label}:\n")
        for i, article in enumerate(articles, 1):
            source = article.get('source', 'Unknown')
            title = article['title'][:50] + '...' if len(article.get('title', '')) > 50 else article.get('title', '')
            
            # ISO tags
            iso_tags = ""
            if show_isos:
                isos = article.get('_detected_isos', [])
                if isos:
                    iso_tags = f" [{', '.join(isos)}]"
            
            # Check if this article has a duplicate
            dup_warning = ""
            for idx1, idx2, score in duplicates:
                if i-1 == idx1:
                    dup_warning = f" ⚠️ DUP #{idx2+1}"
                    break
                elif i-1 == idx2:
                    dup_warning = f" ⚠️ DUP #{idx1+1}"
                    break
            
            print(f"  {i}. [{source}]{iso_tags} {title}{dup_warning}")
        
        if duplicates:
            print(f"\n  ⚠️ {len(duplicates)} potential duplicate(s) detected - consider picking only one")

    # ==================== SLACK NOTIFICATION ====================
    
    def _send_slack_notification(self, subject: str, hubspot_id: str = None):
        """
        Send Slack notification when HubSpot draft is ready.
        """
        if not SLACK_AVAILABLE or not self.SLACK_WEBHOOK_URL:
            return
        
        try:
            region_config = self.REGION_CONFIG.get(self.selected_region, {})
            region_name = region_config.get('name', 'Unknown')
            
            message = {
                "channel": self.SLACK_CHANNEL,
                "username": "Weekly Dispatch Bot",
                "icon_emoji": ":newspaper:",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"📬 Weekly Dispatch Draft Ready ({region_name})"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Subject:*\n{subject}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Region:*\n{region_name}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Draft is ready for review in HubSpot."
                        }
                    }
                ]
            }
            
            if hubspot_id:
                message["blocks"].append({
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Open in HubSpot"
                            },
                            "url": f"https://app.hubspot.com/email/25093280/edit/{hubspot_id}/settings"
                        }
                    ]
                })
            
            response = slack_requests.post(
                self.SLACK_WEBHOOK_URL,
                json=message,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"    📣 Slack notification sent to {self.SLACK_CHANNEL}")
            else:
                print(f"    ⚠ Slack notification failed: {response.status_code}")
                
        except Exception as e:
            print(f"    ⚠ Could not send Slack notification: {e}")

    # ==================== BROWSER PREVIEW ====================
    
    def _preview_in_browser(self, html_path: Path):
        """Open the newsletter HTML in the default browser for preview."""
        try:
            file_url = f'file://{html_path.absolute()}'
            webbrowser.open(file_url)
            print(f"    🌐 Opened preview in browser")
        except Exception as e:
            print(f"    ⚠ Could not open browser: {e}")

    # ==================== DRY RUN MODE ====================
    
    def _get_dummy_content(self) -> Dict:
        """Generate dummy content for dry run mode."""
        return {
            'region': 'us',
            'region_name': 'US',
            'header_url': self.REGION_CONFIG['us']['header_url'],
            'header_alt': self.REGION_CONFIG['us']['header_alt'],
            'subject': '[DRY RUN] Test Subject Line - BESS Market Update',
            'preview_text': 'This is a test preview text for the dry run mode.',
            'featured_articles': [
                {
                    'title': '[TEST] ERCOT Interconnection Queue Analysis',
                    'description': 'A test article description for the dry run mode.',
                    'url': 'https://modoenergy.com/research/en/test-article',
                    'thumbnail_url': 'https://via.placeholder.com/600x400?text=Test+Thumbnail'
                }
            ],
            'intro_text': '<p>This is a <strong>test intro paragraph</strong> generated during dry run mode. It includes a link to the <a href="https://modoenergy.com">test article</a>.</p>',
            'news_items': [
                {
                    'headline': 'Test News Headline 1',
                    'body': 'Test news body text for the first item.',
                    'url': 'https://example.com/news1'
                },
                {
                    'headline': 'Test News Headline 2',
                    'body': 'Test news body text for the second item.',
                    'url': 'https://example.com/news2'
                }
            ],
            'chart': {
                'image_url': 'https://via.placeholder.com/600x400?text=Chart+of+the+Week',
                'intro': 'Test chart introduction text.',
                'description': 'Test chart description explaining what the data shows.'
            },
            'podcast': {
                'title': '[TEST] Transmission Episode - Guest Name',
                'url': 'https://youtube.com/watch?v=test',
                'thumbnail': 'https://via.placeholder.com/480x360?text=Podcast+Thumbnail',
                'description': 'Test podcast description with <strong>guest name</strong> from <strong>Company</strong>.'
            },
            'world_articles': [
                {
                    'title': '[TEST] Europe Article 1',
                    'url': 'https://modoenergy.com/research/en/test-europe',
                    'thumbnail_url': 'https://via.placeholder.com/300x200?text=Europe+Article'
                },
                {
                    'title': '[TEST] Australia Article 1',
                    'url': 'https://modoenergy.com/research/en/test-australia',
                    'thumbnail_url': 'https://via.placeholder.com/300x200?text=Australia+Article'
                }
            ]
        }

    def run(self):
        """Run the interactive newsletter generation workflow."""
        self._print_header()
        
        # Handle dry run mode
        if self.dry_run:
            print("\n" + "=" * 60)
            print("  DRY RUN MODE - Using dummy content")
            print("=" * 60)
            self.content = self._get_dummy_content()
            self._step_assemble()
            print("\n" + "=" * 60)
            print("Dry run complete! Check the output to verify the pipeline.")
            print("=" * 60)
            return
        
        # Handle resume mode
        if self.resume and self.completed_steps:
            print(f"\n  Resuming from checkpoint...")
            print(f"  Will skip: {', '.join(self.completed_steps)}")
            input("\n  Press Enter to continue...")

        # Step 0: Select newsletter region
        if not self._should_skip_step('region'):
            self._step_select_region()
            self._mark_step_complete('region')

        self._print_session_checklist()

        # Step 1: Fetch and select featured articles
        if not self._should_skip_step('featured_articles'):
            self._step_featured_articles()
            self._mark_step_complete('featured_articles')

        # Step 2: Generate subject line
        if not self._should_skip_step('subject_line'):
            self._step_subject_line()
            self._mark_step_complete('subject_line')

        # Step 3: Generate intro/preview text
        if not self._should_skip_step('intro_text'):
            self._step_intro_text()
            self._mark_step_complete('intro_text')

        # Step 4: This week's news
        if not self._should_skip_step('news_section'):
            self._step_news_section()
            self._mark_step_complete('news_section')

        # Step 5: Chart of the week
        if not self._should_skip_step('chart'):
            self._step_chart_of_week()
            self._mark_step_complete('chart')

        # Step 5b: More articles (additional articles after chart)
        if not self._should_skip_step('more_articles'):
            self._step_more_articles()
            self._mark_step_complete('more_articles')

        # Step 6: Promotional banner
        if not self._should_skip_step('banner'):
            self._step_promotional_banner()
            self._mark_step_complete('banner')

        # Step 7: Podcast section
        if not self._should_skip_step('podcast'):
            self._step_podcast()
            self._mark_step_complete('podcast')

        # Step 8: More from around the world
        if not self._should_skip_step('world_articles'):
            self._step_world_articles()
            self._mark_step_complete('world_articles')

        # Step 9: Assemble and output
        self._step_assemble()
        
        # Clear checkpoint on successful completion
        self._clear_checkpoint()

        print("\n" + "=" * 60)
        print("Newsletter generation complete!")
        print("=" * 60)

    def _print_header(self):
        """Print the agent header."""
        print("\n" + "=" * 60)
        print("  MODO ENERGY WEEKLY DISPATCH - Newsletter Agent")
        print("=" * 60)
        print(f"\n  Date: {datetime.now().strftime('%A, %d %B %Y')}")
        print("\n" + "-" * 60)

    def _step_select_region(self):
        """Step 0: Select newsletter region."""
        print("\n[REGION SELECTION]")
        print("-" * 40)
        print("\nWhich edition are you creating?")
        print("  1. US (ERCOT, MISO, CAISO, PJM, NYISO, ISO-NE, SPP) [DEFAULT]")
        print("  2. Europe & GB")
        print("  3. Australia")
        
        choice_input = input("\nEnter choice (1-3) [1]: ").strip()
        choice = int(choice_input) if choice_input else 1
        
        if choice not in [1, 2, 3]:
            print("Invalid choice, defaulting to US.")
            choice = 1
            
        region_map = {1: "us", 2: "europe", 3: "australia"}
        self.selected_region = region_map[choice]

        region_config = self.REGION_CONFIG[self.selected_region]
        print(f"\n✓ Selected: {region_config['name']} Edition")

        # Store region in content for assembler
        self.content['region'] = self.selected_region
        self.content['region_name'] = region_config['name']
        self.content['header_url'] = region_config['header_url']
        self.content['header_alt'] = region_config['header_alt']

        # Set region on content generator for localized content
        self.content_generator.set_region(self.selected_region)

        print(f"  Header banner: {region_config['name']}")
        print(f"  Default article source: {region_config['article_region']}")
        print(f"  Default news region: {region_config['news_region']}")

    def _print_session_checklist(self):
        """Print a checklist of items the user should have ready."""
        print("\n  CREDENTIALS REQUIRED:")
        print("  " + "-" * 50)
        print("  □ OpenAI API credentials")
        print("  □ HubSpot API credentials")
        print("  " + "-" * 50)
        print("\n  CONTENT TO HAVE READY:")
        print("  " + "-" * 50)
        print("  □ Chart of the Week image (local path or URL)")
        print("  □ Promotional banner image (if applicable)")
        print("  □ Podcast guest LinkedIn URL (can look up later)")
        print("  □ Podcast guest company LinkedIn URL (can look up later)")
        print("  " + "-" * 50)
        print("\n  AUTO-FETCHED (no action needed):")
        print("  " + "-" * 50)
        print("  ✓ Article thumbnails (from Modo Terminal og:image)")
        print("  ✓ Podcast thumbnail (from YouTube)")
        print("  ✓ Podcast guest details (parsed from YouTube)")
        print("  " + "-" * 50)
        print("\n  Local file paths will be uploaded to HubSpot automatically.")
        print("\n" + "-" * 60)
        input("\n  Press Enter when ready to continue...")

    def _step_featured_articles(self):
        """Step 1: Fetch and select featured articles."""
        print("\n[STEP 1/9] FEATURED ARTICLES")
        print("-" * 40)

        # Ask how many featured articles
        print("\nHow many featured articles?")
        print("  1. One article (full width)")
        print("  2. Two articles (full width, stacked)")
        print("  3. Three articles (first full width, second two side-by-side)")

        num_articles = self._get_choice(3)

        # Use region-specific article source
        region_config = self.REGION_CONFIG[self.selected_region]
        article_region = region_config['article_region']
        region_name = region_config['name']

        # Adjustable day filter
        days_input = input("\nHow many days to look back? (default: 7): ").strip()
        featured_days = int(days_input) if days_input.isdigit() and int(days_input) > 0 else 7

        print(f"\nFetching {region_name} articles from the last {featured_days} days...")
        articles = self.modo_scraper.get_articles(region=article_region, days=featured_days)

        if not articles:
            print("No articles found. Please enter manually.")
            articles = self._manual_article_entry(count=num_articles)
        else:
            print(f"\nFound {len(articles)} articles from the last {featured_days} days:\n")
            for i, article in enumerate(articles, 1):
                date_raw = article.get('date', '')
                try:
                    from datetime import datetime as _dt
                    date_display = _dt.strptime(date_raw, "%Y-%m-%dT%H:%M:%S%z").strftime("%b %d, %Y")
                except (ValueError, TypeError):
                    date_display = date_raw or 'Unknown'
                print(f"  {i}. {article['title']}")
                print(f"     Date: {date_display}")
                print()

            # Let user select articles based on chosen count
            selected = self._select_items(
                articles,
                count=num_articles,
                prompt=f"Select {num_articles} article{'s' if num_articles > 1 else ''} for featured section"
            )
            articles = selected

        # Show selected articles and offer customization
        print("\nSelected articles:")
        for i, article in enumerate(articles, 1):
            print(f"  {i}. {article['title'][:60]}...")
            print(f"     Thumbnail: {article.get('thumbnail_url', 'None')[:50]}...")

        print("\n1. Use as-is")
        print("2. Customize thumbnails/descriptions")

        if self._get_choice(2) == 2:
            for article in articles:
                print(f"\nArticle: {article['title'][:50]}...")
                print(f"  Current thumbnail: {article.get('thumbnail_url', 'None')[:60]}...")
                custom_thumb = input("  New thumbnail URL or local path (Enter to keep): ").strip()
                if custom_thumb:
                    article['thumbnail_url'] = custom_thumb

                # Only ask for description for full-width articles (first article always, second only if 2 total)
                if articles.index(article) == 0 or (len(articles) == 2 and articles.index(article) == 1):
                    print(f"  Current description: {article.get('description', 'None')[:80]}...")
                    custom_desc = input("  New description (Enter to keep): ").strip()
                    if custom_desc:
                        article['description'] = custom_desc

        self.content['featured_articles'] = articles
        print(f"\n✓ {len(articles)} featured article{'s' if len(articles) > 1 else ''} selected")

    def _step_subject_line(self):
        """Step 2: Generate subject line."""
        print("\n[STEP 2/9] SUBJECT LINE")
        print("-" * 40)

        suggestions = self.content_generator.generate_subject_line(
            self.content.get('featured_articles', [])
        )

        print("\nSuggested subject lines:")
        for i, subject in enumerate(suggestions, 1):
            print(f"  {i}. {subject}")

        print(f"  {len(suggestions) + 1}. Enter custom")

        choice = self._get_choice(len(suggestions) + 1)
        if choice == len(suggestions) + 1:
            self.content['subject'] = input("\nEnter custom subject line: ").strip()
        else:
            selected = suggestions[choice - 1]
            # Allow customization of selected option
            print(f"\nSelected: {selected}")
            print("Press Enter to keep, or type to customize:")
            custom = input("> ").strip()
            self.content['subject'] = custom if custom else selected

        print(f"\n✓ Subject line: {self.content['subject']}")

    def _step_intro_text(self):
        """Step 3: Generate intro/preview text."""
        print("\n[STEP 3/9] INTRO PARAGRAPH")
        print("-" * 40)

        preview = self.content_generator.generate_preview_text(
            self.content.get('featured_articles', [])
        )

        print(f"\nGenerated intro:\n{preview}")
        print("\n1. Use this intro")
        print("2. Customize intro")

        choice = self._get_choice(2)
        if choice == 2:
            print("\nEnter custom intro (HTML supported, or press Enter to edit the generated one):")
            custom = input("> ").strip()
            if custom:
                preview = custom
            else:
                print(f"\nCurrent: {preview}")
                print("Enter your edited version:")
                preview = input("> ").strip() or preview

        self.content['intro_text'] = preview
        print("\n✓ Intro text set")

    def _step_chart_of_week(self):
        """Step 4: Chart of the week."""
        print("\n[STEP 5/9] CHART OF THE WEEK")
        print("-" * 40)

        articles = self.content.get('featured_articles', [])
        if len(articles) >= 2:
            print("\nSelect source article for Chart of the Week:")
            print(f"  1. {articles[0]['title'][:60]}...")
            print(f"  2. {articles[1]['title'][:60]}...")
            print("  3. Skip chart of the week")

            choice = self._get_choice(3)
            if choice == 3:
                print("\n✓ Chart of the week skipped")
                return

            source_article = articles[choice - 1]
        elif len(articles) == 1:
            print(f"\nUsing featured article for chart: {articles[0]['title'][:60]}...")
            print("1. Continue with this article")
            print("2. Skip chart of the week")
            choice = self._get_choice(2)
            if choice == 2:
                print("\n✓ Chart of the week skipped")
                return
            source_article = articles[0]
        else:
            source_article = {"url": input("Enter article URL: ").strip()}

        # Chart title is fixed as "Chart of the week"
        chart_title = "Chart of the week"
        print(f"\nChart title: {chart_title}")

        # Get and validate chart image
        chart_image = ''
        while not chart_image:
            user_input = input("Enter chart image URL or local file path (will be uploaded to HubSpot): ").strip()
            if not user_input:
                print("  Chart image is required. Please enter a URL or file path.")
                continue
            chart_image = self._validate_image_url(user_input)
            if not chart_image:
                print("  Invalid URL or path. Please try again.")

        # Generate chart text
        chart_text = self.content_generator.generate_chart_text(
            chart_title,
            source_article.get('description', '')
        )

        print(f"\nGenerated intro: {chart_text['intro']}")
        print(f"Generated outro: {chart_text['outro']}")

        print("\n1. Use generated text")
        print("2. Customize text")

        choice = self._get_choice(2)
        if choice == 2:
            print("\nEnter custom intro text (or press Enter to keep generated):")
            custom_intro = input("> ").strip()
            if custom_intro:
                chart_text['intro'] = custom_intro
            print("\nEnter custom outro text (or press Enter to keep generated):")
            custom_outro = input("> ").strip()
            if custom_outro:
                chart_text['outro'] = custom_outro

        self.content['chart'] = {
            "title": chart_title,
            "intro_text": chart_text['intro'],
            "outro_text": chart_text['outro'],
            "image_url": chart_image,
            "article_url": source_article.get('url', '')
        }

        print("\n✓ Chart of the week configured")

    def _step_more_articles(self):
        """Step 5b: Additional articles after chart of the week."""
        print("\n[STEP 5b] MORE ARTICLES")
        print("-" * 40)
        print("Add more articles below the chart? These render in a compact inline list.")
        print("1. Yes, fetch and select articles")
        print("2. No, skip this section")

        if self._get_choice(2) == 2:
            print("\n✓ Skipped more articles")
            return

        region_config = self.REGION_CONFIG[self.selected_region]
        article_region = region_config['article_region']

        days_input = input("\nHow many days to look back? (default: 14): ").strip()
        more_days = int(days_input) if days_input.isdigit() and int(days_input) > 0 else 14

        print(f"\nFetching articles from the last {more_days} days...")
        articles = self.modo_scraper.get_articles(region=article_region, days=more_days, limit=20)

        # Exclude articles already selected as featured
        featured_slugs = {a.get('slug') for a in self.content.get('featured_articles', [])}
        articles = [a for a in articles if a.get('slug') not in featured_slugs]

        if not articles:
            print("No additional articles found.")
            return

        print(f"\nFound {len(articles)} articles (excluding featured):\n")
        for i, article in enumerate(articles, 1):
            date_raw = article.get('date', '')
            try:
                from datetime import datetime as _dt
                date_display = _dt.strptime(date_raw, "%Y-%m-%dT%H:%M:%S%z").strftime("%b %d, %Y")
            except (ValueError, TypeError):
                date_display = date_raw or 'Unknown'
            print(f"  {i}. {article['title']}")
            print(f"     {date_display}")

        print(f"\nSelect up to 10 articles (comma-separated, e.g., 1,3,5):")
        print("Or press Enter to skip:")
        selection = input("Your selection: ").strip()

        if not selection:
            print("\n✓ Skipped more articles")
            return

        try:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            selected = [articles[i] for i in indices[:10] if 0 <= i < len(articles)]
        except (ValueError, IndexError):
            print("Invalid selection. Skipping.")
            return

        if selected:
            self.content['more_articles'] = selected
            print(f"\n✓ {len(selected)} additional article{'s' if len(selected) > 1 else ''} selected")
        else:
            print("\n✓ No additional articles selected")

    def _step_promotional_banner(self):
        """Step 5: Promotional banner."""
        print("\n[STEP 6/9] PROMOTIONAL BANNER")
        print("-" * 40)

        print("\nInclude a promotional banner? (e.g., event, announcement)")
        print("1. Yes, add a banner")
        print("2. No, skip this section")

        choice = self._get_choice(2)
        if choice == 2:
            print("\n✓ Promotional banner skipped")
            return

        # Get and validate banner image
        image_url = ''
        while not image_url:
            user_input = input("\nEnter banner image URL or local file path: ").strip()
            if not user_input:
                print("  Banner image is required. Please enter a URL or file path.")
                continue
            image_url = self._validate_image_url(user_input)
            if not image_url:
                print("  Invalid URL or path. Please try again.")

        link_url = input("Enter banner link URL (e.g., https://example.com): ").strip()

        # Ensure link URL has protocol
        if link_url and not link_url.startswith(('http://', 'https://')):
            link_url = 'https://' + link_url

        alt_text = input("Enter alt text (e.g., 'E-World 2026'): ").strip()

        self.content['promotional_banner'] = {
            "image_url": image_url,
            "link": link_url,
            "alt_text": alt_text
        }

        # Allow review and edit
        print(f"\nBanner configured:")
        print(f"  Image: {image_url[:60]}..." if len(image_url) > 60 else f"  Image: {image_url}")
        print(f"  Link: {link_url[:60]}..." if len(link_url) > 60 else f"  Link: {link_url}")
        print(f"  Alt: {alt_text}")
        print("\n1. Confirm")
        print("2. Edit")

        if self._get_choice(2) == 2:
            print("\nEnter new values (press Enter to keep current):")
            new_image = input(f"  Image URL [{image_url[:40]}...]: ").strip()
            new_link = input(f"  Link URL [{link_url[:40]}...]: ").strip()

            # Ensure new link URL has protocol
            if new_link and not new_link.startswith(('http://', 'https://')):
                new_link = 'https://' + new_link

            new_alt = input(f"  Alt text [{alt_text}]: ").strip()

            self.content['promotional_banner'] = {
                "image_url": new_image or image_url,
                "link": new_link or link_url,
                "alt_text": new_alt or alt_text
            }

        print("\n✓ Promotional banner configured")

    def _step_news_section(self):
        """Step 6: This week's news."""
        print("\n[STEP 4/9] THIS WEEK'S NEWS")
        print("-" * 40)

        # Get default region from newsletter selection
        region_config = self.REGION_CONFIG[self.selected_region]
        default_news_region = region_config['news_region']
        default_region_name = region_config['name']

        # Map selected region to choice number for default
        region_to_choice = {"europe": 1, "us": 2, "australia": 3}
        default_choice = region_to_choice.get(default_news_region, 1)

        # Ask for region preference with default highlighted
        print(f"\nSelect news region focus (default: {default_region_name}):")
        print(f"  1. Europe (GB, Italy, Spain, Germany, Poland, Nordics){' (default)' if default_choice == 1 else ''}")
        print(f"  2. The US{' (default)' if default_choice == 2 else ''}")
        print(f"  3. Australia{' (default)' if default_choice == 3 else ''}")
        print("  4. Global")
        print("  5. Customize (select multiple regions)")
        print(f"\n  Press Enter to use default ({default_region_name}), or enter choice:")

        choice_input = input(f"  Choice (1-5) [{default_choice}]: ").strip()

        # Handle comma-separated input (e.g., "2,3") as custom selection
        if ',' in choice_input:
            region_choice = 5  # Treat as customize option
        else:
            try:
                region_choice = int(choice_input) if choice_input else default_choice
            except ValueError:
                print("Invalid input. Using default.")
                region_choice = default_choice

        if region_choice == 5 or ',' in choice_input:
            # Customize - let user select multiple regions
            print("\nSelect regions to include (comma-separated, e.g., 1,2,3):")
            print("  1. Europe")
            print("  2. US")
            print("  3. Australia")
            print("  4. Global")
            selection = input("Your selection: ").strip()
            try:
                indices = [int(x.strip()) for x in selection.split(',')]
                region_map_custom = {1: "europe", 2: "us", 3: "australia", 4: "global"}
                selected_regions = [region_map_custom[i] for i in indices if i in region_map_custom]
                selected_region = selected_regions if selected_regions else ["europe"]
            except (ValueError, KeyError):
                print("Invalid selection. Defaulting to Europe.")
                selected_region = "europe"
        else:
            region_map = {1: "europe", 2: "us", 3: "australia", 4: "global"}
            selected_region = region_map.get(region_choice, "europe")

        # Display region(s) being fetched
        if isinstance(selected_region, list):
            region_display = ", ".join(selected_region)
        else:
            region_display = selected_region
        print(f"\nFetching battery/energy storage news from the past 8 days ({region_display})...")

        # Fetch news - handle both single region and list of regions
        if isinstance(selected_region, list):
            news = []
            for region in selected_region:
                region_news = self.news_scraper.get_news(days=8, limit=10, region=region)
                news.extend(region_news)
            # Sort combined results by date
            news.sort(key=lambda x: x.get('date', ''), reverse=True)
        else:
            news = self.news_scraper.get_news(days=8, limit=20, region=selected_region)

        # Show fetched news first
        if news:
            # Show US news with ISO tags and duplicate detection
            show_isos = (self.selected_region == 'us')
            self._display_with_duplicate_warnings(news[:15], label="relevant news items", show_isos=show_isos)

            print("\n" + "-" * 40)
            print("Select items for the newsletter (comma-separated, e.g., 1,3,5)")
            print("Then you can add custom URLs if needed.")
            if show_isos:
                print("Tip: ISO tags help balance coverage across markets.")
            print("-" * 40)
            selection = input("\nYour selection (or press Enter to skip to custom): ").strip()

            selected_news = []
            if selection:
                try:
                    indices = [int(x.strip()) - 1 for x in selection.split(',')]
                    selected_news = [news[i] for i in indices if 0 <= i < len(news)]
                except (ValueError, IndexError):
                    print("Invalid selection.")

            # Always offer to add custom URLs
            print("\nWould you like to add custom news URLs?")
            print("  1. No, continue with selection")
            print("  2. Yes, add my own URLs")

            if self._get_choice(2) == 2:
                custom_news = self._fetch_custom_news_urls()
                selected_news = selected_news + custom_news  # Append custom to selection

            if selected_news:
                # Format for newsletter with region mentions and hyperlinks
                print("\nGenerating formatted news items with region context...")
                formatted = self._format_news_with_ai(selected_news)
                self.content['news_items'] = formatted

                # Show full preview with hyperlink indication
                print("\nPreview of news items:")
                print("-" * 60)
                for i, item in enumerate(formatted, 1):
                    full_text = item.get('formatted_text', f"{item['headline']}{item['body']}")
                    source = item.get('source', 'source')
                    url = item.get('url', '')
                    print(f"\n  {i}. {full_text}")
                    print(f"     [LINK: \"{source}\" -> {url[:50]}...]")
                print("\n" + "-" * 60)

                print("\n1. Accept these news items")
                print("2. Edit manually")

                if self._get_choice(2) == 2:
                    self._edit_news_items(formatted)
            else:
                print("No items selected. Enter news items manually.")
                self._manual_news_entry()
        else:
            print("No news found. Enter manually.")
            self._manual_news_entry()

        print(f"\n✓ {len(self.content.get('news_items', []))} news items configured")

    def _format_news_with_ai(self, articles: List[Dict]) -> List[Dict]:
        """Format news items with AI to add region context and proper structure."""
        formatted = []

        for article in articles[:4]:  # Max 4 news items
            title = article.get('title', '')
            description = article.get('description', '')
            url = article.get('url', '')
            source = article.get('source', '')
            region = article.get('region', 'global')

            # Determine region/country prefix
            region_prefixes = {
                'europe': 'In Europe',
                'uk': 'In the UK',
                'gb': 'In Great Britain',
                'germany': 'In Germany',
                'spain': 'In Spain',
                'italy': 'In Italy',
                'france': 'In France',
                'us': 'In the US',
                'australia': 'In Australia',
                'global': ''
            }

            # Try to detect specific country from source or title
            country_detected = None
            # IMPORTANT: Check Australia BEFORE UK to avoid 'wales' matching 'New South Wales'
            country_keywords = {
                'australia': ['australia', 'australian', 'nem', 'wem', 'aemo', 'queensland', 'new south wales', 'nsw', 'victoria', 'south australia', 'western australia', 'tasmania'],
                'germany': ['german', 'germany', 'deutschland'],
                'uk': ['uk', 'british', 'britain', 'england', 'scotland', 'wales'],
                'spain': ['spain', 'spanish', 'españa'],
                'italy': ['italy', 'italian', 'italia'],
                'france': ['france', 'french'],
                'us': ['us', 'usa', 'american', 'united states', 'california', 'texas', 'ercot', 'caiso', 'miso']
            }

            # Only check title and description for region, not source (to avoid tagging by publisher location)
            combined_text = (title + ' ' + description).lower()
            for country, keywords in country_keywords.items():
                # Use word boundaries to avoid false matches (e.g., "us" in "focus", "business")
                if any(re.search(r'\b' + re.escape(kw) + r'\b', combined_text) for kw in keywords):
                    country_detected = country
                    break

            # Get the region prefix, but skip it if it matches the newsletter's selected region
            detected_region = country_detected or region
            region_prefix = region_prefixes.get(detected_region, '')

            # Don't add prefix if the news region matches the newsletter region
            if detected_region == self.selected_region:
                region_prefix = ''

            # Try to use AI to format if available
            if self.content_generator.client:
                try:
                    formatted_item = self.content_generator.format_news_item(
                        title=title,
                        description=description,
                        url=url,
                        source=source,
                        region_prefix=region_prefix
                    )
                    formatted.append(formatted_item)
                    continue
                except Exception as e:
                    print(f"    AI formatting failed, using fallback: {e}")

            # Fallback formatting
            if region_prefix:
                headline = f"{region_prefix}, {title}"
            else:
                headline = title

            # Create body text (no separate "Read more" link)
            body_text = f", {description}" if description else "."

            # Wrap headline in hyperlink
            headline_with_link = f'<a href="{url}" style="color:#000000; text-decoration:none; font-weight:bold;">{headline}</a>'

            formatted.append({
                "headline": headline_with_link,
                "body": body_text,
                "url": url,
                "source": source,
                "formatted_text": f"{headline}{body_text}"
            })

        return formatted

    def _edit_news_items(self, items: List[Dict]):
        """Allow manual editing of formatted news items."""
        print("\nEdit news items (press Enter to keep current):")

        for i, item in enumerate(items):
            print(f"\n--- Item {i + 1} ---")
            print(f"Current: {item.get('headline', '')}{item.get('body', '')[:50]}...")

            new_headline = input(f"  New headline (Enter to keep): ").strip()
            if new_headline:
                # Wrap new headline in hyperlink
                url = item.get('url', '')
                item['headline'] = f'<a href="{url}" style="color:#000000; text-decoration:none; font-weight:bold;">{new_headline}</a>'

            new_body = input(f"  New body text (Enter to keep): ").strip()
            if new_body:
                item['body'] = new_body

        self.content['news_items'] = items

    def _fetch_custom_news_urls(self) -> List[Dict]:
        """Fetch and summarize custom news URLs provided by user."""
        custom_news = []
        print("\nEnter custom news URLs (one per line, empty line to finish):")
        print("The agent will fetch and summarize each article automatically.\n")

        while True:
            url = input("  URL (or Enter to finish): ").strip()
            if not url:
                break

            print("    Fetching and summarizing...")
            article = self.news_scraper.fetch_custom_url(url)

            if article:
                print(f"    ✓ Found: {article['title'][:50]}...")
                # Ask for region if not auto-detected
                if article.get('region') == 'global':
                    print("    Which region is this news from?")
                    print("      1. Europe  2. UK  3. Germany  4. US  5. Australia  6. Global")
                    region_choice = input("      Region (1-6, or Enter for Global): ").strip()
                    region_map = {'1': 'europe', '2': 'uk', '3': 'germany', '4': 'us', '5': 'australia', '6': 'global'}
                    article['region'] = region_map.get(region_choice, 'global')
                custom_news.append(article)
            else:
                print("    ✗ Could not fetch article. Enter details manually?")
                print("    1. Yes, enter manually")
                print("    2. No, skip this URL")
                if self._get_choice(2) == 1:
                    title = input("      Title: ").strip()
                    description = input("      Description: ").strip()
                    print("      Which region? (1. Europe  2. UK  3. Germany  4. US  5. Australia  6. Global)")
                    region_choice = input("      Region (1-6): ").strip()
                    region_map = {'1': 'europe', '2': 'uk', '3': 'germany', '4': 'us', '5': 'australia', '6': 'global'}
                    custom_news.append({
                        "title": title,
                        "description": description,
                        "url": url,
                        "source": "Custom",
                        "date": "",
                        "category": "custom",
                        "region": region_map.get(region_choice, 'global')
                    })

        return custom_news

    def _manual_news_entry(self):
        """Manually enter news items."""
        news_items = []
        print("\nEnter news items (empty headline to finish):")
        print("Format: Bold headline first, then the rest of the paragraph.")
        print("Example:")
        print("  Headline: Gresham House has completed its merger with SUSI Partners")
        print("  Body: , creating a £2.7 billion energy transition investment platform. The combined entity is launching a new global energy storage strategy in 2026.")

        while len(news_items) < 5:
            headline = input(f"\n  News {len(news_items) + 1} headline (bold part, or Enter to finish): ").strip()
            if not headline:
                break
            print("  Body (rest of paragraph, can be multiple sentences):")
            body = input("  > ").strip()
            news_items.append({
                "headline": headline,
                "body": body if body.startswith(',') or body.startswith('.') else f", {body}"
            })

        self.content['news_items'] = news_items

    def _step_podcast(self):
        """Step 7: Podcast section."""
        print("\n[STEP 7/9] PODCAST SECTION")
        print("-" * 40)

        print("\nFetching recent Transmission podcast episodes...")
        episodes = self.youtube_scraper.get_recent_episodes(limit=4)

        if episodes:
            print(f"\nFound {len(episodes)} recent episodes:\n")
            for i, ep in enumerate(episodes, 1):
                # Parse guest info for display
                guest_info_preview = self.youtube_scraper.parse_guest_info(ep['title'])
                guest_name = guest_info_preview.get('guest_name', '')
                guest_display = f" - {guest_name}" if guest_name else ""
                print(f"  {i}. {ep['title'][:55]}...{guest_display}")

            print(f"  {len(episodes) + 1}. Enter manually")

            choice = self._get_choice(len(episodes) + 1)

            if choice <= len(episodes):
                episode = episodes[choice - 1]
                print(f"\n✓ Selected: {episode['title']}")
            else:
                episode = {
                    "title": input("\nEpisode title: ").strip(),
                    "url": input("YouTube URL: ").strip(),
                    "thumbnail": input("Thumbnail URL or local path: ").strip()
                }

            # Parse guest info from selected episode
            guest_info = self.youtube_scraper.parse_guest_info(episode['title'])

            # Try to get additional details from video description
            if episode.get('video_id'):
                desc_details = self.youtube_scraper.parse_guest_details_from_description(episode['video_id'])
                if desc_details:
                    guest_info.update(desc_details)

            print(f"\n  Parsed from YouTube:")
            print(f"    Guest: {guest_info.get('guest_name', 'Not found')}")
            if guest_info.get('guest_role'):
                print(f"    Role: {guest_info.get('guest_role')}")
            if guest_info.get('company'):
                print(f"    Company: {guest_info.get('company')}")
            print(f"    Topic: {guest_info.get('topic', 'Unknown')}")
        else:
            print("Could not fetch episodes. Enter manually.")
            episode = {
                "title": input("Episode title: ").strip(),
                "url": input("YouTube URL: ").strip(),
                "thumbnail": input("Thumbnail URL or local path: ").strip()
            }
            guest_info = {"guest_name": "", "topic": episode['title']}

        # Select moderator/host
        print("\nWho is the moderator for this episode?")
        print("  1. Ed (default)")
        print("  2. Other (enter name)")

        moderator_choice = input("  Choice (1-2) [1]: ").strip()
        if moderator_choice == "2":
            moderator = input("  Enter moderator name: ").strip() or "Ed"
        else:
            moderator = "Ed"

        print(f"  ✓ Moderator: {moderator}")

        # Confirm/edit guest details
        print("\nConfirm guest details (press Enter to accept suggested values):")
        guest_name = input(f"  Guest name [{guest_info.get('guest_name', '')}]: ").strip() or guest_info.get('guest_name', '')
        guest_role = input(f"  Guest role [{guest_info.get('guest_role', '')}]: ").strip() or guest_info.get('guest_role', '')
        company = input(f"  Company [{guest_info.get('company', '')}]: ").strip() or guest_info.get('company', '')
        guest_linkedin = input("  Guest LinkedIn URL: ").strip()
        company_linkedin = input("  Company LinkedIn URL: ").strip()

        # Use YouTube thumbnail automatically
        thumbnail = self._validate_image_url(episode.get('thumbnail', ''))
        if thumbnail:
            print(f"\n  ✓ Using YouTube thumbnail: {thumbnail[:60]}...")
            print("    (Enter custom URL/path to override, or press Enter to keep)")
            custom_thumb = input("    Custom thumbnail: ").strip()
            if custom_thumb:
                validated = self._validate_image_url(custom_thumb)
                if validated:
                    thumbnail = validated
                else:
                    print("    Keeping YouTube thumbnail instead.")
        else:
            print("\n  No YouTube thumbnail found.")
            while not thumbnail:
                user_input = input("  Thumbnail URL or local path: ").strip()
                if not user_input:
                    print("    Thumbnail is required. Please enter a URL or file path.")
                    continue
                thumbnail = self._validate_image_url(user_input)
                if not thumbnail:
                    print("    Invalid URL or path. Please try again.")

        # Generate combined description (intro + extended in one step)
        print("\nGenerating podcast description...")
        description = self.content_generator.generate_podcast_description(
            guest_name=guest_name,
            guest_role=guest_role,
            company=company,
            topic=guest_info.get('topic', episode['title']),
            moderator=moderator
        )

        # Add LinkedIn links (bold only, no underline)
        if guest_linkedin:
            description = description.replace(
                f"<strong>{guest_name}</strong>",
                f'<a href="{guest_linkedin}" style="color:#000000; text-decoration:none; font-weight:bold;">{guest_name}</a>'
            )
        if company_linkedin:
            description = description.replace(
                f"<strong>{company}</strong>",
                f'<a href="{company_linkedin}" style="color:#000000; text-decoration:none; font-weight:bold;">{company}</a>'
            )

        # Show generated and ask for optional extended description in one step
        print(f"\nGenerated description:\n  {description}")
        print("\nOptions:")
        print("  1. Use as-is")
        print("  2. Add extended description (2-3 more sentences)")
        print("  3. Replace with custom description")

        choice = self._get_choice(3)

        if choice == 2:
            print("\nEnter extended description (what topics are discussed):")
            print("Example: As battery portfolios scale, the challenge shifts from hardware to software.")
            extended_desc = input("> ").strip()
            if extended_desc:
                description = f"{description}</p><p style=\"Margin:16px 0 0 0; font-size:15px; line-height:1.6; color:#000000; font-family:Arial,sans-serif;\">{extended_desc}"

        elif choice == 3:
            print("\nEnter complete custom description (HTML supported):")
            description = input("> ").strip()

        self.content['podcast'] = {
            "title": episode['title'],
            "url": episode['url'],
            "thumbnail": thumbnail,
            "description": description
        }

        print("\n✓ Podcast section configured")

    def _step_world_articles(self):
        """Step 8: More from around the world."""
        print("\n[STEP 8/9] MORE FROM AROUND THE WORLD")
        print("-" * 40)

        # Adjustable day filter
        days_input = input("\nHow many days to look back? (default: 14): ").strip()
        world_days = int(days_input) if days_input.isdigit() and int(days_input) > 0 else 14

        # Determine which articles to show based on selected region
        if self.selected_region == "europe":
            # Europe edition: show US/Australia articles
            print("(Articles from US, Australia - NEM, WEM, MISO, ERCOT, CAISO)")
            print(f"\nFetching non-Europe articles from the last {world_days} days...")
            articles = self.modo_scraper.get_non_europe_articles(days=world_days, limit=10)
            world_label = "non-Europe"
        elif self.selected_region == "us":
            # US edition: show Europe and Australia articles
            print("(Articles from Europe and Australia - GB, Germany, Spain, NEM, WEM)")
            print(f"\nFetching Europe & Australia articles from the last {world_days} days...")
            articles = self.modo_scraper.get_articles(region="gb_europe", days=world_days, limit=10)
            # Also get Australia articles
            aus_articles = self.modo_scraper.get_articles(region="australia", days=world_days, limit=5)
            articles = articles + aus_articles
            world_label = "Europe & Australia"
        else:
            # Australia edition: show Europe and US articles
            print("(Articles from Europe and US - GB, Germany, ERCOT, MISO, CAISO)")
            print(f"\nFetching Europe & US articles from the last {world_days} days...")
            articles = self.modo_scraper.get_articles(region="gb_europe", days=world_days, limit=10)
            world_label = "Europe & US"

        if articles:
            print(f"\nFound {len(articles)} {world_label} articles:\n")
            for i, article in enumerate(articles[:10], 1):
                region_tag = article.get('detected_region', 'unknown').upper()
                print(f"  {i}. [{region_tag}] {article['title'][:55]}...")

            print("\nSelect 3 articles (comma-separated, e.g., 1,2,3):")
            print("Or enter 'manual' to enter articles manually:")
            selection = input("Your selection: ").strip()

            if selection.lower() == 'manual':
                selected = self._manual_world_article_entry(count=3)
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in selection.split(',')]
                    selected = [articles[i] for i in indices[:3] if 0 <= i < len(articles)]
                except (ValueError, IndexError):
                    print("Invalid selection. Using first 3.")
                    selected = articles[:3]
        else:
            print("No articles found from scraper. Enter manually.")
            selected = self._manual_world_article_entry(count=3)

        # Check if all articles have thumbnails
        missing_thumbs = [a for a in selected if not a.get('thumbnail_url') or a.get('thumbnail_url') == 'None']

        if missing_thumbs:
            print(f"\n{len(missing_thumbs)} article(s) missing thumbnails. Please provide:")
            for article in missing_thumbs:
                print(f"\n  {article['title'][:50]}...")
                thumb = input("  Thumbnail URL or local path: ").strip()
                if thumb:
                    article['thumbnail_url'] = thumb
        else:
            print("\n✓ All thumbnails found from Modo Terminal")
            print("\nWould you like to customize any thumbnails?")
            print("  1. No, use scraped thumbnails")
            print("  2. Yes, customize")

            if self._get_choice(2) == 2:
                for i, article in enumerate(selected, 1):
                    current_thumb = article.get('thumbnail_url', 'None')
                    print(f"\n  {i}. {article['title'][:40]}...")
                    print(f"     Current: {current_thumb[:60]}..." if len(current_thumb) > 60 else f"     Current: {current_thumb}")
                    custom = input(f"     New URL/path (Enter to keep): ").strip()
                    if custom:
                        article['thumbnail_url'] = custom

        self.content['world_articles'] = selected
        print("\n✓ World articles configured")

    def _manual_world_article_entry(self, count: int = 3) -> List[Dict]:
        """Manually enter world articles (title, URL, thumbnail only - no description needed)."""
        articles = []
        print(f"\nEnter {count} articles (title, URL, and thumbnail):")
        for i in range(count):
            print(f"\nArticle {i + 1}:")
            title = input("  Title: ").strip()
            if not title:
                break
            url = input("  URL: ").strip()
            thumbnail = input("  Thumbnail URL: ").strip()

            articles.append({
                "title": title,
                "url": url,
                "thumbnail_url": thumbnail
            })

        return articles

    def _step_assemble(self):
        """Step 9: Assemble and output."""
        print("\n[STEP 9/9] ASSEMBLING NEWSLETTER")
        print("-" * 40)

        html = self.assembler.assemble(self.content)
        metadata = self.assembler.get_email_metadata(self.content)

        # Output to file
        output_dir = Path(__file__).parent / 'output'
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'newsletter_{timestamp}.html'

        output_file.write_text(html)

        print(f"\n✓ Newsletter saved to: {output_file}")
        print(f"\n  Subject: {metadata['subject']}")
        print(f"  Preview: {metadata['preview_text'][:100]}...")

        # Also save metadata
        meta_file = output_dir / f'newsletter_{timestamp}_meta.txt'
        meta_file.write_text(f"Subject: {metadata['subject']}\n\nPreview Text: {metadata['preview_text']}")

        print(f"\n  Metadata saved to: {meta_file}")
        
        # Browser preview option
        print("\nPreview in browser?")
        print("1. Yes, open preview")
        print("2. No, continue")
        
        if self._get_choice(2) == 1:
            self._preview_in_browser(output_file)

        # HubSpot publishing - returns updated HTML with HubSpot image URLs
        final_html = self._step_hubspot_publish(html, metadata)

        # If HubSpot was used and returned updated HTML, use that; otherwise use original
        if final_html:
            html = final_html
            # Verify the HTML has HubSpot URLs
            hubspot_url_count = html.count('hubspotusercontent')
            modoenergy_url_count = html.count('modoenergy.com/post_images')
            local_path_count = html.count('/Users/')
            print(f"\n✓ Using HTML with HubSpot-hosted image URLs")
            print(f"  - HubSpot URLs found: {hubspot_url_count}")
            print(f"  - modoenergy.com URLs remaining: {modoenergy_url_count}")
            print(f"  - Local file paths remaining: {local_path_count}")

        # Copy final HTML to clipboard
        print("\nCopy final HTML to clipboard?")
        print("1. Yes (recommended)")
        print("2. No")

        choice = self._get_choice(2)
        if choice == 1:
            try:
                import subprocess
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                process.communicate(html.encode('utf-8'))
                print("\n✓ HTML copied to clipboard!")
            except Exception as e:
                print(f"\nCould not copy to clipboard: {e}")

    def _step_hubspot_publish(self, html: str, metadata: Dict) -> str:
        """Optional: Publish newsletter to HubSpot.

        Returns:
            Updated HTML with HubSpot image URLs, or None if skipped/failed
        """
        if not HUBSPOT_AVAILABLE:
            print("\n[HubSpot integration not available]")
            return None

        print("\n" + "-" * 40)
        print("HUBSPOT PUBLISHING")
        print("-" * 40)

        print("\nPublish to HubSpot?")
        print("1. Yes, upload images and create email draft")
        print("2. Yes, create email draft only (keep existing image URLs)")
        print("3. No, skip HubSpot")

        choice = self._get_choice(3)

        if choice == 3:
            print("\n✓ HubSpot publishing skipped")
            return None

        try:
            hubspot = HubSpotIntegration()

            # Set region-specific settings
            region_config = self.REGION_CONFIG.get(self.selected_region, {})
            hubspot.settings['include_lists'] = region_config.get('include_lists', [])
            hubspot.settings['exclude_lists'] = region_config.get('exclude_lists', [])
            hubspot.settings['exclude_emails'] = region_config.get('exclude_emails', [])
            hubspot.settings['from_name'] = region_config.get('from_name', hubspot.settings['from_name'])
            hubspot.settings['from_email'] = region_config.get('from_email', hubspot.settings['from_email'])
            hubspot.settings['image_folder'] = region_config.get('image_folder', hubspot.settings['image_folder'])

            upload_images = (choice == 1)

            result = hubspot.publish_newsletter(
                html=html,
                content=self.content,
                subject=metadata['subject'],
                preview_text=metadata['preview_text'],
                upload_images=upload_images
            )

            if result:
                print(f"\n✓ Email draft created in HubSpot!")
                print(f"  Email ID: {result.get('id')}")
                
                # Send Slack notification
                if self.SLACK_WEBHOOK_URL:
                    self._send_slack_notification(
                        subject=metadata['subject'],
                        hubspot_id=result.get('id')
                    )
                
                # Return the updated HTML with HubSpot image URLs
                return result.get('_updated_html', html)
            else:
                print("\n✗ Failed to publish to HubSpot")
                return None

        except FileNotFoundError as e:
            print(f"\n✗ HubSpot credential not found: {e}")
            print("  Run: python3 ~/Desktop/save_hubspot_credential.py")
        except Exception as e:
            print(f"\n✗ HubSpot error: {e}")

    def _select_items(self, items: List[Dict], count: int, prompt: str) -> List[Dict]:
        """Let user select items from a list."""
        print(f"\n{prompt} (comma-separated numbers, e.g., 1,3):")
        selection = input("Your selection: ").strip()

        try:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            selected = [items[i] for i in indices[:count] if 0 <= i < len(items)]
            return selected
        except (ValueError, IndexError):
            print("Invalid selection. Using first items.")
            return items[:count]

    def _manual_article_entry(self, count: int = 2) -> List[Dict]:
        """Manually enter articles."""
        articles = []
        for i in range(count):
            print(f"\nArticle {i + 1}:")
            title = input("  Title: ").strip()
            url = input("  URL: ").strip()
            description = input("  Description: ").strip()
            thumbnail = input("  Thumbnail URL: ").strip()

            articles.append({
                "title": title,
                "url": url,
                "description": description,
                "thumbnail_url": thumbnail
            })

        return articles

    def _get_choice(self, max_choice: int) -> int:
        """Get a numeric choice from user."""
        while True:
            try:
                choice = int(input(f"\nEnter choice (1-{max_choice}): ").strip())
                if 1 <= choice <= max_choice:
                    return choice
            except ValueError:
                pass
            print(f"Please enter a number between 1 and {max_choice}")


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description='Weekly Dispatch Newsletter Agent')
    parser.add_argument('--preview', action='store_true', help='Dry run with dummy content')
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
    args = parser.parse_args()
    
    agent = NewsletterAgent(dry_run=args.preview, resume=args.resume)
    agent.run()


if __name__ == "__main__":
    main()
