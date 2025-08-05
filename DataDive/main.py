import os
import requests
import telebot
from telebot import types
import datetime
import json
import threading
import time
import logging
from flask import Flask, request
from rate_storage import RateStorage
from clp_scraper import CLPTodayScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN", "your_bot_token_here")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))

if not TOKEN or CHAT_ID == 0:
    logger.error("❌ TOKEN o CHAT_ID no configurados correctamente.")
    exit(1)

bot = telebot.TeleBot(TOKEN)
storage = RateStorage()
app = Flask(__name__)  # Flask para Render

# === CLASE DollarBot (igual que ya tienes) ===
dollar_bot = DollarBot()

# === PROGRAMADOR AUTOMÁTICO (Scheduler) ===
def scheduler_loop():
    last_sent_date = None
    while True:
        now = datetime.datetime.now()
        if now.weekday() < 5 and now.hour == 9 and now.minute < 5:  # Lunes a Viernes 9:00
            today = now.date()
            if last_sent_date != today:  # Solo una vez al día
                mensaje = dollar_bot.obtener_tasas()
                try:
                    bot.send_message(CHAT_ID, mensaje, parse_mode="Markdown")
                    logger.info("✅ Actualización diaria enviada")
                    last_sent_date = today
                except Exception as e:
                    logger.error(f"❌ Error enviando actualización diaria: {e}")
        time.sleep(60)

# Iniciar scheduler en segundo plano
threading.Thread(target=scheduler_loop, daemon=True).start()

# === WEBHOOKS ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_URL', 'dolar-bot.onrender.com')}/{TOKEN}")
    return "Webhook configurado y bot en ejecución", 200

# === TECLADO PRINCIPAL ===
def create_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(types.KeyboardButton('💰 Tasas'), types.KeyboardButton('🔄 Actualizar'))
    keyboard.add(types.KeyboardButton('❓ Ayuda'), types.KeyboardButton('📡 Estado'))
    return keyboard

# === COMANDOS ===
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "¡Hola! 👋 Usa los botones para ver tasas o ayuda.", reply_markup=create_main_keyboard())

@bot.message_handler(commands=['tasas'])
def consulta_manual(message):
    mensaje = dollar_bot.obtener_tasas()
    bot.reply_to(message, mensaje, parse_mode="Markdown", reply_markup=create_main_keyboard())

@bot.message_handler(commands=['status'])
def bot_status(message):
    status = dollar_bot.get_status()
    respuesta = (
        f"📡 *Estado del Bot*\n\n"
        f"Última actualización: {status['last_update'] or 'Aún no actualizada'}\n"
        f"Scheduler: {'✅ Activo' if status['scheduler_running'] else '❌ Inactivo'}\n"
        f"Chat ID: {status['chat_id']}\n"
    )
    bot.reply_to(message, respuesta, parse_mode="Markdown", reply_markup=create_main_keyboard())

@bot.message_handler(func=lambda message: message.text in ['💰 Tasas', '🔄 Actualizar', '❓ Ayuda', '📡 Estado'])
def handle_buttons(message):
    if message.text in ['💰 Tasas', '🔄 Actualizar']:
        mensaje = dollar_bot.obtener_tasas()
        bot.reply_to(message, mensaje, parse_mode="Markdown", reply_markup=create_main_keyboard())
    elif message.text == '❓ Ayuda':
        bot.reply_to(message, "Usa los botones para ver tasas o estado del bot.", reply_markup=create_main_keyboard())
    elif message.text == '📡 Estado':
        bot_status(message)

@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    bot.reply_to(message, "No entiendo ese comando. Usa los botones abajo.", reply_markup=create_main_keyboard())

if __name__ == "__main__":
    logger.info("🚀 Iniciando servidor Flask con webhook")
    dollar_bot.start_scheduler()  # Asegura que el objeto sepa que el scheduler corre
    app.run(host="0.0.0.0", port=5000)
