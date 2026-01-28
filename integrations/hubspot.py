"""
HubSpot Integration

Uploads newsletter to HubSpot:
- Upload images to File Manager
- Create marketing email draft with subscriber lists

REQUIRED HUBSPOT API SCOPES:
============================
Your HubSpot private app token must have the following scopes enabled:

1. file-manager-write  - Required to upload images to File Manager
2. content            - Required to create marketing email drafts
3. crm.lists.read     - Required to look up subscriber lists by name

To update scopes:
1. Go to HubSpot Settings → Integrations → Private Apps
2. Find your app and click "Edit"
3. Go to "Scopes" tab
4. Enable: CMS > Files (write), Marketing > Marketing Email (all), CRM > Lists (read)
5. Save changes and use the new token

If you get 403 errors with "Requires scope(s): [file-manager-write]" or
"MISSING_SCOPES", you need to regenerate your token with the above scopes.
"""

import requests
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json


class HubSpotIntegration:
    """HubSpot API integration for newsletter publishing."""

    BASE_URL = "https://api.hubapi.com"
    CREDENTIAL_PATH = os.path.expanduser("~/Desktop/hubspot-credential")

    # Modo Energy HubSpot portal ID
    PORTAL_ID = "25093280"

    # Default email settings (lists will be set from region config)
    DEFAULT_SETTINGS = {
        "from_email": "shaniyaa@modoenergy.com",
        "from_name": "Shaniyaa Holness-Mckenzie",
        "image_folder": "European Weekly Dispatch",
        "include_lists": [],
        "exclude_lists": [],
        "exclude_emails": []  # Individual email addresses to exclude
    }

    def __init__(self):
        self.token = self._load_token()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        })
        # Current settings (can be customized)
        self.settings = self.DEFAULT_SETTINGS.copy()

    def _load_token(self) -> str:
        """Load HubSpot token from credential file."""
        if not os.path.exists(self.CREDENTIAL_PATH):
            raise FileNotFoundError(
                f"HubSpot credential not found at {self.CREDENTIAL_PATH}\n"
                "Run: python3 ~/Desktop/save_hubspot_credential.py"
            )

        with open(self.CREDENTIAL_PATH, 'r') as f:
            token = f.read().strip()

        if not token:
            raise ValueError("HubSpot credential file is empty")

        return token

    def test_connection(self) -> bool:
        """Test if the HubSpot API connection works."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/account-info/v3/api-usage/daily/private-apps",
                timeout=10
            )
            if response.status_code == 200:
                print("✓ HubSpot API connection successful")
                return True
            else:
                print(f"✗ HubSpot API error: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"✗ HubSpot connection failed: {e}")
            return False

    def get_list_id_by_name(self, list_name: str) -> Optional[int]:
        """Look up a HubSpot list ID by its name."""
        try:
            # Search for lists
            response = self.session.get(
                f"{self.BASE_URL}/contacts/v1/lists",
                params={"count": 250},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                for lst in data.get('lists', []):
                    if lst.get('name') == list_name:
                        return lst.get('listId')
            return None
        except Exception as e:
            print(f"  Warning: Could not look up list '{list_name}': {e}")
            return None

    def upload_image(self, image_source: str, folder_path: Optional[str] = None) -> Optional[str]:
        """
        Upload an image to HubSpot File Manager from URL or local file path.

        Args:
            image_source: URL or local file path of image to upload
            folder_path: HubSpot folder path (uses default if not specified)

        Returns:
            HubSpot hosted URL or None if failed
        """
        if folder_path is None:
            folder_path = f"/{self.settings['image_folder']}"

        # Strip surrounding quotes from path (users often paste paths with quotes)
        image_source = image_source.strip().strip("'\"")

        try:
            # Check if it's a local file path
            is_local = self._is_local_path(image_source)

            if is_local:
                # Read from local file
                local_path = os.path.expanduser(image_source)
                if not os.path.exists(local_path):
                    print(f"  ✗ Local file not found: {local_path}")
                    return None

                filename = os.path.basename(local_path)
                # Sanitize filename - replace spaces with underscores
                filename = filename.replace(' ', '_')
                print(f"    Reading local file: {local_path}")
                with open(local_path, 'rb') as f:
                    file_content = f.read()
                print(f"    File size: {len(file_content)} bytes")

                # Determine content type from extension
                ext = os.path.splitext(filename)[1].lower()
                content_type_map = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp',
                    '.svg': 'image/svg+xml'
                }
                content_type = content_type_map.get(ext, 'image/png')
            else:
                # Download from URL
                img_response = requests.get(image_source, timeout=30)
                img_response.raise_for_status()
                file_content = img_response.content

                # Get filename from URL
                filename = image_source.split('/')[-1].split('?')[0]
                if not filename:
                    filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

                # Ensure it has an extension
                if '.' not in filename:
                    content_type = img_response.headers.get('content-type', 'image/png')
                    if 'webp' in content_type:
                        filename += '.webp'
                    elif 'jpeg' in content_type or 'jpg' in content_type:
                        filename += '.jpg'
                    else:
                        filename += '.png'
                else:
                    content_type = img_response.headers.get('content-type', 'image/png')

            # Upload to HubSpot
            upload_url = f"{self.BASE_URL}/filemanager/api/v3/files/upload"

            files = {
                'file': (filename, file_content, content_type)
            }

            data = {
                'folderPath': folder_path,
                'options': json.dumps({
                    'access': 'PUBLIC_INDEXABLE',
                    'overwrite': True
                })
            }

            headers = {"Authorization": f"Bearer {self.token}"}

            response = requests.post(
                upload_url,
                files=files,
                data=data,
                headers=headers,
                timeout=60
            )

            if response.status_code in [200, 201]:
                result = response.json()
                hosted_url = result.get('url') or result.get('objects', [{}])[0].get('url')
                print(f"  ✓ Uploaded: {filename}")
                return hosted_url
            else:
                print(f"  ✗ Upload failed: {response.status_code} - {response.text[:100]}")
                return None

        except Exception as e:
            print(f"  ✗ Error uploading image: {e}")
            return None

    def _is_local_path(self, path: str) -> bool:
        """Check if a string is a local file path rather than a URL."""
        # URLs start with http:// or https://
        if path.startswith('http://') or path.startswith('https://'):
            return False
        # Check for common local path patterns
        if path.startswith('/') or path.startswith('~') or path.startswith('./'):
            return True
        # Check for Windows-style paths (C:\, D:\, etc.)
        if len(path) > 2 and path[1] == ':':
            return True
        # Check if the path exists locally
        expanded = os.path.expanduser(path)
        if os.path.exists(expanded):
            return True
        return False

    def _is_valid_image_source(self, source: str) -> bool:
        """Check if a string is a valid image URL or file path."""
        if not source or not isinstance(source, str):
            return False

        source = source.strip().strip("'\"")

        # Must be at least a few characters
        if len(source) < 5:
            return False

        # Check for valid URL
        if source.startswith('http://') or source.startswith('https://'):
            return True

        # Check for valid local path
        if source.startswith('/') or source.startswith('~') or source.startswith('./'):
            expanded = os.path.expanduser(source)
            return os.path.exists(expanded)

        # Check for Windows paths
        if len(source) > 2 and source[1] == ':':
            return os.path.exists(source)

        return False

    def upload_newsletter_images(self, html: str, content: Dict) -> str:
        """
        Upload all newsletter images to HubSpot and replace URLs in HTML.

        Args:
            html: Newsletter HTML
            content: Newsletter content dict

        Returns:
            HTML with HubSpot-hosted image URLs
        """
        print(f"\nUploading images to HubSpot (/{self.settings['image_folder']}/)...")

        # Collect all image sources from content with labels for logging
        image_sources = []

        # Featured articles
        for i, article in enumerate(content.get('featured_articles', [])):
            if article.get('thumbnail_url'):
                image_sources.append({
                    'source': article['thumbnail_url'],
                    'label': f"Featured article {i+1}"
                })

        # Chart
        if content.get('chart', {}).get('image_url'):
            chart_url = content['chart']['image_url']
            print(f"  DEBUG: Chart image_url from content: '{chart_url}'")
            image_sources.append({
                'source': chart_url,
                'label': "Chart of the week"
            })

        # Promotional banner
        if content.get('promotional_banner', {}).get('image_url'):
            image_sources.append({
                'source': content['promotional_banner']['image_url'],
                'label': "Promotional banner"
            })

        # Podcast thumbnail
        if content.get('podcast', {}).get('thumbnail'):
            image_sources.append({
                'source': content['podcast']['thumbnail'],
                'label': "Podcast thumbnail"
            })

        # World articles
        for i, article in enumerate(content.get('world_articles', [])):
            if article.get('thumbnail_url'):
                image_sources.append({
                    'source': article['thumbnail_url'],
                    'label': f"World article {i+1}"
                })

        print(f"\nFound {len(image_sources)} images to process:")
        for item in image_sources:
            print(f"  - {item['label']}: {item['source'][:70]}...")

        # Upload each image and track URL mappings
        url_mapping = {}
        skipped = 0
        failed = 0

        for item in image_sources:
            original_source = item['source']
            label = item['label']

            # Clean the source for processing
            source = original_source.strip().strip("'\"")

            print(f"\n  Processing: {label}")
            print(f"    Original: '{original_source[:60]}...'")
            print(f"    Cleaned:  '{source[:60]}...'")

            # Validate source
            if not self._is_valid_image_source(source):
                print(f"    ⚠ Invalid source - SKIPPED")
                failed += 1
                continue

            # Skip images already hosted on HubSpot
            if 'hubspotusercontent' in source or ('hubspot' in source.lower() and 'fs1' in source):
                print(f"    ○ Already on HubSpot - skipped")
                skipped += 1
                continue

            # Upload from URL or local path
            print(f"    → Uploading to HubSpot...")
            new_url = self.upload_image(source)
            if new_url:
                # Store BOTH original and cleaned versions for replacement
                url_mapping[source] = new_url
                if original_source != source:
                    url_mapping[original_source] = new_url
                print(f"    ✓ Success! New URL: {new_url[:70]}...")
            else:
                print(f"    ✗ Failed to upload")
                failed += 1

        # Replace URLs in HTML
        print(f"\n{'=' * 40}")
        print(f"Replacing {len(url_mapping)} URLs in HTML...")
        updated_html = html
        for old_url, new_url in url_mapping.items():
            # Replace all occurrences (might appear multiple times in HTML)
            count = updated_html.count(old_url)
            if count > 0:
                updated_html = updated_html.replace(old_url, new_url)
                print(f"  ✓ Replaced {count}x: {old_url[:50]}...")
            else:
                # Try URL-encoded version (spaces become %20)
                import urllib.parse
                encoded_url = urllib.parse.quote(old_url, safe=':/')
                count_encoded = updated_html.count(encoded_url)
                if count_encoded > 0:
                    updated_html = updated_html.replace(encoded_url, new_url)
                    print(f"  ✓ Replaced {count_encoded}x (URL-encoded): {old_url[:50]}...")
                else:
                    # Debug: show what we're looking for vs what's in HTML
                    print(f"  ⚠ NOT FOUND: '{old_url[:60]}...'")
                    # Check if a partial match exists
                    if old_url.split('/')[-1] in html:
                        print(f"    (filename exists in HTML but full URL doesn't match)")

        print(f"\n{'=' * 40}")
        print(f"Image upload summary:")
        print(f"  ✓ Uploaded: {len(url_mapping)}")
        print(f"  ○ Skipped (already on HubSpot): {skipped}")
        print(f"  ✗ Failed/Invalid: {failed}")
        print(f"{'=' * 40}")

        return updated_html

    def create_email_draft(
        self,
        html: str,
        subject: str,
        preview_text: str,
        name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create a marketing email draft in HubSpot.

        Args:
            html: Email HTML content
            subject: Email subject line
            preview_text: Email preview text
            name: Internal email name (defaults to date-based name)

        Returns:
            API response dict or None if failed
        """
        if not name:
            name = f"Weekly Dispatch EU - {datetime.now().strftime('%d %B %Y')}"

        print(f"\nCreating email DRAFT: {name}")
        print(f"  From: {self.settings['from_name']} <{self.settings['from_email']}>")
        print(f"  Preview: {preview_text[:80]}..." if preview_text else "  Preview: (none)")
        print(f"  Include lists: {len(self.settings['include_lists'])} lists")
        print(f"  Exclude lists: {len(self.settings['exclude_lists'])} lists")
        print(f"  Exclude emails: {len(self.settings.get('exclude_emails', []))} addresses")

        # Look up list IDs before creating the email
        print("\nLooking up recipient lists...")
        include_list_ids = []
        exclude_list_ids = []

        for list_name in self.settings['include_lists']:
            list_id = self.get_list_id_by_name(list_name)
            if list_id:
                include_list_ids.append(list_id)
                print(f"  ✓ Include: {list_name[:50]}...")
            else:
                print(f"  ? Not found: {list_name[:50]}...")

        for list_name in self.settings['exclude_lists']:
            list_id = self.get_list_id_by_name(list_name)
            if list_id:
                exclude_list_ids.append(list_id)
                print(f"  ✓ Exclude: {list_name[:50]}...")
            else:
                print(f"  ? Not found: {list_name[:50]}...")

        # Build the email payload with all fields
        # Using HubSpot Marketing Email API v3 fields
        email_data = {
            "name": name,
            "subject": subject,
            "state": "DRAFT"
        }

        # Add preview text
        if preview_text:
            email_data["previewText"] = preview_text[:150]

        # Add from name and email
        # Note: HubSpot API expects 'from' as an object with 'email' property
        if self.settings.get('from_name'):
            email_data["fromName"] = self.settings['from_name']
        if self.settings.get('from_email'):
            email_data["from"] = {"email": self.settings['from_email']}
            email_data["replyTo"] = self.settings['from_email']

        # Add recipient lists (sendTo / contactIlsLists)
        if include_list_ids:
            email_data["sendTo"] = {
                "contactIlsLists": include_list_ids
            }

        # Add exclusion lists and emails (dontSendTo)
        exclude_emails = self.settings.get('exclude_emails', [])
        if exclude_list_ids or exclude_emails:
            dont_send_to = {}
            if exclude_list_ids:
                dont_send_to["contactIlsLists"] = exclude_list_ids
            if exclude_emails:
                dont_send_to["emails"] = exclude_emails
            email_data["dontSendTo"] = dont_send_to

        print(f"\n  Sending API request with {len(include_list_ids)} include lists, {len(exclude_list_ids)} exclude lists, {len(exclude_emails)} exclude emails...")

        try:
            response = self.session.post(
                f"{self.BASE_URL}/marketing/v3/emails",
                json=email_data,
                timeout=60
            )

            if response.status_code in [200, 201]:
                result = response.json()
                email_id = result.get('id')
                print(f"\n✓ Email DRAFT created successfully!")
                print(f"  ID: {email_id}")
                print(f"  Name: {name}")
                print(f"  Subject: {subject}")
                print(f"  Preview: {preview_text[:60]}..." if preview_text else "  Preview: (none)")
                print(f"  From: {self.settings['from_name']} <{self.settings['from_email']}>")
                print(f"  Send to: {len(include_list_ids)} lists")
                print(f"  Don't send to: {len(exclude_list_ids)} lists + {len(exclude_emails)} emails")
                print(f"  Status: DRAFT (not sent)")

                return result
            else:
                print(f"✗ Failed to create email: {response.status_code}")
                print(f"  Response: {response.text[:500]}")

                # Try fallback without lists if that was the issue
                if "sendTo" in email_data or "dontSendTo" in email_data:
                    print("\n  Retrying without recipient lists...")
                    fallback_data = {
                        "name": name,
                        "subject": subject,
                        "state": "DRAFT"
                    }
                    if preview_text:
                        fallback_data["previewText"] = preview_text[:150]
                    if self.settings.get('from_name'):
                        fallback_data["fromName"] = self.settings['from_name']
                    if self.settings.get('from_email'):
                        fallback_data["from"] = {"email": self.settings['from_email']}
                        fallback_data["replyTo"] = self.settings['from_email']

                    fallback_response = self.session.post(
                        f"{self.BASE_URL}/marketing/v3/emails",
                        json=fallback_data,
                        timeout=60
                    )

                    if fallback_response.status_code in [200, 201]:
                        result = fallback_response.json()
                        email_id = result.get('id')
                        print(f"\n✓ Email DRAFT created (without lists - configure manually)")
                        print(f"  ID: {email_id}")
                        print(f"  Note: Recipient lists need to be configured manually in HubSpot")

                        # Try to update the email with lists via PATCH
                        self._update_email_recipients(email_id, include_list_ids, exclude_list_ids)

                        return result

                return None

        except Exception as e:
            print(f"✗ Error creating email draft: {e}")
            return None

    def _update_email_recipients(self, email_id: str, include_ids: List[int], exclude_ids: List[int]):
        """Try to update email recipients via PATCH after creation."""
        if not include_ids and not exclude_ids:
            return

        update_data = {}
        if include_ids:
            update_data["sendTo"] = {"contactIlsLists": include_ids}
        if exclude_ids:
            update_data["dontSendTo"] = {"contactIlsLists": exclude_ids}

        try:
            response = self.session.patch(
                f"{self.BASE_URL}/marketing/v3/emails/{email_id}",
                json=update_data,
                timeout=30
            )
            if response.status_code in [200, 201]:
                print(f"  ✓ Updated recipient lists via PATCH")
            else:
                print(f"  ⚠ Could not update lists via PATCH: {response.status_code}")
                print(f"    You may need to configure lists manually in HubSpot")
        except Exception as e:
            print(f"  ⚠ Could not update lists: {e}")

    def _copy_html_to_clipboard(self, html: str):
        """Copy HTML to clipboard and show instructions."""
        import subprocess

        try:
            # Copy to clipboard using pbcopy (macOS)
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(html.encode('utf-8'))
            print("\n✓ HTML copied to clipboard!")
            print("\n" + "=" * 50)
            print("NEXT STEPS - Paste HTML into HubSpot:")
            print("=" * 50)
            print("1. Go to HubSpot → Marketing → Email")
            print("2. Find your draft and click 'Edit'")
            print("3. In the editor, click 'Actions' → 'Edit HTML'")
            print("   (or look for '</>' code icon)")
            print("4. Select all existing content and DELETE it")
            print("5. Paste (Cmd+V) your HTML from clipboard")
            print("6. Save and preview the email")
            print("=" * 50)
        except Exception as e:
            print(f"\n⚠ Could not copy to clipboard: {e}")
            print("  The HTML has been saved to the output folder.")


    def show_settings(self):
        """Display current settings."""
        print("\nCurrent HubSpot Settings:")
        print("-" * 40)
        print(f"  From Email: {self.settings['from_email']}")
        print(f"  From Name: {self.settings['from_name']}")
        print(f"  Image Folder: {self.settings['image_folder']}")
        print(f"\n  Send TO ({len(self.settings['include_lists'])} lists):")
        for lst in self.settings['include_lists'][:3]:
            print(f"    - {lst[:50]}...")
        if len(self.settings['include_lists']) > 3:
            print(f"    ... and {len(self.settings['include_lists']) - 3} more")

        # Combine exclude lists and emails in one section
        exclude_emails = self.settings.get('exclude_emails', [])
        exclude_lists_count = len(self.settings['exclude_lists'])
        exclude_emails_count = len(exclude_emails)
        print(f"\n  Do NOT send to ({exclude_lists_count} lists, {exclude_emails_count} emails):")
        for lst in self.settings['exclude_lists']:
            print(f"    - [List] {lst[:50]}...")
        for email in exclude_emails[:3]:
            print(f"    - [Email] {email}")
        if exclude_emails_count > 3:
            print(f"    ... and {exclude_emails_count - 3} more emails")

    def customize_settings(self):
        """Interactive settings customization."""
        print("\nCustomize HubSpot Settings")
        print("-" * 40)

        # From email
        print(f"\nFrom Email [{self.settings['from_email']}]:")
        new_email = input("> ").strip()
        if new_email:
            self.settings['from_email'] = new_email

        # From name
        print(f"\nFrom Name [{self.settings['from_name']}]:")
        new_name = input("> ").strip()
        if new_name:
            self.settings['from_name'] = new_name

        # Image folder
        print(f"\nImage Folder [{self.settings['image_folder']}]:")
        new_folder = input("> ").strip()
        if new_folder:
            self.settings['image_folder'] = new_folder

        # Include lists
        print(f"\nModify INCLUDE lists? (Currently {len(self.settings['include_lists'])} lists)")
        print("1. Keep current lists")
        print("2. Add a list")
        print("3. Remove a list")
        print("4. Replace all lists")

        choice = input("\nEnter choice (1-4): ").strip()

        if choice == "2":
            new_list = input("Enter list name to add: ").strip()
            if new_list:
                self.settings['include_lists'].append(new_list)
                print(f"✓ Added: {new_list}")
        elif choice == "3":
            print("\nCurrent lists:")
            for i, lst in enumerate(self.settings['include_lists'], 1):
                print(f"  {i}. {lst}")
            idx = input("Enter number to remove: ").strip()
            try:
                idx = int(idx) - 1
                removed = self.settings['include_lists'].pop(idx)
                print(f"✓ Removed: {removed}")
            except:
                print("Invalid selection")
        elif choice == "4":
            print("Enter list names (one per line, empty line to finish):")
            new_lists = []
            while True:
                lst = input("> ").strip()
                if not lst:
                    break
                new_lists.append(lst)
            if new_lists:
                self.settings['include_lists'] = new_lists
                print(f"✓ Set {len(new_lists)} include lists")

        # Exclude lists
        print(f"\nModify EXCLUDE lists? (Currently {len(self.settings['exclude_lists'])} lists)")
        print("1. Keep current lists")
        print("2. Add a list")
        print("3. Remove a list")

        choice = input("\nEnter choice (1-3): ").strip()

        if choice == "2":
            new_list = input("Enter list name to add: ").strip()
            if new_list:
                self.settings['exclude_lists'].append(new_list)
                print(f"✓ Added: {new_list}")
        elif choice == "3":
            print("\nCurrent lists:")
            for i, lst in enumerate(self.settings['exclude_lists'], 1):
                print(f"  {i}. {lst}")
            idx = input("Enter number to remove: ").strip()
            try:
                idx = int(idx) - 1
                removed = self.settings['exclude_lists'].pop(idx)
                print(f"✓ Removed: {removed}")
            except:
                print("Invalid selection")

        print("\n✓ Settings updated")

    def publish_newsletter(
        self,
        html: str,
        content: Dict,
        subject: str,
        preview_text: str,
        upload_images: bool = True
    ) -> Optional[Dict]:
        """
        Full newsletter publishing workflow:
        1. Upload images to HubSpot (optional)
        2. Create email DRAFT (never sends automatically)

        Args:
            html: Newsletter HTML
            content: Newsletter content dict
            subject: Email subject
            preview_text: Preview text
            upload_images: Whether to upload images to HubSpot

        Returns:
            Email creation result or None
        """
        print("\n" + "=" * 50)
        print("HUBSPOT NEWSLETTER PUBLISHING")
        print("=" * 50)

        # Test connection first
        if not self.test_connection():
            print("\n✗ Cannot connect to HubSpot. Check your credentials.")
            return None

        # Show current settings
        self.show_settings()

        # Ask if user wants to customize
        print("\n1. Use these settings")
        print("2. Customize settings")

        choice = input("\nEnter choice (1-2): ").strip()
        if choice == "2":
            self.customize_settings()
            self.show_settings()

        # Final confirmation
        print("\n" + "-" * 40)
        print("IMPORTANT: This will create a DRAFT email only.")
        print("The email will NOT be sent automatically.")
        print("-" * 40)
        print("\nProceed with creating draft?")
        print("1. Yes, create draft")
        print("2. Cancel")

        confirm = input("\nEnter choice (1-2): ").strip()
        if confirm != "1":
            print("\n✗ Cancelled")
            return None

        # Upload images if requested
        if upload_images:
            html = self.upload_newsletter_images(html, content)

        # Create email draft
        result = self.create_email_draft(
            html=html,
            subject=subject,
            preview_text=preview_text
        )

        if result:
            # Store the updated HTML in the result for the caller
            result['_updated_html'] = html
            print("\n" + "=" * 50)
            print("✓ Newsletter DRAFT created in HubSpot!")
            print("=" * 50)
            print("\nNext steps:")
            print("1. Go to HubSpot → Marketing → Email")
            print("2. Find the draft: 'Weekly Dispatch EU - [date]'")
            print("3. Configure recipient lists if needed")
            print("4. Review content and send/schedule")

        return result


def main():
    """Test HubSpot integration."""
    integration = HubSpotIntegration()

    print("Testing HubSpot connection...")
    if integration.test_connection():
        print("\nHubSpot integration is working!")
        integration.show_settings()
    else:
        print("\nFailed to connect. Check your token.")


if __name__ == "__main__":
    main()
