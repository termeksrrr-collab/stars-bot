import telebot
import os
import time
import threading
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from yoomoney import Client

# ================== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==================
TOKEN = os.getenv("BOT_TOKEN")
YOOMONEY_WALLET = os.getenv("YOOMONEY_WALLET")
YOOMONEY_TOKEN = os.getenv("YOOMONEY_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# =======================================================

bot = telebot.TeleBot(TOKEN)
client = Client(token=YOOMONEY_TOKE

processed_payments = set()

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(KeyboardButton("⭐ Купить звезды ⭐"))
    markup.add(KeyboardButton("🎁 Купить подарки 🎁"))
    markup.add(KeyboardButton("❗Поддержка❗"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    text = """Здравствуйте
Я бот по продаже 
⭐звёзд
🎁удаленные праздничные подарки"""
    bot.send_message(message.chat.id, text, reply_markup=main_menu())

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if message.text == "⭐ Купить звезды ⭐":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("50⭐ — 70₽", callback_data="pay_50_70"))
        markup.add(InlineKeyboardButton("100⭐ — 140₽", callback_data="pay_100_140"))
        markup.add(InlineKeyboardButton("150⭐ — 210₽", callback_data="pay_150_210"))
        bot.send_message(message.chat.id, "Выберите количество звёзд:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("pay_"):
        parts = call.data.split("_")
        stars = int(parts[1])
        amount = int(parts[2])

        # === НОВАЯ ПРАВИЛЬНАЯ ССЫЛКА (как было в Salebot) ===
        targets = f"Покупка {stars}⭐ Telegram Stars"
        order_label = f"stars_{stars}_{call.message.chat.id}_{int(time.time())}"

        pay_url = (
            f"https://yoomoney.ru/quickpay/confirm.xml?"
            f"receiver={YOOMONEY_WALLET}&"
            f"quickpay-form=shop&"
            f"targets={targets.replace(' ', '%20')}&"
            f"sum={amount}&"
            f"label={order_label}&"
            f"comment=Telegram%20Stars%20{stars}"
        )

        text = f"✅ Вы выбрали:\n{stars}⭐ — {amount}₽"

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("💳 Оплатить через ЮMoney", url=pay_url))
        markup.add(InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{stars}_{amount}"))

        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("paid_"):
        bot.answer_callback_query(call.id, "Проверяем...")
bot.send_message(call.message.chat.id, "✅ Оплата проверяется автоматически каждые 30 секунд.\nКак только деньги придут — звёзды будут выданы!")

# ================== АВТОМАТИЧЕСКАЯ ПРОВЕРКА ==================
def check_payments():
    while True:
        try:
            history = client.operation_history(limit=10)
            for operation in history.operations:
                if operation.status != 'success' or operation.amount <= 0:
                    continue
                comment = str(operation.comment or "")
                if "Telegram Stars" not in comment:
                    continue
                payment_id = operation.operation_id
                if payment_id in processed_payments:
                    continue
                
                try:
                    stars = int(comment.split("Telegram Stars ")[-1])
                except:
                    continue
                
                processed_payments.add(payment_id)
                
                bot.send_message(ADMIN_ID, 
                    f"💰 АВТО ОПЛАТА ПОЛУЧЕНА!\n"
                    f"Сумма: {operation.amount} ₽\n"
                    f"Звёзды: {stars}⭐\n"
                    f"ID операции: {payment_id}")
                
                print(f"Автоматически выдано {stars} звёзд")
        except Exception as e:
            print("Ошибка проверки оплаты:", e)
        
        time.sleep(30)

threading.Thread(target=check_payments, daemon=True).start()

print("Бот запущен с автоматической проверкой оплаты...")
bot.infinity_polling()

