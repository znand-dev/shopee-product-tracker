from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from src.monitor import ProductMonitor
import os

monitor = ProductMonitor()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Kirim link produk Shopee pakai /add <url>")

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Format salah. Gunakan:\n`/add <url>`", parse_mode="Markdown")
        return

    url = context.args[0]
    success, product_info = monitor.add_product(url)

    if success:
        msg = (
            f"✅ Produk berhasil ditambahkan!\n\n"
            f"🛒 Nama: {product_info['name']}\n"
            f"📦 Stok: {product_info['stock']}\n"
            f"💰 Harga: {product_info['price']}\n"
            f"🔗 {product_info['url']}"
        )
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("❌ Gagal tambah produk (URL salah / API error).")

def run_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN belum diset!")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_product))
    print("🤖 Bot Telegram is running...")
    app.run_polling()
