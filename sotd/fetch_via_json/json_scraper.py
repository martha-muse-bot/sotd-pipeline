"""JSON-based Reddit scraping functionality.

This module provides functions to fetch Reddit content via JSON API
instead of using the PRAW API. It supports cookie-based authentication
and handles rate limiting gracefully.

Uses Reddit's public JSON endpoints (e.g., .json URLs) - no OAuth required.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except ImportError:
    # Fallback for older requests versions
    from requests.packages.urllib3.util.retry import Retry  # type: ignore[attr-defined]


def _find_project_root() -> Path:
    """Find project root by going up from this file's location.

    This file is at: sotd/fetch_via_json/json_scraper.py
    Project root is 3 levels up.
    """
    return Path(__file__).parent.parent.parent


def _get_cookie_file_paths() -> list[Path]:
    """Get list of cookie file paths to check, in priority order.

    Returns:
        List of paths: [project_root/.reddit_cookies.json, project_root/sotd/.reddit_cookies.json, ~/.reddit_cookies.json]
    """
    project_root = _find_project_root()
    return [
        project_root / ".reddit_cookies.json",  # Project root (preferred)
        project_root / "sotd" / ".reddit_cookies.json",  # Alternative location
        Path.home() / ".reddit_cookies.json",  # Home directory (fallback)
    ]


def _get_preferred_cookie_file() -> Path:
    """Get the preferred location for saving cookies (project root)."""
    return _find_project_root() / ".reddit_cookies.json"


def _get_test_cookie_file() -> Path:
    """Get path to test cookie file (for rate limit testing).

    Returns:
        Path to .reddit_cookies_test.json in project root
    """
    return _find_project_root() / ".reddit_cookies_test.json"


def print_cookie_instructions() -> None:
    """Print step-by-step instructions for extracting Reddit session cookie."""
    preferred_file = _get_preferred_cookie_file()
    print("\n[INFO] No Reddit session cookie found. To enable better rate limits:\n")
    print("1. Open your browser and log in to Reddit (https://www.reddit.com/login)")
    print("2. Open Developer Tools (F12 or Cmd+Option+I)")
    print("3. Go to Application tab → Cookies → https://www.reddit.com")
    print("4. Find the 'reddit_session' cookie")
    print("5. Copy its value")
    print('6. Set environment variable: export REDDIT_SESSION_COOKIE="your_cookie_value"')
    print(f'   Or save to {preferred_file}: {{"reddit_session": "your_cookie_value"}}\n')
    print("Then run the command again. Cookie will be saved for future use.\n")


def get_reddit_cookies(force_refresh: bool = False) -> dict:
    """Get Reddit session cookies from config file or environment variable.

    Checks for cookies in this priority order:
    1. Environment variable: REDDIT_SESSION_COOKIE
    2. Project root: .reddit_cookies.json or sotd/.reddit_cookies.json
    3. Home directory: ~/.reddit_cookies.json (fallback)

    If cookies don't exist or are expired:
    1. Print clear instructions to terminal for manual cookie export
    2. Wait for user to provide cookie (via env var or file)
    3. Validate cookie format
    4. Save to project root .reddit_cookies.json for future use
    5. Return cookies dict

    Args:
        force_refresh: If True, ignore existing cookies and prompt for new ones

    Returns:
        Dictionary of cookies (e.g., {"reddit_session": "abc123..."})
    """
    # Check environment variable first
    env_cookie = os.getenv("REDDIT_SESSION_COOKIE")
    if env_cookie and not force_refresh:
        # Parse cookie from env var (format: "reddit_session=abc123..." or just "abc123...")
        if "=" in env_cookie:
            cookie_name, cookie_value = env_cookie.split("=", 1)
            if cookie_name.strip() == "reddit_session":
                return {"reddit_session": cookie_value.strip()}
        else:
            # Assume it's just the cookie value
            return {"reddit_session": env_cookie.strip()}

    # Check cookie files in priority order (project root first, then home)
    cookie_file_paths = _get_cookie_file_paths()
    for cookie_file in cookie_file_paths:
        if cookie_file.exists() and not force_refresh:
            try:
                with open(cookie_file, "r") as f:
                    cookie_data = json.load(f)

                # Check if cookie is expired
                if "expires_at" in cookie_data:
                    try:
                        expires_at = datetime.fromisoformat(
                            cookie_data["expires_at"].replace("Z", "+00:00")
                        )
                        if expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
                            if "reddit_session" in cookie_data:
                                return {"reddit_session": cookie_data["reddit_session"]}
                    except (ValueError, KeyError):
                        pass

                # If no expiration or expired, check if we have a cookie value
                if "reddit_session" in cookie_data:
                    return {"reddit_session": cookie_data["reddit_session"]}
            except (json.JSONDecodeError, IOError):
                continue

    # No valid cookie found - print instructions
    print_cookie_instructions()

    # Check if user provided cookie after instructions
    env_cookie = os.getenv("REDDIT_SESSION_COOKIE")
    if env_cookie:
        if "=" in env_cookie:
            cookie_name, cookie_value = env_cookie.split("=", 1)
            if cookie_name.strip() == "reddit_session":
                cookie_value = cookie_value.strip()
            else:
                cookie_value = env_cookie.strip()
        else:
            cookie_value = env_cookie.strip()

        # Save cookie for future use (prefer project root)
        preferred_file = _get_preferred_cookie_file()
        now = datetime.now(timezone.utc)
        # Calculate expiration (6 months from now, approximately 180 days)
        expires_at = now + timedelta(days=180)

        cookie_data = {
            "reddit_session": cookie_value,
            "captured_at": now.isoformat().replace("+00:00", "Z"),
            "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        }
        try:
            # Ensure parent directory exists
            preferred_file.parent.mkdir(parents=True, exist_ok=True)
            with open(preferred_file, "w") as f:
                json.dump(cookie_data, f, indent=2)
            print(f"[INFO] Cookie saved to {preferred_file}")
        except IOError as e:
            print(f"[WARN] Could not save cookie to {preferred_file}: {e}")

        return {"reddit_session": cookie_value}

    # Still no cookie - return empty dict (unauthenticated)
    # Note: Warning messages are handled by the caller (run.py)
    return {}


def get_reddit_session(
    cookies: Optional[dict] = None, oauth_creds: Optional[dict] = None
) -> requests.Session:
    """Create authenticated requests session with cookies or OAuth.

    Args:
        cookies: Dictionary of cookies (e.g., {"reddit_session": "abc123..."})
        oauth_creds: Dictionary with REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET (optional)

    Returns:
        requests.Session configured with appropriate authentication
    """
    session = requests.Session()

    # Set User-Agent to avoid bot detection
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )

    # Add cookies if provided
    if cookies:
        session.cookies.update(cookies)

    # Configure retry strategy
    # Note: 429 (rate limit) is NOT in status_forcelist - we handle it manually
    # with proper Retry-After header respect in get_reddit_json()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],  # Server errors only, not rate limits
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def _calculate_delay(cookies: Optional[dict] = None) -> float:
    """Calculate base delay between requests based on authentication status.

    This is the starting delay. The actual delay will be adjusted dynamically
    based on rate limit headers from Reddit responses.

    Args:
        cookies: Optional cookies dict

    Returns:
        Base delay in seconds
    """
    if cookies and "reddit_session" in cookies:
        return 0.1  # Cookie-based auth: start fast, adjust based on rate limit headers
    elif os.getenv("REDDIT_CLIENT_ID"):
        return 1.0  # OAuth: 1 second
    else:
        return 6.0  # Unauthenticated: 6+ seconds (conservative for unauthenticated)


def _calculate_dynamic_delay(
    response: requests.Response, base_delay: float, verbose: bool = False
) -> float:
    """Calculate dynamic delay based on rate limit headers from response.

    Reddit sends x-ratelimit-remaining, x-ratelimit-reset, and x-ratelimit-used
    on every response. We use these to proactively manage rate limits and avoid 429s.

    Strategy (time-based pacing):
    - High remaining (> 20): Burst mode - use minimal delay (base_delay)
    - Medium remaining (10-20): Moderate - slight increase, consider reset time
    - Low remaining (< 10): Time-based pacing - calculate delay = (reset / remaining) * 0.9
      This ensures remaining requests are spread across the reset window to avoid
      exhausting the budget before the window resets.

    Args:
        response: The HTTP response from Reddit
        base_delay: Base delay in seconds
        verbose: If True, print rate limit info

    Returns:
        Calculated delay in seconds
    """
    # Extract rate limit headers (case-insensitive)
    headers = response.headers
    remaining = None
    reset = None
    used = None

    # Try various header name formats
    for header_name in headers:
        header_lower = header_name.lower()
        if header_lower == "x-ratelimit-remaining":
            try:
                remaining = float(headers[header_name])
            except (ValueError, TypeError):
                pass
        elif header_lower == "x-ratelimit-reset":
            try:
                reset = float(headers[header_name])
            except (ValueError, TypeError):
                pass
        elif header_lower == "x-ratelimit-used":
            try:
                used = float(headers[header_name])
            except (ValueError, TypeError):
                pass

    # If we don't have rate limit headers, use base delay
    if remaining is None:
        return base_delay

    # Calculate dynamic delay using time-based pacing algorithm
    if remaining > 20:
        # Burst mode - plenty of requests remaining, use minimal delay
        delay = base_delay
    elif remaining > 10:
        # Moderate remaining - slight increase, but also check reset time
        if reset is not None and reset > 0:
            time_per_request = (reset / remaining) * 0.9  # Safety margin
            delay = max(base_delay * 1.5, time_per_request)
        else:
            delay = base_delay * 1.5
    elif remaining > 0:
        # Low remaining - pace across reset window using time-based calculation
        if reset is not None and reset > 0:
            time_per_request = (reset / remaining) * 0.9  # Safety margin
            delay = max(time_per_request, base_delay)  # Don't go below base
            delay = min(delay, 60.0)  # Cap at 60s to avoid excessive waits
        else:
            # No reset time available, use conservative multiplier
            delay = base_delay * 5.0
    else:
        # Exhausted - should rarely happen, wait for reset
        delay = reset if reset and reset > 0 else base_delay * 10.0

    if verbose and remaining is not None:
        reset_str = f", reset in {reset:.0f}s" if reset is not None else ""
        used_str = f", used {used:.0f}" if used is not None else ""
        print(
            f"[INFO] Rate limit: {remaining:.0f} remaining{used_str}{reset_str}, delay: {delay:.2f}s"
        )

    return delay


def _handle_rate_limit(
    response: requests.Response, url: str, delay: float, session: requests.Session
) -> requests.Response:
    """Handle rate limiting by respecting Reddit's rate limit headers.

    Reddit sends x-ratelimit-reset header indicating when the limit resets (in seconds).
    If not available, falls back to exponential backoff.

    This function may be called multiple times if rate limits persist.

    Args:
        response: The rate-limited response
        url: URL being fetched
        delay: Base delay in seconds
        session: requests.Session to use for retry

    Returns:
        New response after waiting (may still be 429 if rate limit persists)
    """
    # Check for Reddit's rate limit reset header (preferred)
    rate_limit_reset = response.headers.get("x-ratelimit-reset") or response.headers.get(
        "X-RateLimit-Reset"
    )
    if rate_limit_reset:
        try:
            wait_time = int(float(rate_limit_reset))
            print(
                f"[WARN] Rate limit hit, waiting {wait_time}s (rate limit resets in {wait_time}s)"
            )
            time.sleep(wait_time)
        except (ValueError, TypeError):
            # Fall through to exponential backoff if header is invalid
            rate_limit_reset = None

    # Fallback: Check for standard Retry-After header (some APIs use this)
    if not rate_limit_reset:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                wait_time = int(retry_after)
                print(f"[WARN] Rate limit hit, waiting {wait_time}s (from Retry-After header)")
                time.sleep(wait_time)
            except (ValueError, TypeError):
                # Fall through to exponential backoff
                pass

    # Final fallback: exponential backoff
    if not rate_limit_reset and not response.headers.get("Retry-After"):
        wait_time = delay * 2
        print(
            f"[WARN] Rate limit hit, waiting {wait_time}s (exponential backoff, no reset time available)"
        )
        time.sleep(wait_time)

    # Retry the request (may still get 429, caller should check)
    response = session.get(url, timeout=30)
    return response


def get_reddit_json(
    url: str,
    cookies: Optional[dict] = None,
    session: Optional[requests.Session] = None,
    verbose: bool = False,
) -> "Dict[str, Any] | List[Dict[str, Any]]":
    """Fetch JSON from Reddit URL with proper headers, cookies, and error handling.

    Returns a dict for submission/about endpoints and a list for comment-thread
    endpoints (Reddit's two-list comment JSON shape).

    This function proactively manages rate limits by checking x-ratelimit-remaining
    and x-ratelimit-reset headers on every response, adjusting delays dynamically
    to avoid 429 errors.

    Args:
        url: Reddit URL to fetch (should end in .json or have ?format=json)
        cookies: Optional cookies dict
        session: Optional requests.Session (if provided, cookies are ignored)
        verbose: If True, print rate limit information

    Returns:
        Parsed JSON as dictionary

    Raises:
        requests.RequestException: If request fails after retries
        json.JSONDecodeError: If response is not valid JSON
    """
    if session is None:
        session = get_reddit_session(cookies=cookies)

    # Ensure URL ends with .json or has format=json
    if not url.endswith(".json") and "format=json" not in url:
        if "?" in url:
            url = f"{url}&format=json"
        else:
            url = f"{url}?format=json"

    base_delay = _calculate_delay(cookies)
    delay = base_delay  # Start with base delay, will be adjusted dynamically

    try:
        response = session.get(url, timeout=30)

        # Handle rate limiting - may need multiple retries
        max_rate_limit_retries = 3
        retry_count = 0
        while response.status_code == 429 and retry_count < max_rate_limit_retries:
            response = _handle_rate_limit(response, url, delay, session)
            retry_count += 1

        # If still rate limited after retries, raise error
        if response.status_code == 429:
            raise requests.HTTPError(
                f"Rate limit exceeded after {max_rate_limit_retries} retries. "
                f"Please wait before making more requests.",
                response=response,
            )

        response.raise_for_status()

        # Calculate dynamic delay based on rate limit headers (proactive management)
        # This helps avoid 429s by adjusting delay based on remaining requests
        delay = _calculate_dynamic_delay(response, base_delay, verbose=verbose)

        # Parse JSON
        json_data = response.json()

        # Add delay between requests (dynamically calculated based on rate limit status)
        time.sleep(delay)

        return json_data
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON response from {url}: {e}")
        raise
