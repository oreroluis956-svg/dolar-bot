import os
import telebot
import requests
from datetime import datetime

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

bot = telebot.TeleBot(TOKEN)

def obtener_tasas():
    try:
        response = requests.get("https://pydolarvenezuela-api.vercel.app/api/v1/dollar")
        data = response.json()
        if "monitors" not in data:
            return "❌ Error: Respuesta inesperada de la API."

        bcv = data["monitors"].get("bcv", {}).get("price")
        zelle = data["monitors"].get("enparalelovzla", {}).get("price")
        paypal = data["monitors"].get("dollarhouse", {}).get("price")
        eldorado = data["monitors"].get("eldorado", {}).get("price")

        mensaje = f"💱 *Tasas del Dólar en Venezuela* ({datetime.now().strftime('%d/%m/%Y')}):\n"
        if bcv: mensaje += f"🇻🇪 BCV Oficial: {bcv} Bs/USD\n"
        if zelle: mensaje += f"🏦 Zelle (EnParaleloVzla): {zelle} Bs/USD\n"
        if paypal: mensaje += f"💸 PayPal (DollarHouse): {paypal} Bs/USD\n"
        if eldorado: mensaje += f"🏪 El Dorado: {eldorado} Bs/USD\n"

        return mensaje or "❌ No se pudieron obtener las tasas."
    except Exception as e:
        return f"❌ Error al consultar tasas: {e}"

@bot.message_handler(commands=['tasas'])
def enviar_tasas(message):
    texto = obtener_tasas()
    bot.reply_to(message, texto, parse_mode="Markdown")

print("✅ Bot actualizado con El Dorado... esperando comandos.")
bot.polling()
