import logging
import sqlite3
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ---------- НАСТРОЙКИ ----------
import os
TOKEN = 8176638903:AAE8Wtc4fSW9lFTMrRknIUg7SSXl6YWXxqY

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- БАЗА ДАННЫХ ----------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            name TEXT,
            phone TEXT,
            category TEXT,
            experience INTEGER,
            price_per_hour INTEGER,
            location TEXT,
            description TEXT,
            rating REAL DEFAULT 5.0
        )
        """
    )
    conn.commit()
    conn.close()


def add_worker(
    telegram_id: int,
    name: str,
    phone: str,
    category: str,
    experience: int,
    price_per_hour: int,
    location: str,
    description: str,
):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO workers
            (telegram_id, name, phone, category, experience, price_per_hour, location, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_id,
            name,
            phone,
            category,
            experience,
            price_per_hour,
            location,
            description,
        ),
    )
    conn.commit()
    conn.close()


def get_workers_by_category(category: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT name, phone, experience, price_per_hour, location, rating FROM workers WHERE category = ?",
        (category,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- ГЛАВНОЕ МЕНЮ ----------

def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔍 Найти мастера", callback_data="search")],
        [InlineKeyboardButton("👷 Я мастер — добавить себя", callback_data="register")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🏠 <b>Поиск мастеров по ремонту квартир</b>\n\n"
        "Выберите действие ниже:"
    )
    await update.message.reply_text(
        text, reply_markup=main_menu_keyboard(), parse_mode="HTML"
    )


# ---------- ПОИСК МАСТЕРОВ ----------

async def on_search_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Штукатур-маляр", callback_data="cat_Штукатур-маляр")],
        [InlineKeyboardButton("Сантехник", callback_data="cat_Сантехник")],
        [InlineKeyboardButton("Электрик", callback_data="cat_Электрик")],
        [InlineKeyboardButton("Плиточник", callback_data="cat_Плиточник")],
        [InlineKeyboardButton("Комплексный ремонт", callback_data="cat_Комплексный ремонт")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")],
    ]
    await query.edit_message_text(
        "Выберите категорию:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def on_category_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data.split("_", 1)[1]
    workers = get_workers_by_category(category)

    if not workers:
        await query.edit_message_text(
            f"😔 По категории <b>{category}</b> мастеров пока нет.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("➕ Я мастер — добавить себя", callback_data="register")],
                 [InlineKeyboardButton("⬅️ Назад", callback_data="search")]]
            ),
        )
        return

    text = f"<b>{category}</b>\n\nНайдено мастеров: {len(workers)}\n\n"
    for w in workers:
        name, phone, exp, price, loc, rating = w
        text += (
            f"<b>{name}</b>\n"
            f"⭐ {rating} | опыт {exp} лет\n"
            f"💰 {price} ₽/час\n"
            f"📍 {loc}\n"
            f"📞 <code>{phone}</code>\n\n"
        )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="search")]]
        ),
    )


# ---------- РЕГИСТРАЦИЯ МАСТЕРА ----------

(
    ENTER_NAME,
    ENTER_PHONE,
    ENTER_CATEGORY,
    ENTER_EXPERIENCE,
    ENTER_PRICE,
    ENTER_LOCATION,
    ENTER_DESC,
    CONFIRM,
) = range(8)


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data.clear()
    await query.edit_message_text("👷 Регистрация мастера\n\nВведите ваше ФИО:")
    return ENTER_NAME


async def reg_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Пожалуйста, введите ФИО.")
        return ENTER_NAME

    context.user_data["name"] = name
    await update.message.reply_text("Теперь введите номер телефона (например, +79991234567):")
    return ENTER_PHONE


async def reg_get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not phone.startswith("+") or not phone[1:].replace(" ", "").isdigit():
        await update.message.reply_text("Некорректный номер. Введите в формате +7XXXXXXXXXX.")
        return ENTER_PHONE

    context.user_data["phone"] = phone

    keyboard = [
        ["Штукатур-маляр"],
        ["Сантехник"],
        ["Электрик"],
        ["Плиточник"],
        ["Комплексный ремонт"],
    ]
    await update.message.reply_text(
        "Выберите специализацию:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=True
        ),
    )
    return ENTER_CATEGORY


async def reg_get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text.strip()
    context.user_data["category"] = category

    await update.message.reply_text(
        "Сколько лет опыта?", reply_markup=ReplyKeyboardRemove()
    )
    return ENTER_EXPERIENCE


async def reg_get_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        exp = int(update.message.text.strip())
        if exp < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите число лет опыта, например 5.")
        return ENTER_EXPERIENCE

    context.user_data["experience"] = exp
    await update.message.reply_text("Ваша ставка (руб/час), только число:")
    return ENTER_PRICE


async def reg_get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text.strip())
        if price <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите число, например 1500.")
        return ENTER_PRICE

    context.user_data["price_per_hour"] = price
    await update.message.reply_text("В каком районе работаете? (например, Центр, Юг, Любой):")
    return ENTER_LOCATION


async def reg_get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.text.strip()
    context.user_data["location"] = loc
    await update.message.reply_text(
        "Кратко о себе (опыт, что делаете, преимущества). "
        "Или напишите «пропустить»."
    )
    return ENTER_DESC


async def reg_get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    if desc.lower() == "пропустить":
        desc = ""
    context.user_data["description"] = desc

    data = context.user_data
    text = (
        "🔎 Проверьте данные:\n\n"
        f"👤 ФИО: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"🎯 Категория: {data['category']}\n"
        f"🏢 Опыт: {data['experience']} лет\n"
        f"💰 Ставка: {data['price_per_hour']} ₽/час\n"
        f"📍 Район: {data['location']}\n"
        f"📝 Описание: {data['description'] or 'не указано'}\n\n"
        "Если всё верно — напишите «да». Если нет — «нет»."
    )
    await update.message.reply_text(text)
    return CONFIRM


async def reg_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.message.text.strip().lower()
    if ans != "да":
        await update.message.reply_text(
            "Регистрация отменена. Можно начать заново из меню.",
            reply_markup=main_menu_keyboard(),
        )
        context.user_data.clear()
        return ConversationHandler.END

    user = update.effective_user
    data = context.user_data

    add_worker(
        telegram_id=user.id,
        name=data["name"],
        phone=data["phone"],
        category=data["category"],
        experience=data["experience"],
        price_per_hour=data["price_per_hour"],
        location=data["location"],
        description=data["description"],
    )

    await update.message.reply_text(
        "🎉 Вы успешно добавлены в базу мастеров!\n"
        "Теперь клиенты смогут найти вас через поиск.",
        reply_markup=main_menu_keyboard(),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def reg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Регистрация отменена.", reply_markup=main_menu_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END


# ---------- ОБЩИЙ CALLBACK ----------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "search":
        await on_search_click(update, context)
    elif data.startswith("cat_"):
        await on_category_click(update, context)
    elif data == "register":
        # передаём управление ConversationHandler
        return await register_start(update, context)
    elif data == "back_main":
        await query.edit_message_text(
            "Главное меню:", reply_markup=main_menu_keyboard()
        )


# ---------- HELP ----------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 Помощь:\n\n"
        "🔍 Найти мастера — выбрать категорию и посмотреть контакты мастеров.\n"
        "👷 Я мастер — добавить себя в базу через простую анкету.\n"
        "После регистрации вы появитесь в поиске."
    )
    await update.message.reply_text(text)


# ---------- MAIN ----------

def main():
    init_db()

    app = Application.builder().token(TOKEN).build()

    # Регистрация мастера (диалог)
    reg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(register_start, pattern="^register$")],
        states={
            ENTER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_name)
            ],
            ENTER_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_phone)
            ],
            ENTER_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_category)
            ],
            ENTER_EXPERIENCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_experience)
            ],
            ENTER_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_price)
            ],
            ENTER_LOCATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_location)
            ],
            ENTER_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_desc)
            ],
            CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_confirm)
            ],
        },
        fallbacks=[CommandHandler("cancel", reg_cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(reg_conv)
    app.add_handler(CallbackQueryHandler(on_callback))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
