import requests
import json
import re

def parse_curl(file_path="curl.txt"):
    """Parse curl.txt jadi URL, headers, cookies"""
    with open(file_path) as f:
        curl_cmd = f.read()

    # ambil URL
    url_match = re.search(r"curl '([^']+)'", curl_cmd)
    url = url_match.group(1) if url_match else None

    # ambil headers
    headers = {}
    for m in re.finditer(r"-H '([^:]+): ([^']+)'", curl_cmd):
        headers[m.group(1).strip()] = m.group(2).strip()

    # ambil cookies
    cookies = {}
    cookie_match = re.search(r"-b '([^']+)'", curl_cmd)
    if cookie_match:
        cookie_str = cookie_match.group(1)
        for part in cookie_str.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                cookies[k.strip()] = v.strip()

    return url, headers, cookies

def safe_int(value):
    """Convert value ke int, fallback 0 kalau None atau error"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

def fetch_product(file_path="curl.txt"):
    """Fetch produk dari PDP v4 Shopee dan parsing stock/harga/status"""
    url, headers, cookies = parse_curl(file_path)
    if not url:
        print("❌ Gagal parsing URL dari curl.txt")
        return None

    print(f"➡️ Fetching: {url}")
    resp = requests.get(url, headers=headers, cookies=cookies, timeout=20)
    
    try:
        data = resp.json()
    except Exception:
        print("❌ Response bukan JSON:", resp.text[:200])
        return None

    # cek response
    if "data" not in data or "item" not in data["data"]:
        print("❌ API gagal / data item tidak ada:", data)
        return None

    item = data["data"]["item"]
    name = item.get("title", "N/A")
    status = item.get("status", 0)           # 1 = aktif, 0 = nonaktif

    # ambil harga & stok
    models = item.get("models") or item.get("model_list") or []
    products_info = []

    if models:
        for m in models:
            model_name = m.get("name", "")
            price = safe_int(m.get("price")) // 100000
            stock = safe_int(m.get("stock"))
            products_info.append({
                "model": model_name,
                "price": price,
                "stock": stock,
                "available": stock > 0,
            })
    else:
        # kalau tidak ada model, ambil stok dan harga item langsung
        price = safe_int(item.get("price")) // 100000
        stock = safe_int(item.get("stock"))
        products_info.append({
            "model": "",
            "price": price,
            "stock": stock,
            "available": stock > 0,
        })

    return {"name": name, "status": status, "products": products_info}


if __name__ == "__main__":
    result = fetch_product("curl.txt")
    print(json.dumps(result, indent=2))

