#!/usr/bin/env python3
"""HK-geo-blocked site scraper template (curl_cffi + residential SOCKS5).

Works against Fastly/WAF-protected HK sites (e.g. marathonsports.hkstore.com
returns 405 for non-HK IPs). Needs the `scrape` venv on Zeabur:
  ~/.venvs/scrape/bin/python hkstore_scrape.py

Credentials: read from ~/.proxy-env (source it first) — NEVER hardcode.
  . ~/.proxy-env && ~/.venvs/scrape/bin/python hkstore_scrape.py
"""
import os
import re
import sys
import time
import json
from urllib.parse import quote, urlsplit, urlunsplit

from curl_cffi import requests

PROXY = os.environ.get("ALL_PROXY") or os.environ.get("HTTPS_PROXY")
if not PROXY:
    sys.exit("Set ALL_PROXY first: . ~/.proxy-env")
PROXIES = {"http": PROXY, "https": PROXY}
# Proxy exits (username suffix): __cr.hk = HK residential, __cr.us = US.

IMG_RE = re.compile(r"/media/catalog/product/[^\"'\s]+?\.(?:jpg|jpeg|png|webp)")


def fetch(url, referer=None):
    headers = {"Referer": referer} if referer else {}
    return requests.get(url, impersonate="chrome", proxies=PROXIES,
                        headers=headers, timeout=40)


def scrape_product(name, raw_url, outdir):
    p = urlsplit(raw_url)
    url = urlunsplit((p.scheme, p.netloc, quote(p.path), "", ""))
    r = fetch(url)
    if r.status_code != 200:
        return "HTTP_%s" % r.status_code
    urls = []
    for i in IMG_RE.findall(r.text):
        full = ("https://marathonsports.hkstore.com" + i).split("?")[0]
        if full not in urls:
            urls.append(full)
    os.makedirs(outdir, exist_ok=True)
    got = 0
    for i, iu in enumerate(urls, 1):
        for _ in (1, 2):
            try:
                ir = fetch(iu, referer=url)
                if ir.status_code == 200 and len(ir.content) > 2000:
                    ext = iu.rsplit(".", 1)[-1]
                    with open(os.path.join(outdir, "%s_%02d.%s" % (name, i, ext)), "wb") as f:
                        f.write(ir.content)
                    got += 1
                    break
            except Exception:
                time.sleep(1)
    return "OK %d imgs" % got


if __name__ == "__main__":
    # args: pairs of "name url"
    args = sys.argv[1:]
    if len(args) % 2 or not args:
        sys.exit("usage: hkstore_scrape.py <name1> <url1> [name2 url2 ...]")
    report = {}
    for i in range(0, len(args), 2):
        report[args[i]] = scrape_product(args[i], args[i + 1], "/tmp/scrape/" + args[i])
        time.sleep(1)
    print(json.dumps(report, indent=1, ensure_ascii=False))
