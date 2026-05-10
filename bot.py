import telebot
from telebot import types
import json, os, time, random
from flask import Flask
from threading import Thread

# ================= AYARLAR =================
BOT_TOKEN = "8725491244:AAGy5VztUUcPJDLE9ZAFUVaxcRlcf2QwVMM"
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
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
user_steps = {} # Kullanıcıların hangi işlemde olduğunu tutar (Örn: ürün ekliyor mu?)

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
    user_steps[uid] = None # Adımı sıfırla
    
    if uid not in users:
        users[uid] = {"bakiye": 0, "ref_puan": 0, "last_bonus": 0}
        args = msg.text.split()
        if len(args) > 1: # Referans kontrolü
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

    # --- 1. ADIM KONTROLLERİ (Bir girdi bekleniyorsa) ---
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

    # --- 2. TUŞ KONTROLLERİ ---
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
    Thread(target=run).start()
    bot.remove_webhook()
    print("Sistem Hazır!")
    bot.infinity_polling()
    
