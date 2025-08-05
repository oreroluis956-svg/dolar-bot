import os
import requests
import telebot
import datetime
from replit import db

TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
bot = telebot.TeleBot(TOKEN)

if "anterior" not in db:
    db["anterior"] = 0.0

def obtener_tasas():
    base = "https://pydolarve.org/api/v2"
    bcv = requests.get(f"{base}/tipo-cambio?currency=usd&rounded_price=true").json()['price']
    data = requests.get(f"{base}/market-p2p?currency=usd&rounded_price=true").json()['monitors']
    tasas = {d['title']: d['price'] for d in data}
    prom = (sum(tasas.values()) + bcv) / (len(tasas) + 1)

    mensaje = f"🟢 Tasas del dólar hoy ({datetime.datetime.now().strftime('%d-%m-%Y')}):\n\n🇻🇪 BCV: {bcv} Bs"
    for nombre, valor in tasas.items():
        mensaje += f"\n💸 {nombre}: {valor} Bs"
    mensaje += f"\n\n📊 Promedio general: {prom:.2f} Bs"

    anterior = db["anterior"]
    cambio = abs(prom - anterior) / anterior * 100 if anterior > 0 else 0

    if cambio >= 2:
        signo = "📈 Subió" if prom > anterior else "📉 Bajó"
        mensaje += f"\n\n⚠️ {signo} más de 2% respecto al día anterior."

    db["anterior"] = prom
    return mensaje

now = datetime.datetime.now()
if now.weekday() < 5 and now.hour == 9:
    bot.send_message(CHAT_ID, obtener_tasas())

@bot.message_handler(commands=['tasas'])
def consulta_manual(m):
    bot.send_message(m.chat.id, obtener_tasas())

bot.infinity_polling()
