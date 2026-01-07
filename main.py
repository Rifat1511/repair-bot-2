# main.py - Версия для Beget + GitHub
import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite

logging.basicConfig(level=logging.INFO)

# Настройки из переменных окружения (для безопасности)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8176638903:AAE8Wtc4fSW9lFTMrRknIUg7SSXl6YWXxqY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "487625862"))
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "401643678:TEST:test")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# База данных
async def init_db():
    async with aiosqlite.connect("remont.db") as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                name TEXT,
                phone TEXT,
                city TEXT,
                rating REAL DEFAULT 5.0
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                work TEXT,
                price INTEGER,
                status TEXT DEFAULT 'active'
            )
        ''')
        await db.commit()

# Состояния
class ClientOrder(StatesGroup):
    work = State()
    budget = State()

class MasterReg(StatesGroup):
    name = State()
    phone = State()
    city = State()

# КОМАНДА СТАРТ
@router.message(Command("start"))
async def start(message: types.Message):
    kb = types.ReplyKeyboardMarkup(keyboard=[
        [types.KeyboardButton(text="🔨 Найти мастера")],
        [types.KeyboardButton(text="👷 Я мастер")]
    ], resize_keyboard=True)
    
    await message.answer(
        "Привет! Я бот для поиска мастеров.\n"
        "Что тебе нужно?",
        reply_markup=kb
    )

# ПОИСК МАСТЕРА
@router.message(F.text == "🔨 Найти мастера")
async def find_master(message: types.Message, state: FSMContext):
    await state.set_state(ClientOrder.work)
    await message.answer("Что нужно сделать? Опишите работу:")

@router.message(ClientOrder.work)
async def get_work(message: types.Message, state: FSMContext):
    await state.update_data(work=message.text)
    await state.set_state(ClientOrder.budget)
    await message.answer("Какой бюджет? (в рублях)")

@router.message(ClientOrder.budget)
async def show_masters(message: types.Message, state: FSMContext):
    data = await state.get_data()
    budget = int(message.text.replace(" ", "").replace("₽", ""))
    
    # Тестовые мастера
    masters = [
        {"name": "Александр", "rating": 4.9, "price": budget},
        {"name": "Дмитрий", "rating": 5.0, "price": budget + 500},
        {"name": "Сергей", "rating": 4.8, "price": budget - 300}
    ]
    
    await message.answer("Найдено 3 мастера:")
    
    for m in masters:
        text = f"{m['name']} ⭐{m['rating']}\nЦена: {m['price']} ₽"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Выбрать", callback_data=f"sel_{m['price']}")]
        ])
        await message.answer(text, reply_markup=kb)
    
    await state.clear()

# ВЫБОР МАСТЕРА
@router.callback_query(F.data.startswith("sel_"))
async def select_master(callback: types.CallbackQuery):
    price = callback.data.split("_")[1]
    await callback.message.answer(
        f"Отлично! Мастер выбран.\n"
        f"Стоимость: {price} ₽\n"
        f"Он свяжется с вами в течение часа."
    )
    
    # Уведомление админу
    await bot.send_message(ADMIN_ID, 
        f"Новый заказ!\nЦена: {price} ₽\nКлиент: @{callback.from_user.username}")
    
    await callback.answer("✅")

# РЕГИСТРАЦИЯ МАСТЕРА
@router.message(F.text == "👷 Я мастер")
async def reg_master(message: types.Message, state: FSMContext):
    await state.set_state(MasterReg.name)
    await message.answer("Как вас зовут?")

@router.message(MasterReg.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(MasterReg.phone)
    await message.answer("Ваш телефон?")

@router.message(MasterReg.phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(MasterReg.city)
    await message.answer("В каком городе работаете?")

@router.message(MasterReg.city)
async def save_master(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    async with aiosqlite.connect("remont.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO masters (user_id, name, phone, city) VALUES (?, ?, ?, ?)",
            (message.from_user.id, data['name'], data['phone'], message.text)
        )
        await db.commit()
    
    await message.answer(
        f"Вы зарегистрированы!\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Город: {message.text}"
    )
    await state.clear()

# АДМИНКА
@router.message(Command("admin"))
async def admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    async with aiosqlite.connect("remont.db") as db:
        cursor = await db.execute("SELECT COUNT(*) FROM masters")
        count = (await cursor.fetchone())[0]
    
    await message.answer(f"Админ-панель\nМастеров: {count}")

# ЗАПУСК
async def on_startup():
    await init_db()
    print("Bot started!")

async def main():
    dp.include_router(router)
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    "Add payment system 10% commission"
