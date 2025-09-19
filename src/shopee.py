# src/shopee.py
import re
import requests
import json

def parse_curl_file(file_path="curl.txt"):
    """
    Parse curl.txt (should contain full curl command copied from DevTools).
    Mengembalikan: (curl_url or None, headers dict, cookies dict)
    """
    try:
        txt = open(file_path, "r", encoding="utf-8", errors="ignore").read()
    except FileNotFoundError:
        return None, {}, {}

    # ambil URL dari `curl '...url...'` atau curl "url"
    url_match = re.search(r"curl\s+['\"]([^'\"]+)['\"]", txt)
    curl_url = url_match.group(1) if url_match else None

    headers = {}
    # cari -H 'Header: value' atau -H "Header: value"
    for m in re.finditer(r"-H\s+['\"]([^:]+):\s*([^'\"]+)['\"]", txt):
        k = m.group(1).strip()
        v = m.group(2).strip()
        # bersihin trailing backslashes dan kutipan sisa
        v = v.rstrip("\\ ").strip().strip("'\"")
        headers[k] = v

    # juga support lines yang dimulai dengan two spaces then -H '...'
    for m in re.finditer(r"\n\s*-H\s+['\"]([^:]+):\s*([^'\"]+)['\"]", txt):
        k = m.group(1).strip()
        v = m.group(2).strip()
        v = v.rstrip("\\ ").strip().strip("'\"")
        headers[k] = v

    # parse cookies: -b 'a=1; b=2' OR header cookie: 'cookie: a=1; b=2'
    cookies = {}
    cookie_match = re.search(r"-b\s+['\"]([^'\"]+)['\"]", txt)
    if cookie_match:
        cookie_str = cookie_match.group(1)
        for part in cookie_str.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                cookies[k.strip()] = v.strip()
    else:
        # check cookie header
        ck = headers.get("cookie") or headers.get("Cookie")
        if ck:
            for part in ck.split(";"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    cookies[k.strip()] = v.strip()

    return curl_url, headers, cookies


def get_product_status(item_id: str, shop_id: str, curl_file: str = "curl.txt"):
    """
    Fetch product info via pdp/get_pc.
    Returns dict {name, price, stock} or None.
    """
    # allow item_id/shop_id be ints or strings
    item_id = str(item_id)
    shop_id = str(shop_id)

    # load headers & cookies from curl.txt if present
    curl_url, headers, cookies = parse_curl_file(curl_file)

    # fallback minimal headers if none found
    if not headers:
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/114.0.0.0 Safari/537.36",
            "accept": "application/json, text/plain, */*",
        }

    # ensure referer present and valid
    if "referer" not in {k.lower(): v for k, v in headers.items()}:
        # prefer explicit header key 'referer' (case-insensitive)
        headers["referer"] = f"https://shopee.co.id/product/{shop_id}/{item_id}"

    # use the canonical URL (we set tz_offset_in_minutes correct)
    api_url = (
        "https://shopee.co.id/api/v4/pdp/get_pc"
        f"?item_id={item_id}&shop_id={shop_id}&tz_offset_in_minutes=420&detail_level=0"
    )

    # DEBUG prints — ini penting untuk diagnosa
    print("\n=== DEBUG: Shopee Request ===")
    print("API URL:", api_url)
    if curl_url:
        print("curl.txt URL:", curl_url)
    print("Headers used (sample):")
    # print limited headers to avoid leaking huge cookie in console, but show keys
    for k in list(headers.keys())[:20]:
        v = headers[k]
        shortv = v if len(v) < 120 else (v[:110] + "…")
        print(f"  {k}: {shortv}")
    if cookies:
        print("Cookies keys:", list(cookies.keys()))
    print("=============================\n")

    try:
        # send request with headers and cookies if any
        resp = requests.get(api_url, headers=headers, cookies=cookies or None, timeout=15)
    except Exception as e:
        print("❌ Request failed:", e)
        return None

    # debug status
    print("Response status:", resp.status_code)

    # try parse JSON; if fails, print text snippet
    try:
        j = resp.json()
    except Exception:
        txt = resp.text
        snippet = txt[:1500] + ("…" if len(txt) > 1500 else "")
        print("❌ Response is not JSON. Snippet:\n", snippet)
        return None

    # if no 'data' field -> print JSON keys & small dump for diagnosis
    if "data" not in j:
        small = json.dumps(j, indent=2, ensure_ascii=False)[:3000]
        print("❌ Invalid response (no data field). JSON head:\n", small)
        return None

    data = j["data"]
    # parse price/stock from models or top-level
    price = None
    stock = None
    if data.get("models"):
        try:
            price = int(data["models"][0].get("price", 0)) // 100000
            stock = int(data["models"][0].get("stock", 0))
        except Exception:
            # fallback safe extraction
            price = int(data["models"][0].get("price") or 0) // 100000
            stock = int(data["models"][0].get("stock") or 0)
    else:
        price = int(data.get("price", 0)) // 100000 if data.get("price") is not None else 0
        stock = int(data.get("stock", 0)) if data.get("stock") is not None else 0

    name = data.get("name") or data.get("title") or "Unknown"

    result = {
        "name": name,
        "price": int(price or 0),
        "stock": int(stock or 0),
    }

    print("✅ Parsed product:", result["name"], "| price:", result["price"], "| stock:", result["stock"])
    return result
