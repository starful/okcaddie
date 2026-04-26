import sys
import requests

SESSION = requests.Session()
SESSION.trust_env = False


def check(url):
    response = SESSION.get(url, timeout=20, allow_redirects=True)
    ok = response.status_code == 200
    print(f"{'OK' if ok else 'FAIL'} {response.status_code} {url}")
    return ok


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://okcaddie.net").rstrip("/")
    urls = [
        f"{base}/",
        f"{base}/courses?lang=en&page=1",
        f"{base}/courses?lang=ko&page=1",
        f"{base}/guide?lang=en",
        f"{base}/sitemap.xml",
        f"{base}/robots.txt",
    ]

    failures = [url for url in urls if not check(url)]
    if failures:
        print("\nSmoke test failed:")
        for url in failures:
            print(f"- {url}")
        sys.exit(1)

    print("\nSmoke test passed.")


if __name__ == "__main__":
    main()
