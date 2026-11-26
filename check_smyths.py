import requests
from playwright.sync_api import sync_playwright

NTFY_TOPIC = "galway_ps5_alert_9921"  

SMYTHS_URLS = {
    "PS5 Slim Disc Standalone (232873)": "https://smythstoys.com",
    "PS5 Slim Disc + Extra DualSense (800574)": "https://smythstoys.com",
    "PS5 Slim Disc + Astro Bot (800867)": "https://smythstoys.com",
    "PS5 Slim Disc + Spider-Man 2 (800828)": "https://smythstoys.com",
    "PS5 Slim Disc + €20 Wallet Top-Up (800626)": "https://smythstoys.com",
}

TARGET_STORES = [
    "galway",
    "athlone",
    "limerick ennis road",
    "limerick parkway",
    "tralee",
    "claremorris",
]


def send_alert(title: str, message: str, url: str, urgent: bool = True):
    requests.post(
        f"https://ntfy.sh{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": "urgent" if urgent else "low",
            "Click": url,
        },
        timeout=15,
    )


def main():
    hits = []
    blocked_count = 0
    verified_pages = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="en-IE",
            timezone_id="Europe/Dublin",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        for name, url in SMYTHS_URLS.items():
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=35000)
                page.wait_for_timeout(2500)

                for btn_text in ["Accept All", "Accept Cookies", "Accept all cookies"]:
                    cookie_btn = page.locator(f"button:has-text('{btn_text}')").first
                    if cookie_btn.count() > 0:
                        cookie_btn.click()
                        page.wait_for_timeout(1000)
                        break

                body_text = page.inner_text("body").lower()

                if "playstation 5" not in body_text:
                    print(f"[BLOCKED/UNEXPECTED PAGE] {name} - Title: {page.title()}")
                    blocked_count += 1
                    continue

                verified_pages += 1
                print(f"[VERIFIED] Loaded desktop page for {name}")

                
                if "add to basket" in body_text and "home delivery out of stock" not in body_text and "out of stock" not in body_text:
                    hits.append((f"[HOME DELIVERY] {name}", url))

              
                stock_selectors = [
                    "button:has-text('Check Stock')",
                    "a:has-text('Check Stock')",
                    "button:has-text('Click & Collect')",
                    "button:has-text('Find a store')",
                    "[data-testid*='store']",
                ]
                for selector in stock_selectors:
                    btn = page.locator(selector).first
                    if btn.count() > 0 and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(2000)
                        break

                full_text = page.inner_text("body").lower()
                for line in full_text.splitlines():
                    for store in TARGET_STORES:
                        if store in line and "in stock" in line and "out of stock" not in line:
                            hits.append((f"[CLICK & COLLECT - {store.upper()}] {name}", url))

            except Exception as e:
                print(f"[ERROR] {name}: {e}")

        browser.close()

    if hits:
        for msg, link in hits:
            print(f"IN STOCK: {msg}")
            send_alert("PS5 SLIM IN STOCK AT SMYTHS!", msg, link, urgent=True)
    elif blocked_count > 0 and verified_pages == 0:
        print("WARNING: Smyths blocked GitHub's cloud IP.")
        send_alert(
            "Smyths Bot Blocked by Firewall",
            "Smyths served an Access Denied / CAPTCHA page to the cloud server.",
            SMYTHS_URLS["PS5 Slim Disc Standalone (232873)"],
            urgent=False,
        )
    else:
        print(f"Not in stock across all {verified_pages} verified Smyths desktop pages.")
        send_alert(
            "Smyths PS5 Status: Not in stock",
            f"Verified {verified_pages}/5 Smyths pages — still out of stock in Western Ireland.",
            SMYTHS_URLS["PS5 Slim Disc Standalone (232873)"],
            urgent=False,
        )


if __name__ == "__main__":
    main()
