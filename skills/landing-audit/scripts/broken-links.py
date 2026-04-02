#!/usr/bin/env python3
"""Check all links on a page for broken URLs."""
import argparse, json, sys
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--timeout', type=int, default=10)
    parser.add_argument('--max-links', type=int, default=100)
    args = parser.parse_args()

    try:
        resp = requests.get(args.url, timeout=args.timeout,
                          headers={'User-Agent': 'LandingAuditBot/1.0'})
        resp.raise_for_status()
    except Exception as e:
        print(json.dumps({'error': f'Cannot fetch page: {e}'}))
        sys.exit(1)

    soup = BeautifulSoup(resp.text, 'html.parser')

    # Collect links from <a href> and <img src>
    urls = set()
    for tag in soup.find_all('a', href=True):
        urls.add(urljoin(args.url, tag['href']))
    for tag in soup.find_all('img', src=True):
        urls.add(urljoin(args.url, tag['src']))
    for tag in soup.find_all('link', href=True):
        urls.add(urljoin(args.url, tag['href']))
    for tag in soup.find_all('script', src=True):
        urls.add(urljoin(args.url, tag['src']))

    # Filter: only http/https, skip anchors, mailto, tel
    filtered = []
    for u in urls:
        parsed = urlparse(u)
        if parsed.scheme in ('http', 'https') and not u.startswith(('mailto:', 'tel:', 'javascript:')):
            filtered.append(u)
    filtered = filtered[:args.max_links]

    broken = []
    ok_count = 0
    for u in filtered:
        try:
            r = requests.head(u, timeout=args.timeout, allow_redirects=True,
                            headers={'User-Agent': 'LandingAuditBot/1.0'})
            if r.status_code >= 400:
                broken.append({'url': u, 'status': r.status_code})
            else:
                ok_count += 1
        except requests.exceptions.Timeout:
            broken.append({'url': u, 'status': 'timeout'})
        except Exception:
            broken.append({'url': u, 'status': 'error'})

    print(json.dumps({
        'total': len(filtered),
        'ok': ok_count,
        'broken_count': len(broken),
        'broken': broken,
    }, ensure_ascii=False))

if __name__ == '__main__':
    main()
