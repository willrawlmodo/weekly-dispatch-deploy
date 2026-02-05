# Weekly Dispatch Newsletter — GUI Project

## Project Overview

This is the **Modo Energy Weekly Dispatch** newsletter generator. It currently runs as an interactive CLI (`main.py`) with a 9-step wizard that scrapes articles, generates AI content, assembles HTML email templates, and publishes to HubSpot.

The `/gui` directory contains a **web-based GUI** replacement built with FastAPI (backend) + vanilla HTML/CSS/JS (frontend). The GUI wraps the same underlying Python modules — it does NOT rewrite the pipeline, it exposes it through a browser interface.

## Architecture

```
weekly-dispatch-usa/
├── main.py                    # Original CLI agent (reference only, don't modify)
├── assembler.py               # HTML template assembler (IMPORT THIS)
├── scrapers/
│   ├── modo_articles.py       # Modo Terminal article scraper (IMPORT THIS)
│   ├── news_sources.py        # RSS news aggregator (IMPORT THIS)
│   └── youtube_podcast.py     # YouTube podcast scraper (IMPORT THIS)
├── generators/
│   └── content_generator.py   # OpenAI content generator (IMPORT THIS)
├── integrations/
│   └── hubspot.py             # HubSpot publishing (IMPORT THIS)
├── templates/                 # HTML email templates (used by assembler.py)
├── output/                    # Generated newsletter HTML files
├── config/
│   └── sources.json           # RSS feed source configuration
├── gui/
│   ├── app.py                 # FastAPI backend — API endpoints for each step
│   ├── state.py               # Session state manager
│   ├── requirements.txt       # GUI-specific dependencies
│   └── static/
│       ├── index.html         # Main GUI page — step wizard
│       ├── app.js             # Frontend logic — API calls, state, rendering
│       └── styles.css         # Styling
└── CLAUDE.md                  # THIS FILE
```

## Key Design Principles

1. **Wrap, don't rewrite.** Import classes from `scrapers/`, `generators/`, `integrations/`, and `assembler.py` directly. The GUI is a presentation layer over the existing pipeline.

2. **Step-by-step wizard.** The GUI mirrors the CLI's 9 steps as a left sidebar with progress indicators. Each step is a panel with form fields, selection cards, and preview areas.

3. **Live HTML preview.** The right side of the GUI shows a live preview of the assembled newsletter, re-rendered after each step via the `/api/preview` endpoint.

4. **Session state.** All state lives in a server-side `SessionState` object (equivalent to the CLI's `self.content` dict). The frontend fetches and updates state via API calls.

5. **No build step.** The frontend is vanilla HTML/CSS/JS served as static files by FastAPI. No npm, no webpack, no React build. This keeps iteration fast.

## Region Configuration

The newsletter supports 3 regions, each with different:
- Header banner images
- Article source filters (ISO market codes)
- HubSpot mailing lists, sender name/email
- News region defaults

Region config is defined in `main.py`'s `NewsletterAgent.REGION_CONFIG` dict. The GUI backend copies this configuration.

## Content Pipeline (9 Steps)

| Step | Name | Backend Module | What It Does |
|------|------|---------------|--------------|
| 0 | Region | state.py | Select US/Europe/Australia — sets all downstream defaults |
| 1 | Featured Articles | scrapers/modo_articles.py | Scrape Modo Terminal, user picks 1-3 articles |
| 2 | Subject Line | generators/content_generator.py | AI generates 15 options from article themes |
| 3 | Intro Text | generators/content_generator.py | AI generates intro paragraph with hyperlinks |
| 4 | News Section | scrapers/news_sources.py | RSS scrape + AI formatting of 3-4 news blurbs |
| 5 | Chart of Week | generators/content_generator.py | User provides image, AI generates intro/outro text |
| 6 | Promo Banner | (user input only) | Optional banner image + link |
| 7 | Podcast | scrapers/youtube_podcast.py | YouTube scrape + AI description generation |
| 8 | World Articles | scrapers/modo_articles.py | Scrape other-region articles, user picks 3 |
| 9 | Assemble | assembler.py + integrations/hubspot.py | Build HTML, preview, publish to HubSpot |

## API Endpoint Pattern

Every step follows this pattern:
```
GET  /api/step/{n}/data    → Fetch scraped/generated options for display
POST /api/step/{n}/select  → Save user's selections to session state
GET  /api/preview          → Re-assemble and return current HTML preview
```

## Environment Variables

Required in `.env` at project root:
- `OPENAI_API_KEY` — For content generation (subject lines, intros, chart text, podcast descriptions)
- `HUBSPOT_API_KEY` — For publishing drafts (optional, Step 9 only)
- `SLACK_WEBHOOK_URL` — For notifications (optional)

## Running the GUI

```bash
cd weekly-dispatch-usa
pip install -r gui/requirements.txt
python -m gui.app
```

Opens at `http://localhost:8000`

## Coding Conventions

- Python 3.10+ (match statements OK)
- Type hints on all function signatures
- Docstrings on all public methods
- Frontend: ES6+, no jQuery, fetch API for HTTP calls
- CSS: CSS custom properties for theming, no CSS framework
- Error handling: All API endpoints return `{"error": "message"}` on failure with appropriate HTTP status codes

## Common Tasks for Claude Code

### Adding a new step
1. Add endpoint in `gui/app.py`
2. Add panel in `gui/static/index.html`
3. Add API call + render logic in `gui/static/app.js`
4. Update step count in sidebar

### Fixing AI generation
- All AI prompts are in `generators/content_generator.py`
- The GUI doesn't change prompts — it just calls the same methods

### Changing email templates
- HTML templates are in `templates/*.html`
- The assembler uses `str.format()` for variable substitution
- Preview re-renders via `assembler.assemble(content)`

### Debugging scraper issues
- Scrapers are in `scrapers/` — each has a `main()` test function
- Run directly: `python -m scrapers.modo_articles`
