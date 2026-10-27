#!/usr/bin/env python3
"""Download every full-resolution image from a Behance project link.

Usage: behance.py <project-url> [out-dir]   (default out-dir: ~/Downloads)
"""
import os, re, subprocess, sys

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
# Behance's bot-check page sets this exact cookie via JS then reloads. The value is
# a fixed, non-rotating constant (verified: same value across unrelated projects),
# so sending it up front skips the extra round trip.
CHALLENGE_COOKIE = "js_challenge_value=7815265484dc282eaf18dfed2a407a185502835cc4572742354d1659087efb507e865090acfdabbc5db4aafb3dd71a0830d67baed9ac61b84c3815b25f16c29a"

def curl(url, cookie=None, out=None):
    cmd = ["curl", "-sSL", "-A", UA]
    if cookie:
        cmd += ["-b", cookie]
    cmd += [url]
    if out:
        return subprocess.run(cmd + ["-o", out]).returncode == 0
    return subprocess.run(cmd, capture_output=True, text=True).stdout

def fetch_project_page(url):
    html = curl(url, cookie=CHALLENGE_COOKIE)
    if "js_challenge_value=" in html and "<title>" not in html:
        # The constant rotated. Extract the fresh value and retry once.
        m = re.search(r"js_challenge_value=([a-f0-9]+)", html)
        if not m:
            sys.exit("Could not get past Behance's bot check.")
        html = curl(url, cookie=f"js_challenge_value={m.group(1)}")
    return html

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    url = sys.argv[1]
    out_dir = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/Downloads")
    os.makedirs(out_dir, exist_ok=True)

    m = re.search(r"/gallery/(\d+)", url)
    if not m:
        sys.exit(f"Not a Behance project URL: {url}")
    project_id = m.group(1)

    html = fetch_project_page(url)
    # Page HTML is JSON-escaped in places, so "/" shows up as "\/" — normalize before matching.
    html = html.replace("\\/", "/")
    files = sorted(set(re.findall(r"project_modules/source/([\w.]+\.(?:jpg|jpeg|png|gif))", html)))
    if not files:
        sys.exit("No images found in this project (deleted, private, or Behance changed the page).")

    for i, fname in enumerate(files, 1):
        ext = os.path.splitext(fname)[1]
        out = os.path.join(out_dir, f"behance_{project_id[-6:]}_{i}{ext}")
        src_url = f"https://mir-s3-cdn-cf.behance.net/project_modules/source/{fname}"
        if curl(src_url, out=out):
            print(out)
        else:
            print(f"Failed: {fname}", file=sys.stderr)

main()
