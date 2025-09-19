from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
import json
from src.shopee import get_product_status
from src.monitor import ProductMonitor
import re

# Keyboard custom untuk memudahkan penggunaan
main_keyboard = [['/list', '/add'], ['/remove', '/help']]

def is_valid_shopee_url(url):
    """Validasi URL Shopee"""
    pattern = r'https?://shopee\.co\.id/.*\.i\.\d+\.\d+'
    return re.match(pattern, url) is not None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengirim pesan selamat datang ketika command /start diberikan."""
    user = update.effective_user
    welcome_message = (
        f"Halo {user.mention_html()}! 👋\n\n"
        "Saya adalah Bot Monitor Restock Produk Shopee. Saya akan membantu memantau produk Shopee dan memberi notifikasi ketika produk kembali tersedia.\n\n"
        "Perintah yang tersedia:\n"
        "/add - Tambah produk untuk dimonitor\n"
        "/list - Lihat daftar produk yang dimonitor\n"
        "/remove - Hapus produk dari monitor\n"
        "/help - Tampilkan bantuan\n\n"
        "Gunakan keyboard di bawah untuk memudahkan navigasi!"
    )
    
    await update.message.reply_html(
        welcome_message,
        reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan pesan bantuan."""
    help_text = (
        "🤖 <b>Bot Monitor Restock Shopee</b>\n\n"
        "Saya akan memantau produk Shopee dan mengirim notifikasi ketika produk kembali tersedia (restock).\n\n"
        "📋 <b>Perintah yang tersedia:</b>\n"
        "/start - Memulai bot dan menampilkan pesan selamat datang\n"
        "/add - Tambahkan produk Shopee untuk dimonitor\n"
        "/list - Lihat daftar semua produk yang sedang dimonitor\n"
        "/remove - Hapus produk dari daftar monitor\n"
        "/help - Tampilkan pesan bantuan ini\n\n"
        "🔗 <b>Cara menambahkan produk:</b>\n"
        "1. Salin URL produk dari Shopee\n"
        "2. Ketik /add dan ikuti instruksi\n"
        "3. Atau langsung kirim URL produknya\n\n"
        "Contoh URL: https://shopee.co.id/Nama-Produk-i.12345.67890"
    )
    await update.message.reply_html(help_text)

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memulai proses penambahan produk."""
    await update.message.reply_text(
        "Silakan kirim URL produk Shopee yang ingin Anda pantau.\n\n"
        "Contoh: https://shopee.co.id/Nama-Produk-i.12345.67890",
        reply_markup=ReplyKeyboardRemove()
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani URL yang dikirim pengguna."""
    url = update.message.text.strip()
    
    if not is_valid_shopee_url(url):
        await update.message.reply_text(
            "URL tidak valid. Pastikan URL berasal dari Shopee Indonesia (shopee.co.id) dan dalam format yang benar.\n\n"
            "Contoh format: https://shopee.co.id/Nama-Produk-i.12345.67890"
        )
        return
    
    # Cek status produk
    product_info = get_product_status(url)
    if not product_info:
        await update.message.reply_text(
            "Gagal mengambil informasi produk. Pastikan URL benar dan produk masih tersedia."
        )
        return
    
    # Simpan produk ke database
    monitor = ProductMonitor()
    success = monitor.add_product(url, product_info['name'])
    
    if success:
        status_msg = "tersedia" if product_info['available'] else "habis"
        message = (
            f"✅ Produk berhasil ditambahkan!\n\n"
            f"📦 <b>{product_info['name']}</b>\n"
            f"💰 Harga: Rp {product_info['price']:,}\n"
            f"📊 Status: {status_msg}\n\n"
            f"Saya akan memantau produk ini dan memberi tahu Anda ketika restock."
        )
        await update.message.reply_html(message, reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True))
    else:
        await update.message.reply_text(
            "Gagal menambahkan produk. Silakan coba lagi nanti.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )

async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan daftar produk yang sedang dipantau."""
    monitor = ProductMonitor()
    
    if not monitor.products:
        await update.message.reply_text(
            "Belum ada produk yang dipantau. Gunakan /add untuk menambahkan produk.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
        return
    
    message = "📋 <b>Daftar Produk yang Dipantau</b>\n\n"
    
    for i, product in enumerate(monitor.products, 1):
        status = "✅ Tersedia" if product['last_status']['available'] else "❌ Habis"
        message += (
            f"{i}. <b>{product['alias']}</b>\n"
            f"   Status: {status}\n"
            f"   Stok: {product['last_status']['stock']}\n"
            f"   Harga: Rp {product['last_status']['price']:,}\n\n"
        )
    
    await update.message.reply_html(message)

async def remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menghapus produk dari daftar pantauan."""
    monitor = ProductMonitor()
    
    if not monitor.products:
        await update.message.reply_text(
            "Belum ada produk yang dipantau.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
        return
    
    # Buat keyboard dengan daftar produk untuk dihapus
    keyboard = []
    for i, product in enumerate(monitor.products, 1):
        keyboard.append([f"Hapus {i}: {product['alias']}"])
    
    keyboard.append(['Batal'])
    
    await update.message.reply_text(
        "Pilih produk yang ingin dihapus:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def handle_remove_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani pilihan produk yang akan dihapus."""
    selection = update.message.text.strip()
    
    if selection == 'Batal':
        await update.message.reply_text(
            "Penghapusan dibatalkan.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
        return
    
    if selection.startswith('Hapus '):
        try:
            index = int(selection.split(' ')[1].split(':')[0]) - 1
            monitor = ProductMonitor()
            
            if 0 <= index < len(monitor.products):
                removed_product = monitor.products.pop(index)
                monitor.save_products()
                
                await update.message.reply_text(
                    f"Produk '{removed_product['alias']}' berhasil dihapus dari daftar pantauan.",
                    reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
                )
            else:
                await update.message.reply_text(
                    "Indeks tidak valid.",
                    reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
                )
        except (ValueError, IndexError):
            await update.message.reply_text(
                "Format tidak valid. Silakan pilih dari opsi yang diberikan.",
                reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
            )
