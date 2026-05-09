import telebot
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ================== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==================
TOKEN = os.getenv("BOT_TOKEN")
YOOMONEY_WALLET = os.getenv("YOOMONEY_WALLET")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# =======================================================

bot = telebot.TeleBot(TOKEN)

# Главное меню
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
        bot.send_message(message.chat.id, "🎁 Раздел подарков скоро будет готов!")
    elif message.text == "❗Поддержка❗":
        bot.send_message(message.chat.id, "Напишите свой вопрос сюда → @твой_ник")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("pay_"):
        parts = call.data.split("_")
        stars = int(parts[1])
        amount = int(parts[2])
        
        # Точная ссылка как в Salebot (payment_sum)
        pay_url = f"https://yoomoney.ru/transfer?to={YOOMONEY_WALLET}&amount={amount}&comment=Telegram%20Stars%20{stars}"
        
        text = f"✅ Вы выбрали:\n{stars}⭐ — {amount}₽"
        
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("💳 Оплатить через ЮMoney", url=pay_url))
        markup.add(InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{stars}_{amount}"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif call.data.startswith("paid_"):
        parts = call.data.split("_")
        stars = parts[1]
        amount = parts[2]
        
        bot.answer_callback_query(call.id, "Спасибо!")
        bot.send_message(call.message.chat.id, f"✅ Оплата прошла!\nОжидайте выдачу {stars}⭐ (1–5 минут)")
        
        # Пересылаем тебе
        bot.send_message(ADMIN_ID, 
            f"💰 НОВАЯ ОПЛАТА!\n"
            f"Пользователь: @{call.from_user.username} (ID: {call.from_user.id})\n"
            f"Звёзды: {stars}⭐\n"
            f"Сумма: {amount}₽\n"
            f"Проверь оплату и выдай звёзды!")

print("Бот запущен...")
bot.infinity_polling()
