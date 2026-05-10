import telebot
import os

# Tokenini buraya yaz
TOKEN = "8637300414:AAFNaG2KMxMHWBPHi0wLM8KT4H85JkloDX4"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "✅ İskelet Sistem Çalışıyor! Dükkan açılmaya hazır.")

print("Bot şu an aktif...")
# Render'da kapanmaması için polling başlatıyoruz
bot.infinity_polling()
