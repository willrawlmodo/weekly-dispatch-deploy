"""
Test script to create an empty draft email in HubSpot.
This verifies the integration works without any real content.
"""

from integrations.hubspot import HubSpotIntegration

def main():
    print("=" * 50)
    print("HUBSPOT DRAFT TEST")
    print("=" * 50)
    print("\nThis will create an EMPTY draft email in HubSpot.")
    print("No content, no recipients, no images.")
    print("\nAfter running, check HubSpot → Marketing → Email")
    print("You should see a draft called 'TEST DRAFT - Delete Me'")
    print("=" * 50)

    confirm = input("\nProceed? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        return

    # Initialize HubSpot
    print("\nConnecting to HubSpot...")
    hub = HubSpotIntegration()

    # Test connection first
    if not hub.test_connection():
        print("\n✗ Connection failed. Check your token.")
        return

    # Create minimal empty draft
    print("\nCreating empty draft...")

    result = hub.create_email_draft(
        html="<p>This is a test draft. Please delete.</p>",
        subject="TEST - Please Delete",
        preview_text="This is a test email draft",
        name="TEST DRAFT - Delete Me"
    )

    if result:
        print("\n" + "=" * 50)
        print("✓ SUCCESS!")
        print("=" * 50)
        print("\nNow go to HubSpot → Marketing → Email")
        print("Find the draft called 'TEST DRAFT - Delete Me'")
        print("Verify it's a DRAFT (not sent)")
        print("Then delete it manually.")
    else:
        print("\n✗ Failed to create draft. Check errors above.")


if __name__ == "__main__":
    main()
