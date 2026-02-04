# Modo Energy Weekly Dispatch - Newsletter Agent

An interactive CLI tool to generate the **Weekly Dispatch: Europe & GB Edition** newsletter. The agent automates content collection, AI-powered text generation, and HTML assembly for HubSpot.

## What It Does

1. **Scrapes Modo Terminal** for recent GB/Europe articles
2. **Fetches podcast episodes** from the Transmission YouTube playlist
3. **Aggregates energy news** from industry RSS feeds (Energy Storage News, PV Magazine, Current±, etc.)
4. **Generates AI content** using OpenAI (subject lines, intro text, chart descriptions, podcast descriptions)
5. **Assembles Outlook-compatible HTML** email from templates
6. **Uploads images to HubSpot** File Manager (supports local files and URLs)
7. **Creates email draft** in HubSpot with pre-configured subscriber lists

## Prerequisites

### Required Software
- Python 3.9+
- pip (Python package manager)

### Required API Keys
1. **OpenAI API Key** - For AI-generated content
2. **HubSpot Private App Token** - For image uploads and email creation

## Installation

1. **Clone or copy the project folder**
   ```bash
   cd /path/to/newsletter-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=sk-your-openai-key-here
   ```

4. **Set up HubSpot credentials**

   Save your HubSpot token to `~/Desktop/hubspot-credential`:
   ```bash
   echo "your-hubspot-token-here" > ~/Desktop/hubspot-credential
   ```

## HubSpot Setup

### Required API Scopes
Your HubSpot private app must have these scopes enabled:

| Scope | Purpose |
|-------|---------|
| `file-manager-write` | Upload images to File Manager |
| `content` | Create marketing email drafts |
| `crm.lists.read` | Look up subscriber lists by name |

### How to Enable Scopes
1. Go to **HubSpot Settings → Integrations → Private Apps**
2. Find your app and click **Edit**
3. Go to **Scopes** tab
4. Enable:
   - CMS > Files (write)
   - Marketing > Marketing Email (all)
   - CRM > Lists (read)
5. Save changes and copy the new token

### Pre-configured Lists
The agent is set up to send to these lists by default:
- July GB/Europe livestream registrants
- EU contacts [ALL] (Neil's Dispatch list)
- Germany/Spain/GB livestream signups
- Madrid Workshops Guest Lists
- Weekly Newsletter - Great Britain
- Contacts from Company with LIVE GB & Europe Research Deals

And excludes:
- Opted out of weekly newsletter
- GB Weekly Roundup Did Not Sends
- Marketing suppression list

## Usage

### Run the Agent
```bash
python main.py
```

### Workflow Steps
The agent guides you through 9 steps:

1. **Featured Articles** - Select 1-3 articles from Modo Terminal
2. **Subject Line** - Choose from 15 AI-generated suggestions
3. **Intro Paragraph** - Review/edit AI-generated intro with hyperlinks
4. **Chart of the Week** - Add chart image and generated descriptions
5. **Promotional Banner** - Optional banner (e.g., events, announcements)
6. **This Week's News** - Select from aggregated industry news or add custom URLs
7. **Podcast Section** - Auto-fetches latest episode, generates description
8. **World Articles** - 3 articles from US/Australia regions
9. **Assemble & Publish** - Generate HTML, optionally upload to HubSpot

### What to Have Ready
Before starting, prepare:
- Chart of the Week image
- Promotional banner image (if applicable)
- Podcast guest LinkedIn URLs (can look up during the session)

**Auto-fetched (no preparation needed):**
- Article thumbnails are scraped from Modo Terminal (`og:image`)
- Podcast thumbnail is fetched from YouTube
- Podcast guest name/role/company are parsed from YouTube

**Note:** Local file paths are automatically uploaded to HubSpot's "European Weekly Dispatch" folder.

## Project Structure

```
newsletter-agent/
├── main.py                    # Main CLI workflow
├── assembler.py               # HTML assembly from templates
├── requirements.txt           # Python dependencies
├── .env                       # API keys (create this)
│
├── scrapers/
│   ├── modo_articles.py       # Modo Terminal article scraper
│   ├── youtube_podcast.py     # YouTube podcast fetcher
│   └── news_sources.py        # RSS news aggregator
│
├── generators/
│   └── content_generator.py   # OpenAI content generation
│
├── integrations/
│   └── hubspot.py             # HubSpot API integration
│
├── templates/                 # HTML email templates
│   ├── header.html
│   ├── intro.html
│   ├── article_card.html
│   ├── article_card_half.html # Side-by-side layout
│   ├── chart_of_week.html
│   ├── promotional_banner.html
│   ├── news_section.html
│   ├── news_item.html
│   ├── podcast.html
│   ├── more_from_world.html
│   ├── world_article_item.html
│   └── footer.html
│
└── output/                    # Generated newsletters (auto-created)
```

## Output

The agent produces:
- **HTML file**: `output/newsletter_YYYYMMDD_HHMMSS.html`
- **Metadata file**: `output/newsletter_YYYYMMDD_HHMMSS_meta.txt`
- **HubSpot draft**: Email draft in Marketing > Email (if published)

## Troubleshooting

### HubSpot 403 Errors
```
Requires scope(s): [file-manager-write]
```
**Solution:** Regenerate your HubSpot token with the required scopes (see HubSpot Setup above).

### Local Path Not Found
```
Invalid URL "'/path/to/file.png'": No scheme supplied
```
**Solution:** The agent now handles quoted paths. Just paste the path normally.

### OpenAI Errors
```
Error generating subject: ...
```
**Solution:** Check your `OPENAI_API_KEY` in `.env` is valid and has credits.

### No Articles Found
The Modo Terminal uses dynamic loading. If scraping fails, you can enter articles manually when prompted.

## Customization

### Adding News Sources
Edit `scrapers/news_sources.py` and add to the appropriate region in `_get_default_sources()`:
```python
{
    "name": "Source Name",
    "rss": "https://example.com/feed/",
    "category": "industry",
    "region": "europe"  # or "global", "us", "australia"
}
```

### Modifying Email Lists
Edit `integrations/hubspot.py` and update `DEFAULT_SETTINGS`:
```python
"include_lists": [...],
"exclude_lists": [...]
```

### Changing Templates
Edit HTML files in `templates/` folder. Use placeholders like `{article_title}` that match the assembler's `.format()` calls.

## Support

For issues or questions, contact the team or check the code comments for implementation details.
