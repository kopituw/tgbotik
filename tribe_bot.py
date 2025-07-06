import random
import asyncio
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔐 Токен от BotFather
TOKEN = "7923343199:AAEwlBEeao_UjO3m4jiNZegsP2olsqTwTbg"

# 🛡️ Telegram ID администратора
ADMIN_CHAT_ID = 756605376

# Внутренние данные
users = []
teams = []

# Список заданий
tasks = [
    "Общайся только гласными.",
    "Общайся только согласными.",
    "Перемещайся на одной ноге.",
    "Не открывай рот — губы должны быть сомкнуты.",
    "Общайся шепотом.",
    "Объясняйся только жестами.",
    "Каждую фразу начинай со слова «пупочки-пупочки!».",
    "Используй только слова из песен.",
    "Говори только вопросами.",
    "Общайся в рифму.",
    "Используй акцент старого профессора.",
    "Общайся только мемами.",
    "Двигайся танцуя, пока ищешь участников.",
    "Говори только цитатами из фильмов.",
    "Используй только слова, начинающиеся на «С».",
	"В каждом предложении должно быть слово 'Школа'"
]

# Состояния диалога
NAME, NICK, TRIBE = range(3)

# Старт — спрашиваем имя
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Как тебя зовут?", reply_markup=ReplyKeyboardRemove())
    return NAME

# Получаем имя, спрашиваем ник
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Отлично! А твой ник?", reply_markup=ReplyKeyboardRemove())
    return NICK

# Получаем ник, предлагаем выбрать трайб кнопками
async def get_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nick"] = update.message.text

    keyboard = [
        [
            InlineKeyboardButton("🦎 Аксолотли", callback_data="tribe_Аксолотли"),
            InlineKeyboardButton("🐛 Тихоходки", callback_data="tribe_Тихоходки")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎯 Выбери свой трайб:",
        reply_markup=reply_markup
    )
    return TRIBE

# Обработка выбора трайба через кнопку
async def tribe_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tribe = query.data.replace("tribe_", "")
    context.user_data["tribe"] = tribe

    users.append({
        "chat_id": query.message.chat.id,
        "name": context.user_data["name"],
        "nick": context.user_data["nick"],
        "tribe": tribe
    })

    tribe_emoji = "🦎" if tribe == "Аксолотли" else "🐛"

    await query.edit_message_text(
        f"✅ Ты зарегистрирован как {tribe_emoji} <b>{tribe}</b>!\n\n"
        "⏳ Жди формирования команд от администратора.",
        parse_mode='HTML'
    )
    return ConversationHandler.END

# Формирование команд
def create_teams():
    global users, teams
    axolotls = [u for u in users if u['tribe'] == 'Аксолотли']
    tardigrades = [u for u in users if u['tribe'] == 'Тихоходки']
    random.shuffle(axolotls)
    random.shuffle(tardigrades)

    teams.clear()
    team_number = 1
    while len(axolotls) >= 3 and len(tardigrades) >= 3:
        team = [axolotls.pop(), axolotls.pop(), axolotls.pop(), 
                tardigrades.pop(), tardigrades.pop(), tardigrades.pop()]
        # Добавляем номер команды к каждому участнику
        for member in team:
            member['team_number'] = team_number
        teams.append(team)
        team_number += 1

# Рассылка заданий и команд
async def notify_teams(application):
    for team in teams:
        team_description = "\n".join(
            [f"{'🦎' if member['tribe'] == 'Аксолотли' else '🐛'} {member['name']} – {member['nick']} – {member['tribe']}" for member in team]
        )
        for member in team:
            task = random.choice(tasks)
            message = (
                f"🎉 <b>Твоя команда #{member['team_number']}:</b>\n{team_description}\n\n"
                f"🎯 <b>Для поиска команды у тебя есть усложнение:</b> {task}"
            )
            await application.bot.send_message(chat_id=member['chat_id'], text=message, parse_mode='HTML')
            # Небольшая задержка чтобы не превысить лимиты Telegram API
            await asyncio.sleep(0.1)

# Функция для разбивки длинных сообщений
def split_message(text, max_length=4000):
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    lines = text.split('\n')
    
    for line in lines:
        if len(current_part) + len(line) + 1 <= max_length:
            current_part += line + '\n'
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = line + '\n'
    
    if current_part:
        parts.append(current_part.strip())
    
    return parts

# Админ-команда для формирования команд
async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Ты не админ 🙃, ай!")
        return

    keyboard = [
        [InlineKeyboardButton("🚀 Сформировать команды", callback_data="form_teams")],
        [InlineKeyboardButton("👥 Показать участников", callback_data="show_users")],
        [InlineKeyboardButton("🏆 Показать команды", callback_data="show_teams")],
        [InlineKeyboardButton("🗑️ Очистить всех", callback_data="clear_users")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Панель администратора:", reply_markup=reply_markup)

# Обработка кнопки админа
async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global users, teams
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_CHAT_ID:
        return

    if query.data == "form_teams":
        if len(users) < 6:
            await query.edit_message_text("Недостаточно участников для формирования команд. Нужно минимум 6 человек (3 аксолотля + 3 тихоходки).")
        else:
            create_teams()
            await notify_teams(context.application)
            await query.edit_message_text("Команды сформированы и задания разосланы!")
    
    elif query.data == "show_users":
        if not users:
            await query.edit_message_text("Пока нет зарегистрированных участников.")
        else:
            user_list = "\n".join([
                f"{'🦎' if user['tribe'] == 'Аксолотли' else '🐛'} {user['name']} (@{user['nick']}) - {user['tribe']}"
                for user in users
            ])
            
            message_parts = split_message(f"📋 Зарегистрированные участники ({len(users)}):\n\n{user_list}")
            
            if len(message_parts) == 1:
                await query.edit_message_text(message_parts[0])
            else:
                # Если сообщение слишком длинное, отправляем несколько частей
                await query.edit_message_text(f"📋 Зарегистрированные участники ({len(users)}):\n\n{message_parts[0]}")
                for i, part in enumerate(message_parts[1:], 1):
                    await context.application.bot.send_message(
                        chat_id=ADMIN_CHAT_ID, 
                        text=f"📋 Продолжение ({i+1}/{len(message_parts)}):\n\n{part}"
                    )
    
    elif query.data == "show_teams":
        if not teams:
            await query.edit_message_text("Команды еще не сформированы.")
        else:
            # Показываем сформированные команды
            teams_info = []
            for i, team in enumerate(teams, 1):
                team_members = "\n".join([
                    f"  {'🦎' if member['tribe'] == 'Аксолотли' else '🐛'} {member['name']} (@{member['nick']})"
                    for member in team
                ])
                teams_info.append(f"🏆 <b>Команда #{i}:</b>\n{team_members}")
            
            teams_text = "\n\n".join(teams_info)
            
            # Находим участников без команды
            team_members = []
            for team in teams:
                team_members.extend(team)
            
            remaining_users = [user for user in users if user not in team_members]
            
            if remaining_users:
                remaining_list = "\n".join([
                    f"{'🦎' if user['tribe'] == 'Аксолотли' else '🐛'} {user['name']} (@{user['nick']}) - {user['tribe']}"
                    for user in remaining_users
                ])
                remaining_text = f"\n\n👥 <b>Участники без команды ({len(remaining_users)}):</b>\n{remaining_list}"
            else:
                remaining_text = "\n\n✅ Все участники распределены по командам!"
            
            full_message = f"🏆 <b>Сформированные команды ({len(teams)}):</b>\n\n{teams_text}{remaining_text}"
            
            message_parts = split_message(full_message)
            
            if len(message_parts) == 1:
                await query.edit_message_text(message_parts[0], parse_mode='HTML')
            else:
                await query.edit_message_text(message_parts[0], parse_mode='HTML')
                for i, part in enumerate(message_parts[1:], 1):
                    await context.application.bot.send_message(
                        chat_id=ADMIN_CHAT_ID, 
                        text=f"🏆 Продолжение ({i+1}/{len(message_parts)}):\n\n{part}",
                        parse_mode='HTML'
                    )
    
    elif query.data == "clear_users":
        users.clear()
        teams.clear()
        await query.edit_message_text("✅ Все участники удалены!")

def main():
    # Создаем приложение с обработкой ошибок
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Добавляем обработчик ошибок
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error("Exception while handling an update:", exc_info=context.error)
        if "Conflict" in str(context.error):
            logger.info("Conflict detected, restarting bot...")
            await asyncio.sleep(5)
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
    
    app.add_error_handler(error_handler)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nick)],
            TRIBE: [CallbackQueryHandler(tribe_chosen, pattern=r"^tribe_")],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start_admin", start_admin))
    app.add_handler(CallbackQueryHandler(admin_button_handler, pattern="^form_teams$|^show_users$|^show_teams$|^clear_users$"))

    print("Бот запущен.")
    
    # Запуск с обработкой ошибок
    try:
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        if "Conflict" in str(e):
            logger.info("Restarting due to conflict...")
            asyncio.sleep(5)
            main()  # Рекурсивный перезапуск

if __name__ == "__main__":
    main()
