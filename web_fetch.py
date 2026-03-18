import time
import requests
from urllib.parse import urlparse
from collections import defaultdict

_rate_limits = defaultdict(list)
RATE_LIMIT_WINDOW = 60
MAX_REQUESTS_PER_DOMAIN = 10

def _check_rate_limit(domain: str) -> bool:
    now = time.time()
    _rate_limits[domain] = [t for t in _rate_limits[domain] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limits[domain]) >= MAX_REQUESTS_PER_DOMAIN:
        return False
    _rate_limits[domain].append(now)
    return True

def fetch_page(url: str, timeout: int = 15) -> dict:
    parsed = urlparse(url)
    domain = parsed.netloc

    if not _check_rate_limit(domain):
        return {
            "success": False,
            "error": f"Rate limit exceeded for {domain}. Max {MAX_REQUESTS_PER_DOMAIN} requests per {RATE_LIMIT_WINDOW}s.",
            "content": None,
            "status_code": 429,
        }

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (SeVIn AI Hub/1.0; compatible; +https://github.com/sevin-hub)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if "text" in content_type or "json" in content_type:
            content = response.text
        else:
            content = f"[Binary content: {content_type}]"

        return {
            "success": True,
            "error": None,
            "content": content,
            "status_code": response.status_code,
            "url": response.url,
            "content_type": content_type,
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": f"Request timed out after {timeout}s", "content": None, "status_code": None}
    except requests.exceptions.ConnectionError as e:
        return {"success": False, "error": f"Connection error: {e}", "content": None, "status_code": None}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"HTTP error: {e}", "content": None, "status_code": e.response.status_code}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}", "content": None, "status_code": None}


if __name__ == "__main__":
    result = fetch_page("https://httpbin.org/get")
    print(f"Success: {result['success']}")
    if result["content"]:
        print(result["content"][:500])
