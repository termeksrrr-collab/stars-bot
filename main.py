import telebot
import os
import time
import threading
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from yoomoney import Client
from urllib.parse import urlencode

# ================== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==================
TOKEN = os.getenv("BOT_TOKEN")
YOOMONEY_WALLET = os.getenv("YOOMONEY_WALLET")
YOOMONEY_TOKEN = os.getenv("YOOMONEY_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# =======================================================

bot = telebot.TeleBot(TOKEN)
client = Client(token=YOOMONEY_TOKEN)

processed_payments = set()
pending_orders = {}      # label → данные заказа
user_states = {}         # chat_id → {'stars': int, 'amount': int}

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(KeyboardButton("⭐ Купить звезды ⭐"))
    markup.add(KeyboardButton("🎁 Купить подарки 🎁"))
    markup.add(KeyboardButton("❗Поддержка❗"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
                     "Здравствуйте\nЯ бот по продаже\n⭐звёзд\n🎁удаленные праздничные подарки",
                     reply_markup=main_menu())

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    text = message.text.strip()

    if text == "⭐ Купить звезды ⭐":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("50⭐ — 70₽", callback_data="pay_50_70"))
        markup.add(InlineKeyboardButton("100⭐ — 140₽", callback_data="pay_100_140"))
        markup.add(InlineKeyboardButton("150⭐ — 210₽", callback_data="pay_150_210"))
        bot.send_message(message.chat.id, "Выберите количество звёзд:", reply_markup=markup)

    elif text == "🎁 Купить подарки 🎁":
        bot.send_message(message.chat.id, "🎁 Функция покупки подарков пока в разработке.\nСкоро будет доступна!")
    elif text == "❗Поддержка❗":
        bot.send_message(message.chat.id, "❗ Напишите @ваш_ник_для_поддержки\nМы ответим в ближайшее время!")

    # Ввод @username
    elif message.chat.id in user_states:
        username = text.replace("@", "").strip()
        if not username:
            bot.send_message(message.chat.id, "❌ Введите корректный @username")
            return

        data = user_states[message.chat.id]
        stars = data['stars']
        amount = data['amount']

        order_label = f"stars_{stars}_{message.chat.id}_{int(time.time())}"

        pending_orders[order_label] = {
            'user_id': message.chat.id,
            'custom_username': username,
            'stars': stars,
            'amount': amount
        }

        del user_states[message.chat.id]

        targets = f"Покупка {stars}⭐ Telegram Stars"
        params = {
            "receiver": YOOMONEY_WALLET,
            "quickpay-form": "shop",
            "targets": targets,
            "sum": amount,
            "label": order_label,
            "comment": f"Telegram Stars {stars}"
        }
        pay_url = "https://yoomoney.ru/quickpay/confirm.xml?" + urlencode(params)

        text_confirm = f"✅ Заказ:\n{stars}⭐ — {amount}₽\nДля: @{username}"
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("💳 Оплатить через ЮMoney", url=pay_url))
        markup.add(InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{stars}_{amount}"))

        bot.send_message(message.chat.id, text_confirm, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("pay_"):
        parts = call.data.split("_")
        stars = int(parts[1])
        amount = int(parts[2])

        user_states[call.message.chat.id] = {'stars': stars, 'amount': amount}
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            f"Вы выбрали {stars}⭐ — {amount}₽\n\nКому доставить звёзды?\nНапишите @username :",
            call.message.chat.id,
            call.message.message_id
        )

    elif call.data.startswith("paid_"):
        bot.answer_callback_query(call.id, "Проверяем...")
        bot.send_message(
            call.message.chat.id,
            "✅ Оплата проверяется автоматически каждые 30 секунд.\n"
            "Как только деньги придут — я сразу получу уведомление."
        )

# ================== ПРОВЕРКА ОПЛАТЫ ==================
def check_payments():
    while True:
        try:
            history = client.operation_history(limit=30)
            for operation in history.operations:
                if operation.status != 'success' or operation.amount <= 0:
                    continue

                payment_id = operation.operation_id
                if payment_id in processed_payments:
                    continue

                comment = str(getattr(operation, 'comment', '') or "")

                if "Telegram Stars" in comment:
                    try:
                        stars = int(comment.split("Telegram Stars ")[-1])
                        amount_received = operation.amount

                        # Ищем заказ (ослабленная проверка суммы из-за комиссии)
                        for label, data in list(pending_orders.items()):
                            if data['stars'] == stars and abs(data['amount'] - amount_received) < 10:   # ← ИСПРАВЛЕНО
                                username = data['custom_username']
                                user_id = data['user_id']

                                # Клиенту
                                bot.send_message(
                                    user_id,
                                    "✅ Оплата подтверждена!\nОжидайте, звёзды будут выданы вручную."
                                )

                                # Тебе в личку
                                bot.send_message(
                                    ADMIN_ID,
                                    f"💰 Кто-то оплатил!\n"
                                    f"@{username} оплатил {stars}⭐"
                                )

                                processed_payments.add(payment_id)
                                del pending_orders[label]
                                break
                    except:
                        pass

        except Exception as e:
            print("Ошибка проверки оплаты:", e)

        time.sleep(30)

threading.Thread(target=check_payments, daemon=True).start()

print("Бот запущен — комиссия ЮMoney учтена (допуск 10 ₽)")
bot.infinity_polling()
