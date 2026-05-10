import telebot
from telebot import types
import json, os, time, random
from flask import Flask
from threading import Thread

# ================= AYARLAR =================
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
    kb.add("📞 Destek", "📅 Günlük Bonus")
    if msg.from_user.id in ADMIN_ID:
        kb.add("⚙️ Admin")
    bot.send_message(msg.chat.id, "🏪 **PAUL WALKER MARKET**\nHoş geldiniz! İşlem seçiniz:", reply_markup=kb, parse_mode="Markdown")

# ================= KOMUTLAR =================
@bot.message_handler(commands=['start'])
def start(msg):
    user_id = str(msg.from_user.id)
    args = msg.text.split()
    
    # Yeni Kullanıcı Kaydı ve Referans Kontrolü
    is_new_user = False
    if user_id not in users:
        users[user_id] = {"bakiye": 0, "ref_puan": 0, "last_bonus": 0, "invited_by": None}
        is_new_user = True
        
        # Referans ile gelmişse
        if len(args) > 1:
            ref_id = args[1]
            if ref_id in users and ref_id != user_id:
                users[user_id]["invited_by"] = ref_id
                users[ref_id]["ref_puan"] += 1 # Davet edene 1 puan
                users[ref_id]["bakiye"] += 1   # İstersen burayı artırabilirsin
                bot.send_message(ref_id, f"👥 **Yeni Referans!**\nBir arkadaşınız davetinizle katıldı. +1 Puan kazandınız!")
        
        save_data("users.json", users)
    
    if not check_all_joins(msg.from_user.id):
        btn = types.InlineKeyboardMarkup()
        for k in KANALLAR:
            btn.add(types.InlineKeyboardButton(f"📢 Katıl: {k}", url=f"https://t.me/{k.replace('@','')}"))
        btn.add(types.InlineKeyboardButton("✅ Katıldım", callback_data="check_join"))
        bot.send_message(msg.chat.id, "⚠️ Devam etmek için kanallara katılın:", reply_markup=btn)
        return
    main_menu(msg)

# ================= GÜNLÜK BONUS =================
@bot.message_handler(func=lambda m: m.text == "📅 Günlük Bonus")
def daily_bonus(msg):
    uid = str(msg.from_user.id)
    now = time.time()
    last_time = users[uid].get("last_bonus", 0)
    
    if now - last_time > 86400: # 24 Saat
        puan = random.randint(1, 5)
        users[uid]["bakiye"] += puan
        users[uid]["last_bonus"] = now
        save_data("users.json", users)
        bot.send_message(msg.chat.id, f"🎉 **Tebrikler!**\nGünlük şansından hesabına **{puan}₺** eklendi! Yarın tekrar gel.")
    else:
        kalan = int((86400 - (now - last_time)) / 3600)
        bot.send_message(msg.chat.id, f"⏳ **Henüz vakit var!**\nTekrar bonus almak için yaklaşık **{kalan} saat** beklemelisin.")

# ================= REFERANS SİSTEMİ =================
@bot.message_handler(func=lambda m: m.text == "👥 Referans")
def ref_system(msg):
    uid = msg.from_user.id
    u_data = users.get(str(uid), {"ref_puan": 0})
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start={uid}"
    
    text = (f"👥 **REFERANS PANELİ**\n\n"
            f"🔗 **Senin Linkin:** `{ref_link}`\n\n"
            f"📊 **Toplam Davet:** {u_data.get('ref_puan', 0)} Kişi\n"
            f"💡 *Not: Linkinle katılan ve kanallara üye olan her kişi için puan kazanırsın.*")
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

# ================= MARKET & ÜRÜN YÖNETİMİ =================
@bot.message_handler(func=lambda m: m.text == "🛒 Market")
def show_market(msg):
    if not products:
        bot.send_message(msg.chat.id, "🛒 Market şu an boş, yakında eklenecek!")
        return
    
    kb = types.InlineKeyboardMarkup()
    for pid, p in products.items():
        kb.add(types.InlineKeyboardButton(f"{p['ad']} - {p['fiyat']}₺", callback_data=f"buy_{pid}"))
    
    bot.send_message(msg.chat.id, "🛒 **MARKET ÜRÜNLERİ**\nAlmak istediğiniz ürünü seçin:", reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def process_purchase(call):
    pid = call.data.split("_")[1]
    uid = str(call.from_user.id)
    p = products.get(pid)
    
    if not p: return
    
    if users[uid]["bakiye"] >= p["fiyat"]:
        users[uid]["bakiye"] -= p["fiyat"]
        save_data("users.json", users)
        bot.answer_callback_query(call.id, "✅ Satın alım başarılı!", show_alert=True)
        bot.send_message(call.message.chat.id, f"🎁 **{p['ad']}** satın aldınız!\nTeslimat için @WaIkerPaul adresine yazın.")
        bot.send_message(LOG_KANAL, f"💰 **SİPARİŞ!**\nKullanıcı: {call.from_user.first_name}\nÜrün: {p['ad']}")
    else:
        bot.answer_callback_query(call.id, "❌ Bakiyeniz yetersiz!", show_alert=True)

# ================= ADMİN PANELİ =================
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin")
def admin_menu(msg):
    if msg.from_user.id not in ADMIN_ID: return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Ürün Ekle", "🎟 Kod Oluştur")
    kb.add("💸 Bakiye Ver", "⬅️ Menü")
    bot.send_message(msg.chat.id, "🛠 **Yönetici Paneli**", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "➕ Ürün Ekle")
def add_prod_1(msg):
    if msg.from_user.id not in ADMIN_ID: return
    m = bot.send_message(msg.chat.id, "Ürün adını yazın:")
    bot.register_next_step_handler(m, add_prod_2)

def add_prod_2(msg):
    ad = msg.text
    m = bot.send_message(msg.chat.id, f"💰 `{ad}` için fiyat yazın:")
    bot.register_next_step_handler(m, add_prod_3, ad)

def add_prod_3(msg, ad):
    try:
        fiyat = int(msg.text)
        pid = str(int(time.time()))
        products[pid] = {"ad": ad, "fiyat": fiyat}
        save_data("products.json", products)
        bot.send_message(msg.chat.id, "✅ Ürün başarıyla eklendi!")
    except: bot.send_message(msg.chat.id, "❌ Hata: Sayı girin.")

# (DİĞER ADMİN FONKSİYONLARI VE BOT BAŞLATMA AYNI KALIYOR...)
@bot.message_handler(func=lambda m: m.text == "💰 Bakiye")
def show_balance(msg):
    u = users.get(str(msg.from_user.id), {"bakiye": 0})
    bot.send_message(msg.chat.id, f"💳 Bakiyeniz: **{u['bakiye']}₺**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "⬅️ Menü")
def back_home(msg): main_menu(msg)

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join_callback(call):
    if check_all_joins(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Hala eksik kanallar var!", show_alert=True)

@app.route('/')
def home(): return "Bot Aktif"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

if __name__ == "__main__":
    t = Thread(target=run)
    t.start()
    bot.infinity_polling()
    
