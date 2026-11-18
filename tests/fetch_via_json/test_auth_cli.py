"""Simple CLI to test Phase 1 authentication.

Usage:
    python -m tests.fetch_via_json.test_auth_cli
"""

from __future__ import annotations

import sys

from sotd.fetch_via_json.json_scraper import (
    get_reddit_cookies,
    get_reddit_json,
    get_reddit_session,
)


def main() -> int:
    """Test Phase 1 authentication."""
    print("[INFO] Phase 1 Authentication Test")
    print("=" * 60)

    # Get cookies
    cookies = get_reddit_cookies()

    if not cookies:
        print("\n[WARN] No cookie found. You can:")
        print("  1. Continue with unauthenticated requests (10 QPM limit)")
        print("  2. Set REDDIT_SESSION_COOKIE and run again")
        print("\nProceed with unauthenticated? (y/n): ", end="")
        response = input().strip().lower()
        if response != "y":
            print("[INFO] Exiting. Set cookie and try again.")
            return 1
    else:
        print(f"\n[INFO] Cookie found: {list(cookies.keys())}")

    # Test authenticated request
    print("\n[INFO] Testing authenticated request to Reddit...")
    try:
        session = get_reddit_session(cookies=cookies)
        test_url = "https://www.reddit.com/r/wetshaving/about.json"
        response = session.get(test_url, timeout=10)

        if response.status_code == 200:
            print(f"[INFO] ✅ Successfully fetched {test_url} (status: {response.status_code})")
        else:
            print(f"[WARN] Got status code {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Failed to make request: {e}")
        return 1

    # Test JSON fetch
    print("\n[INFO] Testing JSON fetch...")
    try:
        get_reddit_json(
            "https://www.reddit.com/r/wetshaving/about.json", cookies=cookies
        )
        print("[INFO] ✅ Successfully fetched JSON data")
    except Exception as e:
        print(f"[ERROR] Failed to fetch JSON: {e}")
        return 1

    print("\n[INFO] ✅ Phase 1 authentication validation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
