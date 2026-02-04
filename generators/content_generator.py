"""
AI Content Generator

Uses OpenAI API to generate:
- Subject lines
- Preview/intro text
- Chart of the week descriptions
- Podcast descriptions
"""

import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ContentGenerator:
    """AI-powered content generator for newsletter sections."""

    # Example subject lines for style reference
    SUBJECT_EXAMPLES = [
        "Record temperatures drive battery revenues",
        "Surging BESS",
        "Battery revenues reach near two-year lows",
        "Best of BESS 2025",
        "Contract stacking hits the mainstream",
        "Mild volatility, mild NEM battery revenues",
        "Five things you should consider when investing in BESS",
        "Germany's grid fees reshape BESS economics",
        "Renewable curtailment at record highs",
        "Storage revenues climb in Q4",
        "New market rules favor flexible assets",
        "BESS capacity doubles in six months"
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = None
        self.region = None  # Will be set after region selection

        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                print("OpenAI package not installed. Using fallback generators.")

    def set_region(self, region: str):
        """Set the newsletter region for localized content generation."""
        self.region = region

    def _get_writing_guidelines(self) -> str:
        """Get writing style guidelines based on region."""
        # Determine spelling preference
        if self.region in ['australia', 'europe']:
            spelling = "British/Australian English spelling (use 's' not 'z': emphasise, organise, recognise, etc.)"
        else:
            spelling = "American English spelling"

        return f"""
CRITICAL WRITING RULES (Amazon style):
- {spelling}
- Maximum 20 words per sentence
- NO weasel words: avoid "might", "could", "possibly", "somewhat", "perhaps", "maybe", "fairly", "quite", "rather"
- Be direct and definitive
- Use active voice
- State facts clearly without hedging"""

    def generate_subject_line(self, articles: List[Dict]) -> List[str]:
        """
        Generate catchy subject line options based on featured articles.

        Args:
            articles: List of article dicts with title and description

        Returns:
            List of 15 subject line options
        """
        if not articles:
            return ["Weekly Dispatch"]

        # Extract key themes from articles
        titles = [a.get('title', '') for a in articles]
        themes = ' | '.join(titles)

        if self.client:
            return self._generate_subject_with_ai(themes)
        else:
            return self._generate_subject_fallback(articles)

    def _generate_subject_with_ai(self, themes: str) -> List[str]:
        """Generate subject lines using OpenAI."""
        examples_str = '\n'.join(f'- "{ex}"' for ex in self.SUBJECT_EXAMPLES)
        writing_guidelines = self._get_writing_guidelines()

        prompt = f"""Generate 15 email subject lines for a weekly energy industry newsletter.

The subject lines should be:
- Direct, factual, and newsworthy (like industry publication headlines)
- Use industry-specific terminology (BESS, NEM, capacity markets, etc.)
- Include quantitative/data-driven elements when relevant (timeframes, numbers, metrics)
- Variable length: anywhere from 2-9 words (NOT forced into arbitrary limits)
- Professional and informative, NOT gimmicky or cute
- Avoid forced alliteration, wordplay, puns, or marketing speak
- Use strong action verbs or descriptive language
- Frame as news or insights, not marketing copy

{writing_guidelines}

This week's article topics: {themes}

Style examples (for reference, don't copy):
{examples_str}

Return only the 15 subject lines, one per line, no numbering or bullets."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=300
            )
            lines = response.choices[0].message.content.strip().split('\n')
            return [line.strip().strip('"') for line in lines if line.strip()]
        except Exception as e:
            print(f"Error generating subject: {e}")
            return self._generate_subject_fallback([{"title": themes}])

    def _generate_subject_fallback(self, articles: List[Dict]) -> List[str]:
        """Fallback subject line generation without AI."""
        # Simple keyword-based suggestions
        keywords = []
        for article in articles:
            title = article.get('title', '').lower()
            if 'grid' in title:
                keywords.append('Grid')
            if 'battery' in title or 'bess' in title:
                keywords.append('Battery')
            if 'revenue' in title:
                keywords.append('Revenue')
            if 'germany' in title or 'german' in title:
                keywords.append('Germany')
            if 'fee' in title or 'tariff' in title:
                keywords.append('Fees')

        if 'Grid' in keywords and 'Fees' in keywords:
            return ["Fees and fundamentals", "Grid rules", "Tariff talk"]
        elif 'Battery' in keywords:
            return ["Battery builds", "Storage signals", "Power plays"]
        else:
            return ["Market moves", "Energy insights", "Weekly roundup"]

    def generate_preview_text(self, articles: List[Dict]) -> str:
        """
        Generate the intro paragraph for the newsletter.

        Args:
            articles: Featured articles with title, url

        Returns:
            HTML paragraph with hyperlinks
        """
        if not articles:
            return "Good morning and welcome back to the Weekly Dispatch."

        if self.client:
            return self._generate_preview_with_ai(articles)
        else:
            return self._generate_preview_fallback(articles)

    def _generate_preview_with_ai(self, articles: List[Dict]) -> str:
        """Generate preview text using OpenAI."""
        article_info = '\n'.join([
            f"- Title: {a['title']}\n  URL: {a['url']}"
            for a in articles[:2]
        ])
        writing_guidelines = self._get_writing_guidelines()

        prompt = f"""Write a brief intro paragraph (2-3 sentences) for an energy industry newsletter.

Start with "Good morning and welcome back to the Weekly Dispatch."

Then describe what topics are covered this week, naturally embedding hyperlinks within the sentence where the topic is mentioned.

IMPORTANT: Do NOT use phrases like "check out our articles on", "read more about", "see our featured articles", or any call-to-action language. Instead, weave the hyperlinks naturally into the description of what the newsletter covers.

CRITICAL GRAMMAR RULES:
- Use PARALLEL STRUCTURE when listing multiple topics (both items should have the same grammatical form)
- Each verb should be grammatically appropriate and flow naturally with what follows
- Maintain CONSISTENT VERB TENSE throughout (all present tense)
- Ensure subject-verb agreement (we + base verb form)
- You can use different verbs as long as they are grammatically correct and sound natural

{writing_guidelines}

Featured articles:
{article_info}

Format hyperlinks as: <a href="URL" style="color:#000000; text-decoration:underline; font-weight:bold;">short topic phrase</a>

GOOD examples:
- "This week, we examine the potential revenue challenges posed by <a href="URL1" style="color:#000000; text-decoration:underline; font-weight:bold;">BESS overbuild in Germany</a> and analyse upcoming changes to <a href="URL2" style="color:#000000; text-decoration:underline; font-weight:bold;">grid fees for battery storage</a>."
- "This week, we analyse the surge in <a href="URL1" style="color:#000000; text-decoration:underline; font-weight:bold;">battery revenues during January's heatwave</a> and explore the decline in <a href="URL2" style="color:#000000; text-decoration:underline; font-weight:bold;">capture rates in Q4 2025</a>."

The key is that each verb must be grammatically correct with the noun phrase that follows it (e.g., "analyse the surge", "examine the challenges", "explore the decline")

BAD example (call-to-action): "For more insights, check out our featured articles on Germany's fundamentals risk and new rules for battery storage."

Keep it concise and professional. Use short descriptive phrases for the linked text, not full article titles."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=250
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating preview: {e}")
            return self._generate_preview_fallback(articles)

    def _generate_preview_fallback(self, articles: List[Dict]) -> str:
        """Fallback preview text generation."""
        links = []
        for article in articles[:2]:
            # Extract a short topic phrase from the title
            title = article['title']
            # Remove common prefixes and extract key topic
            title_short = title.split(':')[-1].strip() if ':' in title else title
            # Truncate if too long
            if len(title_short) > 40:
                title_short = title_short[:40].rsplit(' ', 1)[0]
            links.append(
                f'<a href="{article["url"]}" style="color:#000000; text-decoration:underline; font-weight:bold;">{title_short.lower()}</a>'
            )

        if len(links) == 2:
            return f"Good morning and welcome back to the Weekly Dispatch. This week, we examine {links[0]} and explore {links[1]}."
        elif len(links) == 1:
            return f"Good morning and welcome back to the Weekly Dispatch. This week, we dive into {links[0]}."
        else:
            return "Good morning and welcome back to the Weekly Dispatch."

    def generate_chart_text(
        self,
        chart_title: str,
        article_context: str
    ) -> Dict[str, str]:
        """
        Generate intro and outro text for Chart of the Week.

        Args:
            chart_title: Title/description of the chart
            article_context: Context from the source article

        Returns:
            Dict with 'intro' and 'outro' text
        """
        if self.client:
            return self._generate_chart_text_with_ai(chart_title, article_context)
        else:
            return {
                "intro": f"{chart_title} reveals shifting dynamics in the market.",
                "outro": "The data points to changing conditions for operators in this segment."
            }

    def _generate_chart_text_with_ai(self, chart_title: str, article_context: str) -> Dict[str, str]:
        """Generate chart text using OpenAI."""
        writing_guidelines = self._get_writing_guidelines()

        prompt = f"""Write two short paragraphs for a "Chart of the Week" section in an energy newsletter.

Chart topic: {chart_title}
Article context: {article_context[:500]}

1. INTRO (2-3 sentences): Directly state what the chart shows and the key insight
2. OUTRO (2-3 sentences): State the practical implication or what this means for the market

IMPORTANT - Be direct and analytical. AVOID:
- Filler phrases: "This week's chart illustrates/shows/highlights...", "The key takeaway is...", "Understanding these dynamics is crucial...", "It is important to note that...", "Companies that proactively adapt..."
- Hyperbolic adjectives: "impressive", "significant", "substantial", "remarkable", "critical", "crucial", "essential", "major", "groundbreaking"
- Filler verbs: "underscores", "highlights", "demonstrates", "showcases", "illustrates" (just state the fact directly)
- Meta-commentary: Don't describe what the data shows, just state the facts

{writing_guidelines}

GOOD example intro: "Germany's grid fee exemption for battery storage expires in 2029, fundamentally changing the cost structure for BESS operators."
BAD example intro: "This week's chart illustrates the projected timeline for the expiration of the grid fee exemption, highlighting the anticipated changes."

GOOD example intro: "Battery revenues in the NEM doubled to $121,000 per MW/year in January. South Australian batteries earned $356,000 per MW/year during heatwave-induced price spikes."
BAD example intro: "In South Australia, batteries achieved an impressive revenue of $356,000 per MW/year, reflecting their critical role during peak demand periods."

GOOD example outro: "Operators with flexible dispatch strategies will capture the remaining margin; those reliant on simple arbitrage face compression."
BAD example outro: "This surge in revenue underscores the profitability of battery storage. Operators who optimise their response can significantly enhance their performance."

Just state the facts and implications directly. No adjectives about how impressive or critical something is.

Return as:
INTRO: [text]
OUTRO: [text]"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )

            text = response.choices[0].message.content

            intro_match = text.split('INTRO:')[1].split('OUTRO:')[0] if 'INTRO:' in text else ""
            outro_match = text.split('OUTRO:')[1] if 'OUTRO:' in text else ""

            return {
                "intro": intro_match.strip(),
                "outro": outro_match.strip()
            }
        except Exception as e:
            print(f"Error generating chart text: {e}")
            return {
                "intro": f"This week's chart examines {chart_title.lower()}.",
                "outro": "The data highlights key trends in the market."
            }

    def generate_podcast_description(
        self,
        guest_name: str,
        guest_role: str,
        company: str,
        topic: str,
        moderator: str = "Ed"
    ) -> str:
        """
        Generate podcast description paragraph.

        Args:
            guest_name: Name of the guest
            guest_role: Guest's job title
            company: Guest's company
            topic: Episode topic
            moderator: Name of the podcast moderator/host

        Returns:
            Description paragraph with bold formatting for names
        """
        if self.client:
            return self._generate_podcast_desc_with_ai(guest_name, guest_role, company, topic, moderator)
        else:
            return self._generate_podcast_desc_fallback(guest_name, guest_role, company, topic, moderator)

    def _generate_podcast_desc_with_ai(
        self,
        guest_name: str,
        guest_role: str,
        company: str,
        topic: str,
        moderator: str = "Ed"
    ) -> str:
        """Generate podcast description using OpenAI."""
        writing_guidelines = self._get_writing_guidelines()

        prompt = f"""Write a 2-3 sentence description for a podcast episode.

Host: {moderator}
Guest: {guest_name}, {guest_role} at {company}
Topic: {topic}

Start with "In this week's episode of Transmission, {moderator} is joined by..."

The guest name should be wrapped as: <strong>{guest_name}</strong>
The company should be wrapped as: <strong>{company}</strong>

{writing_guidelines}

Keep it professional and mention what topics are explored."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating podcast description: {e}")
            return self._generate_podcast_desc_fallback(guest_name, guest_role, company, topic, moderator)

    def _generate_podcast_desc_fallback(
        self,
        guest_name: str,
        guest_role: str,
        company: str,
        topic: str,
        moderator: str = "Ed"
    ) -> str:
        """Fallback podcast description."""
        return (
            f"In this week's episode of Transmission, {moderator} is joined by "
            f"<strong>{guest_name}</strong>, {guest_role} at <strong>{company}</strong>, "
            f"to explore {topic.lower()}."
        )

    def format_news_item(
        self,
        title: str,
        description: str,
        url: str,
        source: str,
        region_prefix: str = ""
    ) -> Dict:
        """
        Format a news item with region context and source hyperlink using AI.

        Returns:
            Dict with headline, body (including hyperlink), url, source, formatted_text
        """
        if self.client:
            return self._format_news_with_ai(title, description, url, source, region_prefix)
        else:
            return self._format_news_fallback(title, description, url, source, region_prefix)

    def _format_news_with_ai(
        self,
        title: str,
        description: str,
        url: str,
        source: str,
        region_prefix: str
    ) -> Dict:
        """Format news item using AI."""
        writing_guidelines = self._get_writing_guidelines()

        prompt = f"""Summarize this news item as a factual, objective sentence for an energy industry newsletter.

Original title: {title}
Description: {description}
Region prefix: {"'" + region_prefix + "'" if region_prefix else "NONE - DO NOT ADD ANY REGION PREFIX"}

Requirements:
1. Region prefix: {"Start with: " + region_prefix if region_prefix else "DO NOT add any region prefix (like 'In Australia,', 'In NSW,', etc.) even if you detect location names in the content. Start directly with the key fact."}
2. Write 1-2 factual sentences that objectively describe what happened
3. Use neutral, professional language - no marketing speak or hype
4. Include specific details (company names, MW figures, dates) when available
5. The first few words should be the key fact that will appear in bold
6. Avoid words like "exciting", "groundbreaking", "major" - just state the facts
7. CRITICAL: Return PLAIN TEXT ONLY - NO markdown syntax (**, __, etc.), NO HTML tags. Just plain text.

{writing_guidelines}

Return ONLY the plain text, nothing else. Do not use ** or any markdown formatting.
Example {"with region prefix" if region_prefix else "without region prefix"}: {"In Germany, Fluence has been awarded a 200MW battery storage contract by EnBW for delivery in 2026." if region_prefix else "Origin Energy has begun generating revenue from the Supernode and Eraring Stage 1 battery storage projects in Queensland and New South Wales."}
Where {"'Fluence has been awarded a 200MW battery storage contract'" if region_prefix else "'Origin Energy has begun generating revenue from the Supernode and Eraring Stage 1 battery storage projects'"} would be the bold headline part."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=150
            )
            formatted_text = response.choices[0].message.content.strip()

            # Split into headline and body
            # Try to find a natural break point (after company name or key fact)
            words = formatted_text.split()
            if len(words) > 5:
                # Take first ~5-8 words as headline
                headline_words = []
                for i, word in enumerate(words):
                    headline_words.append(word)
                    # Break after a company-like word or comma
                    if i >= 4 and (word.endswith(',') or i >= 7):
                        break
                headline = ' '.join(headline_words).rstrip(',')
                body_start = len(headline)
                body = formatted_text[body_start:].strip()
                if not body.startswith(','):
                    body = ', ' + body if body else '.'
            else:
                headline = formatted_text
                body = '.'

            # Wrap headline in hyperlink (bold styling applied in template)
            headline_with_link = f'<a href="{url}" style="color:#000000; text-decoration:none; font-weight:bold;">{headline}</a>'

            return {
                "headline": headline_with_link,
                "body": body,
                "url": url,
                "source": source,
                "formatted_text": formatted_text
            }

        except Exception as e:
            print(f"Error formatting news with AI: {e}")
            return self._format_news_fallback(title, description, url, source, region_prefix)

    def _format_news_fallback(
        self,
        title: str,
        description: str,
        url: str,
        source: str,
        region_prefix: str
    ) -> Dict:
        """Fallback news formatting without AI."""
        if region_prefix:
            headline = f"{region_prefix}, {title}"
        else:
            headline = title

        body_text = f", {description[:150]}..." if description and len(description) > 150 else (f", {description}" if description else ".")

        # Wrap headline in hyperlink (bold styling applied in template)
        headline_with_link = f'<a href="{url}" style="color:#000000; text-decoration:none; font-weight:bold;">{headline}</a>'

        return {
            "headline": headline_with_link,
            "body": body_text,
            "url": url,
            "source": source,
            "formatted_text": f"{headline}{body_text}"
        }


def main():
    """Test the generator."""
    generator = ContentGenerator()

    test_articles = [
        {
            "title": "New rules for German battery storage: How grid fees will change from 2029",
            "url": "https://modoenergy.com/research/en/germany-batteries-bess-grid-fees"
        },
        {
            "title": "Germany's fundamentals risk: How battery overbuild could cannibalise revenues",
            "url": "https://modoenergy.com/research/en/germany-fundamentals-risk"
        }
    ]

    print("Testing subject line generation...")
    subjects = generator.generate_subject_line(test_articles)
    print(f"Subject options: {subjects}")

    print("\nTesting preview text generation...")
    preview = generator.generate_preview_text(test_articles)
    print(f"Preview: {preview}")

    print("\nTesting podcast description...")
    desc = generator.generate_podcast_description(
        guest_name="Roger Hollies",
        guest_role="CTO",
        company="Arenko",
        topic="Automation, AI and market enforcement"
    )
    print(f"Podcast desc: {desc}")


if __name__ == "__main__":
    main()
