import telebot
from telebot import types
import json, os, time
from flask import Flask
from threading import Thread

# ================= AYARLAR =================
# Yeni tokenini buraya ekledim
BOT_TOKEN = "8725491244:AAGy5VztUUcPJDLE9ZAFUVaxcRlcf2QwVMM"
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

ADMIN_ID = [8695334986]  
LOG_KANAL = "-1003986617455" 
KANALLAR = ["@PaulWalkerArsiv", "@BYZANTIUMS"]

# ================= VERİ SİSTEMİ =================
def load_data(file, default):
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False)
        return default
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return default

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
        users[user_id] = {"bakiye": 0}
        save_data("users.json", users)
    
    if not check_all_joins(msg.from_user.id):
        btn = types.InlineKeyboardMarkup()
        for k in KANALLAR:
            btn.add(types.InlineKeyboardButton(f"📢 Katıl: {k}", url=f"https://t.me/{k.replace('@','')}"))
        btn.add(types.InlineKeyboardButton("✅ Katıldım", callback_data="check_join"))
        bot.send_message(msg.chat.id, "⚠️ Devam etmek için kanallara katılın:", reply_markup=btn)
        return
    main_menu(msg)

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_callback(call):
    if check_all_joins(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Eksik kanallar var!", show_alert=True)

# ================= HEDİYE KODU SİSTEMİ =================
@bot.message_handler(func=lambda m: m.text == "🎁 Hediye Kodu")
def promo_start(msg):
    m = bot.send_message(msg.chat.id, "🎟 **Lütfen hediye kodunuzu girin:**", parse_mode="Markdown")
    bot.register_next_step_handler(m, process_promo)

def process_promo(msg):
    code = msg.text.strip()
    uid = str(msg.from_user.id)
    if code in promos:
        p = promos[code]
        if p["limit"] > 0:
            users[uid]["bakiye"] += p["miktar"]
            p["limit"] -= 1
            bot.send_message(msg.chat.id, f"✅ Başarılı! Hesabınıza **{p['miktar']}₺** eklendi.", parse_mode="Markdown")
            if p["limit"] <= 0: del promos[code]
            save_data("users.json", users)
            save_data("promos.json", promos)
        else: bot.send_message(msg.chat.id, "❌ Bu kodun kullanım limiti dolmuş.")
    else: bot.send_message(msg.chat.id, "❌ Geçersiz kod.")

# ================= ADMIN PANELİ =================
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin")
def admin_panel(msg):
    if msg.from_user.id not in ADMIN_ID: return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎟 Kod Oluştur", "💸 Bakiye Ver")
    kb.add("⬅️ Menü")
    bot.send_message(msg.chat.id, "🛠 **ADMİN PANELİ**", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🎟 Kod Oluştur")
def admin_promo_1(msg):
    if msg.from_user.id not in ADMIN_ID: return
    m = bot.send_message(msg.chat.id, "Oluşturulacak kodu yazın (Örn: WALKER50):")
    bot.register_next_step_handler(m, admin_promo_2)

def admin_promo_2(msg):
    code = msg.text.strip()
    m = bot.send_message(msg.chat.id, f"Kod: `{code}`\nKaç ₺ bakiye versin?", parse_mode="Markdown")
    bot.register_next_step_handler(m, admin_promo_3, code)

def admin_promo_3(msg, code):
    try:
        miktar = int(msg.text)
        m = bot.send_message(msg.chat.id, "Kaç kişi kullanabilsin?")
        bot.register_next_step_handler(m, admin_promo_4, code, miktar)
    except: bot.send_message(msg.chat.id, "❌ Hata: Sayı girmelisiniz.")

def admin_promo_4(msg, code, miktar):
    try:
        limit = int(msg.text)
        promos[code] = {"miktar": miktar, "limit": limit}
        save_data("promos.json", promos)
        bot.send_message(msg.chat.id, f"✅ Kod Oluşturuldu: `{code}`\nMiktar: {miktar}₺\nLimit: {limit}", parse_mode="Markdown")
    except: bot.send_message(msg.chat.id, "❌ Hata: Sayı girmelisiniz.")

# ================= DİĞERLERİ =================
@bot.message_handler(func=lambda m: m.text == "💰 Bakiye")
def bakiye(msg):
    u = users.get(str(msg.from_user.id), {"bakiye": 0})
    bot.send_message(msg.chat.id, f"💳 Bakiyeniz: **{u['bakiye']}₺**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "⬅️ Menü")
def back(msg): main_menu(msg)

# ================= RENDER AYAKTA TUTMA =================
@app.route('/')
def home(): return "Bot Aktif!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

if __name__ == "__main__":
    t = Thread(target=run)
    t.start()
    print("Sistem Başlatıldı!")
    bot.infinity_polling()
    
