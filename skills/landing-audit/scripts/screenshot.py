#!/usr/bin/env python3
"""Take mobile + desktop screenshots and extract page text/HTML."""
import argparse, time, os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output-dir', default='/tmp')
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    ts = int(time.time())
    mobile_png = os.path.join(args.output_dir, f'landing-audit-mobile-{ts}.png')
    desktop_png = os.path.join(args.output_dir, f'landing-audit-desktop-{ts}.png')
    text_file = os.path.join(args.output_dir, f'landing-audit-text-{ts}.txt')
    html_file = os.path.join(args.output_dir, f'landing-audit-html-{ts}.html')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-gpu'])

        # Mobile screenshot
        mobile = browser.new_context(
            viewport={'width': 375, 'height': 812},
            device_scale_factor=2,
            is_mobile=True,
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) Mobile/15E148'
        )
        page = mobile.new_page()
        page.goto(args.url, wait_until='load', timeout=60000)
        page.wait_for_timeout(2000)
        page.screenshot(path=mobile_png, full_page=True)

        # Extract text and HTML from mobile page
        text = page.inner_text('body')
        html = page.content()
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text)
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)

        mobile.close()

        # Desktop screenshot
        desktop = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = desktop.new_page()
        page.goto(args.url, wait_until='load', timeout=60000)
        page.wait_for_timeout(2000)
        page.screenshot(path=desktop_png, full_page=True)
        desktop.close()

        browser.close()

    import json
    print(json.dumps({
        'mobile_screenshot': mobile_png,
        'desktop_screenshot': desktop_png,
        'text_file': text_file,
        'html_file': html_file,
    }))

if __name__ == '__main__':
    main()
