import telebot
import os
from flask import Flask
import threading

# --- BOT AYARLARI ---
TOKEN = "8725491244:AAGVepKX3Re4zQQk4vqDoP6lWPKimZQ6wJA"
bot = telebot.TeleBot(TOKEN)

# --- RENDER İÇİN KÜÇÜK BİR HİLE (FLASK) ---
# Render botu bir web sitesi sanmazsa 10 dakika sonra kapatır.
app = Flask('')

@app.route('/')
def home():
    return "Bot aktif!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

# --- BOT KOMUTLARI ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "✅ Mahmut dükkanı açtı! Sistem canavar gibi çalışıyor.")

# Botu ve Web Sunucusunu Aynı Anda Çalıştır
if __name__ == "__main__":
    t = threading.Thread(target=run)
    t.start()
    print("Bot başlatılıyor...")
    bot.infinity_polling()
