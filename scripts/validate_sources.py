"""
Validate that all source URLs in data/sources.json are reachable.
Reports status for each URL and exits with non-zero code if any fail.
"""

import json
import sys
import requests

SOURCES_PATH = "data/sources.json"
TIMEOUT_SECONDS = 15


def load_sources(path: str) -> list[dict]:
    """Load sources from JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    return data["sources"]


def check_url(url: str, timeout: int = TIMEOUT_SECONDS) -> tuple[bool, int | None, str]:
    """
    Check if a URL returns HTTP 200.
    Returns (is_reachable, status_code, message).
    """
    try:
        response = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        })
        is_ok = response.status_code == 200
        return is_ok, response.status_code, "OK" if is_ok else f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return False, None, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, None, "Connection Error"
    except requests.exceptions.RequestException as e:
        return False, None, str(e)


def main():
    print(f"Loading sources from {SOURCES_PATH}...")
    sources = load_sources(SOURCES_PATH)
    print(f"Found {len(sources)} sources\n")

    failures = []
    for source in sources:
        sid = source["id"]
        url = source["url"]
        title = source["title"]

        is_reachable, status_code, message = check_url(url)
        status_icon = "✓" if is_reachable else "✗"
        status_line = f"  {status_icon} [{sid}] {title}"

        if status_code is not None:
            status_line += f" (HTTP {status_code})"
        else:
            status_line += f" ({message})"

        print(status_line)

        if not is_reachable:
            failures.append({"id": sid, "url": url, "reason": message})

    print(f"\n{'='*60}")
    if failures:
        print(f"FAILURES: {len(failures)}/{len(sources)} sources unreachable")
        for f in failures:
            print(f"  - {f['id']}: {f['url']} ({f['reason']})")
        sys.exit(1)
    else:
        print(f"SUCCESS: All {len(sources)} sources are reachable")


if __name__ == "__main__":
    main()
