import psycopg2
from aiogram import Bot, Dispatcher, types, F
import os
import asyncio
from aiogram.filters.command import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BotCommand, BotCommandScope,Message, BotCommandScopeDefault, BotCommandScopeChat
import requests


# Подключение к базе данных PostgreSQL
conn = psycopg2.connect(dbname="bot_lab", user="maxim_dlia_bota",
                        password="shtangauer05", host="127.0.0.1")


bot_token = os.getenv('TOKEN')
router = Router()

class CurrencyInfo_Delete(StatesGroup):
    name = State()
    rate = State()
class CurrencyInfo_Change(StatesGroup):
    name = State()
    rate = State()
class CurrencyInfo(StatesGroup):
    name = State()
    rate = State()
class ConvertCurrency(StatesGroup):
    name = State()
    amount = State()


@router.message(Command('check_admin'))
async def check_admin(message: types.Message):
    chat_id = message.from_user.id
    response = requests.post('http://127.0.0.1:5002/check_admin', json={"chat_id": chat_id})
    result = response.json()["is_admin"]
    return result

# Старт
@router.message(Command('start'))                                                                               
@router.message(F.text.lower() == "Старт")
async def start_command(message: types.Message):
    await message.reply(
        "Привет! Я помогу в работе с конвертацией!"
        "\n /user - Пользователь"
        "\n /manage_currency - Администратор")

# Меню пользователя
@router.message(Command('user'))                                                                    
async def user_command(message: types.Message):
    kb = [
        [types.KeyboardButton(text="Конвертация")],
        [types.KeyboardButton(text="Список валют")],
        [types.KeyboardButton(text="Основное меню")]
        ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, )
    await message.answer("Рады приветстовать! Что сделаем на этот раз?", reply_markup=keyboard)

# Меню администратора
@router.message(Command('manage_currency'))                                                       
async def manage_currency_command(message: types.Message):
    if not check_admin(message):
        await message.reply("Нет доступа к команде")
    else:
        kb = [
            [types.KeyboardButton(text="Добавить валюту")],
            [types.KeyboardButton(text="Удалить валюту")],
            [types.KeyboardButton(text="Изменить курс валюты")],
            [types.KeyboardButton(text="Конвертация")],
            [types.KeyboardButton(text="Список валют")],
            [types.KeyboardButton(text="Основное меню")]
        ]
        keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, )
        await message.answer("Добро пожаловать! Что вы хотите?", reply_markup=keyboard)

def check_admin(message: types.Message) -> bool:
    cur = conn.cursor()
    id = message.from_user.id
    cur.execute("SELECT id FROM admins WHERE id = %s", (id,))
    result = cur.fetchone()
    cur.close()
    return bool(result)

user_commands = [
    types.BotCommand(command="/start", description="Начать работу"),
    types.BotCommand(command="/convert", description="Конвертировать валюту"),
    types.BotCommand(command="/get_currencies", description="Получить список всех валют"), ]

admin_commands = [
    types.BotCommand(command="/start", description="Начать работу"),
    types.BotCommand(command="/convert", description="Конвертировать валюту"),
    types.BotCommand(command="/manage_currency", description="Добавить валюту"),
    types.BotCommand(command="/get_currencies", description="Получить список всех валют"), ]        

# Конвертация
@router.message(Command('convert'))                                                                       
@router.message(F.text.lower() == "Конвертация")
async def process_convert_currency_command_1(message: types.Message, state: FSMContext):
    await message.reply("Выберите валюту для конвертации:")
    await state.set_state(ConvertCurrency.name)

# Конвертация
@router.message(ConvertCurrency.name)                                                                     
async def process_convert_currency_command_2(message: types.Message, state: FSMContext):
    currency_name = message.text

    await state.update_data(currency_name=currency_name)
    await state.set_state(ConvertCurrency.amount)
    await state.update_data(user_data=await state.get_data())
    await message.reply("Введите сумму для конвертации:")


@router.message(ConvertCurrency.amount)
async def process_convert_currency_command3(message: types.Message, state: FSMContext):
    amount = message.text

    data = await state.get_data()
    currency_name = data.get('currency_name')

    response = requests.get('http://127.0.0.1:5002/convert',
                            json={'currency_name': currency_name, 'amount': amount})

    if response.status_code == 200:
        response_data = response.json()
        if 'converted_amount' in response_data:
            converted_amount = response_data['converted_amount']
            await message.reply(f"{amount} {currency_name} равно {converted_amount} рублей")
        else:
            await message.reply("Не удалось получить конвертированную сумму. Пожалуйста, попробуйте снова.")
    else:
        await message.reply("Произошла ошибка при конвертации. Пожалуйста, попробуйте снова.")
        await state.clear()


# Показ списка валют
@router.message(Command('get_currencies'))                                                         
@router.message(F.text.lower() == "список валют")
async def process_show_currencies_command_1(message: types.Message, state: FSMContext):
    response = requests.get('http://127.0.0.1:5002/currencies')
    if response.status_code == 200:
        actual_currencies = response.json().get('currencies', [])
        if actual_currencies:
            currencies_info = "\n".join([f"{currency[0]}: {currency[1]} к рублю" for currency in actual_currencies])
            await message.reply(f"Сохраненные валюты:\n{currencies_info}")
        else:
            await message.reply("Нет сохраненных валют")
    else:
        await message.reply("Произошла ошибка при получении списка валют")



# Добавление валюты
@router.message(F.text.lower() == "добавить валюту")
async def button_1_1(message: types.Message, state: FSMContext):
    if not check_admin:
        await message.reply("Нет доступа к команде")
    else:
        await state.set_state(CurrencyInfo.name)
        await message.reply("Введите название валюты")

# Добавление валюты
@router.message(CurrencyInfo.name)
async def button_1_2(message: types.Message, state: FSMContext):
    currency_name = message.text
    await state.update_data(currency_name=currency_name)
    await state.set_state(CurrencyInfo.rate)
    await message.reply("Введите курс валюты к рублю")

# Добавление валюты
@router.message(CurrencyInfo.rate)
async def button_1_3(message: types.Message, state: FSMContext):
    currency_name_from_last_step = await state.get_data()
    currency_name = currency_name_from_last_step.get('currency_name')
    rate = message.text
    response = requests.post('http://127.0.0.1:5001/load',
                             json={"currency_name":currency_name,"rate":rate})
    if response.status_code == 200:
        await message.reply(f"Валюта: {currency_name} добавлена")
    else:
        await message.reply(f"error: Валюта уже существует в базе данных")
    await state.clear()

# Удаление валюты
@router.message(F.text.lower() == "удалить валюту")
async def button_2_1(message: types.Message, state: FSMContext):
    if not check_admin:
        await message.reply("Нет доступа к команде")
    else:
        await state.set_state(CurrencyInfo_Delete.name)
        await message.reply("Введите название валюты, которую хотите удалить")

# Удаление валюты
@router.message(CurrencyInfo_Delete.name)
async def button_2_2(message: types.Message, state: FSMContext):
    currency_name = message.text
    response = requests.post('http://127.0.0.1:5001/delete',
                               json={"currency_name": currency_name})
    if response.status_code == 200:
        await message.reply(f"Валюта {currency_name} удалена из списка")
        await state.clear()
    else:
        await message.reply("Такая валюта отсутствует в списке")


# Изменение курса валюты
@router.message(F.text.lower() == "изменить курс валюты")
async def button_3_1(message: types.Message, state: FSMContext):
    if not check_admin:
        await message.reply("Нет доступа к команде")
    else:
        await state.set_state(CurrencyInfo_Change.name)
        await message.reply("Введите название валюты, которую хотите изменить")


# Изменение курса валюты
@router.message(CurrencyInfo_Change.name)
async def button_3_2(message: types.Message, state: FSMContext):
    currency_name = message.text
    await state.update_data(currency_name=currency_name)
    await state.set_state(CurrencyInfo_Change.rate)
    await message.reply("Введите новый курс валюты к рублю")

# Изменение курса валюты
@router.message(CurrencyInfo_Change.rate)
async def button_3_3(message: types.Message, state: FSMContext):
    currency_name_from_last_step = await state.get_data()
    currency_name = currency_name_from_last_step.get('currency_name')
    currency_rate = message.text
    response = requests.post('http://127.0.0.1:5001/update_currency',
                             json={"currency_name": currency_name, "rate": currency_rate})
    if response.status_code == 200:
        await message.reply(f"Сохранено: {currency_name} - {currency_rate} к рублю.")
    else:
        await message.reply("Не удалось обновить курс валюты.")
    await state.clear()

cur = conn.cursor()
cur.execute("SELECT id FROM admins", (id,))
ADMIN_ID = cur.fetchone()
cur.close()


async def setup_bot_commands(bot):
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    for admin in ADMIN_ID:
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=str(admin)))


async def main():
    bot = Bot(token=bot_token)
    await setup_bot_commands(bot)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
# cur.close()
# conn.close()


