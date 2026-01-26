"""
HTML Assembler

Assembles the complete newsletter HTML from templates and content.
"""

from pathlib import Path
from typing import List, Dict, Optional


class NewsletterAssembler:
    """Assembles newsletter HTML from templates and content."""

    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = Path(__file__).parent / 'templates'

    def _load_template(self, name: str) -> str:
        """Load a template file."""
        template_path = self.templates_dir / f"{name}.html"
        if template_path.exists():
            return template_path.read_text()
        else:
            raise FileNotFoundError(f"Template not found: {template_path}")

    def _build_header(self, content: Dict) -> str:
        """Build the header with dynamic banner based on region."""
        # Default header values (Europe)
        default_header_url = "https://25093280.fs1.hubspotusercontent-eu1.net/hubfs/25093280/European%20Weekly%20Dispatch/Weekly%20Dispatch%20Header_EU.png"
        default_header_alt = "MODOENERGY Weekly Dispatch Europe & GB Edition"

        # Get custom header from content (set by region selection)
        header_url = content.get('header_url', default_header_url)
        header_alt = content.get('header_alt', default_header_alt)

        # Build header HTML directly (not using template to allow dynamic URLs)
        header_html = f'''<!-- HEADER - MODOENERGY WEEKLY DISPATCH -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; background-color:#ffffff;">
  <tr>
    <td align="center" style="padding:24px 24px 16px;">
      <!--[if mso]>
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" align="center">
        <tr>
          <td align="center">
            <a href="https://modoenergy.com/research" target="_blank">
              <img src="{header_url}"
                   alt="{header_alt}"
                   width="560"
                   height="auto"
                   border="0"
                   style="display:block; border:0;">
            </a>
          </td>
        </tr>
      </table>
      <![endif]-->
      <!--[if !mso]><!-->
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" align="center" style="max-width:560px;">
        <tr>
          <td align="center">
            <a href="https://modoenergy.com/research" target="_blank" style="display:block; text-decoration:none;">
              <img src="{header_url}"
                   alt="{header_alt}"
                   width="560"
                   style="display:block; border:0; width:100%; max-width:560px;">
            </a>
          </td>
        </tr>
      </table>
      <!--<![endif]-->
    </td>
  </tr>
</table>'''
        return header_html

    def assemble(self, content: Dict) -> str:
        """
        Assemble the complete newsletter HTML.

        Args:
            content: Dictionary containing all newsletter content:
                - subject: Email subject line
                - intro_text: Intro paragraph with hyperlinks
                - featured_articles: List of 2 article dicts
                - chart: Dict with title, intro_text, outro_text, image_url, article_url
                - promotional_banner: Optional dict with image_url, link, alt_text
                - news_items: List of news item dicts
                - podcast: Dict with title, url, thumbnail, description
                - world_articles: List of 3 article dicts

        Returns:
            Complete HTML string
        """
        html_parts = []

        # 1. Header (with dynamic banner based on region)
        header_html = self._build_header(content)
        html_parts.append(header_html)

        # 2. Intro paragraph
        intro_html = self._load_template('intro')
        html_parts.append(intro_html.format(intro_text=content.get('intro_text', '')))

        # 3. Featured articles wrapper
        html_parts.append(self._build_featured_articles(content.get('featured_articles', [])))

        # 4. Chart of the week
        if content.get('chart'):
            html_parts.append(self._build_chart_section(content['chart']))

        # 5. Promotional banner (optional)
        if content.get('promotional_banner'):
            html_parts.append(self._build_promotional_banner(content['promotional_banner']))

        # 6. This week's news
        if content.get('news_items'):
            html_parts.append(self._build_news_section(content['news_items']))

        # 7. Podcast section
        if content.get('podcast'):
            html_parts.append(self._build_podcast_section(content['podcast']))

        # 8. More from around the world
        if content.get('world_articles'):
            html_parts.append(self._build_world_section(content['world_articles']))

        # 9. Footer
        html_parts.append(self._load_template('footer'))

        # Join all parts
        body_content = '\n\n'.join(html_parts)

        # Wrap in complete HTML document for HubSpot compatibility
        html_wrapper = '''<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <title>Weekly Dispatch</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style type="text/css">
        body {{ margin: 0; padding: 0; width: 100% !important; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table {{ border-collapse: collapse; }}
        img {{ border: 0; outline: none; text-decoration: none; -ms-interpolation-mode: bicubic; }}
        a img {{ border: none; }}
    </style>
</head>
<body style="margin:0; padding:0; background-color:#f5f5f5;">
    <center style="width:100%; background-color:#f5f5f5;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f5f5;">
            <tr>
                <td align="center" valign="top">
                    <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center" style="max-width:600px; background-color:#ffffff;">
                        <tr>
                            <td>
{body_content}
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </center>
</body>
</html>'''

        return html_wrapper.format(body_content=body_content)

    def _build_featured_articles(self, articles: List[Dict]) -> str:
        """Build the featured articles section (supports 1, 2, or 3 articles)."""
        if not articles:
            return ''

        article_template = self._load_template('article_card')
        articles_html = []

        num_articles = len(articles)

        if num_articles == 1:
            # Single full-width article
            html = article_template.format(
                padding="12px 24px 24px",
                article_url=articles[0].get('url', ''),
                thumbnail_url=articles[0].get('thumbnail_url', ''),
                article_title=articles[0].get('title', ''),
                article_description=articles[0].get('description', '')
            )
            articles_html.append(html)

        elif num_articles == 2:
            # Two full-width articles stacked
            for i, article in enumerate(articles[:2]):
                padding = "12px 24px 24px" if i == 0 else "0 24px 24px"
                html = article_template.format(
                    padding=padding,
                    article_url=article.get('url', ''),
                    thumbnail_url=article.get('thumbnail_url', ''),
                    article_title=article.get('title', ''),
                    article_description=article.get('description', '')
                )
                articles_html.append(html)

        elif num_articles >= 3:
            # First article full-width, then two side-by-side
            # First article (full width)
            html = article_template.format(
                padding="12px 24px 24px",
                article_url=articles[0].get('url', ''),
                thumbnail_url=articles[0].get('thumbnail_url', ''),
                article_title=articles[0].get('title', ''),
                article_description=articles[0].get('description', '')
            )
            articles_html.append(html)

            # Side-by-side articles (2nd and 3rd)
            side_by_side_html = self._build_side_by_side_articles(articles[1], articles[2])
            articles_html.append(side_by_side_html)

        # Wrap in container
        wrapper = '''<!-- OUTER WRAPPER -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; background-color:#ffffff;">
  <tr>
    <td align="center" style="padding:0;">

      <!-- INNER CONTAINER -->
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center"
             style="max-width:600px; border-collapse:collapse; font-family:Arial,sans-serif; color:#000000;">

        {articles}

      </table>

    </td>
  </tr>
</table>'''

        return wrapper.format(articles='\n\n'.join(articles_html))

    def _build_side_by_side_articles(self, article1: Dict, article2: Dict) -> str:
        """Build two articles side-by-side (50% width each)."""
        half_template = self._load_template('article_card_half')

        article1_html = half_template.format(
            article_url=article1.get('url', ''),
            thumbnail_url=article1.get('thumbnail_url', ''),
            article_title=article1.get('title', '')
        )

        article2_html = half_template.format(
            article_url=article2.get('url', ''),
            thumbnail_url=article2.get('thumbnail_url', ''),
            article_title=article2.get('title', '')
        )

        # Side-by-side wrapper with MSO support
        wrapper = '''<!-- SIDE-BY-SIDE ARTICLES -->
<tr>
  <td align="center" style="padding:0 24px 24px;">
    <!--[if mso]>
    <table role="presentation" width="552" cellpadding="0" cellspacing="0" border="0">
    <tr>
    <![endif]-->
    <!--[if !mso]><!-->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
    <!--<![endif]-->

        {article1}

        <!--[if mso]>
        <td width="24" style="padding:0;">&nbsp;</td>
        <![endif]-->

        {article2}

    <!--[if mso]>
    </tr>
    </table>
    <![endif]-->
    <!--[if !mso]><!-->
      </tr>
    </table>
    <!--<![endif]-->
  </td>
</tr>'''

        return wrapper.format(article1=article1_html, article2=article2_html)

    def _build_chart_section(self, chart: Dict) -> str:
        """Build the chart of the week section."""
        template = self._load_template('chart_of_week')
        return template.format(
            chart_title=chart.get('title', ''),
            chart_intro_text=chart.get('intro_text', ''),
            chart_image_url=chart.get('image_url', ''),
            chart_outro_text=chart.get('outro_text', ''),
            article_url=chart.get('article_url', '')
        )

    def _build_promotional_banner(self, banner: Dict) -> str:
        """Build the promotional banner section."""
        template = self._load_template('promotional_banner')
        return template.format(
            banner_image_url=banner.get('image_url', ''),
            banner_link=banner.get('link', ''),
            banner_alt_text=banner.get('alt_text', 'Promotional Banner')
        )

    def _build_news_section(self, news_items: List[Dict]) -> str:
        """Build the This Week's News section."""
        item_template = self._load_template('news_item')

        items_html = []
        for item in news_items:
            html = item_template.format(
                news_headline=item.get('headline', ''),
                news_body=item.get('body', '')
            )
            items_html.append(html)

        section_template = self._load_template('news_section')
        return section_template.format(news_items='\n'.join(items_html))

    def _build_podcast_section(self, podcast: Dict) -> str:
        """Build the podcast section."""
        template = self._load_template('podcast')
        return template.format(
            podcast_url=podcast.get('url', ''),
            podcast_thumbnail=podcast.get('thumbnail', ''),
            podcast_title=podcast.get('title', ''),
            podcast_description=podcast.get('description', '')
        )

    def _build_world_section(self, articles: List[Dict]) -> str:
        """Build the More from Around the World section."""
        item_template = self._load_template('world_article_item')

        items_html = []
        for article in articles[:3]:
            html = item_template.format(
                article_url=article.get('url', ''),
                thumbnail_url=article.get('thumbnail_url', ''),
                article_title=article.get('title', '')
            )
            items_html.append(html)

        section_template = self._load_template('more_from_world')
        return section_template.format(world_articles='\n'.join(items_html))

    def get_email_metadata(self, content: Dict) -> Dict:
        """
        Get email metadata for HubSpot.

        Returns:
            Dict with subject and preview_text
        """
        return {
            "subject": content.get('subject', 'Weekly Dispatch'),
            "preview_text": self._strip_html(content.get('intro_text', ''))[:150]
        }

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags from text."""
        import re
        clean = re.sub(r'<[^>]+>', '', html)
        return clean.strip()


def main():
    """Test the assembler."""
    assembler = NewsletterAssembler()

    # Test content
    test_content = {
        "subject": "Fees and fundamentals",
        "intro_text": 'Good morning and welcome back to the Weekly Dispatch. This week, we explore <a href="#">grid fees</a> and <a href="#">overbuild risks</a>.',
        "featured_articles": [
            {
                "title": "New rules for German battery storage: How grid fees will change from 2029",
                "description": "Battery storage operators in Germany face a fundamental shift as the regulator aims to phase out the 20-year grid fee exemption.",
                "url": "https://modoenergy.com/research/en/germany-grid-fees",
                "thumbnail_url": "https://example.com/thumb1.png"
            },
            {
                "title": "Germany's fundamentals risk: How battery overbuild could cannibalise revenues",
                "description": "German grid operators have approved 78 GW of battery storage against just 2.5 GW installed.",
                "url": "https://modoenergy.com/research/en/germany-overbuild",
                "thumbnail_url": "https://example.com/thumb2.png"
            }
        ],
        "chart": {
            "title": "What 78 GW of batteries would do to Germany's power prices",
            "intro_text": "Germany's grid operators have now preliminarily approved 78 GW of battery pipeline.",
            "outro_text": "It is unlikely that all 78 GW will be built, but the scenario highlights the range of buildout paths now in play.",
            "image_url": "https://example.com/chart.png",
            "article_url": "https://modoenergy.com/research/en/germany-overbuild"
        },
        "news_items": [
            {
                "headline": "Gresham House has completed its merger with SUSI Partners",
                "body": ", creating a £2.7 billion energy transition investment platform."
            }
        ],
        "podcast": {
            "title": "Automation, AI and market enforcement with Roger Hollies",
            "url": "https://youtube.com/watch?v=xxx",
            "thumbnail": "https://example.com/podcast-thumb.png",
            "description": "In this week's episode..."
        },
        "world_articles": [
            {
                "title": "NEM Buildout Report: BESS capacity exceeds 5 GW",
                "url": "https://modoenergy.com/research/en/nem-buildout",
                "thumbnail_url": "https://example.com/nem.png"
            }
        ]
    }

    html = assembler.assemble(test_content)
    print(f"Generated HTML length: {len(html)} characters")
    print("\nFirst 500 characters:")
    print(html[:500])


if __name__ == "__main__":
    main()
