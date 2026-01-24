"""
YouTube Podcast Scraper

Fetches the latest episode from the Transmission podcast playlist.
Includes improved guest detection from title, description, and LinkedIn.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Dict, Optional, List


class YouTubePodcastScraper:
    """Scraper for YouTube podcast episodes."""

    PLAYLIST_URL = "https://www.youtube.com/playlist?list=PL_lhNBgOJnjQrdbgV5COaOREGVfOU6ek5"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })

    def get_latest_episode(self) -> Optional[Dict]:
        """
        Fetch the latest podcast episode from the playlist.

        Returns:
            Dictionary with title, url, thumbnail, video_id
        """
        episodes = self.get_recent_episodes(limit=1)
        return episodes[0] if episodes else None

    def get_recent_episodes(self, limit: int = 4) -> List[Dict]:
        """
        Fetch the most recent podcast episodes from the playlist.

        Args:
            limit: Number of episodes to return (default 4)

        Returns:
            List of dictionaries with title, url, thumbnail, video_id
        """
        try:
            response = self.session.get(self.PLAYLIST_URL, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching playlist: {e}")
            return []

        return self._parse_playlist_multiple(response.text, limit=limit)

    def _parse_playlist(self, html: str) -> Optional[Dict]:
        """Parse the playlist page to extract the latest video."""
        episodes = self._parse_playlist_multiple(html, limit=1)
        return episodes[0] if episodes else None

    def _parse_playlist_multiple(self, html: str, limit: int = 4) -> List[Dict]:
        """Parse the playlist page to extract multiple videos."""
        # YouTube loads content via JavaScript, so we need to extract from the initial data
        # Look for the ytInitialData JSON object

        match = re.search(r'var ytInitialData = ({.*?});</script>', html, re.DOTALL)
        if not match:
            # Try alternative pattern
            match = re.search(r'ytInitialData\s*=\s*({.*?});', html, re.DOTALL)

        if match:
            try:
                data = json.loads(match.group(1))
                return self._extract_videos_from_data(data, limit=limit)
            except json.JSONDecodeError:
                pass

        # Fallback: parse HTML for video links
        soup = BeautifulSoup(html, 'lxml')
        episodes = []
        seen_ids = set()

        # Look for video links
        video_links = soup.find_all('a', href=re.compile(r'/watch\?v='))

        for link in video_links:
            if len(episodes) >= limit:
                break

            href = link.get('href', '')
            video_id_match = re.search(r'v=([a-zA-Z0-9_-]{11})', href)
            if video_id_match:
                video_id = video_id_match.group(1)
                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)

                title = link.get('title', '') or link.get_text(strip=True)
                if not title or len(title) < 5:
                    continue

                episodes.append({
                    "title": title,
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                })

        return episodes

    def _extract_video_from_data(self, data: dict) -> Optional[Dict]:
        """Extract video info from ytInitialData JSON."""
        videos = self._extract_videos_from_data(data, limit=1)
        return videos[0] if videos else None

    def _extract_videos_from_data(self, data: dict, limit: int = 4) -> List[Dict]:
        """Extract multiple videos from ytInitialData JSON."""
        episodes = []
        try:
            # Navigate through the nested structure to find playlist videos
            contents = data.get('contents', {})
            two_column = contents.get('twoColumnBrowseResultsRenderer', {})
            tabs = two_column.get('tabs', [])

            for tab in tabs:
                tab_renderer = tab.get('tabRenderer', {})
                content = tab_renderer.get('content', {})
                section_list = content.get('sectionListRenderer', {})
                section_contents = section_list.get('contents', [])

                for section in section_contents:
                    item_section = section.get('itemSectionRenderer', {})
                    item_contents = item_section.get('contents', [])

                    for item in item_contents:
                        playlist_renderer = item.get('playlistVideoListRenderer', {})
                        videos = playlist_renderer.get('contents', [])

                        if videos:
                            # Get up to 'limit' videos
                            for video_data in videos[:limit]:
                                video_renderer = video_data.get('playlistVideoRenderer', {})
                                if not video_renderer:
                                    continue

                                video_id = video_renderer.get('videoId', '')
                                if not video_id:
                                    continue

                                title_runs = video_renderer.get('title', {}).get('runs', [])
                                title = title_runs[0].get('text', '') if title_runs else ''

                                thumbnail_list = video_renderer.get('thumbnail', {}).get('thumbnails', [])
                                thumbnail = thumbnail_list[-1].get('url', '') if thumbnail_list else ''

                                episodes.append({
                                    "title": title,
                                    "video_id": video_id,
                                    "url": f"https://www.youtube.com/watch?v={video_id}",
                                    "thumbnail": thumbnail or f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                                })

                            return episodes[:limit]
        except (KeyError, IndexError, TypeError):
            pass

        return episodes

    def get_video_details(self, video_id: str) -> Optional[Dict]:
        """
        Fetch additional details about a specific video.

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with description and other metadata
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            response = self.session.get(video_url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching video details: {e}")
            return None

        # Extract description from og:description or ytInitialPlayerResponse
        soup = BeautifulSoup(response.text, 'lxml')

        og_description = soup.find('meta', property='og:description')
        description = og_description.get('content') if og_description else ""

        # Also try to get full description from ytInitialPlayerResponse
        full_description = self._extract_full_description(response.text)
        if full_description and len(full_description) > len(description):
            description = full_description

        return {
            "video_id": video_id,
            "description": description
        }

    def _extract_full_description(self, html: str) -> str:
        """Extract full video description from ytInitialPlayerResponse."""
        try:
            match = re.search(r'ytInitialPlayerResponse\s*=\s*({.*?});', html, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                description = data.get('videoDetails', {}).get('shortDescription', '')
                return description
        except (json.JSONDecodeError, KeyError):
            pass
        return ""

    def parse_guest_info(self, title: str) -> Dict:
        """
        Parse guest name, company, and topic from podcast title.

        Handles multiple common title formats.

        Returns:
            Dictionary with guest_name, company (if in title), topic
        """
        result = {
            "topic": title,
            "guest_name": "",
            "company": ""
        }

        # Pattern 1: "Topic with Guest Name (Company)"
        with_company_match = re.search(
            r'(.+?)\s+with\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s*\(([^)]+)\)',
            title, re.I
        )
        if with_company_match:
            result['topic'] = with_company_match.group(1).strip()
            result['guest_name'] = with_company_match.group(2).strip()
            result['company'] = with_company_match.group(3).strip()
            return result

        # Pattern 2: "Topic with Guest Name, Company"
        with_comma_match = re.search(
            r'(.+?)\s+with\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s*,\s*([A-Za-z0-9\s&]+?)(?:\s*[-|]|$)',
            title, re.I
        )
        if with_comma_match:
            result['topic'] = with_comma_match.group(1).strip()
            result['guest_name'] = with_comma_match.group(2).strip()
            result['company'] = with_comma_match.group(3).strip()
            return result

        # Pattern 3: "Topic with Guest Name" (basic)
        with_match = re.search(r'(.+?)\s+with\s+(.+?)(?:\s*[-|]|$)', title, re.I)
        if with_match:
            result['topic'] = with_match.group(1).strip()
            guest_part = with_match.group(2).strip()

            # Check if guest part contains company in parentheses
            paren_match = re.search(r'^([^(]+)\s*\(([^)]+)\)', guest_part)
            if paren_match:
                result['guest_name'] = paren_match.group(1).strip()
                result['company'] = paren_match.group(2).strip()
            else:
                result['guest_name'] = guest_part
            return result

        # Pattern 4: "Guest Name | Topic" or "Guest Name - Topic"
        guest_first_match = re.search(
            r'^([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)\s*[-|]\s*(.+)$',
            title
        )
        if guest_first_match:
            result['guest_name'] = guest_first_match.group(1).strip()
            result['topic'] = guest_first_match.group(2).strip()
            return result

        return result

    def parse_guest_details_from_description(self, video_id: str) -> Dict:
        """
        Parse guest details (name, role, company) from video description.

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with guest_name, guest_role, company (if found)
        """
        details = self.get_video_details(video_id)
        if not details or not details.get('description'):
            return {}

        description = details['description']
        result = {}

        # Pattern 1: "Guest: Name, Title at Company" or "Featuring: Name, Title at Company"
        guest_match = re.search(
            r'(?:guest|featuring|joined by)[:\s]+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)[,\s]+([^,\n]+?)\s+(?:at|from|of)\s+([A-Za-z0-9\s&]+)',
            description, re.I
        )
        if guest_match:
            result['guest_name'] = guest_match.group(1).strip()
            result['guest_role'] = guest_match.group(2).strip()
            result['company'] = guest_match.group(3).strip().rstrip('.')
            return result

        # Pattern 2: "Name is the/a Role at Company"
        is_match = re.search(
            r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)\s+is\s+(?:the|a|an)\s+([^,\n]+?)\s+(?:at|of|from)\s+([A-Za-z0-9\s&]+)',
            description, re.I
        )
        if is_match:
            result['guest_name'] = is_match.group(1).strip()
            result['guest_role'] = is_match.group(2).strip()
            result['company'] = is_match.group(3).strip().rstrip('.')
            return result

        # Pattern 3: "Name, Role at Company" (at start of description or after newline)
        start_match = re.search(
            r'(?:^|\n)([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)[,\s]+([^,\n]+?)\s+(?:at|from|of)\s+([A-Za-z0-9\s&]+)',
            description, re.I
        )
        if start_match:
            result['guest_name'] = start_match.group(1).strip()
            result['guest_role'] = start_match.group(2).strip()
            result['company'] = start_match.group(3).strip().rstrip('.')
            return result

        # Pattern 4: Look for LinkedIn-style formats "Name | Role | Company"
        linkedin_match = re.search(
            r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)\s*[|]\s*([^|\n]+?)\s*[|]\s*([A-Za-z0-9\s&]+)',
            description
        )
        if linkedin_match:
            result['guest_name'] = linkedin_match.group(1).strip()
            result['guest_role'] = linkedin_match.group(2).strip()
            result['company'] = linkedin_match.group(3).strip()
            return result

        # Pattern 5: Look for "Role at Company" followed by name mention
        role_at_match = re.search(
            r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)[,\s]+(?:the\s+)?([A-Za-z\s]+?)\s+(?:at|of|from)\s+([A-Za-z0-9\s&]+)',
            description
        )
        if role_at_match:
            # Validate that first group looks like a name (2-3 words, capitalized)
            potential_name = role_at_match.group(1).strip()
            words = potential_name.split()
            if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words):
                result['guest_name'] = potential_name
                result['guest_role'] = role_at_match.group(2).strip()
                result['company'] = role_at_match.group(3).strip().rstrip('.')
                return result

        return result

    def scrape_linkedin_profile(self, linkedin_url: str) -> Dict:
        """
        Scrape name, role, and company from a LinkedIn profile URL.

        Note: This has limited success due to LinkedIn's anti-scraping measures.
        Best effort extraction from public profile page.

        Args:
            linkedin_url: Full LinkedIn profile URL

        Returns:
            Dictionary with name, role, company (if found)
        """
        if not linkedin_url or 'linkedin.com' not in linkedin_url:
            return {}

        try:
            response = self.session.get(linkedin_url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching LinkedIn profile: {e}")
            return {}

        soup = BeautifulSoup(response.text, 'lxml')
        result = {}

        # Try to get name from og:title or title tag
        og_title = soup.find('meta', property='og:title')
        if og_title:
            title_content = og_title.get('content', '')
            # Format is typically "Name - Title - Company | LinkedIn"
            parts = title_content.split(' - ')
            if len(parts) >= 1:
                result['guest_name'] = parts[0].strip()
            if len(parts) >= 2:
                result['guest_role'] = parts[1].strip()
            if len(parts) >= 3:
                company_part = parts[2].split('|')[0].strip()
                result['company'] = company_part

        # Fallback: try page title
        if not result.get('guest_name'):
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text()
                parts = title_text.split(' - ')
                if len(parts) >= 1:
                    result['guest_name'] = parts[0].strip()

        return result

    def scrape_company_linkedin(self, company_url: str) -> Dict:
        """
        Scrape company name from a LinkedIn company page URL.

        Args:
            company_url: Full LinkedIn company page URL

        Returns:
            Dictionary with company name (if found)
        """
        if not company_url or 'linkedin.com' not in company_url:
            return {}

        try:
            response = self.session.get(company_url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching LinkedIn company page: {e}")
            return {}

        soup = BeautifulSoup(response.text, 'lxml')
        result = {}

        # Try to get company name from og:title
        og_title = soup.find('meta', property='og:title')
        if og_title:
            title_content = og_title.get('content', '')
            # Format is typically "Company Name | LinkedIn"
            company_name = title_content.split('|')[0].strip()
            if company_name:
                result['company'] = company_name

        return result


def main():
    """Test the scraper."""
    scraper = YouTubePodcastScraper()

    print("Fetching latest podcast episode...")
    episode = scraper.get_latest_episode()

    if episode:
        print(f"\nLatest Episode:")
        print(f"  Title: {episode['title']}")
        print(f"  URL: {episode['url']}")
        print(f"  Thumbnail: {episode['thumbnail']}")

        # Parse from title
        guest_info = scraper.parse_guest_info(episode['title'])
        print(f"\nParsed from Title:")
        print(f"  Topic: {guest_info.get('topic', '')}")
        print(f"  Guest: {guest_info.get('guest_name', '')}")
        print(f"  Company: {guest_info.get('company', '')}")

        # Parse from description
        desc_info = scraper.parse_guest_details_from_description(episode['video_id'])
        if desc_info:
            print(f"\nParsed from Description:")
            print(f"  Guest: {desc_info.get('guest_name', '')}")
            print(f"  Role: {desc_info.get('guest_role', '')}")
            print(f"  Company: {desc_info.get('company', '')}")
    else:
        print("Could not fetch episode")


if __name__ == "__main__":
    main()
