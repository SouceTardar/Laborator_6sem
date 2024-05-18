import asyncio
import logging
import os

import psycopg2
from aiogram import Dispatcher, Bot, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand, BotCommandScopeDefault

# Подключение к базе данных
conn = psycopg2.connect(dbname="bot_lab", user="maxim_dlia_bota",
                        password="shtangauer05", host="127.0.0.1")
cursor = conn.cursor()

router = Router()
# получаем все данные из таблицы admins
cursor.execute("SELECT * FROM admins")
print(cursor.fetchall())


# Функция для создания меню команд
def get_keyboard(is_admin):
    buttons = [
        KeyboardButton(text="/start"),
        KeyboardButton(text="/get_currencies"),
        KeyboardButton(text="/convert")
    ]
    if is_admin:
        buttons.insert(1, KeyboardButton(text="/manage_currency"))  # Добавляем кнопку для админов
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, keyboard=[buttons])
    # keyboard.add(*buttons)
    return keyboard


# Приветствие и отображение меню
@router.message(Command('start'))
async def start(message: Message):
    # Проверяем, является ли пользователь админом
    cursor.execute("SELECT id FROM admins WHERE id = %s", (message.chat.id,))
    is_admin = bool(cursor.fetchone())

    if is_admin:
        greeting = "Привет, админ!\n Команды которые есть:\n /start-что понятно для приветсвия,\n /manage_currency-при написании (Добавить валюту, Удалить валюту, Изменить курс валюты) будет выпролнять что вы написали,\n /get_currencies-выводит все сохраненные валюты с курсом к рублю,\n /convert-конвертирует заданную сумму в валюте в сумму в рублях"
    else:
        greeting = "Добрый день, гость! \n\n"

    await message.answer(greeting, reply_markup=get_keyboard(is_admin))


# Класс для хранения состояний
class CurrencyManagement(StatesGroup):
    waiting_for_currency_name = State()
    waiting_for_currency_rate = State()
    get_currency_name = State()


# Проверка является ли пользователь админом
def is_admin(chat_id):
    cursor.execute("SELECT id FROM admins WHERE id = %s", (chat_id,))
    return bool(cursor.fetchone())


# Команда /manage_currency
@router.message(Command('manage_currency'))

async def manage_currency(message: Message, state: FSMContext):
    if not is_admin(message.chat.id):
        await message.answer("Нет доступа к команде")
        return

    kb = [
        [types.KeyboardButton(text="Добавить валюту")],
        [types.KeyboardButton(text="Удалить валюту")],
        [types.KeyboardButton(text="Изменить курс валюты")]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb)
    await message.answer("Выберите действие:", reply_markup=keyboard)

# Обработчик команды добавления валюты
@router.message(F.text == "Добавить валюту")
async def add_currency_command(message: Message, state:FSMContext):
    if not is_admin(message.chat.id):
        await message.answer("Нет доступа к команде")
        return
    await message.answer("Введите название валюты:")
    await state.update_data(action="Добавить валюту")
    await state.set_state(CurrencyManagement.waiting_for_currency_name)


# Обработчик команды изменения валюты
@router.message(F.text == "Изменить курс валюты")
async def update_currency_command(message: Message, state:FSMContext):
    if not is_admin(message.chat.id):
        await message.answer("Нет доступа к команде")
        return
    await message.answer("Введите название валюты:")
    await state.update_data(action="Изменить курс валюты")
    await state.set_state(CurrencyManagement.waiting_for_currency_name)


# Обработчик команды удаления валюты
@router.message(F.text == "Удалить валюту")
async def delete_currency_command(message: Message, state:FSMContext):
    if not is_admin(message.chat.id):
        await message.answer("Нет доступа к команде")
        return
    await message.answer("Введите название валюты:")
    await state.update_data(action="Удалить валюту")
    await state.set_state(CurrencyManagement.waiting_for_currency_name)

# Команда /get_currencies (доступна всем пользователям)
@router.message(Command('get_currencies'))
async def get_currencies(message: Message):
    with conn.cursor() as cursor:
        cursor.execute("SELECT currency_name, rate FROM currencies")  # Извлекаем только нужные столбцы
        currencies = cursor.fetchall()

        if not currencies:
            await message.answer("Нет сохраненных валют.")
        else:
            response = "Сохраненные валюты:\n\n"
            for currency in currencies:
                currency_name, rate = currency  # Распаковываем кортеж
                response += f"{currency_name}: {rate} RUB\n"
            await message.answer(response)


# Получение названия валюты
@router.message(CurrencyManagement.waiting_for_currency_name)
async def get_currency_name(message: Message, state: FSMContext):
    currency_name = message.text.upper()
    data = await state.get_data()
    action = data.get('action')
    await state.update_data(currency_name=currency_name)


    if action == "Добавить валюту":
        with conn.cursor() as cursor:  # Используем контекстный менеджер
            cursor.execute(f"SELECT * FROM currencies WHERE currency_name = '{currency_name}'")
            if cursor.fetchone():
                await message.answer("Данная валюта уже существует")
                await state.clear()
                return
            await message.answer("Введите курс к рублю:")
            await state.set_state(CurrencyManagement.waiting_for_currency_rate)
    elif action == "Удалить валюту":
        with conn.cursor() as cursor:
            cursor.execute(f"DELETE FROM currencies WHERE currency_name = '{currency_name}'")
            conn.commit()
            await message.answer(f"Валюта: {currency_name} успешно удалена")
            await state.clear()
    elif action == "Изменить курс валюты":
        await message.answer("Введите новый курс к рублю:")
        await state.set_state(CurrencyManagement.waiting_for_currency_rate)



# Получение курса валюты (для добавления и изменения)
@router.message(CurrencyManagement.waiting_for_currency_rate)
async def get_currency_rate(message: Message, state: FSMContext):
    try:
        currency_rate = float(message.text)
    except ValueError:
        await message.answer("Неверный формат курса. Введите число.")
        return


    data = await state.get_data()
    action = data.get('action')
    currency_name = data.get('currency_name')

    with conn.cursor() as cursor:
        if action == "Добавить валюту":
            cursor.execute(f"INSERT INTO currencies (currency_name, rate) VALUES ('{currency_name}', {currency_rate});")
            conn.commit()
            await message.answer(f"Валюта: {currency_name} успешно добавлена")
        elif action == "Изменить курс валюты":
            cursor.execute(f"UPDATE currencies SET rate = {currency_rate} WHERE currency_name = '{currency_name}';")
            conn.commit()
            await message.answer(f"Курс валюты {currency_name} успешно изменен")

    await state.clear()


# Класс для хранения состояний при конвертации
class CurrencyConversion(StatesGroup):
    waiting_for_currency_name = State()
    waiting_for_amount = State()


# Команда /convert (доступна всем)
@router.message(Command('convert'))
async def convert_command(message: Message, state: FSMContext):
    await message.answer("Введите название валюты:")
    await state.set_state(CurrencyConversion.waiting_for_currency_name)


# Получение названия валюты для конвертации
@router.message(CurrencyConversion.waiting_for_currency_name)
async def get_currency_name_for_conversion(message: Message, state: FSMContext):
    currency_name = message.text.upper()
    await state.update_data(currency_name=currency_name)

    with conn.cursor() as cursor:
        cursor.execute("SELECT rate FROM currencies WHERE currency_name = %s", (currency_name,))
        currency_data = cursor.fetchone()

        if not currency_data:
            await message.answer("Валюта не найдена.")
            await state.clear()
        else:
            await state.update_data(currency_data=currency_data)  # Сохраняем курс
            await message.answer("Введите сумму:")
            await state.set_state(CurrencyConversion.waiting_for_amount)


# Получение суммы и расчет результата
@router.message(CurrencyConversion.waiting_for_amount)
async def get_amount_and_convert(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Неверный формат суммы. Введите число.")
        return

    data = await state.get_data()
    currency_name = data['currency_name']
    rate = data['currency_data'][0]  # Получаем курс из кортежа
    result = amount * float(rate)

    await message.answer(f"{amount} {currency_name} = {result:.2f} RUB")
    await state.clear()


user_command = [
    BotCommand(command="/start", description="Начать работу"),
    BotCommand(command="/convert", description="Конвертировать валюту"),
    BotCommand(command="/get_currencies", description="Получить список всех валют")]

admin_command = [
    BotCommand(command="/start", description="Начать работу"),
    BotCommand(command="/convert", description="Конвертировать валюту"),
    BotCommand(command="/manage_currency", description="Добавить валюту"),
    BotCommand(command="/get_currencies", description="Получить список всех валют")]

ADMIN_ID='1313775325'

async def main():
    bot_token = os.getenv('TOKEN')
    bot = Bot(token=bot_token)
    await bot.set_my_commands(user_command, scope=BotCommandScopeDefault())

    for admin in ADMIN_ID:
        await bot.set_my_commands(admin_command, scope=BotCommandScopeDefault(id=admin))

    dp = Dispatcher()

    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
    # dp.middleware.setup(LoggingMiddleware())

cursor.close()
conn.close()
