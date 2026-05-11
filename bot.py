#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sqlite3
import random
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ==================== YAPILANDIRMA ====================
TOKEN = "8725491244:AAGy5VztUUcPJDLE9ZAFUVaxcRlcf2QwVMM"
ADMIN_IDS = [8695334986] 

# BURAYA 2 KANALIN KULLANICI ADINI VE LİNKİNİ YAZ
REQUIRED_CHANNELS = ["@PaulWalkerArsiv", "@BYZANTIUMS"] 
CHANNEL_LINKS = [
    ["📢 1. Kanala Katıl", "https://t.me/PaulWalkerArsiv"],
    ["📢 2. Kanala Katıl", "https://t.me/BYZANTIUMS"]
]

# ==================== LOGLAMA ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== YARDIMCI FONKSİYONLAR ====================
async def check_sub(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Kullanıcının her iki kanala da abone olup olmadığını kontrol eder."""
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except BadRequest:
            continue # Bot kanalda değilse geç
        except Exception as e:
            logger.error(f"Kontrol hatası ({channel}): {e}")
            continue
    return True

def get_sub_keyboard():
    keyboard = []
    for text, link in CHANNEL_LINKS:
        keyboard.append([InlineKeyboardButton(text, url=link)])
    keyboard.append([InlineKeyboardButton("✅ Katıldım / Kontrol Et", callback_data="check_subscription")])
    return InlineKeyboardMarkup(keyboard)

# ==================== VERİTABANI ====================
def init_db():
    conn = sqlite3.connect("market_bot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, balance REAL DEFAULT 0,
        referral_code TEXT, referred_by INTEGER, referral_count INTEGER DEFAULT 0, last_daily TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, price REAL NOT NULL, stock INTEGER NOT NULL, description TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, quantity INTEGER, total_price REAL, order_date TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS promo_codes (
        code TEXT PRIMARY KEY, value INTEGER, max_uses INTEGER, used_count INTEGER DEFAULT 0,
        promo_type TEXT, target_product_id INTEGER, created_by INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS promo_uses (user_id INTEGER, code TEXT, PRIMARY KEY (user_id, code))""")
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect("market_bot.db")
    conn.row_factory = sqlite3.Row
    return conn

# ==================== KLAVYELER ====================
def get_main_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("🛍 Ürünler", callback_data="products")],
        [InlineKeyboardButton("💰 Bakiyem", callback_data="balance")],
        [InlineKeyboardButton("🎁 Günlük Ödül", callback_data="daily_reward")],
        [InlineKeyboardButton("📢 Referans", callback_data="referral"), InlineKeyboardButton("🏆 Top 10", callback_data="top10")],
        [InlineKeyboardButton("💎 Daha Fazla Alım Satım", callback_data="more_trade")],
        [InlineKeyboardButton("🎟 Kod Kullan", callback_data="enter_promo")],
        [InlineKeyboardButton("👥 Yetkililer", callback_data="staff_list")],
        [InlineKeyboardButton("👤 Admin İletişim", callback_data="contact_admin")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Ürün Ekle", callback_data="admin_add_product")],
        [InlineKeyboardButton("❌ Ürün Sil", callback_data="admin_remove_product")],
        [InlineKeyboardButton("🎟 Kod Oluştur", callback_data="admin_create_promo")],
        [InlineKeyboardButton("⭐ Puan Ekle (ID)", callback_data="admin_give_point")],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== HANDLERLAR ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not await check_sub(user.id, context):
        await update.message.reply_text(
            f"⚠️ Botu kullanabilmek için her iki kanalımıza da katılmalısınız!",
            reply_markup=get_sub_keyboard()
        )
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
    if not c.fetchone():
        ref_code = f"REF{user.id}{random.randint(1000, 9999)}"
        referred_by = None
        if context.args:
            try:
                ref_by_code = context.args[0]
                c.execute("SELECT user_id FROM users WHERE referral_code = ?", (ref_by_code,))
                ref_row = c.fetchone()
                if ref_row and ref_row['user_id'] != user.id:
                    referred_by = ref_row['user_id']
                    c.execute("UPDATE users SET balance = balance + 1, referral_count = referral_count + 1 WHERE user_id = ?", (referred_by,))
            except: pass
        
        c.execute("INSERT INTO users (user_id, username, first_name, balance, referral_code, referred_by) VALUES (?, ?, ?, ?, ?, ?)",
                  (user.id, user.username, user.first_name, 0.0, ref_code, referred_by))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"👋 Selam {user.first_name}! Market botuna hoş geldin.", reply_markup=get_main_keyboard(user.id))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in ADMIN_IDS:
        await update.message.reply_text("🔐 Admin Paneli:", reply_markup=get_admin_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "check_subscription":
        if await check_sub(user_id, context):
            await query.answer("✅ Teşekkürler, tüm kanallara üyesiniz!", show_alert=True)
            await query.edit_message_text("🏠 Ana Menü:", reply_markup=get_main_keyboard(user_id))
        else:
            await query.answer("❌ Lütfen her iki kanala da katıldığınızdan emin olun!", show_alert=True)
        return

    if not await check_sub(user_id, context):
        await query.answer("⚠️ Devam etmek için kanallara katılmalısın!", show_alert=True)
        return

    await query.answer()
    conn = get_db()
    c = conn.cursor()

    if data == "main_menu":
        await query.edit_message_text("🏠 Ana Menü:", reply_markup=get_main_keyboard(user_id))

    elif data == "staff_list":
        text = "👑 *Kurucu*\n@WaIkerPaul\n\n🛠 *Adminler*\n@Hatayapmam99\n@WaIkerPaul"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Geri", callback_data="main_menu")]]), parse_mode="Markdown")

    elif data == "more_trade":
        trade_text = (
            "🔥 *Lenax x Paul*\n━━━━━━━━━━━━━━━━━━\n"
            "✅ *Satılık Sağlam Takaslar:*\n"
            "- banka hesabları+m\n- FAKE NO - TG-WP❤️‍🔥\n- RAT-PC-ANDROİD\n- C.C\n- C.C CHECKER💰\n"
            "- TOLLAR VE CHECKERLAR\n- HESAB KAPATMA MT\n- PİSHİNG(HESAB ÇALMAK İÇİN BÜTÜN SOSYAL MEDYALARDA GEÇERLİ)\n- PANEL\n"
            "GALERİ SİZMA VB.❤️‍🔥\nHESAB KAPATMA KANAL PATLATMA RUS OSİNT (TR) VE DAHA NE İSTERSENJZ VARDİR\n\n"
            "ELİMDE HERTÜRLÜ TOOL&SCRİPT BULUNUR\n"
            "TELEGRAM BANNED MT&TOOL  İNSTAGRAM BANNET MT&TOOL\n"
            "DDOS,VDS,BOT YAPIM\n"
            "WP,TG FRESH OTP SAHTE İBAN HESABI OYUN HESAPLARI TÜM PLATFORMLAR SMS ONAY HER ÜLKE VE HER PLATFORM BOT BASIM  HEPSİ SATILIK\n\n"
            "+1-+49-+44-+90 fake numaralar mevcuttur\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🛒 *Satın alım için:* @Hatayapmam99"
        )
        await query.edit_message_text(trade_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Geri", callback_data="main_menu")]]), parse_mode="Markdown")

    elif data == "balance":
        c.execute("SELECT balance, referral_count FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        await query.edit_message_text(f"💰 Bakiyeniz: {row['balance']}₺\n📢 Toplam Referans: {row['referral_count']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Geri", callback_data="main_menu")]]))

    elif data == "daily_reward":
        c.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
        last = c.fetchone()['last_daily']
        today = str(datetime.date.today())
        if last == today:
            await query.edit_message_text("❌ Bugün ödülünü zaten aldın!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Geri", callback_data="main_menu")]]))
        else:
            gift = round(random.uniform(1, 5), 2)
            c.execute("UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id = ?", (gift, today, user_id))
            conn.commit()
            await query.edit_message_text(f"🎁 Tebrikler! Bugünün şansına {gift}₺ kazandın.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Geri", callback_data="main_menu")]]))

    elif data == "products":
        c.execute("SELECT * FROM products WHERE stock > 0")
        prods = c.fetchall()
        if not prods:
            await query.edit_message_text("📦 Şu an stokta ürün bulunmuyor.", reply_markup=get_main_keyboard(user_id))
        else:
            keyboard = [[InlineKeyboardButton(f"{p['name']} ({p['price']}₺)", callback_data=f"view_{p['product_id']}")] for p in prods]
            keyboard.append([InlineKeyboardButton("🔙 Geri", callback_data="main_menu")])
            await query.edit_message_text("🛍 Ürünler:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("view_"):
        pid = int(data.split("_")[1])
        c.execute("SELECT * FROM products WHERE product_id = ?", (pid,))
        p = c.fetchone()
        discount = 0
        saved = context.user_data.get(f"promo_{user_id}")
        if saved and saved['type'] == 'discount' and saved['target'] == pid:
            discount = saved['value']
        
        final_price = p['price'] - (p['price'] * discount / 100)
        text = f"📦 *Ürün:* {p['name']}\n📝 *Açıklama:* {p['description']}\n💰 *Fiyat:* {final_price}₺\n🎟 *Aktif İndirim:* %{discount}"
        keyboard = [[InlineKeyboardButton("💳 Satın Al", callback_data=f"buy_{pid}_{final_price}")], [InlineKeyboardButton("🔙 Geri", callback_data="products")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("buy_"):
        parts = data.split("_")
        pid, price = int(parts[1]), float(parts[2])
        c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        if c.fetchone()['balance'] < price:
            await query.edit_message_text("❌ Yetersiz bakiye!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Geri", callback_data="products")]]))
        else:
            c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
            c.execute("UPDATE products SET stock = stock - 1 WHERE product_id = ?", (pid,))
            conn.commit()
            if f"promo_{user_id}" in context.user_data: del context.user_data[f"promo_{user_id}"]
            await query.edit_message_text("✅ Satın alım başarılı!", reply_markup=get_main_keyboard(user_id))

    elif data == "enter_promo":
        context.user_data["awaiting_promo"] = True
        await query.edit_message_text("🎟 Kodunuzu girin:")

    elif data == "admin_give_point":
        context.user_data["admin_action"] = "get_uid"
        await query.edit_message_text("⭐ Puan eklenecek Kullanıcı ID:")

    elif data == "admin_create_promo":
        context.user_data["admin_action"] = "p_name"
        await query.edit_message_text("1. Kod ismini yazın:")

    elif data == "admin_add_product":
        context.user_data["admin_action"] = "add_p_name"
        await query.edit_message_text("Ürün adını yazın:")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_sub(user_id, context):
        await update.message.reply_text("⚠️ İşlem yapabilmek için kanallara katılmalısın!", reply_markup=get_sub_keyboard())
        return

    text = update.message.text
    action = context.user_data.get("admin_action")
    conn = get_db()
    c = conn.cursor()

    if context.user_data.get("awaiting_promo"):
        context.user_data["awaiting_promo"] = False
        c.execute("SELECT * FROM promo_codes WHERE code = ?", (text.upper(),))
        p = c.fetchone()
        if p and p['used_count'] < p['max_uses']:
            if p['promo_type'] == 'point':
                c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (p['value'], user_id))
                c.execute("UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?", (p['code'],))
                conn.commit()
                await update.message.reply_text(f"✅ {p['value']}₺ eklendi.")
            else:
                context.user_data[f"promo_{user_id}"] = {"type": "discount", "value": p['value'], "target": p['target_product_id']}
                await update.message.reply_text(f"✅ İndirim tanımlandı.")
        else:
            await update.message.reply_text("❌ Geçersiz kod.")
        return

    if action == "get_uid":
        context.user_data["target_uid"] = text
        context.user_data["admin_action"] = "get_amount"
        await update.message.reply_text("Miktar:")
    elif action == "get_amount":
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (float(text), context.user_data["target_uid"]))
        conn.commit()
        await update.message.reply_text(f"✅ Puan eklendi.")
        context.user_data["admin_action"] = None

    elif action == "p_name":
        context.user_data["tmp_code"] = text.upper()
        context.user_data["admin_action"] = "p_type"
        await update.message.reply_text("Tür: 1(%) 2(₺)")
    elif action == "p_type":
        context.user_data["tmp_type"] = "discount" if text == "1" else "point"
        context.user_data["admin_action"] = "p_val"
        await update.message.reply_text("Değer:")
    elif action == "p_val":
        context.user_data["tmp_val"] = int(text)
        context.user_data["admin_action"] = "p_target"
        await update.message.reply_text("Ürün ID (0=puan):")
    elif action == "p_target":
        context.user_data["tmp_target"] = int(text)
        context.user_data["admin_action"] = "p_limit"
        await update.message.reply_text("Limit:")
    elif action == "p_limit":
        c.execute("INSERT INTO promo_codes (code, value, max_uses, promo_type, target_product_id) VALUES (?,?,?,?,?)",
                  (context.user_data["tmp_code"], context.user_data["tmp_val"], int(text), context.user_data["tmp_type"], context.user_data["tmp_target"]))
        conn.commit()
        await update.message.reply_text("✅ Oluşturuldu.")
        context.user_data["admin_action"] = None

    elif action == "add_p_name":
        context.user_data["new_p_name"] = text
        context.user_data["admin_action"] = "add_p_price"
        await update.message.reply_text("Fiyat:")
    elif action == "add_p_price":
        context.user_data["new_p_price"] = float(text)
        context.user_data["admin_action"] = "add_p_stock"
        await update.message.reply_text("Stok:")
    elif action == "add_p_stock":
        context.user_data["new_p_stock"] = int(text)
        context.user_data["admin_action"] = "add_p_desc"
        await update.message.reply_text("Açıklama:")
    elif action == "add_p_desc":
        c.execute("INSERT INTO products (name, price, stock, description) VALUES (?,?,?,?)",
                  (context.user_data["new_p_name"], context.user_data["new_p_price"], context.user_data["new_p_stock"], text))
        conn.commit()
        await update.message.reply_text("✅ Ürün eklendi.")
        context.user_data["admin_action"] = None
    
    conn.close()

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("✅ Bot Aktif...")
    app.run_polling()

if __name__ == "__main__":
    main()
# ================= FONKSİYONLAR =================
def check_all_joins(user_id):
    for kanal in KANALLAR:
        try:
            member = bot.get_chat_member(kanal, user_id)
            if member.status not in ["member", "creator", "administrator"]:
                return False
        except: return False
    return True

def main_menu(msg):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🛒 Market", "💰 Bakiye")
    kb.add("🎁 Hediye Kodu", "👥 Referans")
    kb.add("📞 Destek", "📅 Günlük Bonus")
    if msg.from_user.id in ADMIN_ID:
        kb.add("⚙️ Admin")
    bot.send_message(msg.chat.id, "🏪 **PAUL WALKER MARKET**\nİşlem seçiniz:", reply_markup=kb, parse_mode="Markdown")

# ================= KOMUTLAR =================
@bot.message_handler(commands=['start'])
def start(msg):
    uid = str(msg.from_user.id)
    user_steps[uid] = None
    
    if uid not in users:
        users[uid] = {"bakiye": 0, "ref_puan": 0, "last_bonus": 0}
        args = msg.text.split()
        if len(args) > 1:
            ref_id = args[1]
            if ref_id in users and ref_id != uid:
                users[ref_id]["bakiye"] += 1
                users[ref_id]["ref_puan"] += 1
                bot.send_message(ref_id, "👥 Yeni referans! +1₺ kazandınız.")
        save_data("users.json", users)
    
    if not check_all_joins(msg.from_user.id):
        btn = types.InlineKeyboardMarkup()
        for k in KANALLAR:
            btn.add(types.InlineKeyboardButton(f"📢 Katıl: {k}", url=f"https://t.me/{k.replace('@','')}"))
        btn.add(types.InlineKeyboardButton("✅ Katıldım", callback_data="check_join"))
        bot.send_message(msg.chat.id, "⚠️ Kanallara katılmadan botu kullanamazsınız:", reply_markup=btn)
        return
    main_menu(msg)

# ================= ANA MESAJ YÖNETİCİSİ =================
@bot.message_handler(func=lambda m: True)
def handle_all(msg):
    uid = str(msg.from_user.id)
    if uid not in users: return

    step = user_steps.get(uid)
    
    if step == "waiting_promo":
        code = msg.text.strip()
        if code in promos:
            users[uid]["bakiye"] += promos[code]["miktar"]
            promos[code]["limit"] -= 1
            bot.send_message(msg.chat.id, f"✅ Başarılı! +{promos[code]['miktar']}₺ eklendi.")
            if promos[code]["limit"] <= 0: del promos[code]
            save_data("users.json", users); save_data("promos.json", promos)
        else: bot.send_message(msg.chat.id, "❌ Geçersiz veya süresi dolmuş kod.")
        user_steps[uid] = None
        return

    if step == "admin_give_bal_id":
        user_steps[uid] = f"admin_give_bal_amount:{msg.text.strip()}"
        bot.send_message(msg.chat.id, "Eklenecek miktar?")
        return

    if step and step.startswith("admin_give_bal_amount:"):
        target = step.split(":")[1]
        try:
            miktar = int(msg.text)
            if target in users:
                users[target]["bakiye"] += miktar
                save_data("users.json", users)
                bot.send_message(msg.chat.id, "✅ Bakiye başarıyla verildi.")
                bot.send_message(target, f"💰 Hesabınıza {miktar}₺ eklendi!")
            else: bot.send_message(msg.chat.id, "❌ Kullanıcı bulunamadı.")
        except: bot.send_message(msg.chat.id, "❌ Hata: Sayı girin.")
        user_steps[uid] = None
        return

    if step == "add_product_name":
        ad = msg.text
        user_steps[uid] = f"add_product_price:{ad}"
        bot.send_message(msg.chat.id, f"💰 `{ad}` için fiyat yazın:")
        return

    if step and step.startswith("add_product_price:"):
        ad = step.split(":")[1]
        try:
            fiyat = int(msg.text)
            pid = str(int(time.time()))
            products[pid] = {"ad": ad, "fiyat": fiyat}
            save_data("products.json", products)
            bot.send_message(msg.chat.id, "✅ Ürün markete eklendi.")
        except: bot.send_message(msg.chat.id, "❌ Hata: Fiyat sayı olmalı.")
        user_steps[uid] = None
        return

    # --- TUŞLAR ---
    if msg.text == "🛒 Market":
        if not products:
            bot.send_message(msg.chat.id, "❌ Market şu an boş.")
        else:
            kb = types.InlineKeyboardMarkup()
            for pid, p in products.items():
                kb.add(types.InlineKeyboardButton(f"{p['ad']} - {p['fiyat']}₺", callback_data=f"buy_{pid}"))
            bot.send_message(msg.chat.id, "🛒 **Ürün Listesi:**", reply_markup=kb)

    elif msg.text == "💰 Bakiye":
        bot.send_message(msg.chat.id, f"💳 Bakiyeniz: **{users[uid]['bakiye']}₺**", parse_mode="Markdown")

    elif msg.text == "📞 Destek":
        bot.send_message(msg.chat.id, "🆘 **DESTEK HATTI**\nSorunlarınız için: @WaIkerPaul")

    elif msg.text == "📅 Günlük Bonus":
        now = time.time()
        if now - users[uid].get("last_bonus", 0) > 86400:
            puan = random.randint(1, 5)
            users[uid]["bakiye"] += puan
            users[uid]["last_bonus"] = now
            save_data("users.json", users)
            bot.send_message(msg.chat.id, f"🎉 Günlük bonus: **{puan}₺** kazandın!")
        else: bot.send_message(msg.chat.id, "❌ Bonus için 24 saat beklemelisin.")

    elif msg.text == "🎁 Hediye Kodu":
        user_steps[uid] = "waiting_promo"
        bot.send_message(msg.chat.id, "🎟 Kullanmak istediğiniz kodu yazın:")

    elif msg.text == "👥 Referans":
        bot_name = bot.get_me().username
        bot.send_message(msg.chat.id, f"👥 **Referans Linkin:**\n`https://t.me/{bot_name}?start={uid}`", parse_mode="Markdown")

    elif msg.text == "⚙️ Admin" and msg.from_user.id in ADMIN_ID:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("➕ Ürün Ekle", "🎟 Kod Oluştur")
        kb.add("💸 Bakiye Ver", "⬅️ Menü")
        bot.send_message(msg.chat.id, "🛠 **Yönetici Paneli**", reply_markup=kb)

    elif msg.text == "💸 Bakiye Ver" and msg.from_user.id in ADMIN_ID:
        user_steps[uid] = "admin_give_bal_id"
        bot.send_message(msg.chat.id, "Bakiye verilecek kişinin ID'sini yazın:")

    elif msg.text == "➕ Ürün Ekle" and msg.from_user.id in ADMIN_ID:
        user_steps[uid] = "add_product_name"
        bot.send_message(msg.chat.id, "📦 Ürün ismini yazın:")

    elif msg.text == "⬅️ Menü":
        user_steps[uid] = None
        main_menu(msg)

# ================= CALLBACKS =================
@bot.callback_query_handler(func=lambda c: True)
def handle_calls(call):
    uid = str(call.from_user.id)
    if call.data == "check_join":
        if check_all_joins(call.from_user.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            main_menu(call.message)
        else: bot.answer_callback_query(call.id, "❌ Kanallara katılmamışsınız!", show_alert=True)
    
    elif call.data.startswith("buy_"):
        pid = call.data.split("_")[1]
        p = products.get(pid)
        if p and users[uid]["bakiye"] >= p["fiyat"]:
            users[uid]["bakiye"] -= p["fiyat"]
            save_data("users.json", users)
            bot.send_message(call.message.chat.id, f"✅ **{p['ad']}** satın alındı!\nDetaylar için @WaIkerPaul'a yazın.")
            bot.send_message(LOG_KANAL, f"Sipariş: {call.from_user.first_name} ({uid}) - {p['ad']}")
        else: bot.answer_callback_query(call.id, "❌ Bakiye yetersiz!", show_alert=True)

# ================= RUN =================
@app.route('/')
def home(): return "Bot Aktif"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

if __name__ == "__main__":
    t = Thread(target=run)
    t.daemon = True
    t.start()
    bot.remove_webhook()
    print("Sistem Hazır!")
    bot.infinity_polling()
    
