from src.shopee import fetch_product as get_product_status

class ProductMonitor:
    def __init__(self):
        self.products = {}

    def add_product(self, url: str):
        try:
            # ambil shop_id & item_id dari URL
            if "-i." in url:
                parts = url.split("-i.")
            elif "i." in url:
                parts = url.split("i.")
            else:
                print("❌ URL invalid (tidak mengandung i.<shop_id>.<item_id>)")
                return False, None

            ids_part = parts[1].split("?")[0]  # buang query string
            ids = ids_part.split(".")
            if len(ids) < 2:
                print("❌ URL invalid (gagal parsing shop_id & item_id)")
                return False, None

            shop_id, item_id = ids[0], ids[1]

            print(f"➡️ Parsed shop_id={shop_id}, item_id={item_id}")
            data = get_product_status(shop_id, item_id)

            if not data:
                print("❌ Gagal fetch Shopee API")
                return False, None

            product_info = {
                "name": data.get("name", "Unknown"),
                "stock": data.get("stock", "N/A"),
                "price": data.get("price", "N/A"),
                "item_id": item_id,
                "shop_id": shop_id,
                "url": url,
            }

            # simpan ke cache
            self.products[item_id] = product_info
            return True, product_info

        except Exception as e:
            print(f"❌ add_product error: {e}")
            return False, None
