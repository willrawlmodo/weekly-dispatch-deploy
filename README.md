# Weekly Dispatch - US Edition

*Last updated: February 4, 2026*

Forked from the Modo Energy Weekly Dispatch newsletter tool, customized for North American markets.

## Markets Covered

- **ERCOT** (Texas)
- **MISO** (Midwest)
- **CAISO** (California)
- **PJM** (Mid-Atlantic/Midwest)
- **NYISO** (New York)
- **ISO-NE** (New England)
- **SPP** (Southwest Power Pool)

## Setup

### 1. Install Dependencies
```bash
cd /Users/williamrawlings/Documents/GitHub/weekly-dispatch-usa
pip install -r requirements.txt
```

### 2. Configure API Keys

**OpenAI** (already configured in `.env`):
```
OPENAI_API_KEY=your-key-here
```

**HubSpot** (already configured at `~/Desktop/hubspot-credential`):
```
pat-eu1-xxxx-xxxx-xxxx
```

### 3. Configure Slack (Optional)
Set environment variables for Slack notifications when HubSpot drafts are created:
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/xxx/xxx/xxx"
export SLACK_CHANNEL="#weekly-dispatch"
```

To create a webhook:
1. Go to api.slack.com/apps → Create New App
2. Add "Incoming Webhooks" feature
3. Activate and create webhook for your channel

### 4. Run the Agent
```bash
python3 main.py           # Normal interactive mode
python3 main.py --preview  # Dry run with dummy content
python3 main.py --resume   # Resume from last checkpoint
```

## Customizations from European Version

### Region Selection
- Defaults to **US** (press Enter to accept)
- Lists all 7 covered ISOs upfront

### News Sources (US-Focused)
- Utility Dive
- PV Magazine USA
- Solar Power World
- Canary Media
- Energy Storage News (global)
- E&E News (policy)
- CleanTechnica
- Electrek

### Subject Line Examples (US Market Themes)
- "ERCOT's interconnection queue hits 200 GW"
- "Winter storm tests Texas grid resilience"
- "MISO capacity auction clears at record highs"
- "CAISO curtailment reaches new peaks"
- "PJM queue reforms reshape developer strategy"
- "FERC Order 2023 accelerates storage deployment"
- "IRA incentives reshape project economics"

### Article Detection Keywords
Expanded US keywords including:
- All 7 ISOs/RTOs
- FERC, NERC, DOE, EPA
- All major BESS states
- Key utilities (NextEra, Vistra, AES, etc.)
- US market terms (LCR, resource adequacy, capacity auction)

### Sender Configuration
- **From**: Brandt Vermillion (brandt@modoenergy.com)
- **Edition Name**: US

### "More From Around the World"
For US edition, shows articles from Europe AND Australia to give readers global BESS market context.

## New Features (v2)

### Browser Preview
After assembling the newsletter, you can preview it in your default browser before finalizing.

### Save/Resume Workflow
Progress is automatically saved after each step. If you close the terminal mid-workflow:
```bash
python3 main.py --resume
```
This will skip completed steps and resume where you left off. Checkpoint is cleared on successful completion.

### ISO-Specific Tagging
For US editions, news articles are automatically tagged with detected ISOs:
```
  3. [Utility Dive] [ERCOT, MISO] Battery storage deployment accelerates...
  4. [PV Magazine] [CAISO] California grid operator approves...
```
Helps you balance coverage across markets when selecting news items.

### Duplicate Detection
Potential duplicate stories (>65% headline similarity) are flagged:
```
  5. [Energy Storage News] Texas battery project announced... ⚠️ DUP #8
  8. [CleanTechnica] Vistra announces Texas storage... ⚠️ DUP #5
```
Avoid picking both to prevent repetitive content.

### Slack Notifications
When a HubSpot draft is created, a notification is sent to your configured Slack channel with:
- Subject line
- Region
- Direct link to edit in HubSpot

### Dry Run Mode
Test the entire pipeline without API calls or user input:
```bash
python3 main.py --preview
```
Generates a newsletter with dummy content to verify templates and output work correctly.

## Workflow Steps

1. **Region Selection** - Defaults to US
2. **Featured Articles** - Select 1-3 from Modo Terminal (US markets)
3. **Subject Line** - AI generates 15 options using US themes
4. **Intro Paragraph** - AI-written with article hyperlinks
5. **This Week's News** - RSS aggregation from US sources
6. **Chart of the Week** - Upload image + AI descriptions
7. **Promotional Banner** - Optional
8. **Podcast Section** - From Modo's Transmission podcast
9. **More From Around the World** - Europe & Australia articles
10. **Assembly** - HTML output + optional HubSpot publishing

## Output

- HTML file saved to `./output/newsletter_YYYYMMDD_HHMMSS.html`
- Metadata saved to `./output/newsletter_YYYYMMDD_HHMMSS_meta.txt`
- Option to copy to clipboard
- Option to publish directly to HubSpot as draft

## HubSpot Lists (Configured)

**Include Lists:**
- Weekly Newsletter - ERCOT
- ERCOT livestream signups
- US Growth US Outreach
- US Research Sequence
- ESS USA attendees
- US BESS Operators and Optimizers viewers
- Paying customers in North America

**Exclude Lists:**
- Opted out of weekly newsletter
- Marketing suppression list

## Security Note

If API keys were shared in plaintext, rotate them:
- **OpenAI**: platform.openai.com → API Keys → Create new key
- **HubSpot**: Settings → Integrations → Private Apps → Regenerate

Then update:
- `.env` file with new OpenAI key
- `~/Desktop/hubspot-credential` with new HubSpot token
