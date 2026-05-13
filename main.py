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
pending_orders = {}  # label → данные заказа

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

    elif message.text == "🎁 Купить подарки 🎁":
        bot.send_message(message.chat.id, "🎁 Функция покупки подарков пока в разработке.\nСкоро будет доступна!")

    elif message.text == "❗Поддержка❗":
        bot.send_message(message.chat.id, "❗ Напишите @ваш_ник_для_поддержки\nМы ответим в ближайшее время!")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("pay_"):
        parts = call.data.split("_")
        stars = int(parts[1])
        amount = int(parts[2])

        order_label = f"stars_{stars}_{call.message.chat.id}_{int(time.time())}"

        pending_orders[order_label] = {
            'user_id': call.message.chat.id,
            'username': call.from_user.username or call.from_user.first_name or "no_username",
            'stars': stars,
            'amount': amount,
            'time': time.time()
        }

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

        text = f"✅ Вы выбрали:\n{stars}⭐ — {amount}₽"

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("💳 Оплатить через ЮMoney", url=pay_url))
        markup.add(InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{stars}_{amount}"))

        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("paid_"):
        bot.answer_callback_query(call.id, "Проверяем...")
        bot.send_message(
            call.message.chat.id,
            "✅ Оплата проверяется автоматически каждые 30 секунд.\n"
            "Как только деньги придут — я сразу получу уведомление."
        )

    elif call.data == "back_to_menu":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            "Главное меню:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )
        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=main_menu())

# ================== АВТОМАТИЧЕСКАЯ ПРОВЕРКА ==================
def check_payments():
    while True:
        try:
            # Удаляем старые заказы (старше 2 часов)
            now = time.time()
            for label in list(pending_orders.keys()):
                if now - pending_orders[label]['time'] > 7200:
                    del pending_orders[label]

            history = client.operation_history(limit=30)
            for operation in history.operations:
                if operation.status != 'success' or operation.amount <= 0:
                    continue

                payment_id = operation.operation_id
                if payment_id in processed_payments:
                    continue

                label = getattr(operation, 'label', None) or ""
                comment = str(getattr(operation, 'comment', '') or "")

                # === ОСНОВНАЯ ПРОВЕРКА ПО LABEL ===
                if label and label in pending_orders:
                    data = pending_orders[label]
                    if abs(operation.amount - data['amount']) > 1:
                        continue

                    user_id = data['user_id']
                    username = data['username']
                    stars = data['stars']

                    bot.send_message(
                        user_id,
                        "✅ Оплата подтверждена!\nОжидайте, звёзды будут выданы вручную в ближайшее время."
                    )

                    # Кнопка возврата в меню
                    menu_markup = InlineKeyboardMarkup()
                    menu_markup.add(InlineKeyboardButton("🏠 Вернуться в меню", callback_data="back_to_menu"))
                    bot.send_message(user_id, "Выберите действие:", reply_markup=menu_markup)

                    bot.send_message(
                        ADMIN_ID,
                        f"💰 **ОПЛАТА ПОДТВЕРЖДЕНА!**\n"
                        f"@{username} (id{user_id}) оплатил {stars}⭐\n"
                        f"Сумма: {operation.amount} ₽\n"
                        f"Label: {label}",
                        parse_mode='Markdown'
                    )

                    processed_payments.add(payment_id)
                    del pending_orders[label]
                    continue

                # Запасной вариант — по комментарию
                if "Telegram Stars" in comment:
                    try:
                        stars = int(comment.split("Telegram Stars ")[-1])
                        bot.send_message(
                            ADMIN_ID,
                            f"💰 **ОПЛАТА ПОДТВЕРЖДЕНА!**\n"
                            f"Неизвестный пользователь оплатил {stars}⭐\n"
                            f"Сумма: {operation.amount} ₽",
                            parse_mode='Markdown'
                        )
                        processed_payments.add(payment_id)
                    except:
                        pass

        except Exception as e:
            print("Ошибка проверки оплаты:", e)

        time.sleep(30)

threading.Thread(target=check_payments, daemon=True).start()

print("Бот запущен с автоматической проверкой оплаты...")
bot.infinity_polling()
