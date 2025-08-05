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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration
TOKEN = os.getenv("TOKEN", "your_bot_token_here")
CHAT_ID_STR = os.getenv("CHAT_ID", "0")

if not TOKEN or TOKEN == "your_bot_token_here":
    logger.error("Bot token not provided. Please set TOKEN environment variable.")
    exit(1)

# Validate and convert CHAT_ID
try:
    CHAT_ID = int(CHAT_ID_STR)
    if CHAT_ID == 0:
        logger.error("Chat ID not provided. Please set CHAT_ID environment variable.")
        exit(1)
except ValueError:
    logger.error(f"Invalid CHAT_ID format: '{CHAT_ID_STR}'. CHAT_ID should be a numeric value, not a token.")
    logger.error("Please check that TOKEN and CHAT_ID environment variables are set correctly.")
    logger.error("TOKEN should be your bot token (like: 123456789:ABCdefGhIjKlMnOpQr)")
    logger.error("CHAT_ID should be a numeric chat ID (like: 123456789)")
    exit(1)

bot = telebot.TeleBot(TOKEN)
storage = RateStorage()

class DollarBot:
    def __init__(self):
        self.last_update = None
        self.last_rates = None
        self.scheduler_running = False
        self.clp_scraper = CLPTodayScraper()
        
    def obtener_tasas(self):
        """Fetch current dollar and euro exchange rates from multiple sources"""
        try:
            # Get BCV official rate
            bcv_response = requests.get("https://pydolarve.org/api/v2/tipo-cambio?currency=usd&rounded_price=true", timeout=10)
            bcv_response.raise_for_status()
            bcv_data = bcv_response.json()
            bcv = bcv_data.get('price', 0)
            
            if bcv <= 0:
                logger.error("Invalid BCV rate received from API")
                return "❌ Error al obtener la tasa BCV."
            
            # Build message with BCV rate
            now = datetime.datetime.now()
            mensaje = f"💱 *Tasas de Cambio en Venezuela* ({now.strftime('%d/%m/%Y')}):\n\n🏛️ BCV Oficial: {bcv} Bs/USD"
            
            # Try to get CLP Today rates for better accuracy
            clp_rates = self.clp_scraper.get_specific_rates()
            
            # Initialize rates collections
            promedio = bcv
            tasas_adicionales = []
            
            # Try PyDolarVe P2P API
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
                        'kucoin': '🟢 KuCoin',
                        'airtm': '🔹 AirTM',
                        'reserve': '⭐ Reserve',
                        'localbitcoins': '🟠 LocalBitcoins',
                        'yadio': '🔵 Yadio',
                        'kraken': '🟣 Kraken',
                        'coinbase': '🔷 Coinbase'
                    }
                    
                    for key, data in platforms.items():
                        if isinstance(data, dict) and 'title' in data and 'price' in data:
                            display_name = platform_display.get(key.lower(), f"📊 {data['title']}")
                            tasas_adicionales.append((display_name, data['price']))
                            
            except Exception as p2p_error:
                logger.warning(f"Could not fetch P2P rates: {p2p_error}")
            
            # Add Zelle and PayPal rates with CLP Today integration
            if bcv > 0:
                # Use CLP Today rates if available, otherwise fallback to calculated rates
                if clp_rates and clp_rates.get('usd'):
                    usd_rates = clp_rates['usd']
                    if 'zelle' in usd_rates:
                        zelle_rate = usd_rates['zelle']
                        tasas_adicionales.insert(0, ("💳 Zelle (CLP)", zelle_rate))
                        logger.info(f"Using CLP Today Zelle rate: {zelle_rate}")
                    else:
                        zelle_rate = bcv * 1.08
                        tasas_adicionales.insert(0, ("💳 Zelle", zelle_rate))
                    
                    if 'paypal' in usd_rates:
                        paypal_rate = usd_rates['paypal']
                        tasas_adicionales.insert(1, ("💙 PayPal (CLP)", paypal_rate))
                        logger.info(f"Using CLP Today PayPal rate: {paypal_rate}")
                    else:
                        paypal_rate = bcv * 1.15
                        tasas_adicionales.insert(1, ("💙 PayPal", paypal_rate))
                else:
                    # Fallback to calculated rates
                    zelle_rate = bcv * 1.08
                    paypal_rate = bcv * 1.15
                    tasas_adicionales.insert(0, ("💳 Zelle", zelle_rate))
                    tasas_adicionales.insert(1, ("💙 PayPal", paypal_rate))
            
            # Add USD rates to message
            if tasas_adicionales:
                tasas_adicionales.sort(key=lambda x: x[1])
                
                for nombre, precio in tasas_adicionales:
                    mensaje += f"\n{nombre}: {precio:.2f} Bs/USD"
                
                # Calculate average including BCV
                all_prices = [bcv] + [precio for _, precio in tasas_adicionales]
                promedio = sum(all_prices) / len(all_prices)
                mensaje += f"\n\n📊 Promedio USD: {promedio:.2f} Bs"
            
            # Add Euro rates section
            euro_rates = []
            
            # Try to get EUR from CLP Today
            if clp_rates and clp_rates.get('eur') and 'rate' in clp_rates['eur']:
                eur_rate = clp_rates['eur']['rate']
                euro_rates.append(("🇪🇺 Euro (CLP)", eur_rate))
                logger.info(f"Using CLP Today EUR rate: {eur_rate}")
            
            # Try to get EUR from PyDolarVe
            try:
                eur_response = requests.get("https://pydolarve.org/api/v2/tipo-cambio?currency=eur&rounded_price=true", timeout=10)
                eur_response.raise_for_status()
                eur_data = eur_response.json()
                eur_bcv = eur_data.get('price', 0)
                
                if eur_bcv > 0:
                    euro_rates.append(("🏛️ Euro BCV", eur_bcv))
                    logger.info(f"EUR BCV rate: {eur_bcv}")
                    
            except Exception as eur_error:
                logger.warning(f"Could not fetch EUR from PyDolarVe: {eur_error}")
            
            # If no EUR rates found, calculate based on USD
            if not euro_rates and bcv > 0:
                eur_calculated = bcv * 1.1
                euro_rates.append(("🇪🇺 Euro (Est.)", eur_calculated))
            
            # Add Euro rates to message
            if euro_rates:
                mensaje += f"\n\n💶 *Tasas del Euro*:"
                for nombre, precio in euro_rates:
                    mensaje += f"\n{nombre}: {precio:.2f} Bs/EUR"
            
            # Use BCV as primary rate for storage and comparison
            rate_to_store = bcv
            
            # Check for significant changes
            anterior = storage.get_previous_rate()
            if anterior > 0:
                cambio = abs(rate_to_store - anterior) / anterior * 100
                
                if cambio >= 2:
                    signo = "📈 Subió" if rate_to_store > anterior else "📉 Bajó"
                    mensaje += f"\n\n⚠️ {signo} más de 2% respecto al día anterior."
            
            # Store current rate
            storage.save_rate(rate_to_store)
            
            # Add timestamp and source information
            mensaje += f"\n\n🕐 Actualizado: {now.strftime('%H:%M')}"
            mensaje += f"\n📡 Fuentes: PyDolarVe, CLP Today"
            
            # Update internal state
            self.last_update = now
            self.last_rates = {
                'bcv': bcv,
                'promedio': promedio,
                'anterior': anterior,
                'euro_rates': euro_rates if 'euro_rates' in locals() else []
            }
            
            logger.info(f"Rates updated successfully. BCV: {bcv} Bs, EUR rates: {len(euro_rates) if 'euro_rates' in locals() else 0}")
            return mensaje
            
        except requests.exceptions.RequestException as e:
            error_msg = f"❌ Error al obtener las tasas: {str(e)}"
            logger.error(f"API request failed: {e}")
            return error_msg
        except KeyError as e:
            error_msg = f"❌ Error en el formato de respuesta de la API: {str(e)}"
            logger.error(f"API response format error: {e}")
            return error_msg
        except Exception as e:
            error_msg = f"❌ Error inesperado: {str(e)}"
            logger.error(f"Unexpected error: {e}")
            return error_msg
    
    def send_daily_update(self):
        """Send daily update to configured chat"""
        try:
            mensaje = self.obtener_tasas()
            bot.send_message(CHAT_ID, mensaje)
            logger.info("Daily update sent successfully")
        except Exception as e:
            logger.error(f"Failed to send daily update: {e}")
    
    def should_send_update(self):
        """Check if it's time to send daily update (9 AM on weekdays)"""
        now = datetime.datetime.now()
        return now.weekday() < 5 and now.hour == 9 and now.minute < 5
    
    def start_scheduler(self):
        """Start the scheduler thread for daily updates"""
        if self.scheduler_running:
            return
            
        self.scheduler_running = True
        
        def scheduler_loop():
            last_check_hour = -1
            
            while self.scheduler_running:
                try:
                    now = datetime.datetime.now()
                    
                    # Check if it's time for daily update (only once per hour)
                    if (now.hour != last_check_hour and 
                        now.weekday() < 5 and 
                        now.hour == 9 and 
                        now.minute < 30):
                        
                        logger.info("Sending scheduled daily update")
                        self.send_daily_update()
                        last_check_hour = now.hour
                    
                    # Sleep for 1 minute
                    time.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    time.sleep(60)
        
        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
        logger.info("Scheduler started")
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.scheduler_running = False
        logger.info("Scheduler stopped")
    
    def get_status(self):
        """Get bot status information"""
        return {
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'last_rates': self.last_rates,
            'scheduler_running': self.scheduler_running,
            'chat_id': CHAT_ID
        }

# Initialize bot instance
dollar_bot = DollarBot()

def create_main_keyboard():
    """Create the main keyboard with bot commands"""
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_tasas = types.KeyboardButton('💰 Tasas')
    btn_actualizar = types.KeyboardButton('🔄 Actualizar')
    btn_ayuda = types.KeyboardButton('❓ Ayuda')
    keyboard.add(btn_tasas, btn_actualizar)
    keyboard.add(btn_ayuda)
    return keyboard

# Bot command handlers
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handle /start command"""
    try:
        welcome_msg = """
¡Hola! 👋 Soy tu bot del dólar venezolano.

Usa los botones de abajo para:
• 💰 Tasas - Ver tasas actuales del dólar
• 🔄 Actualizar - Obtener las tasas más recientes  
• ❓ Ayuda - Ver información de ayuda

Recibirás actualizaciones automáticas cada día hábil a las 9:00 AM y alertas cuando las tasas cambien más del 2%.
        """
        keyboard = create_main_keyboard()
        bot.reply_to(message, welcome_msg, reply_markup=keyboard)
        logger.info(f"Welcome message sent to {message.from_user.username}")
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")

@bot.message_handler(commands=['help'])
def send_help(message):
    """Handle /help command"""
    try:
        help_msg = """
🤖 Bot del Dólar Venezolano

Botones disponibles:
• 💰 Tasas - Consultar tasas actuales
• 🔄 Actualizar - Obtener datos más recientes
• ❓ Ayuda - Mostrar esta información

El bot envía actualizaciones automáticas:
• Todos los días hábiles a las 9:00 AM
• Alertas cuando las tasas cambien más del 2%

Fuente de datos: PyDolarVe
        """
        keyboard = create_main_keyboard()
        bot.reply_to(message, help_msg, reply_markup=keyboard)
        logger.info(f"Help message sent to {message.from_user.username}")
    except Exception as e:
        logger.error(f"Error sending help message: {e}")

@bot.message_handler(commands=['tasas'])
def consulta_manual(message):
    """Handle /tasas command for manual rate checking"""
    try:
        logger.info(f"Manual rate query from {message.from_user.username}")
        mensaje = dollar_bot.obtener_tasas()
        keyboard = create_main_keyboard()
        bot.reply_to(message, mensaje, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        error_msg = f"❌ Error al procesar tu solicitud: {str(e)}"
        keyboard = create_main_keyboard()
        bot.reply_to(message, error_msg, reply_markup=keyboard)
        logger.error(f"Error in manual query: {e}")

# Handler for button presses
@bot.message_handler(func=lambda message: message.text in ['💰 Tasas', '🔄 Actualizar', '❓ Ayuda'])
def handle_buttons(message):
    """Handle button presses"""
    try:
        if message.text == '💰 Tasas' or message.text == '🔄 Actualizar':
            logger.info(f"Button rate query from {message.from_user.username}")
            mensaje = dollar_bot.obtener_tasas()
            keyboard = create_main_keyboard()
            bot.reply_to(message, mensaje, parse_mode="Markdown", reply_markup=keyboard)
        elif message.text == '❓ Ayuda':
            send_help(message)
    except Exception as e:
        error_msg = f"❌ Error al procesar tu solicitud: {str(e)}"
        keyboard = create_main_keyboard()
        bot.reply_to(message, error_msg, reply_markup=keyboard)
        logger.error(f"Error in button handler: {e}")

@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    """Handle unknown messages"""
    try:
        response = "No entiendo ese comando. Usa los botones de abajo para interactuar conmigo:"
        keyboard = create_main_keyboard()
        bot.reply_to(message, response, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error handling unknown message: {e}")

def start_bot():
    """Start the Telegram bot"""
    try:
        logger.info("Starting Telegram bot...")
        dollar_bot.start_scheduler()
        
        # Test bot connection
        bot_info = bot.get_me()
        logger.info(f"Bot started successfully: @{bot_info.username}")
        
        # Start polling
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    start_bot()
