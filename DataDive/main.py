import os
import requests
import telebot
from telebot import types
import datetime
import json
import threading
import time
import logging
from rate_storage import RateStorage
from clp_scraper import CLPTodayScraper

# ==========================
# Configuración de logs
# ==========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==========================
# Configuración del bot
# ==========================
TOKEN = os.getenv("TOKEN", "your_bot_token_here")
CHAT_ID_STR = os.getenv("CHAT_ID", "0")

if not TOKEN or TOKEN == "your_bot_token_here":
    logger.error("Bot token not provided. Please set TOKEN environment variable.")
    exit(1)

try:
    CHAT_ID = int(CHAT_ID_STR)
    if CHAT_ID == 0:
        logger.error("Chat ID not provided. Please set CHAT_ID environment variable.")
        exit(1)
except ValueError:
    logger.error(f"Invalid CHAT_ID format: '{CHAT_ID_STR}'. CHAT_ID should be numeric.")
    exit(1)

bot = telebot.TeleBot(TOKEN)
storage = RateStorage()

# ==========================
# Clase principal del bot
# ==========================
class DollarBot:
    def __init__(self):
        self.last_update = None
        self.last_rates = None
        self.scheduler_running = False
        self.clp_scraper = CLPTodayScraper()

    def obtener_tasas(self):
        """Obtiene las tasas de cambio"""
        try:
            bcv_response = requests.get("https://pydolarve.org/api/v2/tipo-cambio?currency=usd&rounded_price=true", timeout=10)
            bcv_response.raise_for_status()
            bcv_data = bcv_response.json()
            bcv = bcv_data.get('price', 0)

            if bcv <= 0:
                return "❌ Error al obtener la tasa BCV."

            now = datetime.datetime.now()
            mensaje = f"💱 *Tasas de Cambio en Venezuela* ({now.strftime('%d/%m/%Y')}):\n\n🏛️ BCV Oficial: {bcv} Bs/USD"

            clp_rates = self.clp_scraper.get_specific_rates()
            promedio = bcv
            tasas_adicionales = []

            # Tasas P2P
            try:
                p2p_response = requests.get("https://pydolarve.org/api/v2/market-p2p?currency=usd&rounded_price=true", timeout=10)
                p2p_response.raise_for_status()
                p2p_data = p2p_response.json()

                if 'platforms' in p2p_data:
                    platforms = p2p_data['platforms']
                    platform_display = {
                        'binance': '🔸 Binance',
                        'bybit': '🔶 Bybit',
                        'okx': '⚫ OKX',
                        'yadio': '🔵 Yadio'
                    }
                    for key, data in platforms.items():
                        if isinstance(data, dict) and 'title' in data and 'price' in data:
                            display_name = platform_display.get(key.lower(), data['title'])
                            tasas_adicionales.append((display_name, data['price']))
            except Exception as e:
                logger.warning(f"No se pudieron obtener tasas P2P: {e}")

            # Tasas Zelle y PayPal
            if bcv > 0:
                if clp_rates and clp_rates.get('usd'):
                    usd_rates = clp_rates['usd']
                    zelle_rate = usd_rates.get('zelle', bcv * 1.08)
                    paypal_rate = usd_rates.get('paypal', bcv * 1.15)
                else:
                    zelle_rate = bcv * 1.08
                    paypal_rate = bcv * 1.15

                tasas_adicionales.insert(0, ("💳 Zelle", zelle_rate))
                tasas_adicionales.insert(1, ("💙 PayPal", paypal_rate))

            if tasas_adicionales:
                tasas_adicionales.sort(key=lambda x: x[1])
                for nombre, precio in tasas_adicionales:
                    mensaje += f"\n{nombre}: {precio:.2f} Bs/USD"

                all_prices = [bcv] + [precio for _, precio in tasas_adicionales]
                promedio = sum(all_prices) / len(all_prices)
                mensaje += f"\n\n📊 Promedio USD: {promedio:.2f} Bs"

            # Tasas Euro
            euro_rates = []
            if clp_rates and clp_rates.get('eur') and 'rate' in clp_rates['eur']:
                euro_rates.append(("🇪🇺 Euro (CLP)", clp_rates['eur']['rate']))

            try:
                eur_response = requests.get("https://pydolarve.org/api/v2/tipo-cambio?currency=eur&rounded_price=true", timeout=10)
                eur_response.raise_for_status()
                eur_data = eur_response.json()
                eur_bcv = eur_data.get('price', 0)
                if eur_bcv > 0:
                    euro_rates.append(("🏛️ Euro BCV", eur_bcv))
            except:
                pass

            if not euro_rates and bcv > 0:
                euro_rates.append(("🇪🇺 Euro (Est.)", bcv * 1.1))

            if euro_rates:
                mensaje += "\n\n💶 *Tasas del Euro*:"
                for nombre, precio in euro_rates:
                    mensaje += f"\n{nombre}: {precio:.2f} Bs/EUR"

            rate_to_store = bcv
            anterior = storage.get_previous_rate()
            if anterior > 0:
                cambio = abs(rate_to_store - anterior) / anterior * 100
                if cambio >= 2:
                    signo = "📈 Subió" if rate_to_store > anterior else "📉 Bajó"
                    mensaje += f"\n\n⚠️ {signo} más de 2% respecto al día anterior."

            storage.save_rate(rate_to_store)
            mensaje += f"\n\n🕐 Actualizado: {now.strftime('%H:%M')}"
            mensaje += f"\n📡 Fuentes: PyDolarVe, CLP Today"

            self.last_update = now
            self.last_rates = {'bcv': bcv, 'promedio': promedio}
            return mensaje
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def send_daily_update(self):
        try:
            mensaje = self.obtener_tasas()
            bot.send_message(CHAT_ID, mensaje)
        except Exception as e:
            logger.error(f"Error al enviar actualización: {e}")

    def should_send_update(self):
        now = datetime.datetime.now()
        return now.weekday() < 5 and now.hour == 9 and now.minute < 5

    def start_scheduler(self):
        if self.scheduler_running:
            return
        self.scheduler_running = True

        def scheduler_loop():
            last_check_hour = -1
            while self.scheduler_running:
                try:
                    now = datetime.datetime.now()
                    if (now.hour != last_check_hour and now.weekday() < 5 and now.hour == 9 and now.minute < 30):
                        self.send_daily_update()
                        last_check_hour = now.hour
                    time.sleep(60)
                except Exception as e:
                    logger.error(f"Error en scheduler: {e}")
                    time.sleep(60)

        threading.Thread(target=scheduler_loop, daemon=True).start()

    def stop_scheduler(self):
        self.scheduler_running = False

    def get_status(self):
        return {
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'last_rates': self.last_rates,
            'scheduler_running': self.scheduler_running,
            'chat_id': CHAT_ID
        }

# Inicializar bot
dollar_bot = DollarBot()

# ==========================
# Teclado principal
# ==========================
def create_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_tasas = types.KeyboardButton('💰 Tasas')
    btn_actualizar = types.KeyboardButton('🔄 Actualizar')
    btn_ayuda = types.KeyboardButton('❓ Ayuda')
    keyboard.add(btn_tasas, btn_actualizar)
    keyboard.add(btn_ayuda)
    return keyboard

# ==========================
# Comandos del bot
# ==========================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_msg = """
¡Hola! 👋 Soy tu bot del dólar venezolano.

• 💰 Tasas - Ver tasas actuales del dólar
• 🔄 Actualizar - Obtener tasas recientes  
• ❓ Ayuda - Información del bot

Recibirás actualizaciones automáticas cada día hábil a las 9:00 AM.
    """
    bot.reply_to(message, welcome_msg, reply_markup=create_main_keyboard())

@bot.message_handler(commands=['help'])
def send_help(message):
    help_msg = """
🤖 Bot del Dólar Venezolano

• 💰 Tasas - Consultar tasas actuales
• 🔄 Actualizar - Obtener datos más recientes
• ❓ Ayuda - Mostrar esta información

El bot envía actualizaciones automáticas:
• Todos los días hábiles a las 9:00 AM
• Alertas cuando las tasas cambien más del 2%

Fuente de datos: PyDolarVe
    """
    bot.reply_to(message, help_msg, reply_markup=create_main_keyboard())

@bot.message_handler(commands=['tasas'])
def consulta_manual(message):
    mensaje = dollar_bot.obtener_tasas()
    bot.reply_to(message, mensaje, parse_mode="Markdown", reply_markup=create_main_keyboard())

@bot.message_handler(func=lambda message: message.text in ['💰 Tasas', '🔄 Actualizar', '❓ Ayuda'])
def handle_buttons(message):
    if message.text in ['💰 Tasas', '🔄 Actualizar']:
        mensaje = dollar_bot.obtener_tasas()
        bot.reply_to(message, mensaje, parse_mode="Markdown", reply_markup=create_main_keyboard())
    elif message.text == '❓ Ayuda':
        send_help(message)

@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    response = "No entiendo ese comando. Usa los botones de abajo:"
    bot.reply_to(message, response, reply_markup=create_main_keyboard())

# ==========================
# Iniciar bot
# ==========================
def start_bot():
    dollar_bot.start_scheduler()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    start_bot()
