import telebot
from telebot import types
import json, os, time

# ================= AYARLAR =================
BOT_TOKEN = "8725491244:AAETeBzhgIrBjWVyCHbaVMvOM7dnGMiR2IU"
bot = telebot.TeleBot(BOT_TOKEN)

# Buraya Kurucu ve 2 Adminin ID numaralarını ekle (Şu an seninkini yazdım)
# Örnek: [SeninID, 1.AdminID, 2.AdminID]
ADMIN_ID = [8695334986]  

LOG_KANAL = "-1003986617455" # -100 ile başlayan kanal ID'si
KANALLAR = ["@PaulWalkerArsiv", "@BYZANTIUMKRALLIK"]

# Destek Menüsü Tasarımı
DESTEK_MESAJI = """
🆘 **PAUL WALKER MARKET DESTEK HATTI**

Bir sorun mu yaşıyorsunuz? Ekibimize ulaşın:

👑 **KURUCU**
└ @WaIkerPaul

🛡️ **ADMİNLER**
├ @KullaniciAdi_Admin1


📌 *Lütfen mesaj atarken Bot ID'nizi belirtmeyi unutmayın.*
"""

# ================= VERİ SİSTEMİ =================
def load_data(file, default):
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False)
        return default
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

users = load_data("users.json", {})
products = load_data("products.json", {}) 
promos = load_data("promos.json", {})

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
    kb.add("📞 Destek")
    if msg.from_user.id in ADMIN_ID:
        kb.add("⚙️ Admin")
    bot.send_message(msg.chat.id, "🏪 **PAUL WALKER MARKET**\nİşlem seçiniz:", reply_markup=kb, parse_mode="Markdown")

# ================= KOMUTLAR =================
@bot.message_handler(commands=['start'])
def start(msg):
    user_id = str(msg.from_user.id)
    if user_id not in users:
        users[user_id] = {"bakiye": 0, "ref_kazanc": 0}
        save_data("users.json", users)
    
    if not check_all_joins(msg.from_user.id):
        btn = types.InlineKeyboardMarkup()
        for k in KANALLAR:
            btn.add(types.InlineKeyboardButton(f"📢 Katıl: {k}", url=f"https://t.me/{k.replace('@','')}"))
        btn.add(types.InlineKeyboardButton("✅ Katıldım", callback_data="check_join"))
        bot.send_message(msg.chat.id, "⚠️ Devam etmek için kanallara katılın:", reply_markup=btn)
        return
    main_menu(msg)

@bot.message_handler(func=lambda m: m.text == "📞 Destek")
def support(msg):
    bot.send_message(msg.chat.id, DESTEK_MESAJI, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_callback(call):
    if check_all_joins(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Eksik kanallar var!", show_alert=True)

# ================= MARKET & SİPARİŞ =================
@bot.message_handler(func=lambda m: m.text == "🛒 Market")
def market(msg):
    if not products:
        bot.send_message(msg.chat.id, "❌ Market şu an boş.")
        return
    kb = types.InlineKeyboardMarkup()
    for pid, p in products.items():
        kb.add(types.InlineKeyboardButton(f"{p['ad']} - {p['fiyat']}₺", callback_data=f"buy_{pid}"))
    bot.send_message(msg.chat.id, "🛒 Bir ürün seçin:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy_callback(call):
    pid = call.data.split("_")[1]
    uid = str(call.from_user.id)
    p = products[pid]
    if users[uid]["bakiye"] < p["fiyat"]:
        bot.answer_callback_query(call.id, "❌ Yetersiz bakiye!", show_alert=True)
        return
    users[uid]["bakiye"] -= p["fiyat"]
    save_data("users.json", users)
    bot.send_message(call.message.chat.id, "✅ Sipariş iletildi! En kısa sürede teslim edilecek.")
    bot.send_message(LOG_KANAL, f"🚨 **YENİ SİPARİŞ!**\n👤: `{call.from_user.first_name}`\n🆔: `{uid}`\n📦: {p['ad']}")

# ================= HEDİYE KODU =================
@bot.message_handler(func=lambda m: m.text == "🎁 Hediye Kodu")
def promo_start(msg):
    m = bot.send_message(msg.chat.id, "🎟 **Kodunuzu yazın:**", parse_mode="Markdown")
    bot.register_next_step_handler(m, process_promo)

def process_promo(msg):
    code = msg.text.strip()
    uid = str(msg.from_user.id)
    if code in promos:
        p = promos[code]
        if p["limit"] > 0:
            users[uid]["bakiye"] += p["miktar"]
            p["limit"] -= 1
            if p["limit"] <= 0: del promos[code]
            save_data("users.json", users)
            save_data("promos.json", promos)
            bot.send_message(msg.chat.id, f"✅ Hesabınıza {p['miktar']}₺ eklendi!")
        else: bot.send_message(msg.chat.id, "❌ Limit dolmuş.")
    else: bot.send_message(msg.chat.id, "❌ Geçersiz kod.")

# ================= ADMIN PANELİ =================
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin")
def admin_panel(msg):
    if msg.from_user.id not in ADMIN_ID: return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Ürün Ekle", "🎟 Kod Oluştur")
    kb.add("💸 Bakiye Ver", "⬅️ Menü")
    bot.send_message(msg.chat.id, "🛠 **Yönetici Paneli**", reply_markup=kb)

# (Diğer admin fonksiyonları buraya eklenebilir...)

@bot.message_handler(func=lambda m: m.text == "💰 Bakiye")
def bakiye(msg):
    u = users.get(str(msg.from_user.id), {"bakiye": 0})
    bot.send_message(msg.chat.id, f"💳 Bakiyeniz: **{u['bakiye']}₺**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "⬅️ Menü")
def back(msg): main_menu(msg)

print("Paul Walker Market Sistemi Hazır!")
bot.infinity_polling()
                         
