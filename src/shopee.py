# src/shopee.py
import re
import json
import os
import requests
from typing import Tuple, Dict, Optional

CURL_FILE = os.path.join(os.path.dirname(__file__), "..", "curl.txt")
ERROR_LOG = os.path.join(os.path.dirname(__file__), "..", "shopee_error.log")


def load_headers_and_cookies_from_curl(curl_file: str = CURL_FILE) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Parse a 'curl' string saved in curl.txt into headers and cookies dicts.
    Works with cURL lines like: -H 'key: value' and -H 'cookie: a=b; c=d'
    """
    headers: Dict[str, str] = {}
    cookies: Dict[str, str] = {}

    if not os.path.isfile(curl_file):
        return headers, cookies

    text = open(curl_file, "r", encoding="utf-8").read()

    # Find all -H 'Key: value' or --header 'Key: value'
    for m in re.finditer(r"-H\s+'([^:]+):\s*(.*?)'", text):
        key = m.group(1).strip()
        val = m.group(2).strip()
        if key.lower() == "cookie":
            # parse cookies
            for c in val.split(";"):
                if "=" in c:
                    k, v = c.strip().split("=", 1)
                    cookies[k] = v
        else:
            headers[key] = val

    # Also try to capture a --cookie "..." or --header "cookie: ..."
    for m in re.finditer(r"--cookie\s+['\"]?(.*?)['\"]?(?:\s|$)", text):
        raw = m.group(1).strip()
        for c in raw.split(";"):
            if "=" in c:
                k, v = c.strip().split("=", 1)
                cookies[k] = v

    return headers, cookies


def load_cookies_from_env(env_var="SHOPEE_COOKIE") -> Dict[str, str]:
    """
    Fallback: read cookies from environment variable (format: 'a=1; b=2; ...').
    """
    raw = os.getenv(env_var, "")
    cookies = {}
    if raw:
        for c in raw.split(";"):
            if "=" in c:
                k, v = c.strip().split("=", 1)
                cookies[k] = v
    return cookies


def log_error(msg: str):
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def fetch_product(shop_id: str, item_id: str, curl_file: str = CURL_FILE) -> Optional[dict]:
    """
    Fetch product detail using headers + cookies parsed from curl.txt (or env).
    Returns a dict with name/stock/price or None if fail.
    """
    try:
        # Use tz_offset_minutes (correct param)
        url = (
            "https://shopee.co.id/api/v4/pdp/get_pc"
            f"?item_id={item_id}&shop_id={shop_id}&tz_offset_minutes=420&detail_level=0"
        )

        # Load headers + cookies from curl.txt
        headers, cookies = load_headers_and_cookies_from_curl(curl_file)

        # Minimal headers if curl.txt not present or missing keys
        default_headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "referer": f"https://shopee.co.id/product-i.{shop_id}.{item_id}",
            "x-api-source": "pc",
            "x-requested-with": "XMLHttpRequest",
            "if-none-match-": "*",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }
        # merge - prefer values from curl.txt
        merged_headers = {**default_headers, **headers}

        # If no cookies parsed from curl.txt try env
        if not cookies:
            cookies = load_cookies_from_env()

        # If still no cookies, leave cookies empty (requests will send none)
        s = requests.Session()
        s.headers.update(merged_headers)
        if cookies:
            s.cookies.update(cookies)

        print("\n=== DEBUG: Shopee Request ===")
        print("API URL:", url)
        print("Headers sample:", list(merged_headers.keys())[:10])
        print("Cookies keys:", list(s.cookies.keys()))
        print("=============================\n")

        # request
        resp = s.get(url, timeout=15)
        print("Response status:", resp.status_code)

        if resp.status_code == 403:
            msg = f"403 Forbidden for item {item_id} shop {shop_id} — cookies/headers likely invalid or blocked."
            print("❌ Shopee API error: 403")
            log_error(msg)
            return None

        if resp.status_code != 200:
            msg = f"HTTP {resp.status_code} for item {item_id} shop {shop_id}"
            print("❌ Shopee API error:", resp.status_code)
            log_error(msg)
            return None

        try:
            data = resp.json()
        except Exception as e:
            print("❌ Failed to decode JSON:", e)
            log_error(f"JSON decode error: {e} | resp_text_snippet: {resp.text[:300]}")
            return None

        # Normal path
        if isinstance(data, dict) and "data" in data and data["data"]:
            pdata = data["data"]
            return {
                "name": pdata.get("name", "Unknown"),
                "stock": pdata.get("stock", "N/A"),
                "price": pdata.get("price", "N/A"),
            }

        # explicit Shopee error code handling
        if isinstance(data, dict) and "error" in data:
            err = data.get("error")
            print(f"⚠️ Shopee returned error code: {err}")
            log_error(f"Item {item_id} Shop {shop_id} returned error {err} | raw_head: {json.dumps(dict(list(data.items())[:8]))}")
            # return a marker so monitor can store something (optional)
            return {
                "name": f"ErrorCode-{err}",
                "stock": "N/A",
                "price": "N/A",
            }

        # Unknown response
        print("❌ Invalid response (no data field). JSON head:")
        try:
            head = json.dumps(dict(list(data.items())[:8]), indent=2)
        except Exception:
            head = str(data)[:400]
        print(head)
        log_error(f"Invalid response for {item_id}@{shop_id} | head: {head}")
        return None

    except Exception as e:
        print("❌ fetch_product error:", e)
        log_error(f"Exception fetch_product: {e}")
        return None
